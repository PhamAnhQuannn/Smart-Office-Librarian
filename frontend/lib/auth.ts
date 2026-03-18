/**
 * Client-side auth utilities.
 *
 * Token stored in sessionStorage so a tab refresh doesn't log the user out.
 * Cleared on tab close. Never written to localStorage to limit XSS exposure.
 */
import type { AuthUser, UserRole } from "../types/user";

const SESSION_KEY = "embed_token";

function readRaw(): string | null {
  if (typeof window === "undefined") return null;
  try { return window.sessionStorage.getItem(SESSION_KEY); } catch { return null; }
}

/** Store the JWT in sessionStorage. */
export function setToken(jwt: string): void {
  if (typeof window === "undefined") return;
  try { window.sessionStorage.setItem(SESSION_KEY, jwt); } catch {}
}

/** Return the stored JWT, or null if unauthenticated. */
export function getToken(): string | null {
  return readRaw();
}

/** Clear the stored JWT (logout). */
export function clearToken(): void {
  if (typeof window === "undefined") return;
  try { window.sessionStorage.removeItem(SESSION_KEY); } catch {}
}

/** True when a valid token exists in sessionStorage. */
export function isAuthenticated(): boolean {
  return readRaw() !== null;
}

/**
 * Decode the JWT payload without verification (server verifies on every
 * request). Used only for reading display fields like role and email.
 */
export function decodePayload(jwt: string): AuthUser | null {
  try {
    const parts = jwt.split(".");
    if (parts.length !== 3) return null;
    const padded = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(padded)) as AuthUser;
  } catch {
    return null;
  }
}

/** Return the decoded payload for the current token, or null. */
export function currentUser(): AuthUser | null {
  const token = readRaw();
  if (!token) return null;
  return decodePayload(token);
}

/** True when the current token has expired. */
export function isTokenExpired(): boolean {
  const user = currentUser();
  if (!user) return true;
  return Date.now() / 1_000 > user.exp;
}

/** Return true when the current user has the required role. */
export function hasRole(required: UserRole): boolean {
  const user = currentUser();
  if (!user) return false;
  if (required === "user") return true;
  return user.role === required;
}
