"use client";

import { useState } from "react";
import { Github, RefreshCw, CheckCircle2, XCircle, Clock, AlertCircle, BookOpen, FileText } from "lucide-react";
import { getToken } from "../../../lib/auth";
import { useRouter } from "next/navigation";
import { buildApiUrl } from "../../../lib/api-client";
import { useAuth } from "../../../hooks/useAuth";
import { useToast } from "../../../context/toast-context";
import { Badge } from "../../../components/ui/badge";
import type { BadgeProps } from "../../../components/ui/badge";
import { formatDate } from "../../../lib/utils";
import { useEffect, useCallback } from "react";
import { INGEST_ENDPOINT, ADMIN_INGEST_RUNS_ENDPOINT } from "../../../lib/constants";

type Strategy = "incremental" | "full";

interface IngestRun {
  id: string;
  namespace: string;
  status: "queued" | "running" | "completed" | "failed";
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  chunks_created: number | null;
}

const STATUS_VARIANT: Record<IngestRun["status"], BadgeProps["variant"]> = {
  queued: "outline",
  running: "warning",
  completed: "success",
  failed: "danger",
};

const STATUS_ICON: Record<IngestRun["status"], React.ElementType> = {
  queued: Clock,
  running: RefreshCw,
  completed: CheckCircle2,
  failed: XCircle,
};

const CONNECTORS = [
  { id: "github", label: "GitHub", icon: Github, active: true },
  { id: "gdocs", label: "Google Docs", icon: FileText, active: false },
  { id: "confluence", label: "Confluence", icon: BookOpen, active: false },
] as const;

export default function SyncPage(): JSX.Element {
  const router = useRouter();
  const { token } = useAuth();
  const { addToast } = useToast();

  // Form state
  const [step, setStep] = useState(1);
  const [connector, setConnector] = useState<string | null>(null);
  const [repoUrl, setRepoUrl] = useState("");
  const [strategy, setStrategy] = useState<Strategy>("incremental");
  const [loading, setLoading] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Runs state
  const [runs, setRuns] = useState<IngestRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);

  function repoName(): string {
    try {
      const parts = repoUrl.trim().replace(/\/$/, "").split("/");
      return parts.at(-1) ?? repoUrl;
    } catch {
      return repoUrl;
    }
  }

  const fetchRuns = useCallback(async () => {
    const t = token ?? getToken();
    if (!t) return;
    setRunsLoading(true);
    try {
      const res = await fetch(buildApiUrl(ADMIN_INGEST_RUNS_ENDPOINT), {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (res.ok) {
        const data = (await res.json()) as { items: IngestRun[] };
        setRuns(data.items ?? []);
      }
    } finally {
      setRunsLoading(false);
    }
  }, [token]);

  useEffect(() => { void fetchRuns(); }, [fetchRuns, refreshTrigger]);

  async function handleStart(): Promise<void> {
    if (!repoUrl.trim()) return;
    const t = token ?? getToken();
    if (!t) { router.replace("/login"); return; }
    setLoading(true);
    try {
      const res = await fetch(buildApiUrl(INGEST_ENDPOINT), {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
        body: JSON.stringify({ source_url: repoUrl.trim(), strategy, connector }),
      });
      if (!res.ok) {
        const json = (await res.json().catch(() => ({}))) as { message?: string };
        throw new Error(json.message ?? `HTTP ${res.status}`);
      }
      addToast("Sync queued", `Started syncing ${repoName()}`, "success");
      setStep(1);
      setConnector(null);
      setRepoUrl("");
      setStrategy("incremental");
      setRefreshTrigger((n) => n + 1);
    } catch (err: unknown) {
      addToast("Sync failed", err instanceof Error ? err.message : "Unknown error", "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-10 py-4">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Sync Sources</h1>
        <p className="text-sm text-slate-500 mt-1">
          Connect a repository to index its content. Embedlyzer will process and embed the files so you can query them.
        </p>
      </div>

      {/* Add source card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-6 shadow-sm">
        {/* Step progress */}
        <div className="flex gap-2">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full transition-colors ${step >= s ? "bg-teal-500" : "bg-slate-100"}`}
            />
          ))}
        </div>

        {/* Step 1 — pick connector */}
        {step === 1 && (
          <div className="space-y-4">
            <p className="text-xs font-black text-slate-500 uppercase tracking-widest">Step 1 — Choose source type</p>
            <div className="grid grid-cols-3 gap-4">
              {CONNECTORS.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  disabled={!c.active}
                  onClick={() => { setConnector(c.id); setStep(2); }}
                  className={`relative p-6 rounded-2xl border-2 flex flex-col items-center gap-3 transition-all ${
                    !c.active
                      ? "opacity-40 grayscale bg-slate-50 border-slate-100 cursor-not-allowed"
                      : connector === c.id
                      ? "border-teal-500 bg-teal-50/50 text-teal-600"
                      : "border-slate-100 bg-white hover:border-slate-300"
                  }`}
                >
                  {!c.active && (
                    <span className="absolute top-2 right-2 text-[8px] font-black bg-slate-200 text-slate-500 px-1.5 py-0.5 rounded">SOON</span>
                  )}
                  <c.icon size={28} />
                  <span className="text-sm font-semibold">{c.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2 — repo URL */}
        {step === 2 && (
          <div className="space-y-4">
            <p className="text-xs font-black text-slate-500 uppercase tracking-widest">Step 2 — Repository URL</p>
            <input
              type="url"
              placeholder="https://github.com/owner/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
              onKeyDown={(e) => { if (e.key === "Enter" && repoUrl.trim()) setStep(3); }}
            />
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="px-4 py-2 text-sm font-semibold text-slate-500 hover:text-slate-700"
              >← Back</button>
              <button
                type="button"
                disabled={!repoUrl.trim()}
                onClick={() => setStep(3)}
                className="px-5 py-2 bg-teal-500 hover:bg-teal-600 text-white text-sm font-bold rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >Next →</button>
            </div>
          </div>
        )}

        {/* Step 3 — strategy + confirm */}
        {step === 3 && (
          <div className="space-y-4">
            <p className="text-xs font-black text-slate-500 uppercase tracking-widest">Step 3 — Sync mode</p>
            <div className="grid grid-cols-2 gap-3">
              {(["incremental", "full"] as Strategy[]).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setStrategy(s)}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${
                    strategy === s ? "border-teal-500 bg-teal-50/50" : "border-slate-100 hover:border-slate-300"
                  }`}
                >
                  <p className="text-sm font-bold capitalize text-slate-800">{s}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {s === "incremental" ? "Only re-index changed files (faster)" : "Re-index all files from scratch"}
                  </p>
                </button>
              ))}
            </div>
            <div className="pt-1 flex gap-3">
              <button type="button" onClick={() => setStep(2)} className="px-4 py-2 text-sm font-semibold text-slate-500 hover:text-slate-700">
                ← Back
              </button>
              <button
                type="button"
                onClick={handleStart}
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2 bg-teal-500 hover:bg-teal-600 text-white text-sm font-bold rounded-xl disabled:opacity-60 transition-colors"
              >
                {loading && <RefreshCw size={14} className="animate-spin" />}
                {loading ? "Starting…" : `Sync ${repoName()}`}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Recent sync runs */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-bold text-slate-800">Recent syncs</h2>
          <button
            type="button"
            onClick={() => setRefreshTrigger((n) => n + 1)}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600"
          >
            <RefreshCw size={12} className={runsLoading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>

        {runsLoading && !runs.length ? (
          <p className="text-sm text-slate-400">Loading&hellip;</p>
        ) : !runs.length ? (
          <div className="flex items-center gap-2 text-sm text-slate-400 bg-slate-50 rounded-xl p-4">
            <AlertCircle size={16} />
            No syncs yet. Add your first source above.
          </div>
        ) : (
          <ul className="divide-y divide-slate-100 bg-white border border-slate-200 rounded-2xl overflow-hidden">
            {runs.map((run) => {
              const Icon = STATUS_ICON[run.status];
              return (
                <li key={run.id} className="flex items-center justify-between gap-4 px-5 py-4">
                  <div className="flex items-center gap-3 min-w-0">
                    <Icon
                      size={16}
                      className={`shrink-0 ${
                        run.status === "completed" ? "text-teal-500" :
                        run.status === "failed" ? "text-rose-500" :
                        run.status === "running" ? "text-amber-500 animate-spin" :
                        "text-slate-400"
                      }`}
                    />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-800 truncate">{run.namespace}</p>
                      <p className="text-xs text-slate-400">{formatDate(run.created_at)}</p>
                      {run.error_message && (
                        <p className="text-xs text-rose-600 mt-0.5">{run.error_message}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    {run.chunks_created !== null && (
                      <span className="text-xs text-slate-400">{run.chunks_created} chunks</span>
                    )}
                    <Badge variant={STATUS_VARIANT[run.status]}>{run.status}</Badge>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
