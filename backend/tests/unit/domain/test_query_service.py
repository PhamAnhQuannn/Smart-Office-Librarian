from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.services.query_service import QueryRequest, QueryService
from app.domain.services.index_safety_service import IndexSafetyMismatchError, IndexSafetyService


class _FakeThresholdService:
    def __init__(self, value: float) -> None:
        self.value = value
        self.calls: list[tuple[str, int]] = []

    def get_threshold(self, *, namespace: str, index_version: int) -> float:
        self.calls.append((namespace, index_version))
        return self.value


class _FakePipeline:
    def __init__(self) -> None:
        self.last_kwargs = None

    def run(self, **kwargs):
        self.last_kwargs = kwargs
        return {"mode": "ok", "threshold": kwargs["threshold"]}


class _FakeIndexMetadataProvider:
    def __init__(self, *, model_id: str, index_version: int) -> None:
        self.model_id = model_id
        self.index_version = index_version
        self.calls: list[str] = []

    def get_index_metadata(self, *, namespace: str):
        self.calls.append(namespace)
        return {
            "model_id": self.model_id,
            "index_version": self.index_version,
        }


def test_query_service_fetches_threshold_and_passes_to_pipeline() -> None:
    threshold_service = _FakeThresholdService(value=0.65)
    pipeline = _FakePipeline()
    service = QueryService(pipeline=pipeline, threshold_service=threshold_service)

    request = QueryRequest(
        query_text="How does refusal work?",
        namespace="dev",
        index_version=1,
        rbac_filter={"visibility": "private"},
        retrieval_only_mode=False,
    )

    result = service.execute(request)

    assert threshold_service.calls == [("dev", 1)]
    assert pipeline.last_kwargs is not None
    assert pipeline.last_kwargs["threshold"] == 0.65
    assert pipeline.last_kwargs["query_text"] == "How does refusal work?"
    assert pipeline.last_kwargs["namespace"] == "dev"
    assert pipeline.last_kwargs["rbac_filter"] == {"visibility": "private"}
    assert result == {"mode": "ok", "threshold": 0.65}


def test_query_service_passes_retrieval_only_mode_through() -> None:
    threshold_service = _FakeThresholdService(value=0.7)
    pipeline = _FakePipeline()
    service = QueryService(pipeline=pipeline, threshold_service=threshold_service)

    request = QueryRequest(
        query_text="budget exceeded behavior",
        namespace="staging",
        index_version=1,
        retrieval_only_mode=True,
    )

    service.execute(request)

    assert pipeline.last_kwargs is not None
    assert pipeline.last_kwargs["retrieval_only_mode"] is True


def test_query_service_propagates_pipeline_errors() -> None:
    threshold_service = _FakeThresholdService(value=0.65)

    class _FailingPipeline:
        def run(self, **kwargs):
            raise RuntimeError("pipeline boom")

    service = QueryService(pipeline=_FailingPipeline(), threshold_service=threshold_service)

    request = QueryRequest(
        query_text="failure case",
        namespace="dev",
        index_version=1,
    )

    with pytest.raises(RuntimeError, match="pipeline boom"):
        service.execute(request)


def test_query_service_validates_index_safety_when_services_provided() -> None:
    threshold_service = _FakeThresholdService(value=0.65)
    pipeline = _FakePipeline()
    index_safety_service = IndexSafetyService()
    metadata_provider = _FakeIndexMetadataProvider(
        model_id="text-embedding-3-small-v1",
        index_version=1,
    )
    service = QueryService(
        pipeline=pipeline,
        threshold_service=threshold_service,
        index_safety_service=index_safety_service,
        index_metadata_provider=metadata_provider,
    )

    service.execute(
        QueryRequest(
            query_text="safety check",
            namespace="dev",
            index_version=1,
            model_id="text-embedding-3-small-v1",
        )
    )

    assert metadata_provider.calls == ["dev"]
    assert threshold_service.calls == [("dev", 1)]


def test_query_service_raises_canonical_model_mismatch_error() -> None:
    threshold_service = _FakeThresholdService(value=0.65)
    pipeline = _FakePipeline()
    service = QueryService(
        pipeline=pipeline,
        threshold_service=threshold_service,
        index_safety_service=IndexSafetyService(),
        index_metadata_provider=_FakeIndexMetadataProvider(
            model_id="text-embedding-3-small-v1",
            index_version=1,
        ),
    )

    with pytest.raises(IndexSafetyMismatchError) as exc:
        service.execute(
            QueryRequest(
                query_text="mismatch",
                namespace="dev",
                index_version=1,
                model_id="text-embedding-3-large-v1",
            )
        )

    payload = exc.value.to_error_payload()
    assert exc.value.error_code == "EMBEDDING_MODEL_MISMATCH"
    assert payload["error_code"] == "EMBEDDING_MODEL_MISMATCH"
    assert payload["details"]["expected_model_id"] == "text-embedding-3-small-v1"
    assert payload["details"]["received_model_id"] == "text-embedding-3-large-v1"
    # Mismatch must short-circuit before threshold/pipeline execution.
    assert threshold_service.calls == []
