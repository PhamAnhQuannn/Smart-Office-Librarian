"use client";

import Link from "next/link";
import { useEffect } from "react";
import { PlusCircle } from "lucide-react";
import { QueryHeader } from "../../components/query/QueryHeader";
import { QueryInput } from "../../components/query/QueryInput";
import { StreamingAnswer } from "../../components/query/StreamingAnswer";
import { ThumbsFeedback } from "../../components/query/ThumbsFeedback";
import { useQuery } from "../../hooks/useQuery";
import { useAuth } from "../../hooks/useAuth";

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

  const hasResult = state.status !== "idle" || isStreaming;

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

          {/* No-sources CTA */}
          {!hasResult && hasWorkspace && (
            <div className="flex items-center justify-center">
              <Link
                href="/sources"
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-teal-50 border border-teal-200 text-teal-700 rounded-xl text-sm font-semibold hover:bg-teal-100 transition-colors"
              >
                <PlusCircle size={16} />
                Add GitHub repos to query
              </Link>
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
        </div>
      </div>
    </div>
  );
}
