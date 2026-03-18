"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";
import type { FeedbackStatus } from "../../types/query";

interface ThumbsFeedbackProps {
  queryLogId: string | null;
  feedbackStatus: FeedbackStatus;
  feedbackError: string | null;
  onFeedback: (feedback: 1 | -1) => Promise<void>;
}

export function ThumbsFeedback({
  queryLogId,
  feedbackStatus,
  feedbackError,
  onFeedback,
}: ThumbsFeedbackProps): JSX.Element {
  const disabled = !queryLogId || feedbackStatus === "sending" || feedbackStatus === "sent";

  if (feedbackStatus === "sent") {
    return (
      <p className="text-center text-xs font-bold text-teal-600 uppercase tracking-widest">
        Thanks for your feedback!
      </p>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
        Was this helpful?
      </p>
      <div className="flex gap-3">
        <button
          type="button"
          disabled={disabled}
          onClick={() => onFeedback(1)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-500 hover:border-teal-500 hover:text-teal-600 transition-all text-sm font-bold shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ThumbsUp size={16} /> Helpful
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => onFeedback(-1)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-500 hover:border-rose-400 hover:text-rose-500 transition-all text-sm font-bold shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ThumbsDown size={16} /> Not helpful
        </button>
      </div>
      {feedbackStatus === "error" && feedbackError && (
        <p className="text-xs text-rose-600">{feedbackError}</p>
      )}
    </div>
  );
}

