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

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface TokenResponse {
	access_token: string;
	token_type: string;
}

export async function postLogin(email: string, password: string): Promise<TokenResponse> {
	const response = await fetch(buildApiUrl("/api/v1/auth/login"), {
		method: "POST",
		headers: createHeaders(),
		body: JSON.stringify({ email, password }),
	});
	if (response.ok) return response.json() as Promise<TokenResponse>;
	const errorPayload = await parseApiError(response);
	throw new ApiClientError(
		errorPayload?.message ?? "Login failed.",
		response.status,
		errorPayload?.error_code,
	);
}

export async function postRegister(
	email: string,
	password: string,
	display_name?: string,
): Promise<TokenResponse> {
	const response = await fetch(buildApiUrl("/api/v1/auth/register"), {
		method: "POST",
		headers: createHeaders(),
		body: JSON.stringify({ email, password, display_name: display_name ?? "" }),
	});
	if (response.ok) return response.json() as Promise<TokenResponse>;
	const errorPayload = await parseApiError(response);
	throw new ApiClientError(
		errorPayload?.message ?? "Registration failed.",
		response.status,
		errorPayload?.error_code,
	);
}

// ─── Workspace ───────────────────────────────────────────────────────────────

export interface WorkspaceInfo {
	id: string;
	slug: string;
	display_name: string;
	limits: { max_sources: number; max_chunks: number; monthly_query_cap: number };
	usage: { sources: number };
}

export interface WorkspaceSource {
	id: string;
	repo: string;
	file_path: string;
	source_url: string | null;
	last_indexed_sha: string | null;
	created_at: string | null;
}

export async function getWorkspaceMe(authToken: string): Promise<WorkspaceInfo> {
	const response = await fetch(buildApiUrl("/api/v1/workspace/me"), {
		headers: createHeaders(authToken),
	});
	if (response.ok) return response.json() as Promise<WorkspaceInfo>;
	const errorPayload = await parseApiError(response);
	throw new ApiClientError(
		errorPayload?.message ?? "Failed to load workspace.",
		response.status,
		errorPayload?.error_code,
	);
}

export async function getWorkspaceSources(
	authToken: string,
	limit = 50,
	offset = 0,
): Promise<{ sources: WorkspaceSource[]; total: number }> {
	const response = await fetch(
		buildApiUrl(`/api/v1/workspace/sources?limit=${limit}&offset=${offset}`),
		{ headers: createHeaders(authToken) },
	);
	if (response.ok) return response.json() as Promise<{ sources: WorkspaceSource[]; total: number }>;
	const errorPayload = await parseApiError(response);
	throw new ApiClientError(
		errorPayload?.message ?? "Failed to load sources.",
		response.status,
		errorPayload?.error_code,
	);
}

export async function deleteWorkspaceSource(sourceId: string, authToken: string): Promise<void> {
	const response = await fetch(buildApiUrl(`/api/v1/workspace/sources/${encodeURIComponent(sourceId)}`), {
		method: "DELETE",
		headers: createHeaders(authToken),
	});
	if (response.status === 204 || response.ok) return;
	const errorPayload = await parseApiError(response);
	throw new ApiClientError(
		errorPayload?.message ?? "Failed to delete source.",
		response.status,
		errorPayload?.error_code,
	);
}

export async function postIngest(
	repo: string,
	branch: string,
	authToken: string,
): Promise<{ job_id: string; status: string }> {
	const response = await fetch(buildApiUrl("/api/v1/ingest"), {
		method: "POST",
		headers: createHeaders(authToken),
		body: JSON.stringify({ repo, branch }),
	});
	if (response.ok) return response.json() as Promise<{ job_id: string; status: string }>;
	const errorPayload = await parseApiError(response);
	throw new ApiClientError(
		errorPayload?.message ?? "Failed to start ingestion.",
		response.status,
		errorPayload?.error_code,
	);
}

// ─── Admin — Workspaces ────────────────────────────────────────────────────

export interface AdminWorkspace {
	id: string;
	slug: string;
	display_name: string;
	owner_id: string;
	source_count: number;
	limits: { max_sources: number; max_chunks: number; monthly_query_cap: number };
	created_at: string | null;
}

export async function adminListWorkspaces(
	authToken: string,
	limit = 50,
	offset = 0,
): Promise<{ workspaces: AdminWorkspace[] }> {
	const response = await fetch(
		buildApiUrl(`/api/v1/admin/workspaces?limit=${limit}&offset=${offset}`),
		{ headers: createHeaders(authToken) },
	);
	if (response.ok) return response.json() as Promise<{ workspaces: AdminWorkspace[] }>;
	const errorPayload = await parseApiError(response);
	throw new ApiClientError(
		errorPayload?.message ?? "Failed to list workspaces.",
		response.status,
		errorPayload?.error_code,
	);
}

export async function adminDeleteWorkspace(workspaceId: string, authToken: string): Promise<void> {
	const response = await fetch(
		buildApiUrl(`/api/v1/admin/workspaces/${encodeURIComponent(workspaceId)}`),
		{ method: "DELETE", headers: createHeaders(authToken) },
	);
	if (response.ok) return;
	const errorPayload = await parseApiError(response);
	throw new ApiClientError(
		errorPayload?.message ?? "Failed to delete workspace.",
		response.status,
		errorPayload?.error_code,
	);
}

export async function adminUpdateWorkspaceLimits(
	workspaceId: string,
	limits: Partial<AdminWorkspace["limits"]>,
	authToken: string,
): Promise<void> {
	const response = await fetch(
		buildApiUrl(`/api/v1/admin/workspaces/${encodeURIComponent(workspaceId)}/limits`),
		{
			method: "PUT",
			headers: createHeaders(authToken),
			body: JSON.stringify(limits),
		},
	);
	if (response.ok) return;
	const errorPayload = await parseApiError(response);
	throw new ApiClientError(
		errorPayload?.message ?? "Failed to update workspace limits.",
		response.status,
		errorPayload?.error_code,
	);
}

