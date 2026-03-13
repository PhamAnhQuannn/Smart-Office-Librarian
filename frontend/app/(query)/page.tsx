"use client";

import { QueryInput } from "../../components/query/QueryInput";
import { StreamingAnswer } from "../../components/query/StreamingAnswer";
import { ThumbsFeedback } from "../../components/query/ThumbsFeedback";
import { useQuery } from "../../hooks/useQuery";

export default function QueryPage(): JSX.Element {
	const { state, isStreaming, queriesRemaining, showRateWarning, submitQuery, sendFeedback } = useQuery();

	return (
		<section className="space-y-5">
			<header className="rounded-2xl border border-cyan-300/40 bg-white/10 p-6 backdrop-blur-sm">
				<p className="text-xs uppercase tracking-[0.18em] text-cyan-200">Smart Office Librarian</p>
				<h1 className="mt-2 text-3xl font-semibold text-white sm:text-4xl">Live Query Console</h1>
				<p className="mt-3 max-w-2xl text-sm text-cyan-100/90">
					Ask a question and watch the response stream in real time. Every answer includes confidence and source snippets so users can inspect traceability.
				</p>
			</header>

			<QueryInput
				isStreaming={isStreaming}
				queriesRemaining={queriesRemaining}
				showRateWarning={showRateWarning}
				onSubmit={submitQuery}
			/>

			<StreamingAnswer
				answer={state.answer}
				mode={state.mode}
				confidence={state.confidence}
				refusalReason={state.refusalReason}
				sources={state.sources}
				isStreaming={isStreaming}
				errorMessage={state.errorMessage}
			/>

			<ThumbsFeedback
				queryLogId={state.queryLogId}
				feedbackStatus={state.feedbackStatus}
				feedbackError={state.feedbackError}
				onFeedback={sendFeedback}
			/>
		</section>
	);
}
