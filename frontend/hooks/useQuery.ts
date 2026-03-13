"use client";

import { useCallback, useMemo, useState } from "react";

import { postFeedback } from "../lib/api-client";
import type { QueryMode } from "../types/api";
import { INITIAL_QUERY_STATE, type QueryState } from "../types/query";
import { useSSEStream } from "./useSSEStream";

const MAX_QUERIES_PER_HOUR = 50;
const RATE_WINDOW_MS = 60 * 60 * 1000;

interface SubmitQueryOptions {
	retrievalOnly?: boolean;
	authToken?: string;
}

interface UseQueryResult {
	state: QueryState;
	isStreaming: boolean;
	queriesRemaining: number;
	showRateWarning: boolean;
	submitQuery: (query: string, options?: SubmitQueryOptions) => Promise<void>;
	sendFeedback: (feedback: 1 | -1, authToken?: string) => Promise<void>;
	resetQuery: () => void;
}

export function useQuery(): UseQueryResult {
	const [state, setState] = useState<QueryState>(INITIAL_QUERY_STATE);
	const [queryCount, setQueryCount] = useState(0);
	const [windowStartMs, setWindowStartMs] = useState(() => Date.now());

	const { startStream, isStreaming } = useSSEStream();

	const refreshRateWindow = useCallback(() => {
		const now = Date.now();
		if (now - windowStartMs > RATE_WINDOW_MS) {
			setWindowStartMs(now);
			setQueryCount(0);
			return true;
		}

		return false;
	}, [windowStartMs]);

	const submitQuery = useCallback(async (query: string, options?: SubmitQueryOptions) => {
		const trimmedQuery = query.trim();
		if (!trimmedQuery) {
			setState((prev) => ({
				...prev,
				status: "error",
				errorMessage: "Please enter a question before submitting.",
			}));
			return;
		}

		const resetHappened = refreshRateWindow();
		if (!resetHappened) {
			setQueryCount((prev) => prev + 1);
		} else {
			setQueryCount(1);
		}

		setState({
			...INITIAL_QUERY_STATE,
			status: "streaming",
		});

		await startStream({
			path: "/api/v1/query",
			authToken: options?.authToken,
			body: {
				query: trimmedQuery,
				retrieval_only: Boolean(options?.retrievalOnly),
			},
			onStart: (event) => {
				setState((prev) => ({
					...prev,
					mode: event.mode,
					queryLogId: event.query_log_id,
					status: "streaming",
				}));
			},
			onToken: (event) => {
				setState((prev) => ({
					...prev,
					answer: `${prev.answer}${event.text}`,
				}));
			},
			onComplete: (event) => {
				const computedMode: QueryMode = event.refusal_reason
					? event.refusal_reason === "LOW_SIMILARITY"
						? "refusal"
						: "retrieval_only"
					: "answer";

				setState((prev) => ({
					...prev,
					status: "complete",
					queryLogId: event.query_log_id,
					confidence: event.confidence,
					refusalReason: event.refusal_reason,
					sources: event.sources,
					mode: prev.mode ?? computedMode,
					errorMessage: null,
				}));
			},
			onError: (error) => {
				setState((prev) => ({
					...prev,
					status: "error",
					errorMessage: error.message,
				}));
			},
		});
	}, [refreshRateWindow, startStream]);

	const sendFeedback = useCallback(async (feedback: 1 | -1, authToken?: string) => {
		if (!state.queryLogId) {
			return;
		}

		setState((prev) => ({
			...prev,
			feedbackStatus: "sending",
			feedbackError: null,
		}));

		try {
			await postFeedback(
				{
					query_log_id: state.queryLogId,
					feedback,
				},
				authToken,
			);

			setState((prev) => ({
				...prev,
				feedbackStatus: "sent",
			}));
		} catch (error) {
			setState((prev) => ({
				...prev,
				feedbackStatus: "error",
				feedbackError: error instanceof Error ? error.message : "Unable to send feedback.",
			}));
		}
	}, [state.queryLogId]);

	const resetQuery = useCallback(() => {
		setState(INITIAL_QUERY_STATE);
	}, []);

	const queriesRemaining = useMemo(() => Math.max(MAX_QUERIES_PER_HOUR - queryCount, 0), [queryCount]);
	const showRateWarning = queriesRemaining <= 5;

	return {
		state,
		isStreaming,
		queriesRemaining,
		showRateWarning,
		submitQuery,
		sendFeedback,
		resetQuery,
	};
}
