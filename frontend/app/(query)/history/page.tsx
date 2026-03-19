"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { useAuth } from "../../../hooks/useAuth";
import { clearHistory, deleteHistoryItem, getHistory, type HistoryItem } from "../../../lib/api-client";

export default function HistoryPage(): JSX.Element {
  const { token, isLoggedIn } = useAuth();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    if (!isLoggedIn || !token) {
      setLoading(false);
      return;
    }
    getHistory(token)
      .then((data) => setItems(data.items))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load history."))
      .finally(() => setLoading(false));
  }, [token, isLoggedIn]);

  async function handleDelete(id: string): Promise<void> {
    if (!token) return;
    try {
      await deleteHistoryItem(id, token);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch {
      // non-critical; silently ignore
    }
  }

  async function handleClearAll(): Promise<void> {
    if (!token || clearing) return;
    setClearing(true);
    try {
      await clearHistory(token);
      setItems([]);
    } catch {
      // non-critical
    } finally {
      setClearing(false);
    }
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto w-full px-6 py-10 space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-1">You</p>
            <h1 className="text-2xl font-black text-slate-900">Query History</h1>
            <p className="text-sm text-slate-500 mt-1">Your past searches and answers.</p>
          </div>
          {isLoggedIn && items.length > 0 && (
            <button
              type="button"
              onClick={handleClearAll}
              disabled={clearing}
              className="mt-4 flex items-center gap-2 px-4 py-2 text-xs font-bold text-rose-500 border border-rose-200 rounded-lg hover:bg-rose-50 transition-colors disabled:opacity-50"
            >
              <Trash2 size={14} />
              {clearing ? "Clearing…" : "Clear all"}
            </button>
          )}
        </div>

        {/* Guest state */}
        {!isLoggedIn && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl px-8 py-14 text-center space-y-3">
            <p className="font-black text-lg text-amber-800">Sign in to see your history</p>
            <p className="text-sm text-amber-700">
              History is saved only for signed-in users. Guests can query freely but their searches aren&apos;t stored.
            </p>
            <Link
              href="/login"
              className="inline-block mt-2 px-6 py-2.5 bg-teal-500 hover:bg-teal-400 text-white rounded-lg text-sm font-bold transition-colors"
            >
              Sign In
            </Link>
          </div>
        )}

        {/* Loading */}
        {isLoggedIn && loading && (
          <div className="py-16 text-center text-slate-400 text-sm">Loading…</div>
        )}

        {/* Error */}
        {isLoggedIn && error && (
          <div className="bg-rose-50 border border-rose-200 rounded-xl px-6 py-4 text-sm text-rose-700">
            {error}
          </div>
        )}

        {/* Empty state */}
        {isLoggedIn && !loading && !error && items.length === 0 && (
          <div className="bg-slate-50 rounded-2xl px-8 py-16 text-center text-slate-400 border-2 border-dashed border-slate-200">
            <p className="font-black text-lg">No history yet</p>
            <p className="text-sm mt-1">Your queries will appear here once you start searching.</p>
          </div>
        )}

        {/* History list */}
        {items.length > 0 && (
          <ul className="space-y-3">
            {items.map((item) => (
              <li
                key={item.id}
                className="flex items-start justify-between gap-4 bg-white border border-slate-100 rounded-xl px-5 py-4 shadow-sm hover:border-slate-200 transition-colors"
              >
                <div className="flex-1 min-w-0 space-y-1">
                  <p className="text-sm font-semibold text-slate-900 truncate">{item.query_text}</p>
                  <div className="flex gap-3 text-xs text-slate-400">
                    <span className="capitalize">{item.mode}</span>
                    <span>·</span>
                    <span className="capitalize">{item.confidence}</span>
                    {item.sources_count > 0 && (
                      <>
                        <span>·</span>
                        <span>{item.sources_count} source{item.sources_count !== 1 ? "s" : ""}</span>
                      </>
                    )}
                    {item.created_at && (
                      <>
                        <span>·</span>
                        <span>{new Date(item.created_at).toLocaleDateString()}</span>
                      </>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(item.id)}
                  className="shrink-0 p-1.5 text-slate-300 hover:text-rose-400 transition-colors rounded"
                  title="Delete"
                >
                  <Trash2 size={15} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

