"use client";

import { useCallback, useEffect, useState } from "react";
import { Database, RefreshCw, Trash2, X } from "lucide-react";
import { buildApiUrl } from "../../lib/api-client";
import { ADMIN_SOURCES_ENDPOINT, INGEST_ENDPOINT } from "../../lib/constants";
import { useToast } from "../../context/toast-context";
import { formatDate } from "../../lib/utils";

interface Source {
  id: string;
  name?: string;
  file_path: string;
  source_url: string | null;
  namespace: string;
  chunk_count: number;
  created_at: string;
  status?: "healthy" | "indexing" | "error";
  type?: string;
}

interface SourceListProps {
  authToken?: string;
}

interface DeleteDialogProps {
  source: Source;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
}

function DeleteDialog({ source, onConfirm, onCancel, loading }: DeleteDialogProps) {
  const displayName = source.name ?? source.file_path.split("/").at(-1) ?? source.file_path;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backdropFilter: "blur(4px)", background: "rgba(15,23,42,0.4)" }}
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl space-y-6">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs font-black text-rose-500 uppercase tracking-widest">Confirm deletion</p>
            <p className="font-black text-slate-900 text-lg">Delete &ldquo;{displayName}&rdquo;?</p>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-all"
          >
            <X size={20} />
          </button>
        </div>
        <p className="text-sm text-slate-500">
          This will permanently remove the source and all&nbsp;
          <strong>{source.chunk_count}</strong> indexed chunks. This action cannot be undone.
        </p>
        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="px-5 py-2.5 border border-slate-200 rounded-xl font-bold text-slate-500 hover:bg-slate-50 transition-all"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className="px-5 py-2.5 bg-rose-500 text-white rounded-xl font-bold hover:bg-rose-600 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: Source["status"] }) {
  if (status === "indexing")
    return <span className="inline-block w-2.5 h-2.5 rounded-full bg-blue-400 animate-pulse" title="Indexing" />;
  if (status === "error")
    return <span className="inline-block w-2.5 h-2.5 rounded-full bg-rose-500" title="Error" />;
  return <span className="inline-block w-2.5 h-2.5 rounded-full bg-green-400" title="Healthy" />;
}

export function SourceList({ authToken }: SourceListProps): JSX.Element {
  const { addToast } = useToast();
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [reindexingId, setReindexingId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Source | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchSources = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(buildApiUrl(ADMIN_SOURCES_ENDPOINT), {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { items: Source[] };
      setSources(data.items ?? []);
    } catch (err: unknown) {
      addToast("Load failed", err instanceof Error ? err.message : "Could not load sources", "error");
    } finally {
      setLoading(false);
    }
  }, [authToken, addToast]);

  useEffect(() => { void fetchSources(); }, [fetchSources]);

  async function handleReindex(source: Source): Promise<void> {
    setReindexingId(source.id);
    try {
      const res = await fetch(buildApiUrl(INGEST_ENDPOINT), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({
          source_url: source.source_url ?? source.file_path,
          strategy: "incremental",
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const name = source.name ?? source.file_path.split("/").at(-1) ?? source.file_path;
      addToast("Queued", `Re-index job queued for ${name}`, "success");
    } catch (err: unknown) {
      addToast("Failed", err instanceof Error ? err.message : "Re-index failed", "error");
    } finally {
      setReindexingId(null);
    }
  }

  async function confirmDelete(): Promise<void> {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const res = await fetch(buildApiUrl(`${ADMIN_SOURCES_ENDPOINT}/${deleteTarget.id}`), {
        method: "DELETE",
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSources((prev) => prev.filter((s) => s.id !== deleteTarget.id));
      const name = deleteTarget.name ?? deleteTarget.file_path.split("/").at(-1) ?? deleteTarget.file_path;
      addToast("Deleted", `${name} removed`, "success");
      setDeleteTarget(null);
    } catch (err: unknown) {
      addToast("Delete failed", err instanceof Error ? err.message : "Unknown error", "error");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-2xl border border-slate-100 p-6 space-y-3 animate-pulse">
            <div className="h-8 w-8 bg-slate-100 rounded-xl" />
            <div className="h-4 w-32 bg-slate-100 rounded" />
            <div className="h-3 w-20 bg-slate-100 rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (!sources.length) {
    return (
      <div className="text-center py-16 text-slate-400">
        <Database size={32} className="mx-auto mb-3 opacity-40" />
        <p className="font-bold">No sources ingested yet</p>
        <p className="text-sm">Use the Ingest tab to add your first source.</p>
      </div>
    );
  }

  return (
    <>
      {deleteTarget && (
        <DeleteDialog
          source={deleteTarget}
          onConfirm={() => void confirmDelete()}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {sources.map((s) => {
          const displayName = s.name ?? s.file_path.split("/").at(-1) ?? s.file_path;
          return (
            <div
              key={s.id}
              className="bg-white rounded-2xl border border-slate-100 p-6 space-y-4 hover:border-slate-200 transition-all"
            >
              <div className="flex items-start justify-between">
                <div className="p-2.5 bg-slate-100 rounded-xl">
                  <Database size={20} className="text-slate-500" />
                </div>
                <StatusDot status={s.status ?? "healthy"} />
              </div>

              <div>
                <p className="font-black text-slate-900 truncate" title={displayName}>{displayName}</p>
                {s.type && (
                  <span className="mt-1 inline-block text-[10px] font-black uppercase tracking-wider bg-teal-50 text-teal-600 px-2 py-0.5 rounded">
                    {s.type}
                  </span>
                )}
              </div>

              <p className="text-xs text-slate-400 font-bold">{formatDate(s.created_at)}</p>

              <div className="flex gap-2 pt-2 border-t border-slate-50">
                <button
                  type="button"
                  onClick={() => void handleReindex(s)}
                  disabled={reindexingId === s.id}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50 transition-all disabled:opacity-50"
                >
                  <RefreshCw size={12} className={reindexingId === s.id ? "animate-spin" : ""} />
                  Re-index
                </button>
                <button
                  type="button"
                  onClick={() => setDeleteTarget(s)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-rose-500 border border-rose-100 rounded-lg hover:bg-rose-50 transition-all"
                >
                  <Trash2 size={12} />
                  Delete
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

