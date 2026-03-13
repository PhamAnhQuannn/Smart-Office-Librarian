import type { SourceCitation } from "./source";

export type QueryMode = "answer" | "refusal" | "retrieval_only";
export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";
export type RefusalReason = "LOW_SIMILARITY" | "BUDGET_EXCEEDED" | "LLM_UNAVAILABLE";

export interface QueryRequestPayload {
	query: string;
	retrieval_only?: boolean;
}

export interface ApiErrorPayload {
	error_code?: string;
	message: string;
	request_id?: string;
	details?: Record<string, unknown>;
}

export interface FeedbackRequestPayload {
	query_log_id: string;
	feedback: 1 | -1;
}

export interface SSEStartEvent {
	type: "start";
	query_log_id: string;
	mode: QueryMode;
	model_id?: string;
	index_version?: number;
	namespace?: string;
}

export interface SSETokenEvent {
	type: "token";
	text: string;
}

export interface SSECompleteEvent {
	type: "complete";
	query_log_id: string;
	confidence: ConfidenceLevel;
	refusal_reason: RefusalReason | null;
	sources: SourceCitation[];
}

export interface SSEErrorEvent {
	type: "error";
	error_code?: string;
	message: string;
	request_id?: string;
}

export type SSEEvent = SSEStartEvent | SSETokenEvent | SSECompleteEvent | SSEErrorEvent;

export interface StreamError {
	code?: string;
	message: string;
}
