import type { ConfidenceLevel, QueryMode, RefusalReason } from "../../types/api";
import type { SourceCitation } from "../../types/source";
import { CitationPanel } from "./CitationPanel";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface StreamingAnswerProps {
	answer: string;
	mode: QueryMode | null;
	confidence: ConfidenceLevel | null;
	refusalReason: RefusalReason | null;
	sources: SourceCitation[];
	isStreaming: boolean;
	errorMessage: string | null;
}

function refusalCopy(reason: RefusalReason | null): string {
	if (reason === "LOW_SIMILARITY") {
		return "The retrieved context is not similar enough to provide a reliable answer.";
	}

	if (reason === "BUDGET_EXCEEDED") {
		return "Context budget was exceeded. Showing top sources without generation.";
	}

	if (reason === "LLM_UNAVAILABLE") {
		return "The LLM is temporarily unavailable. Showing retrieved sources only.";
	}

	return "No answer could be generated for this request.";
}

export function StreamingAnswer({
	answer,
	mode,
	confidence,
	refusalReason,
	sources,
	isStreaming,
	errorMessage,
}: StreamingAnswerProps): JSX.Element {
	return (
		<section className="space-y-4 rounded-2xl border border-slate-300 bg-white/90 p-5 shadow-sm">
			<header className="flex flex-wrap items-center justify-between gap-2">
				<h2 className="text-base font-semibold text-slate-900">Answer Stream</h2>
				<div className="flex items-center gap-2">
					{confidence ? <ConfidenceBadge confidence={confidence} /> : null}
					{isStreaming ? <span className="text-xs font-medium text-cyan-700">Streaming...</span> : null}
				</div>
			</header>

			{errorMessage ? (
				<div className="rounded-lg border border-rose-300 bg-rose-50 p-3 text-sm text-rose-800">{errorMessage}</div>
			) : null}

			{mode === "answer" || (!mode && answer) ? (
				<article className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm leading-relaxed text-slate-900 whitespace-pre-wrap">
					{answer || (isStreaming ? "Waiting for first token..." : "No answer content returned.")}
					{isStreaming ? <span className="ml-1 inline-block h-4 w-[2px] animate-pulse bg-cyan-700 align-middle" /> : null}
				</article>
			) : null}

			{mode === "refusal" || mode === "retrieval_only" ? (
				<article className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
					<p className="font-semibold">{mode === "refusal" ? "Refusal" : "Retrieval-only response"}</p>
					<p className="mt-1">{refusalCopy(refusalReason)}</p>
				</article>
			) : null}

			<CitationPanel sources={sources} />
		</section>
	);
}
