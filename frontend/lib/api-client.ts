import type { ApiErrorPayload, FeedbackRequestPayload } from "../types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

function withLeadingSlash(path: string): string {
	return path.startsWith("/") ? path : `/${path}`;
}

export function buildApiUrl(path: string): string {
	const normalizedPath = withLeadingSlash(path);
	if (!API_BASE_URL) {
		return normalizedPath;
	}

	return `${API_BASE_URL.replace(/\/$/, "")}${normalizedPath}`;
}

export class ApiClientError extends Error {
	status: number;

	code?: string;

	details?: Record<string, unknown>;

	constructor(message: string, status: number, code?: string, details?: Record<string, unknown>) {
		super(message);
		this.name = "ApiClientError";
		this.status = status;
		this.code = code;
		this.details = details;
	}
}

async function parseApiError(response: Response): Promise<ApiErrorPayload | null> {
	const contentType = response.headers.get("content-type") ?? "";
	if (!contentType.toLowerCase().includes("application/json")) {
		return null;
	}

	try {
		return (await response.json()) as ApiErrorPayload;
	} catch {
		return null;
	}
}

function createHeaders(authToken?: string): HeadersInit {
	const headers: Record<string, string> = {
		"Content-Type": "application/json",
	};

	if (authToken) {
		headers.Authorization = `Bearer ${authToken}`;
	}

	return headers;
}

export async function postFeedback(payload: FeedbackRequestPayload, authToken?: string): Promise<void> {
	const response = await fetch(buildApiUrl("/api/v1/feedback"), {
		method: "POST",
		headers: createHeaders(authToken),
		body: JSON.stringify(payload),
	});

	if (response.ok) {
		return;
	}

	const errorPayload = await parseApiError(response);
	throw new ApiClientError(
		errorPayload?.message ?? "Failed to submit feedback.",
		response.status,
		errorPayload?.error_code,
		errorPayload?.details,
	);
}
