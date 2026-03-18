"use client";

import { useCallback, useEffect, useState } from "react";
import { buildApiUrl } from "../../lib/api-client";
import { ADMIN_INGEST_RUNS_ENDPOINT } from "../../lib/constants";
import { Badge } from "../ui/badge";
import { formatDate } from "../../lib/utils";
import type { BadgeProps } from "../ui/badge";

interface IngestRun {
  id: string;
  namespace: string;
  status: "queued" | "running" | "completed" | "failed";
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  chunks_created: number | null;
}

interface IngestRunMonitorProps {
  authToken?: string;
  refreshTrigger?: number;
}

const STATUS_VARIANT: Record<IngestRun["status"], BadgeProps["variant"]> = {
  queued: "outline",
  running: "warning",
  completed: "success",
  failed: "danger",
};

export function IngestRunMonitor({ authToken, refreshTrigger }: IngestRunMonitorProps): JSX.Element {
  const [runs, setRuns] = useState<IngestRun[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(buildApiUrl(ADMIN_INGEST_RUNS_ENDPOINT), {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { items: IngestRun[] };
      setRuns(data.items ?? []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load runs.");
    } finally {
      setLoading(false);
    }
  }, [authToken]);

  useEffect(() => { void fetchRuns(); }, [fetchRuns, refreshTrigger]);

  if (loading) return <p className="text-sm text-slate-500">Loading runs&hellip;</p>;
  if (error) return <p className="text-sm text-rose-600" role="alert">{error}</p>;
  if (!runs.length) return <p className="text-sm text-slate-500">No ingest runs yet.</p>;

  return (
    <ul className="divide-y divide-slate-100 text-sm">
      {runs.map((run) => (
        <li key={run.id} className="flex items-start justify-between gap-4 py-3">
          <div>
            <p className="font-medium text-slate-900">{run.namespace}</p>
            <p className="text-xs text-slate-500">{formatDate(run.created_at)}</p>
            {run.error_message && (
              <p className="mt-1 text-xs text-rose-600">{run.error_message}</p>
            )}
          </div>
          <div className="flex flex-col items-end gap-1">
            <Badge variant={STATUS_VARIANT[run.status]}>{run.status}</Badge>
            {run.chunks_created !== null && (
              <span className="text-xs text-slate-500">{run.chunks_created} chunks</span>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
