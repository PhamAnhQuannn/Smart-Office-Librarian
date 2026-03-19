"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Save } from "lucide-react";
import { Card, CardHeader, CardBody } from "../../../components/ui/card";
import { useAuth } from "../../../hooks/useAuth";
import {
  adminGetBudget,
  adminUpdateBudget,
  type BudgetWorkspace,
  ApiClientError,
} from "../../../lib/api-client";

function UsageBar({ used, cap }: { used: number; cap: number }) {
  const pct = cap > 0 ? Math.min(used / cap, 1) : 0;
  const color =
    pct > 0.9 ? "bg-rose-500" : pct > 0.7 ? "bg-amber-400" : "bg-teal-500";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-slate-500 font-semibold">
        <span>{used.toLocaleString()} used</span>
        <span>{(pct * 100).toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: `${pct * 100}%` }}
        />
      </div>
      <p className="text-xs text-slate-400">cap: {cap.toLocaleString()} / month</p>
    </div>
  );
}

interface RowProps {
  ws: BudgetWorkspace;
  authToken: string;
  onSaved: (id: string, cap: number) => void;
}

function WorkspaceRow({ ws, authToken, onSaved }: RowProps) {
  const [draft, setDraft] = useState(String(ws.monthly_query_cap));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const isDirty = draft !== String(ws.monthly_query_cap);

  async function handleSave(): Promise<void> {
    const val = parseInt(draft, 10);
    if (Number.isNaN(val) || val < 0) { setError("Must be a non-negative integer"); return; }
    setSaving(true);
    setError("");
    try {
      await adminUpdateBudget(ws.id, val, authToken);
      onSaved(ws.id, val);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <tr className="border-t border-slate-100 hover:bg-slate-50 transition-colors">
      <td className="px-4 py-4 align-top">
        <p className="text-sm font-bold text-slate-900">{ws.display_name}</p>
        <p className="text-xs text-slate-400 font-mono">{ws.slug}</p>
      </td>
      <td className="px-4 py-4 align-middle min-w-[200px]">
        <UsageBar used={ws.used_this_month} cap={ws.monthly_query_cap} />
      </td>
      <td className="px-4 py-4 align-middle text-xs text-slate-500">
        {ws.max_sources} sources / {ws.max_chunks.toLocaleString()} chunks
      </td>
      <td className="px-4 py-4 align-middle">
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            value={draft}
            onChange={(e) => { setDraft(e.target.value); setError(""); }}
            className="w-28 px-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono"
          />
          {isDirty && (
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-teal-500 hover:bg-teal-400 text-white text-xs font-bold rounded-lg transition-colors disabled:opacity-50"
            >
              <Save size={13} />
              {saving ? "Saving…" : "Save"}
            </button>
          )}
        </div>
        {error && <p className="text-xs text-rose-500 mt-1">{error}</p>}
      </td>
    </tr>
  );
}

export default function BudgetPage(): JSX.Element {
  const { token } = useAuth();
  const [workspaces, setWorkspaces] = useState<BudgetWorkspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  async function load(showSpinner = true): Promise<void> {
    if (!token) return;
    if (showSpinner) setLoading(true);
    else setRefreshing(true);
    setError("");
    try {
      const data = await adminGetBudget(token);
      setWorkspaces(data.workspaces);
    } catch (e) {
      setError(e instanceof ApiClientError ? e.message : "Failed to load budget data.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => { void load(); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleSaved(id: string, cap: number): void {
    setWorkspaces((prev) =>
      prev.map((w) => (w.id === id ? { ...w, monthly_query_cap: cap } : w)),
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Budget</h2>
            <p className="mt-1 text-sm text-slate-500">
              Monthly query caps per workspace. Edits take effect immediately.
            </p>
          </div>
          <button
            type="button"
            onClick={() => load(false)}
            disabled={refreshing || loading}
            className="flex items-center gap-2 px-3 py-2 text-xs font-bold text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors disabled:opacity-40"
          >
            <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </CardHeader>
      <CardBody>
        {loading && (
          <div className="py-12 text-center text-slate-400 text-sm animate-pulse">Loading…</div>
        )}

        {error && (
          <div className="bg-rose-50 border border-rose-200 rounded-xl px-5 py-4 text-sm text-rose-700 font-semibold">
            {error}
          </div>
        )}

        {!loading && !error && workspaces.length === 0 && (
          <div className="py-12 text-center text-slate-400 text-sm">
            No workspaces found.
          </div>
        )}

        {!loading && workspaces.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-black text-slate-400 uppercase tracking-widest">
                  <th className="px-4 pb-3">Workspace</th>
                  <th className="px-4 pb-3">This month</th>
                  <th className="px-4 pb-3">Limits</th>
                  <th className="px-4 pb-3">Monthly cap</th>
                </tr>
              </thead>
              <tbody>
                {workspaces.map((ws) => (
                  <WorkspaceRow
                    key={ws.id}
                    ws={ws}
                    authToken={token ?? ""}
                    onSaved={handleSaved}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

