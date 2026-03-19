"use client";

import { useCallback, useEffect, useState } from "react";
import { buildApiUrl } from "../../lib/api-client";
import { ADMIN_THRESHOLDS_ENDPOINT, ADMIN_WORKSPACES_ENDPOINT } from "../../lib/constants";
import { useToast } from "../../context/toast-context";

interface ThresholdConfig {
  namespace: string;
  index_version: number;
  threshold: number;
  updated_at?: string;
}

interface ThresholdListResponse {
  thresholds: ThresholdConfig[];
}

interface ThresholdTunerProps {
  authToken?: string;
}

interface WorkspaceSummary {
  id: string;
  slug: string;
  display_name: string;
}

function getStrictnessLabel(v: number): string {
  if (v < 0.25) return "Very Permissive";
  if (v < 0.5)  return "Permissive";
  if (v < 0.75) return "Balanced";
  if (v < 0.9)  return "Strict";
  return "Very Strict";
}

function getStrictnessDescription(v: number): string {
  if (v < 0.25)
    return "Almost every query will get an answer. Expect many loosely-related citations.";
  if (v < 0.5)
    return "Most queries will get an answer. Some tangentially-related citations may appear.";
  if (v < 0.75)
    return "Only clearly-relevant chunks are returned. Good starting point for most teams.";
  if (v < 0.9)
    return "Only highly-similar chunks surface. Expect occasional 'no results' for edge queries.";
  return "Maximum precision. The system will often refuse to answer ambiguous questions.";
}

export function ThresholdTuner({ authToken }: ThresholdTunerProps): JSX.Element {
  const { addToast } = useToast();
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [namespace, setNamespace] = useState("default");
  const [indexVersion, setIndexVersion] = useState(1);
  const [savedValue, setSavedValue] = useState(0.65);
  const [value, setValue] = useState(0.65);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const fetchThreshold = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(
        buildApiUrl(`${ADMIN_THRESHOLDS_ENDPOINT}?namespace=${encodeURIComponent(namespace)}`),
        { headers: authToken ? { Authorization: `Bearer ${authToken}` } : {} },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as ThresholdListResponse;
      // Find the matching namespace+index_version entry, or keep default 0.65
      const match = data.thresholds?.find(
        (t) => t.namespace === namespace && t.index_version === indexVersion,
      );
      const resolved = match?.threshold ?? 0.65;
      setValue(resolved);
      setSavedValue(resolved);
    } catch (err: unknown) {
      addToast("Load failed", err instanceof Error ? err.message : "Could not load threshold", "error");
    } finally {
      setLoading(false);
    }
  }, [authToken, namespace, indexVersion, addToast]);

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch(buildApiUrl(ADMIN_WORKSPACES_ENDPOINT), {
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
        });
        if (!res.ok) return;
        const data = (await res.json()) as { workspaces?: WorkspaceSummary[] };
        const list = data.workspaces ?? [];
        setWorkspaces(list);
        if (list.length > 0) {
          setSelectedWorkspaceId(list[0].id);
          setNamespace(list[0].slug);
        }
      } catch {
        // silently ignore — user can still type a namespace
      }
    })();
  }, [authToken]);

  useEffect(() => { void fetchThreshold(); }, [fetchThreshold]);

  async function handleSave(): Promise<void> {
    setSaving(true);
    try {
      const res = await fetch(buildApiUrl(ADMIN_THRESHOLDS_ENDPOINT), {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        body: JSON.stringify({ namespace, index_version: indexVersion, threshold: value, workspace_id: selectedWorkspaceId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setSavedValue(value);
      addToast("Saved", `Threshold updated to ${value.toFixed(2)}`, "success");
    } catch (err: unknown) {
      addToast("Save failed", err instanceof Error ? err.message : "Unknown error", "error");
    } finally {
      setSaving(false);
    }
  }

  const isDirty = value !== savedValue;

  return (
    <div className="max-w-lg space-y-8">
      {/* Namespace selector */}
      <div className="space-y-1">
        <label className="text-xs font-black text-slate-400 uppercase tracking-wider">Workspace</label>
        {workspaces.length > 0 ? (
          <select
            value={selectedWorkspaceId}
            onChange={(e) => {
              const ws = workspaces.find((w) => w.id === e.target.value);
              if (ws) {
                setSelectedWorkspaceId(ws.id);
                setNamespace(ws.slug);
              }
            }}
            className="w-full px-4 py-3 bg-slate-50 border-2 border-transparent rounded-xl focus:bg-white focus:border-teal-500 outline-none font-medium text-slate-900"
          >
            {workspaces.map((ws) => (
              <option key={ws.id} value={ws.id}>
                {ws.display_name} ({ws.slug})
              </option>
            ))}
          </select>
        ) : (
          <input
            value={namespace}
            onChange={(e) => setNamespace(e.target.value)}
            onBlur={() => void fetchThreshold()}
            placeholder="namespace"
            className="w-full px-4 py-3 bg-slate-50 border-2 border-transparent rounded-xl focus:bg-white focus:border-teal-500 outline-none font-medium text-slate-900"
          />
        )}
      </div>

      {/* Index version */}
      <div className="space-y-1">
        <label className="text-xs font-black text-slate-400 uppercase tracking-wider">Index Version</label>
        <input
          type="number"
          min={1}
          step={1}
          value={indexVersion}
          onChange={(e) => setIndexVersion(Math.max(1, parseInt(e.target.value, 10) || 1))}
          onBlur={() => void fetchThreshold()}
          className="w-full px-4 py-3 bg-slate-50 border-2 border-transparent rounded-xl focus:bg-white focus:border-teal-500 outline-none font-medium text-slate-900"
        />
      </div>

      {/* Slider section */}
      <div className="space-y-4">
        <div className="flex items-end justify-between">
          <p className="text-3xl font-black text-slate-900">{getStrictnessLabel(value)}</p>
          <p className="text-2xl font-black text-teal-500">{value.toFixed(2)}</p>
        </div>

        <p className="text-sm text-slate-500 leading-relaxed">{getStrictnessDescription(value)}</p>

        <div className="space-y-2 pt-2">
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={value}
            disabled={loading}
            onChange={(e) => setValue(parseFloat(e.target.value))}
            className="w-full accent-teal-500 cursor-pointer disabled:opacity-50"
          />
          <div className="flex justify-between text-xs font-black text-slate-400 uppercase">
            <span>Permissive</span>
            <span>Strict</span>
          </div>
        </div>
      </div>

      <button
        type="button"
        onClick={() => void handleSave()}
        disabled={!isDirty || saving || loading}
        className="w-full py-3 bg-teal-500 text-white rounded-xl font-bold hover:bg-teal-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {saving ? "Saving…" : "Save threshold"}
      </button>
    </div>
  );
}
