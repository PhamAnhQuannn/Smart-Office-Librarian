"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Plus, Trash2, RefreshCw, ExternalLink, CheckCircle2, ChevronDown, ChevronUp, Github } from "lucide-react";
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

// ── Repo grouping ────────────────────────────────────────────────────────────

interface RepoGroup {
  repo: string;
  files: WorkspaceSource[];
  baseUrl: string | null;
  earliestDate: string | null;
}

function groupByRepo(sources: WorkspaceSource[]): RepoGroup[] {
  const map = new Map<string, RepoGroup>();
  for (const s of sources) {
    const existing = map.get(s.repo);
    const date = s.created_at ?? null;
    if (!existing) {
      const baseUrl = s.source_url
        ? s.source_url.replace(/\/blob\/[^/]+\/.*$/, "").replace(/\/tree\/[^/]+\/.*$/, "")
        : null;
      map.set(s.repo, { repo: s.repo, files: [s], baseUrl, earliestDate: date });
    } else {
      existing.files.push(s);
      // Keep earliest (oldest) date as "added"
      if (date && (!existing.earliestDate || date < existing.earliestDate)) {
        existing.earliestDate = date;
      }
    }
  }
  return Array.from(map.values());
}

function friendlyDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch {
    return "—";
  }
}

// ── Main component ───────────────────────────────────────────────────────────

export default function SourcesPage(): JSX.Element {
  const router = useRouter();
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);
  const [sources, setSources] = useState<WorkspaceSource[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Expanded repos (showing individual files)
  const [expandedRepos, setExpandedRepos] = useState<Set<string>>(new Set());

  // Add source modal state
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

  async function handleDeleteRepo(repoName: string): Promise<void> {
    const token = getToken();
    if (!token) return;
    const group = groupByRepo(sources).find((g) => g.repo === repoName);
    if (!group) return;
    if (!confirm(`Remove "${repoName}" and all ${group.files.length} indexed file(s) from your workspace?`)) return;
    try {
      await Promise.all(group.files.map((f) => deleteWorkspaceSource(f.id, token)));
      setSources((prev) => prev.filter((s) => s.repo !== repoName));
      setTotal((t) => t - group.files.length);
    } catch {
      alert("Failed to remove source.");
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
      setIngestMsg(`Sync queued: job ${result.job_id.slice(0, 8)}…`);
      setRepo("");
      setBranch("main");
      setTimeout(() => { setShowAdd(false); setIngestMsg(""); void loadData(); }, 2000);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setIngestMsg(err.message);
      } else {
        setIngestMsg("Failed to start sync.");
      }
    } finally {
      setIngesting(false);
    }
  }

  function toggleExpand(repoName: string): void {
    setExpandedRepos((prev) => {
      const next = new Set(prev);
      if (next.has(repoName)) next.delete(repoName);
      else next.add(repoName);
      return next;
    });
  }

  if (loading) {
    return <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">Loading…</div>;
  }

  const groups = groupByRepo(sources);

  return (
    <div className="max-w-3xl mx-auto space-y-8 py-4 px-4 md:px-0">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Sources</h1>
          <p className="text-sm text-slate-500 mt-1">
            GitHub repositories connected to your workspace.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => void loadData()}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
            title="Refresh"
          >
            <RefreshCw size={16} />
          </button>
          <button
            type="button"
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-4 py-2 bg-teal-500 text-white rounded-xl font-semibold text-sm hover:bg-teal-600 transition-colors"
          >
            <Plus size={16} />
            Add Repository
          </button>
        </div>
      </div>

      {/* Quota bar */}
      {workspace && (
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
          <div className="flex justify-between text-xs text-slate-500 font-semibold mb-2">
            <span>Repositories indexed</span>
            <span>{groups.length} repos · {workspace.usage.sources} / {workspace.limits.max_sources} files limit</span>
          </div>
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-teal-500 rounded-full transition-all"
              style={{ width: `${Math.min(100, (workspace.usage.sources / workspace.limits.max_sources) * 100)}%` }}
            />
          </div>
        </div>
      )}

      {error && (
        <p className="text-sm text-rose-500 bg-rose-50 border border-rose-200 rounded-xl p-3" role="alert">{error}</p>
      )}

      {/* Repo list */}
      {groups.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center gap-4">
          <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center">
            <Github size={28} className="text-slate-400" />
          </div>
          <div>
            <p className="text-slate-700 font-semibold">No repositories connected yet</p>
            <p className="text-slate-400 text-sm mt-1 max-w-xs">
              Add a GitHub repository to start building your knowledge base.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-teal-500 text-white rounded-xl font-semibold text-sm hover:bg-teal-600 transition-colors"
          >
            <Plus size={16} /> Add your first repository
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {groups.map((g) => {
            const isExpanded = expandedRepos.has(g.repo);
            return (
              <div key={g.repo} className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                {/* Repo header row */}
                <div className="flex items-center gap-3 px-5 py-4">
                  <div className="w-9 h-9 bg-slate-100 rounded-xl flex items-center justify-center shrink-0">
                    <Github size={16} className="text-slate-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold text-slate-900 truncate">{g.repo}</p>
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-teal-50 text-teal-700 rounded-full text-xs font-semibold">
                        <CheckCircle2 size={10} />
                        Indexed
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {g.files.length} file{g.files.length !== 1 ? "s" : ""} · Added {friendlyDate(g.earliestDate)}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {g.baseUrl && (
                      <a
                        href={g.baseUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-teal-600 hover:bg-teal-50 transition-colors"
                        title="View on GitHub"
                      >
                        <ExternalLink size={14} />
                      </a>
                    )}
                    <Link
                      href="/sync"
                      className="p-1.5 rounded-lg text-slate-400 hover:text-teal-600 hover:bg-teal-50 transition-colors"
                      title="Sync this repository"
                    >
                      <RefreshCw size={14} />
                    </Link>
                    <button
                      type="button"
                      onClick={() => void handleDeleteRepo(g.repo)}
                      className="p-1.5 rounded-lg text-slate-300 hover:text-rose-500 hover:bg-rose-50 transition-colors"
                      title="Remove repository"
                    >
                      <Trash2 size={14} />
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleExpand(g.repo)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                      title={isExpanded ? "Hide files" : "Show files"}
                    >
                      {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </button>
                  </div>
                </div>

                {/* File list (expandable) */}
                {isExpanded && (
                  <div className="border-t border-slate-100 divide-y divide-slate-50">
                    {g.files.map((f) => (
                      <div key={f.id} className="flex items-center gap-3 px-5 py-2.5">
                        <p className="flex-1 text-xs font-mono text-slate-500 truncate">{f.file_path}</p>
                        {f.source_url && (
                          <a
                            href={f.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="shrink-0 text-slate-300 hover:text-teal-500 transition-colors"
                            title="View file on GitHub"
                          >
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}

          {total > sources.length && (
            <p className="text-xs text-slate-400 text-center pt-1">
              Showing {sources.length} of {total} indexed files
            </p>
          )}
        </div>
      )}

      {/* Add source modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md space-y-6 border border-slate-200">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Add GitHub Repository</h2>
              <p className="text-sm text-slate-500 mt-1">
                Embedlyzer will index all supported files and make them queryable.
                To manage sync strategy, use{" "}
                <Link href="/sync" className="text-teal-600 hover:underline font-medium" onClick={() => setShowAdd(false)}>
                  Sync
                </Link>.
              </p>
            </div>
            <form onSubmit={(e) => void handleIngest(e)} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Repository
                </label>
                <input
                  type="text"
                  value={repo}
                  onChange={(e) => setRepo(e.target.value)}
                  placeholder="owner/repo-name or https://github.com/owner/repo"
                  required
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-teal-500 outline-none transition-all text-sm"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Branch
                </label>
                <input
                  type="text"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  placeholder="main"
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-teal-500 outline-none transition-all text-sm"
                />
              </div>
              {ingestMsg && (
                <p className={`text-sm text-center rounded-xl px-3 py-2 ${ingestMsg.startsWith("Sync") ? "bg-teal-50 text-teal-700" : "bg-rose-50 text-rose-600"}`}>
                  {ingestMsg}
                </p>
              )}
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowAdd(false); setIngestMsg(""); }}
                  className="flex-1 py-3 rounded-xl border border-slate-200 text-slate-600 font-semibold text-sm hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={ingesting}
                  className="flex-1 py-3 bg-teal-500 text-white rounded-xl font-bold text-sm hover:bg-teal-600 transition-colors disabled:opacity-60"
                >
                  {ingesting ? "Queuing…" : "Start Sync"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
