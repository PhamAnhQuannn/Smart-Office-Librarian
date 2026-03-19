"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { BookOpen } from "lucide-react";
import { buildApiUrl, postRegister } from "../../../lib/api-client";
import { setToken } from "../../../lib/auth";

function GoogleIcon(): JSX.Element {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}

export default function SignupPage(): JSX.Element {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSignup(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      const data = await postRegister(email, password, displayName);
      setToken(data.access_token);
      router.replace("/");
    } catch (err: unknown) {
      if (err instanceof Error) {
        const apiErr = err as { status?: number; message: string };
        if (apiErr.status === 409) {
          setError("That email is already registered. Try signing in instead.");
        } else {
          setError(apiErr.message || "Registration failed. Please try again.");
        }
      } else {
        setError("Unable to connect to the server. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-md w-full bg-white rounded-2xl shadow-2xl p-10 space-y-8">
      <div className="text-center space-y-3">
        <div className="w-16 h-16 bg-teal-500 rounded-xl flex items-center justify-center mx-auto shadow-lg text-white">
          <BookOpen size={32} />
        </div>
        <h1 className="text-2xl font-black text-slate-900">Embedlyzer</h1>
        <p className="text-slate-500 text-sm">Create your free account</p>
      </div>

      <form onSubmit={handleSignup} className="space-y-5">
        <div className="space-y-1">
          <label className="text-xs font-bold text-slate-400 uppercase tracking-widest px-1">
            Display Name
          </label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Your name or team"
            className="w-full px-4 py-3 rounded-lg border border-slate-200 focus:ring-2 focus:ring-teal-500 outline-none transition-all text-slate-900"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-bold text-slate-400 uppercase tracking-widest px-1">
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
            required
            className="w-full px-4 py-3 rounded-lg border border-slate-200 focus:ring-2 focus:ring-teal-500 outline-none transition-all text-slate-900"
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-bold text-slate-400 uppercase tracking-widest px-1">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Min. 8 characters"
            required
            className="w-full px-4 py-3 rounded-lg border border-slate-200 focus:ring-2 focus:ring-teal-500 outline-none transition-all text-slate-900"
          />
        </div>

        {error && (
          <p className="text-sm text-rose-600 text-center" role="alert">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-4 bg-teal-500 text-white rounded-lg font-bold hover:bg-teal-600 transition-all shadow-lg shadow-teal-500/20 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {loading ? "Creating account…" : "Create account"}
        </button>
      </form>

      {/* Google OAuth */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-slate-200" />
        <span className="text-xs text-slate-400 font-medium">or</span>
        <div className="flex-1 h-px bg-slate-200" />
      </div>
      <a
        href={buildApiUrl("/api/v1/auth/google")}
        className="w-full flex items-center justify-center gap-3 px-4 py-3 border border-slate-200 rounded-lg text-slate-700 font-semibold hover:bg-slate-50 transition-all"
      >
        <GoogleIcon />
        Sign up with Google
      </a>

      <p className="text-center text-sm text-slate-500">
        Already have an account?{" "}
        <Link href="/login" className="text-teal-600 font-semibold hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
