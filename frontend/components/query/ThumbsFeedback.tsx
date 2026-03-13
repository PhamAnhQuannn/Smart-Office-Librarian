"use client";

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
	const disabled = !queryLogId || feedbackStatus === "sending";

	return (
		<section className="rounded-xl border border-slate-300 bg-white/90 p-4 shadow-sm">
			<p className="text-sm font-semibold text-slate-900">Was this answer helpful?</p>

			<div className="mt-3 flex gap-2">
				<button
					type="button"
					disabled={disabled}
					onClick={() => onFeedback(1)}
					className="rounded-lg border border-emerald-500 bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-800 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
				>
					Thumbs up
				</button>

				<button
					type="button"
					disabled={disabled}
					onClick={() => onFeedback(-1)}
					className="rounded-lg border border-rose-500 bg-rose-50 px-3 py-1 text-sm font-medium text-rose-800 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
				>
					Thumbs down
				</button>
			</div>

			{feedbackStatus === "sent" ? (
				<p className="mt-2 text-xs text-emerald-700">Thanks, your feedback was saved.</p>
			) : null}

			{feedbackStatus === "error" && feedbackError ? (
				<p className="mt-2 text-xs text-rose-700">{feedbackError}</p>
			) : null}
		</section>
	);
}
