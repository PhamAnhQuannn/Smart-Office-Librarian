"use client";

/**
 * Google OAuth callback page.
 *
 * The backend redirects here as:
 *   /auth/google-callback#<JWT>          — success (fragment, never sent to server)
 *   /login?error=<reason>                — error (backend redirects directly to /login)
 *
 * This page reads the JWT from the URL fragment, stores it via setToken(), then
 * clears the fragment from browser history before redirecting to the app home.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { setToken } from "../../../lib/auth";

export default function GoogleCallbackPage(): JSX.Element {
  const router = useRouter();

  useEffect(() => {
    // Fragment (#...) is never sent to the server — only accessible client-side.
    const fragment = window.location.hash.slice(1); // strip leading '#'
    if (!fragment) {
      router.replace("/login?error=oauth_failed");
      return;
    }

    setToken(fragment);
    // Remove the token from browser history so it doesn't persist in the URL bar.
    window.history.replaceState({}, "", "/auth/google-callback");
    router.replace("/");
  }, [router]);

  return (
    <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-10 text-center space-y-4">
      <div className="w-8 h-8 border-2 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto" />
      <p className="text-slate-500 text-sm">Signing you in with Google…</p>
    </div>
  );
}
