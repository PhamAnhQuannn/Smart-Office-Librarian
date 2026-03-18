"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { BookOpen } from "lucide-react";
import { buildApiUrl } from "../../../lib/api-client";
import { setToken } from "../../../lib/auth";

export default function LoginPage(): JSX.Element {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleLogin(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(buildApiUrl("/api/v1/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        setError("Incorrect email or password.");
        return;
      }
      const data = (await res.json()) as { access_token: string };
      setToken(data.access_token);
      router.replace("/");
    } catch {
      setError("Unable to connect to the server. Please try again.");
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
        <p className="text-slate-500 text-sm">Sign in to your account</p>
      </div>

      <form onSubmit={handleLogin} className="space-y-6">
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
            placeholder="••••••••"
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
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="text-center text-sm text-slate-500">
        No account?{" "}
        <Link href="/signup" className="text-teal-600 font-semibold hover:underline">
          Create one free
        </Link>
      </p>
    </div>
  );
}
