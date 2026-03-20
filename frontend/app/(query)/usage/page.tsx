"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Zap, Database, HardDrive, TrendingUp, AlertCircle, ChevronDown } from "lucide-react";
import { getWorkspaceMe, ApiClientError, type WorkspaceInfo } from "../../../lib/api-client";
import { getToken } from "../../../lib/auth";

function StatCard({
  label,
  value,
  max,
  unit,
  icon: Icon,
  warning,
}: {
  label: string;
  value: number;
  max: number;
  unit: string;
  icon: React.ElementType;
  warning?: boolean;
}): JSX.Element {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  const barColor = pct >= 90 ? "bg-rose-500" : pct >= 70 ? "bg-amber-400" : "bg-teal-500";

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-500">
          <Icon size={16} />
          <span className="text-sm font-semibold">{label}</span>
        </div>
        {warning && pct >= 90 && (
          <div className="flex items-center gap-1 text-rose-500 text-xs font-bold">
            <AlertCircle size={12} />
            Near limit
          </div>
        )}
      </div>
      <div>
        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-black text-slate-900">{value.toLocaleString()}</span>
          <span className="text-slate-400 text-sm">/ {max.toLocaleString()} {unit}</span>
        </div>
        <div className="mt-3 h-2 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="text-xs text-slate-400 mt-1">{pct}% used</p>
      </div>
    </div>
  );
}

export default function UsagePage(): JSX.Element {
  const router = useRouter();
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) { router.replace("/login"); return; }
    getWorkspaceMe(token)
      .then(setWorkspace)
      .catch((err: unknown) => {
        if (err instanceof ApiClientError && err.status === 401) {
          router.replace("/login");
        } else {
          setError("Failed to load usage data.");
        }
      })
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-slate-400">
        Loading&hellip;
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-rose-600 text-sm bg-rose-50 rounded-xl p-4">
        <AlertCircle size={16} /> {error}
      </div>
    );
  }

  if (!workspace) return <></>;

  const now = new Date();
  const monthName = now.toLocaleString("default", { month: "long", year: "numeric" });

  return (
    <div className="max-w-2xl mx-auto space-y-8 py-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Usage</h1>
        <p className="text-sm text-slate-500 mt-1">
          Workspace <span className="font-semibold text-slate-700">{workspace.display_name}</span> · {monthName}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <StatCard
          label="Queries this month"
          value={workspace.usage.queries_this_month ?? 0}
          max={workspace.limits.monthly_query_cap}
          unit="queries"
          icon={Zap}
          warning
        />
        <StatCard
          label="Sources indexed"
          value={workspace.usage.sources}
          max={workspace.limits.max_sources}
          unit="sources"
          icon={Database}
          warning
        />
        <StatCard
          label="Chunks stored"
          value={0}
          max={workspace.limits.max_chunks}
          unit="chunks"
          icon={HardDrive}
        />
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-3">
          <div className="flex items-center gap-2 text-slate-500">
            <TrendingUp size={16} />
            <span className="text-sm font-semibold">Plan</span>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500">Workspace</span>
              <span className="font-semibold text-slate-800">{workspace.display_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Monthly query cap</span>
              <span className="font-semibold text-slate-800">{workspace.limits.monthly_query_cap.toLocaleString()}</span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setShowDetails((v) => !v)}
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors pt-1"
          >
            <ChevronDown size={12} className={`transition-transform ${showDetails ? "rotate-180" : ""}`} />
            {showDetails ? "Hide details" : "Show technical details"}
          </button>
          {showDetails && (
            <div className="space-y-1.5 text-xs border-t border-slate-100 pt-3">
              <div className="flex justify-between">
                <span className="text-slate-400">Namespace</span>
                <span className="font-mono text-slate-500">{workspace.slug}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Workspace ID</span>
                <span className="font-mono text-slate-500 truncate ml-4 max-w-[160px]">{workspace.id}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      <p className="text-xs text-slate-400">
        Usage counters reset at the start of each calendar month. Contact support if you need higher limits.
      </p>
    </div>
  );
}
