"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronUp, Download } from "lucide-react";
import { buildApiUrl } from "../../lib/api-client";
import { ADMIN_AUDIT_LOGS_ENDPOINT } from "../../lib/constants";

interface AuditEntry {
  id: string;
  timestamp: string;
  user_email: string;
  query: string;
  answer?: string;
  confidence: "HIGH" | "MEDIUM" | "LOW" | "REFUSED";
  sources_used?: string[];
}

interface AuditLogResponse {
  items: AuditEntry[];
  total: number;
}

interface AuditLogTableProps {
  authToken?: string;
}

const PAGE_SIZE = 25;

function ConfidencePill({ level }: { level: AuditEntry["confidence"] }) {
  const styles: Record<AuditEntry["confidence"], string> = {
    HIGH:    "bg-green-50 text-green-700 border border-green-200",
    MEDIUM:  "bg-amber-50 text-amber-700 border border-amber-200",
    LOW:     "bg-rose-50 text-rose-700 border border-rose-200",
    REFUSED: "bg-slate-100 text-slate-500 border border-slate-200",
  };
  return (
    <span className={`inline-block text-[10px] font-black uppercase px-2 py-0.5 rounded-full ${styles[level]}`}>
      {level}
    </span>
  );
}

export function AuditLogTable({ authToken }: AuditLogTableProps): JSX.Element {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchPage = useCallback(async (p: number) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(
        buildApiUrl(`${ADMIN_AUDIT_LOGS_ENDPOINT}?offset=${p * PAGE_SIZE}&limit=${PAGE_SIZE}`),
        { headers: authToken ? { Authorization: `Bearer ${authToken}` } : {} },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as AuditLogResponse;
      setEntries(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load audit log.");
    } finally {
      setLoading(false);
    }
  }, [authToken]);

  useEffect(() => { void fetchPage(page); }, [fetchPage, page]);

  function handleCsvExport(): void {
    const header = "timestamp,user,query,confidence";
    const rows = entries.map((e) =>
      [
        e.timestamp,
        e.user_email,
        `"${e.query.replace(/"/g, '""')}"`,
        e.confidence,
      ].join(","),
    );
    const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-log-page${page + 1}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const start = page * PAGE_SIZE + 1;
  const end = Math.min((page + 1) * PAGE_SIZE, total);

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <p className="text-sm font-bold text-slate-500">
          {loading ? "Loading…" : `Showing ${start}–${end} of ${total} rows`}
        </p>
        <button
          type="button"
          onClick={handleCsvExport}
          disabled={loading || !entries.length}
          className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white text-xs font-black uppercase tracking-wider rounded-xl hover:bg-slate-700 transition-all disabled:opacity-40"
        >
          <Download size={14} />
          Export CSV
        </button>
      </div>

      {error && (
        <div className="bg-rose-50 text-rose-700 rounded-2xl px-5 py-4 text-sm font-bold">{error}</div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-100">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left">
              <th className="px-5 py-3 text-xs font-black text-slate-400 uppercase tracking-widest">Timestamp</th>
              <th className="px-5 py-3 text-xs font-black text-slate-400 uppercase tracking-widest">User</th>
              <th className="px-5 py-3 text-xs font-black text-slate-400 uppercase tracking-widest">Query</th>
              <th className="px-5 py-3 text-xs font-black text-slate-400 uppercase tracking-widest">Confidence</th>
              <th className="px-5 py-3 w-8" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-5 py-4"><div className="h-3 w-32 bg-slate-100 rounded" /></td>
                    <td className="px-5 py-4"><div className="h-3 w-24 bg-slate-100 rounded" /></td>
                    <td className="px-5 py-4"><div className="h-3 w-48 bg-slate-100 rounded" /></td>
                    <td className="px-5 py-4"><div className="h-3 w-14 bg-slate-100 rounded-full" /></td>
                    <td />
                  </tr>
                ))
              : entries.map((e) => {
                  const isOpen = expanded === e.id;
                  return (
                    <>
                      <tr
                        key={e.id}
                        className="hover:bg-slate-50 cursor-pointer transition-colors"
                        onClick={() => setExpanded(isOpen ? null : e.id)}
                      >
                        <td className="px-5 py-4 font-mono text-xs text-slate-500 whitespace-nowrap">
                          {new Date(e.timestamp).toLocaleString()}
                        </td>
                        <td className="px-5 py-4 text-slate-700 font-bold">{e.user_email}</td>
                        <td className="px-5 py-4 text-slate-600 italic max-w-xs truncate">
                          &ldquo;{e.query}&rdquo;
                        </td>
                        <td className="px-5 py-4">
                          <ConfidencePill level={e.confidence} />
                        </td>
                        <td className="px-5 py-4 text-slate-300">
                          {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </td>
                      </tr>
                      {isOpen && (
                        <tr key={`${e.id}-expand`} className="bg-slate-50">
                          <td colSpan={5} className="px-5 py-5">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                              <div>
                                <p className="text-xs font-black text-slate-400 uppercase mb-2">Full Answer</p>
                                <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                                  {e.answer ?? <span className="italic text-slate-300">No answer recorded.</span>}
                                </p>
                              </div>
                              <div>
                                <p className="text-xs font-black text-slate-400 uppercase mb-2">Sources Used</p>
                                {e.sources_used?.length ? (
                                  <ul className="space-y-1">
                                    {e.sources_used.map((src, idx) => (
                                      <li key={idx} className="text-xs font-mono text-slate-500 bg-white rounded-lg px-3 py-2 border border-slate-100">
                                        {src}
                                      </li>
                                    ))}
                                  </ul>
                                ) : (
                                  <p className="text-sm italic text-slate-300">None recorded.</p>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button
            type="button"
            disabled={page === 0 || loading}
            onClick={() => setPage((p) => p - 1)}
            className="px-5 py-2 border border-slate-200 rounded-xl text-xs font-black uppercase text-slate-500 hover:bg-slate-50 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            ← Prev
          </button>
          <p className="text-xs font-black text-slate-400 uppercase">
            Page {page + 1} / {totalPages}
          </p>
          <button
            type="button"
            disabled={page >= totalPages - 1 || loading}
            onClick={() => setPage((p) => p + 1)}
            className="px-5 py-2 border border-slate-200 rounded-xl text-xs font-black uppercase text-slate-500 hover:bg-slate-50 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
