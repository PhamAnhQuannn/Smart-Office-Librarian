"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Database, Plus, Trash2, RefreshCw, ExternalLink } from "lucide-react";
import {
  getWorkspaceMe,
  getWorkspaceSources,
  deleteWorkspaceSource,
  postIngest,
  type WorkspaceInfo,
  type WorkspaceSource,
  ApiClientError,
} from "../../../lib/api-client";
import { getToken } from "../../../lib/auth";

export default function SourcesPage(): JSX.Element {
  const router = useRouter();
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);
  const [sources, setSources] = useState<WorkspaceSource[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Ingest modal state
  const [showAdd, setShowAdd] = useState(false);
  const [repo, setRepo] = useState("");
  const [branch, setBranch] = useState("main");
  const [ingesting, setIngesting] = useState(false);
  const [ingestMsg, setIngestMsg] = useState("");

  async function loadData(): Promise<void> {
    const token = getToken();
    if (!token) { router.replace("/login"); return; }

    try {
      const [ws, { sources: s, total: t }] = await Promise.all([
        getWorkspaceMe(token),
        getWorkspaceSources(token),
      ]);
      setWorkspace(ws);
      setSources(s);
      setTotal(t);
      setError("");
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 401) {
        router.replace("/login");
      } else {
        setError("Failed to load workspace data.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadData(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleDelete(sourceId: string): Promise<void> {
    const token = getToken();
    if (!token) return;
    if (!confirm("Remove this source from your workspace?")) return;
    try {
      await deleteWorkspaceSource(sourceId, token);
      setSources((prev) => prev.filter((s) => s.id !== sourceId));
      setTotal((t) => t - 1);
    } catch {
      alert("Failed to delete source.");
    }
  }

  async function handleIngest(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    const token = getToken();
    if (!token) return;
    setIngesting(true);
    setIngestMsg("");
    try {
      const result = await postIngest(repo.trim(), branch.trim() || "main", token);
      setIngestMsg(`Job queued: ${result.job_id}`);
      setRepo("");
      setBranch("main");
      setTimeout(() => { setShowAdd(false); setIngestMsg(""); void loadData(); }, 2000);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setIngestMsg(err.message);
      } else {
        setIngestMsg("Failed to start ingestion.");
      }
    } finally {
      setIngesting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 md:p-10 space-y-8 max-w-4xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-teal-500/10 rounded-xl flex items-center justify-center">
            <Database size={20} className="text-teal-400" />
          </div>
          <div>
            <h1 className="text-xl font-black text-white">My Sources</h1>
            {workspace && (
              <p className="text-xs text-slate-500">
                {workspace.usage.sources} / {workspace.limits.max_sources} sources used
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadData()}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={16} />
          </button>
          <button
            type="button"
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2 bg-teal-500 text-white rounded-lg font-semibold text-sm hover:bg-teal-600 transition-colors"
          >
            <Plus size={16} />
            Add Source
          </button>
        </div>
      </div>

      {/* Quota bar */}
      {workspace && (
        <div className="bg-slate-800/50 rounded-xl p-4 border border-white/5">
          <div className="flex justify-between text-xs text-slate-400 mb-2">
            <span>Sources</span>
            <span>{workspace.usage.sources} / {workspace.limits.max_sources}</span>
          </div>
          <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-teal-500 rounded-full transition-all"
              style={{ width: `${Math.min(100, (workspace.usage.sources / workspace.limits.max_sources) * 100)}%` }}
            />
          </div>
        </div>
      )}

      {error && (
        <p className="text-sm text-rose-400 text-center" role="alert">{error}</p>
      )}

      {/* Sources list */}
      {sources.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center gap-4">
          <div className="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center">
            <Database size={28} className="text-slate-600" />
          </div>
          <p className="text-slate-400 font-medium">No sources indexed yet</p>
          <p className="text-slate-600 text-sm max-w-xs">
            Add a GitHub repository to start building your knowledge base.
          </p>
          <button
            type="button"
            onClick={() => setShowAdd(true)}
            className="mt-2 flex items-center gap-2 px-5 py-2.5 bg-teal-500 text-white rounded-lg font-semibold text-sm hover:bg-teal-600 transition-colors"
          >
            <Plus size={16} /> Add your first source
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {sources.map((source) => (
            <div
              key={source.id}
              className="flex items-center gap-4 bg-slate-800/50 rounded-xl p-4 border border-white/5 group"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-white truncate">{source.repo}</p>
                <p className="text-xs text-slate-500 truncate">{source.file_path}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {source.source_url && (
                  <a
                    href={source.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 text-slate-600 hover:text-teal-400 transition-colors"
                    title="View on GitHub"
                  >
                    <ExternalLink size={14} />
                  </a>
                )}
                <button
                  type="button"
                  onClick={() => void handleDelete(source.id)}
                  className="p-1.5 text-slate-600 hover:text-rose-400 transition-colors opacity-0 group-hover:opacity-100"
                  title="Remove source"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
          {total > sources.length && (
            <p className="text-xs text-slate-600 text-center pt-2">
              Showing {sources.length} of {total} sources
            </p>
          )}
        </div>
      )}

      {/* Add source modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 rounded-2xl shadow-2xl p-8 w-full max-w-md space-y-6 border border-white/10">
            <h2 className="text-lg font-black text-white">Add GitHub Repository</h2>
            <form onSubmit={(e) => void handleIngest(e)} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                  Repository
                </label>
                <input
                  type="text"
                  value={repo}
                  onChange={(e) => setRepo(e.target.value)}
                  placeholder="owner/repo-name"
                  required
                  className="w-full px-4 py-3 rounded-lg bg-slate-800 border border-white/10 text-white placeholder-slate-600 focus:ring-2 focus:ring-teal-500 outline-none transition-all text-sm"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                  Branch
                </label>
                <input
                  type="text"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  placeholder="main"
                  className="w-full px-4 py-3 rounded-lg bg-slate-800 border border-white/10 text-white placeholder-slate-600 focus:ring-2 focus:ring-teal-500 outline-none transition-all text-sm"
                />
              </div>
              {ingestMsg && (
                <p className={`text-sm text-center ${ingestMsg.startsWith("Job") ? "text-teal-400" : "text-rose-400"}`}>
                  {ingestMsg}
                </p>
              )}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowAdd(false); setIngestMsg(""); }}
                  className="flex-1 py-3 rounded-lg border border-white/10 text-slate-400 font-semibold text-sm hover:bg-white/5 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={ingesting}
                  className="flex-1 py-3 bg-teal-500 text-white rounded-lg font-bold text-sm hover:bg-teal-600 transition-colors disabled:opacity-60"
                >
                  {ingesting ? "Queuing…" : "Start Ingestion"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
