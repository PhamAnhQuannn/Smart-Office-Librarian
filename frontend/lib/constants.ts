/** Maximum number of characters allowed in a single query input. */
export const MAX_QUERY_CHARS = 1_000;

/** Base URL for the backend API, injected at build time via .env */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

/** SSE streaming query endpoint on the backend. */
export const SSE_QUERY_ENDPOINT = "/api/v1/query";

/** Feedback endpoint. */
export const FEEDBACK_ENDPOINT = "/api/v1/feedback";

/** Admin endpoints */
export const ADMIN_THRESHOLDS_ENDPOINT = "/api/v1/admin/thresholds";
export const ADMIN_SOURCES_ENDPOINT = "/api/v1/admin/sources";
export const ADMIN_AUDIT_LOGS_ENDPOINT = "/api/v1/admin/audit-logs";
export const ADMIN_INGEST_RUNS_ENDPOINT = "/api/v1/admin/ingest-runs";
export const INGEST_ENDPOINT = "/api/v1/ingest";

/** Rate limiting (client-side guard, mirrors server-side rule). */
export const MAX_QUERIES_PER_HOUR = 50;
export const RATE_WINDOW_MS = 60 * 60 * 1_000;

/** Confidence badge label map. */
export const CONFIDENCE_LABELS: Record<string, string> = {
  HIGH: "High confidence",
  MEDIUM: "Medium confidence",
  LOW: "Low confidence",
};

/** Human-readable refusal reasons. */
export const REFUSAL_REASON_LABELS: Record<string, string> = {
  LOW_SIMILARITY: "No sufficiently relevant documents found.",
  BUDGET_EXCEEDED: "Monthly token budget has been exhausted.",
  LLM_UNAVAILABLE: "The language model is temporarily unavailable.",
};

/** Application display name. */
export const APP_NAME = "Embedlyzer";

/** Nav links used in the sidebar / header. */
export const NAV_LINKS = [
  { label: "Query", href: "/query" },
  { label: "Admin", href: "/admin" },
] as const;
