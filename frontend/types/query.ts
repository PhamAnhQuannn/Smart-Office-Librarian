import type { ConfidenceLevel, QueryMode, RefusalReason } from "./api";
import type { SourceCitation } from "./source";

export type QueryStatus = "idle" | "streaming" | "complete" | "error";
export type FeedbackStatus = "idle" | "sending" | "sent" | "error";

export interface QueryState {
	status: QueryStatus;
	mode: QueryMode | null;
	answer: string;
	confidence: ConfidenceLevel | null;
	refusalReason: RefusalReason | null;
	sources: SourceCitation[];
	queryLogId: string | null;
	errorMessage: string | null;
	feedbackStatus: FeedbackStatus;
	feedbackError: string | null;
}

export const INITIAL_QUERY_STATE: QueryState = {
	status: "idle",
	mode: null,
	answer: "",
	confidence: null,
	refusalReason: null,
	sources: [],
	queryLogId: null,
	errorMessage: null,
	feedbackStatus: "idle",
	feedbackError: null,
};
