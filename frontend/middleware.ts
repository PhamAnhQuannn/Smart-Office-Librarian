/**
 * Next.js Edge Middleware — server-side route protection.
 *
 * Admin routes (/admin/*) are gated here before any page component renders.
 * The check reads the `embed_session` cookie written by auth.ts on login.
 * The cookie contains { role, exp } — it never holds the full JWT.
 *
 * API calls are still protected by JWT verification on the FastAPI backend;
 * this middleware is the UI-layer gate that prevents admin pages from loading
 * for non-admin users without a round-trip to the API.
 */

import { type NextRequest, NextResponse } from "next/server";

interface SessionMeta {
  role: string;
  exp: number;
}

function parseSessionCookie(req: NextRequest): SessionMeta | null {
  const raw = req.cookies.get("embed_session")?.value;
  if (!raw) return null;
  try {
    return JSON.parse(atob(raw)) as SessionMeta;
  } catch {
    return null;
  }
}

function isExpired(exp: number): boolean {
  return Date.now() / 1000 > exp;
}

export function middleware(req: NextRequest): NextResponse {
  const { pathname } = req.nextUrl;

  // ── Admin routes ─────────────────────────────────────────────────────────────
  // Require authenticated admin role. Redirect to /login if missing or expired.
  if (pathname.startsWith("/admin")) {
    const session = parseSessionCookie(req);
    if (!session || isExpired(session.exp) || session.role !== "admin") {
      const loginUrl = req.nextUrl.clone();
      loginUrl.pathname = "/login";
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  // Only run middleware for admin routes.
  // Auth/query routes use page-level or component-level guards.
  matcher: ["/admin/:path*"],
};
