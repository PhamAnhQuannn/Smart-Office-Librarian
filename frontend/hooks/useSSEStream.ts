"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { buildApiUrl } from "../lib/api-client";
import type {
	ApiErrorPayload,
	SSECompleteEvent,
	SSEErrorEvent,
	SSEEvent,
	SSEStartEvent,
	SSETokenEvent,
	StreamError,
} from "../types/api";

export interface StartStreamOptions {
	path: string;
	body: Record<string, unknown>;
	authToken?: string;
	onStart?: (event: SSEStartEvent) => void;
	onToken?: (event: SSETokenEvent) => void;
	onComplete?: (event: SSECompleteEvent) => void;
	onError?: (error: StreamError) => void;
}

export interface UseSSEStreamResult {
	isStreaming: boolean;
	streamError: StreamError | null;
	startStream: (options: StartStreamOptions) => Promise<void>;
	cancelStream: () => void;
}

const SSE_JSON_HEADERS = {
	Accept: "text/event-stream",
	"Content-Type": "application/json",
};

function parseEventPayload(payload: string): SSEEvent | null {
	try {
		const parsed = JSON.parse(payload) as SSEEvent;
		if (!parsed || typeof parsed !== "object" || !("type" in parsed)) {
			return null;
		}

		return parsed;
	} catch {
		return null;
	}
}

async function parseErrorResponse(response: Response): Promise<StreamError> {
	const contentType = response.headers.get("content-type") ?? "";
	if (!contentType.toLowerCase().includes("application/json")) {
		return {
			message: `Request failed with status ${response.status}.`,
		};
	}

	try {
		const payload = (await response.json()) as ApiErrorPayload;
		return {
			code: payload.error_code,
			message: payload.message || `Request failed with status ${response.status}.`,
		};
	} catch {
		return {
			message: `Request failed with status ${response.status}.`,
		};
	}
}

export function useSSEStream(): UseSSEStreamResult {
	const [isStreaming, setIsStreaming] = useState(false);
	const [streamError, setStreamError] = useState<StreamError | null>(null);
	const abortRef = useRef<AbortController | null>(null);

	const cancelStream = useCallback(() => {
		if (abortRef.current) {
			abortRef.current.abort();
			abortRef.current = null;
		}
		setIsStreaming(false);
	}, []);

	useEffect(() => cancelStream, [cancelStream]);

	const startStream = useCallback(async (options: StartStreamOptions) => {
		cancelStream();

		const abortController = new AbortController();
		abortRef.current = abortController;
		setStreamError(null);
		setIsStreaming(true);

		try {
			const headers: Record<string, string> = { ...SSE_JSON_HEADERS };
			if (options.authToken) {
				headers.Authorization = `Bearer ${options.authToken}`;
			}

			const response = await fetch(buildApiUrl(options.path), {
				method: "POST",
				headers,
				body: JSON.stringify(options.body),
				signal: abortController.signal,
			});

			if (!response.ok || !response.body) {
				const error = await parseErrorResponse(response);
				setStreamError(error);
				options.onError?.(error);
				setIsStreaming(false);
				return;
			}

			const reader = response.body.getReader();
			const decoder = new TextDecoder("utf-8");

			let carryOver = "";
			let dataLines: string[] = [];
			let shouldStop = false;

			const flushDataLines = () => {
				if (dataLines.length === 0) {
					return;
				}

				const payload = dataLines.join("\n");
				dataLines = [];

				const parsedEvent = parseEventPayload(payload);
				if (!parsedEvent) {
					const malformedError: StreamError = {
						code: "MALFORMED_SSE_MESSAGE",
						message: "Received malformed SSE payload.",
					};
					setStreamError(malformedError);
					options.onError?.(malformedError);
					shouldStop = true;
					return;
				}

				if (parsedEvent.type === "start") {
					options.onStart?.(parsedEvent);
					return;
				}

				if (parsedEvent.type === "token") {
					options.onToken?.(parsedEvent);
					return;
				}

				if (parsedEvent.type === "complete") {
					options.onComplete?.(parsedEvent);
					shouldStop = true;
					return;
				}

				if (parsedEvent.type === "error") {
					const streamErr: StreamError = {
						code: (parsedEvent as SSEErrorEvent).error_code,
						message: parsedEvent.message,
					};
					setStreamError(streamErr);
					options.onError?.(streamErr);
					shouldStop = true;
				}
			};

			while (!shouldStop) {
				const { value, done } = await reader.read();
				if (done) {
					break;
				}

				carryOver += decoder.decode(value, { stream: true });
				const lines = carryOver.split(/\r?\n/);
				carryOver = lines.pop() ?? "";

				for (const line of lines) {
					if (!line) {
						flushDataLines();
						if (shouldStop) {
							break;
						}
						continue;
					}

					if (line.startsWith(":")) {
						continue;
					}

					if (line.startsWith("data:")) {
						dataLines.push(line.slice(5).replace(/^\s/, ""));
					}
				}
			}

			carryOver += decoder.decode();
			if (carryOver) {
				for (const line of carryOver.split(/\r?\n/)) {
					if (!line) {
						flushDataLines();
						continue;
					}

					if (line.startsWith(":")) {
						continue;
					}

					if (line.startsWith("data:")) {
						dataLines.push(line.slice(5).replace(/^\s/, ""));
					}
				}
			}

			flushDataLines();
			await reader.cancel();
		} catch (error) {
			if (!abortController.signal.aborted) {
				const streamErr: StreamError = {
					message: error instanceof Error ? error.message : "Unknown stream error.",
				};
				setStreamError(streamErr);
				options.onError?.(streamErr);
			}
		} finally {
			if (abortRef.current === abortController) {
				abortRef.current = null;
			}
			setIsStreaming(false);
		}
	}, [cancelStream]);

	return {
		isStreaming,
		streamError,
		startStream,
		cancelStream,
	};
}
