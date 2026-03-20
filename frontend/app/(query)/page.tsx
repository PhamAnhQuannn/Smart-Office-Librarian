"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Github, PlusCircle, Loader2 } from "lucide-react";
import { QueryHeader } from "../../components/query/QueryHeader";
import { QueryInput } from "../../components/query/QueryInput";
import { StreamingAnswer } from "../../components/query/StreamingAnswer";
import { ThumbsFeedback } from "../../components/query/ThumbsFeedback";
import { useQuery } from "../../hooks/useQuery";
import { useAuth } from "../../hooks/useAuth";
import { getWorkspaceMe, ApiClientError } from "../../lib/api-client";

const SUGGESTIONS = [
  "Summarise the architecture overview",
  "How do I contribute to this repo?",
  "What does the onboarding doc say?",
];

const GUEST_HISTORY_KEY = "embed_guest_history";
const GUEST_HISTORY_MAX = 20;

export default function QueryPage(): JSX.Element {
  const { token, user, isLoggedIn } = useAuth();
  const hasWorkspace = Boolean(user?.workspace_id);
  const { state, isStreaming, queriesRemaining, showRateWarning, submitQuery, sendFeedback, resetQuery } =
    useQuery();

  // Source count — null = not yet loaded, -1 = load failed (show query box anyway)
  const [sourcesCount, setSourcesCount] = useState<number | null>(null);

  useEffect(() => {
    if (!isLoggedIn || !token || !hasWorkspace) { setSourcesCount(-1); return; }
    getWorkspaceMe(token)
      .then((ws) => setSourcesCount(ws.usage.sources))
      .catch((err: unknown) => {
        // Non-blocking — if this fails, fall back to showing the query box
        if (err instanceof ApiClientError && err.status === 401) setSourcesCount(-1);
        else setSourcesCount(-1);
      });
  }, [isLoggedIn, token, hasWorkspace]);

  const hasResult = state.status !== "idle" || isStreaming;
  // Only show the "no sources" gate once we have a confirmed 0 count
  const showNoSourcesGate = isLoggedIn && hasWorkspace && sourcesCount === 0 && !hasResult;

  // Persist guest queries to sessionStorage
  useEffect(() => {
    if (isLoggedIn || state.status !== "complete") return;
    try {
      const existing: unknown[] = JSON.parse(sessionStorage.getItem(GUEST_HISTORY_KEY) ?? "[]");
      const entry = {
        query_text: state.answer?.slice(0, 120) ?? "",
        response_snippet: state.answer?.slice(0, 200) ?? "",
        timestamp: new Date().toISOString(),
      };
      const updated = [entry, ...(Array.isArray(existing) ? existing : [])].slice(0, GUEST_HISTORY_MAX);
      sessionStorage.setItem(GUEST_HISTORY_KEY, JSON.stringify(updated));
    } catch {
      // sessionStorage unavailable — ignore
    }
  }, [isLoggedIn, state.status, state.answer]);

  return (
    <div className="flex flex-col h-full">
      <QueryHeader onNewChat={resetQuery} />

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-6 py-12 space-y-10 min-h-full">

          {/* ── No-sources onboarding gate ── */}
          {showNoSourcesGate ? (
            <div className="flex flex-col items-center justify-center py-16 text-center gap-6">
              <div className="w-20 h-20 bg-slate-100 rounded-3xl flex items-center justify-center">
                <Github size={36} className="text-slate-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-slate-900">Add a repository to get started</h1>
                <p className="text-slate-400 text-sm mt-2 max-w-sm mx-auto">
                  Connect a GitHub repository and Embedlyzer will index its contents so you can ask questions about it.
                </p>
              </div>
              <div className="flex flex-col sm:flex-row gap-3">
                <Link
                  href="/sources"
                  className="flex items-center gap-2 px-6 py-3 bg-teal-500 text-white rounded-xl font-bold text-sm hover:bg-teal-600 transition-colors"
                >
                  <PlusCircle size={16} />
                  Add your first repository
                </Link>
                <Link
                  href="/sync"
                  className="flex items-center gap-2 px-6 py-3 bg-white border border-slate-200 text-slate-700 rounded-xl font-semibold text-sm hover:bg-slate-50 transition-colors"
                >
                  Go to Sync
                </Link>
              </div>
            </div>
          ) : (
            <>
              {/* Hero — only shown when no result */}
              {!hasResult && (
                <div className="text-center space-y-3">
                  <h1 className="text-5xl font-black text-slate-900 tracking-tighter">
                    Ask your codebase.
                  </h1>
                  <p className="text-slate-400 text-lg max-w-md mx-auto leading-snug">
                    Grounded answers from every repo you&apos;ve indexed — no hallucinations.
                  </p>
                </div>
              )}

              {/* Guest banner */}
              {!isLoggedIn && !hasResult && (
                <div className="flex items-center justify-between gap-4 bg-amber-50 border border-amber-200 text-amber-800 rounded-xl px-4 py-3 text-sm">
                  <span>You&apos;re browsing as a guest. Queries are not saved.</span>
                  <Link href="/login" className="shrink-0 font-bold underline hover:text-amber-900">
                    Sign in
                  </Link>
                </div>
              )}

              {/* Source count badge — only shown to logged-in users who have sources */}
              {!hasResult && isLoggedIn && sourcesCount !== null && sourcesCount > 0 && (
                <div className="flex justify-center">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-teal-50 border border-teal-200 text-teal-700 rounded-full text-xs font-semibold">
                    <span className="w-1.5 h-1.5 rounded-full bg-teal-500 inline-block" />
                    Querying across {sourcesCount} indexed source{sourcesCount !== 1 ? "s" : ""}
                  </span>
                </div>
              )}

              {/* Loading indicator while fetching source count */}
              {!hasResult && isLoggedIn && sourcesCount === null && (
                <div className="flex justify-center">
                  <Loader2 size={16} className="text-slate-300 animate-spin" />
                </div>
              )}

              {/* Input */}
              <QueryInput
                isStreaming={isStreaming}
                queriesRemaining={queriesRemaining}
                showRateWarning={showRateWarning}
                onSubmit={(q, opts) => submitQuery(q, { ...opts, authToken: token ?? undefined })}
              />

              {/* Empty state — suggestion chips */}
              {!hasResult && (
                <div className="text-center space-y-4">
                  <p className="text-xs font-black text-slate-300 uppercase tracking-widest">
                    Suggestions
                  </p>
                  <div className="flex flex-wrap justify-center gap-3">
                    {SUGGESTIONS.map((q) => (
                      <button
                        key={q}
                        type="button"
                        onClick={() => submitQuery(q, { authToken: token ?? undefined })}
                        className="px-4 py-2 bg-white border border-slate-200 rounded-full text-xs font-semibold text-slate-500 hover:border-teal-500 hover:text-teal-600 transition-all shadow-sm"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Answer + sources */}
              {hasResult && (
                <StreamingAnswer
                  answer={state.answer}
                  mode={state.mode}
                  confidence={state.confidence}
                  refusalReason={state.refusalReason}
                  sources={state.sources}
                  isStreaming={isStreaming}
                  errorMessage={state.errorMessage}
                />
              )}

              {/* Feedback — only after streaming finishes */}
              {state.status === "complete" && (
                <ThumbsFeedback
                  queryLogId={state.queryLogId}
                  feedbackStatus={state.feedbackStatus}
                  feedbackError={state.feedbackError}
                  onFeedback={(vote) => sendFeedback(vote, token ?? undefined)}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
