#!/usr/bin/env python
"""Pinecone index migration utility.

Copies vectors from one Pinecone index/namespace to another, optionally
re-embedding chunks from the database with the current embedding model.
Useful when the embedding model changes (e.g. text-embedding-3-small →
text-embedding-3-large) or when restructuring namespace layout.

Usage (from backend/):
    python scripts/migrate_index.py \\
        --src-index embedlyzer-v1 \\
        --dst-index embedlyzer-v2 \\
        --src-namespace dev \\
        --dst-namespace dev \\
        [--re-embed]    # re-embed chunks from DB instead of copying vectors
        [--dry-run]     # print plan without making changes
        [--batch-size N]
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

# Ensure backend package is importable when executed directly.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))


def _build_pinecone_client(api_key: str) -> Any:
    try:
        from pinecone import Pinecone  # type: ignore[import]
        return Pinecone(api_key=api_key)
    except ImportError as exc:
        raise SystemExit("pinecone-client is not installed. Run: pip install pinecone-client") from exc


def _copy_vectors(
    *,
    src_index: Any,
    dst_index: Any,
    src_namespace: str,
    dst_namespace: str,
    batch_size: int,
    dry_run: bool,
) -> int:
    """Copy all vectors from src to dst, returning the total count."""
    total = 0
    cursor: str | None = None

    while True:
        kwargs: dict[str, Any] = {"namespace": src_namespace, "limit": batch_size}
        if cursor:
            kwargs["pagination_token"] = cursor

        result = src_index.list(**kwargs)
        ids: list[str] = result.get("vectors", [])

        if not ids:
            break

        # Fetch full vectors including metadata.
        fetch_result = src_index.fetch(ids=ids, namespace=src_namespace)
        vectors = list(fetch_result.get("vectors", {}).values())

        if not dry_run:
            upsert_payload = [
                {
                    "id": v["id"],
                    "values": v["values"],
                    "metadata": v.get("metadata", {}),
                }
                for v in vectors
            ]
            dst_index.upsert(vectors=upsert_payload, namespace=dst_namespace)

        total += len(ids)
        print(f"  {'[dry-run] ' if dry_run else ''}copied {total} vectors …")

        cursor = result.get("pagination", {}).get("next")
        if not cursor:
            break

    return total


def _re_embed_from_db(
    *,
    dst_index: Any,
    dst_namespace: str,
    batch_size: int,
    dry_run: bool,
) -> int:
    """Re-embed all chunks from the database and upsert into dst_index."""
    from app.core.config import get_settings
    from app.db.models import ChunkModel
    from app.db.session import get_engine
    from sqlalchemy.orm import Session

    settings = get_settings()
    engine = get_engine()

    try:
        import openai  # type: ignore[import]
    except ImportError as exc:
        raise SystemExit("openai package is not installed. Run: pip install openai") from exc

    client = openai.OpenAI(api_key=settings.openai_api_key)
    total = 0

    with Session(engine) as session:
        offset = 0
        while True:
            chunks = (
                session.query(ChunkModel)
                .offset(offset)
                .limit(batch_size)
                .all()
            )
            if not chunks:
                break

            texts = [c.text for c in chunks]
            resp = client.embeddings.create(
                model=settings.embedding_model,
                input=texts,
            )
            upsert_payload = [
                {
                    "id": c.vector_id,
                    "values": emb.embedding,
                    "metadata": {
                        "source_id": c.source_id,
                        "file_path": "",  # enriched downstream
                        "start_line": c.start_line or 0,
                        "end_line": c.end_line or 0,
                        "namespace": dst_namespace,
                    },
                }
                for c, emb in zip(chunks, resp.data)
            ]

            if not dry_run:
                dst_index.upsert(vectors=upsert_payload, namespace=dst_namespace)

            total += len(chunks)
            print(f"  {'[dry-run] ' if dry_run else ''}re-embedded {total} chunks …")
            offset += batch_size

    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Pinecone index vectors.")
    parser.add_argument("--src-index", required=True, help="Source Pinecone index name.")
    parser.add_argument("--dst-index", required=True, help="Destination Pinecone index name.")
    parser.add_argument("--src-namespace", default="dev", help="Source namespace (default: dev).")
    parser.add_argument("--dst-namespace", default="dev", help="Destination namespace (default: dev).")
    parser.add_argument("--re-embed", action="store_true", help="Re-embed chunks from DB instead of copying vectors.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without making changes.")
    parser.add_argument("--batch-size", type=int, default=100, help="Vectors per batch (default: 100).")
    args = parser.parse_args()

    from app.core.config import get_settings
    settings = get_settings()

    pc = _build_pinecone_client(settings.pinecone_api_key)

    print(f"Migration plan:")
    print(f"  Source:      {args.src_index} / {args.src_namespace}")
    print(f"  Destination: {args.dst_index} / {args.dst_namespace}")
    print(f"  Strategy:    {'re-embed from DB' if args.re_embed else 'copy vectors'}")
    print(f"  Dry run:     {args.dry_run}")
    print()

    if args.re_embed:
        dst_index = pc.Index(args.dst_index)
        count = _re_embed_from_db(
            dst_index=dst_index,
            dst_namespace=args.dst_namespace,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
    else:
        src_index = pc.Index(args.src_index)
        dst_index = pc.Index(args.dst_index)
        count = _copy_vectors(
            src_index=src_index,
            dst_index=dst_index,
            src_namespace=args.src_namespace,
            dst_namespace=args.dst_namespace,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )

    action = "Would migrate" if args.dry_run else "Migrated"
    print(f"\n{action} {count} vectors.")


if __name__ == "__main__":
    main()
