"use client";

import { useState } from "react";
import { BookOpen, FileText, Github } from "lucide-react";
import { buildApiUrl } from "../../lib/api-client";
import { INGEST_ENDPOINT } from "../../lib/constants";
import { useToast } from "../../context/toast-context";

interface IngestFormProps {
  authToken?: string;
  onSuccess?: () => void;
}

type Strategy = "full" | "incremental";

const CONNECTORS = [
  { id: "github",     label: "GitHub",      icon: Github,   active: true },
  { id: "gdocs",      label: "Google Docs", icon: FileText, active: false },
  { id: "confluence", label: "Confluence",  icon: BookOpen, active: false },
] as const;

export function IngestForm({ authToken, onSuccess }: IngestFormProps): JSX.Element {
  const { addToast } = useToast();
  const [step, setStep] = useState(1);
  const [connector, setConnector] = useState<string | null>(null);
  const [repoUrl, setRepoUrl] = useState("");
  const [strategy, setStrategy] = useState<Strategy>("incremental");
  const [loading, setLoading] = useState(false);

  function repoName(): string {
    try {
      const parts = repoUrl.trim().replace(/\/$/, "").split("/");
      return parts.at(-1) ?? repoUrl;
    } catch {
      return repoUrl;
    }
  }

  async function handleStart(): Promise<void> {
    if (!repoUrl.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(buildApiUrl(INGEST_ENDPOINT), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({
          source_url: repoUrl.trim(),
          strategy,
          connector,
        }),
      });
      if (!res.ok) {
        const json = (await res.json().catch(() => ({}))) as { message?: string };
        throw new Error(json.message ?? `HTTP ${res.status}`);
      }
      addToast("Queued", `Ingestion job queued for ${repoName()}`, "success");
      setStep(1);
      setConnector(null);
      setRepoUrl("");
      setStrategy("incremental");
      onSuccess?.();
    } catch (err: unknown) {
      addToast(
        "Ingestion failed",
        err instanceof Error ? err.message : "Unknown error",
        "error",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl space-y-8">
      {/* Step progress bar */}
      <div className="flex gap-2">
        {[1, 2, 3].map((s) => (
          <div
            key={s}
            className={`h-1 flex-1 rounded-full transition-colors ${
              step >= s ? "bg-teal-500" : "bg-slate-100"
            }`}
          />
        ))}
      </div>

      {/* Step 1 — Choose connector */}
      {step === 1 && (
        <div className="space-y-6">
          <p className="text-xs font-black text-slate-500 uppercase tracking-widest">
            Step 1 — Choose Source
          </p>
          <div className="grid grid-cols-3 gap-4">
            {CONNECTORS.map((c) => (
              <button
                key={c.id}
                type="button"
                disabled={!c.active}
                onClick={() => {
                  setConnector(c.id);
                  setStep(2);
                }}
                className={`relative p-8 rounded-2xl border-2 flex flex-col items-center gap-3 transition-all ${
                  !c.active
                    ? "opacity-40 grayscale bg-slate-50 border-slate-100 cursor-not-allowed"
                    : connector === c.id
                    ? "border-teal-500 bg-teal-50/50 text-teal-600"
                    : "border-slate-100 bg-white hover:border-slate-300"
                }`}
              >
                {!c.active && (
                  <span className="absolute top-2 right-2 text-[8px] font-black bg-slate-200 text-slate-500 px-1.5 py-0.5 rounded">
                    SOON
                  </span>
                )}
                <c.icon size={32} />
                <span className="font-bold text-sm">{c.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step 2 — Paste link */}
      {step === 2 && (
        <div className="space-y-6">
          <p className="text-xs font-black text-slate-500 uppercase tracking-widest">
            Step 2 — Paste Link
          </p>
          <div className="space-y-2">
            <label className="text-xs font-black text-slate-400 uppercase">
              Repository URL
            </label>
            <input
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/your-org/your-repo"
              className="w-full px-5 py-4 bg-slate-50 border-2 border-transparent rounded-xl focus:bg-white focus:border-teal-500 outline-none transition-all font-medium text-slate-900"
            />
          </div>
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="px-6 py-3 border border-slate-200 rounded-xl font-bold text-slate-500 hover:bg-slate-50 transition-all"
            >
              Back
            </button>
            <button
              type="button"
              onClick={() => setStep(3)}
              disabled={!repoUrl.trim()}
              className="flex-1 py-3 bg-teal-500 text-white rounded-xl font-bold hover:bg-teal-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Step 3 — Choose strategy */}
      {step === 3 && (
        <div className="space-y-6">
          <p className="text-xs font-black text-slate-500 uppercase tracking-widest">
            Step 3 — Choose Strategy
          </p>
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setStrategy("full")}
              className={`w-full p-5 rounded-2xl border-2 text-left space-y-1 transition-all ${
                strategy === "full"
                  ? "bg-teal-50 border-teal-500"
                  : "bg-white border-slate-100 hover:border-slate-300"
              }`}
            >
              <p className="font-bold text-slate-900">Full re-index — reads everything from scratch</p>
              <p className="text-xs text-amber-600 font-bold uppercase tracking-wider">
                Warning: source will be unavailable during re-indexing
              </p>
            </button>
            <button
              type="button"
              onClick={() => setStrategy("incremental")}
              className={`w-full p-5 rounded-2xl border-2 text-left space-y-1 transition-all ${
                strategy === "incremental"
                  ? "bg-teal-50 border-teal-500"
                  : "bg-white border-slate-100 hover:border-slate-300"
              }`}
            >
              <p className="font-bold text-slate-900">Incremental — reads only new changes</p>
              <p className="text-xs text-slate-400 font-bold uppercase tracking-wider">
                Faster, keeps existing content available
              </p>
            </button>
          </div>
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setStep(2)}
              className="px-6 py-3 border border-slate-200 rounded-xl font-bold text-slate-500 hover:bg-slate-50 transition-all"
            >
              Back
            </button>
            <button
              type="button"
              onClick={handleStart}
              disabled={loading}
              className="flex-1 py-3 bg-teal-500 text-white rounded-xl font-bold hover:bg-teal-600 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? "Queuing…" : "Start Ingestion Job"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

