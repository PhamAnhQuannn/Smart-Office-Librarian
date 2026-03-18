"use client";

import { useCallback, useEffect, useState } from "react";
import { buildApiUrl } from "../../lib/api-client";

interface EvaluationSummary {
  total: number;
  pass_count: number;
  fail_count: number;
  pass_rate: number;
  namespace: string;
  index_version: number | null;
  token_usage?: number;
  token_budget?: number;
  confidence_high?: number;
  confidence_medium?: number;
  confidence_refused?: number;
  volume_by_day?: number[];
  p50_ms?: number;
  p95_ms?: number;
  latency_sparkline?: number[];
}

type DateRange = "7d" | "30d" | "all";

interface AnalyticsDashboardProps {
  authToken?: string;
}

// --- sub-components ---

function PanelCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-6 space-y-4">
      <p className="text-xs font-black text-slate-400 uppercase tracking-widest">{title}</p>
      {children}
    </div>
  );
}

function SkeletonPanel() {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-6 space-y-3 animate-pulse">
      <div className="h-3 w-24 bg-slate-100 rounded" />
      <div className="h-16 bg-slate-100 rounded-xl" />
    </div>
  );
}

function BudgetGauge({ used, budget }: { used: number; budget: number }) {
  const pct = budget > 0 ? Math.min(used / budget, 1) : 0;
  const r = 52;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - pct);
  const color = pct > 0.9 ? "#f43f5e" : pct > 0.7 ? "#f59e0b" : "#14b8a6";
  return (
    <div className="flex items-center gap-8">
      <div className="relative flex items-center justify-center w-32 h-32">
        <svg viewBox="0 0 120 120" className="w-32 h-32 -rotate-90">
          <circle cx="60" cy="60" r={r} fill="none" stroke="#f1f5f9" strokeWidth="12" />
          <circle
            cx="60" cy="60" r={r} fill="none"
            stroke={color} strokeWidth="12"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.6s ease" }}
          />
        </svg>
        <div className="absolute text-center">
          <p className="text-xl font-black text-slate-900">{(pct * 100).toFixed(0)}%</p>
          <p className="text-[10px] font-bold text-slate-400 uppercase">used</p>
        </div>
      </div>
      <div className="space-y-1">
        <p className="text-sm font-bold text-slate-900">{used.toLocaleString()} tokens used</p>
        <p className="text-sm text-slate-400">of {budget.toLocaleString()} budget</p>
      </div>
    </div>
  );
}

function ConfidenceBar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs font-bold text-slate-500">
        <span>{label}</span><span>{pct}%</span>
      </div>
      <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function VolumeChart({ days }: { days: number[] }) {
  const max = Math.max(...days, 1);
  return (
    <div className="flex items-end gap-0.5 h-24 w-full">
      {days.map((v, i) => (
        <div
          key={i}
          title={`${v} queries`}
          className="flex-1 bg-teal-400 rounded-sm hover:bg-teal-600 transition-colors"
          style={{ height: `${Math.max(4, (v / max) * 100)}%` }}
        />
      ))}
    </div>
  );
}

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return null;
  const max = Math.max(...values, 1);
  const min = Math.min(...values);
  const range = max - min || 1;
  const w = 200, h = 40;
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / range) * h;
      return `${x},${y}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-10 overflow-visible">
      <polyline points={pts} fill="none" stroke="#14b8a6" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

// --- main component ---

export function AnalyticsDashboard({ authToken }: AnalyticsDashboardProps): JSX.Element {
  const [range, setRange] = useState<DateRange>("7d");
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchSummary = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(
        buildApiUrl(`/api/v1/admin/evaluation/summary?range=${range}`),
        { headers: authToken ? { Authorization: `Bearer ${authToken}` } : {} },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSummary((await res.json()) as EvaluationSummary);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load analytics.");
    } finally {
      setLoading(false);
    }
  }, [authToken, range]);

  useEffect(() => { void fetchSummary(); }, [fetchSummary]);

  const confTotal =
    (summary?.confidence_high ?? 0) +
    (summary?.confidence_medium ?? 0) +
    (summary?.confidence_refused ?? 0);

  return (
    <div className="space-y-6">
      {/* Date range toggle */}
      <div className="flex gap-2">
        {(["7d", "30d", "all"] as DateRange[]).map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => setRange(r)}
            className={`px-4 py-1.5 text-xs font-black uppercase rounded-lg transition-all ${
              range === r
                ? "bg-teal-500 text-white"
                : "bg-slate-100 text-slate-500 hover:bg-slate-200"
            }`}
          >
            {r}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-rose-50 text-rose-700 rounded-2xl px-5 py-4 text-sm font-bold">{error}</div>
      )}

      {/* Panel grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Budget gauge */}
        {loading ? <SkeletonPanel /> : (
          <PanelCard title="Token budget">
            <BudgetGauge
              used={summary?.token_usage ?? 0}
              budget={summary?.token_budget ?? 1000000}
            />
          </PanelCard>
        )}

        {/* Confidence distribution */}
        {loading ? <SkeletonPanel /> : (
          <PanelCard title="Confidence distribution">
            <div className="space-y-3">
              <ConfidenceBar label="HIGH" value={summary?.confidence_high ?? 0} total={confTotal} color="bg-green-400" />
              <ConfidenceBar label="MEDIUM" value={summary?.confidence_medium ?? 0} total={confTotal} color="bg-amber-400" />
              <ConfidenceBar label="REFUSED" value={summary?.confidence_refused ?? 0} total={confTotal} color="bg-rose-400" />
            </div>
          </PanelCard>
        )}

        {/* Query volume */}
        {loading ? <SkeletonPanel /> : (
          <PanelCard title="Query volume">
            <VolumeChart days={summary?.volume_by_day ?? Array(30).fill(0)} />
          </PanelCard>
        )}

        {/* Latency */}
        {loading ? <SkeletonPanel /> : (
          <PanelCard title="Latency">
            <div className="flex gap-8 mb-2">
              <div>
                <p className="text-2xl font-black text-slate-900">{summary?.p50_ms ?? "—"}<span className="text-sm font-bold text-slate-400 ml-1">ms</span></p>
                <p className="text-xs font-black text-slate-400 uppercase">p50</p>
              </div>
              <div>
                <p className="text-2xl font-black text-slate-900">{summary?.p95_ms ?? "—"}<span className="text-sm font-bold text-slate-400 ml-1">ms</span></p>
                <p className="text-xs font-black text-slate-400 uppercase">p95</p>
              </div>
            </div>
            <Sparkline values={summary?.latency_sparkline ?? []} />
          </PanelCard>
        )}
      </div>
    </div>
  );
}
