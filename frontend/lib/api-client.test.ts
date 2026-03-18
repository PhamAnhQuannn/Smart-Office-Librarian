import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("buildApiUrl", () => {
  it("returns a relative path when NEXT_PUBLIC_API_BASE_URL is unset", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    const { buildApiUrl } = await import("./api-client");

    expect(buildApiUrl("api/v1/feedback")).toBe("/api/v1/feedback");
  });

  it("prefixes the configured API origin and normalizes slashes", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "https://api.example.com/");
    const { buildApiUrl } = await import("./api-client");

    expect(buildApiUrl("/api/v1/feedback")).toBe("https://api.example.com/api/v1/feedback");
  });
});

describe("ApiClientError", () => {
  it("preserves status, code, and details for callers", async () => {
    const { ApiClientError } = await import("./api-client");

    const error = new ApiClientError("failure", 429, "RATE_LIMIT_EXCEEDED", { retry_after_seconds: 60 });

    expect(error.name).toBe("ApiClientError");
    expect(error.status).toBe(429);
    expect(error.code).toBe("RATE_LIMIT_EXCEEDED");
    expect(error.details).toEqual({ retry_after_seconds: 60 });
  });
});