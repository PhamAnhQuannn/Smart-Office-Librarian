"use client";

import { CheckCircle2, Info, X, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { clearToken, isAuthenticated, isTokenExpired } from "../../lib/auth";
import { Sidebar } from "./Sidebar";
import { ToastProvider, useToast, type ToastItem } from "../../context/toast-context";

// ── Toast bubble ────────────────────────────────────────────────────────────

function ToastBubble({ t, onDismiss }: { t: ToastItem; onDismiss: (id: string) => void }): JSX.Element {
  const borderColor =
    t.variant === "error" ? "border-l-rose-500" :
    t.variant === "info"  ? "border-l-cyan-500" :
                            "border-l-teal-500";
  const Icon =
    t.variant === "error" ? XCircle :
    t.variant === "info"  ? Info :
                            CheckCircle2;
  const iconColor =
    t.variant === "error" ? "text-rose-500" :
    t.variant === "info"  ? "text-cyan-500" :
                            "text-teal-500";

  return (
    <div className={`w-80 bg-white border-l-4 ${borderColor} shadow-2xl rounded-lg p-4 flex items-start gap-3 pointer-events-auto`}>
      <Icon size={20} className={`shrink-0 mt-0.5 ${iconColor}`} />
      <div className="flex-1 min-w-0">
        <p className="font-bold text-sm text-slate-900">{t.title}</p>
        <p className="text-xs text-slate-500 mt-0.5">{t.message}</p>
      </div>
      <button onClick={() => onDismiss(t.id)} className="text-slate-300 hover:text-slate-500 transition-colors shrink-0">
        <X size={16} />
      </button>
    </div>
  );
}

function ToastOverlay(): JSX.Element {
  const { toasts, dismissToast } = useToast();
  return (
    <div className="fixed top-6 right-6 z-[500] space-y-3 pointer-events-none">
      {toasts.map((t) => (
        <ToastBubble key={t.id} t={t} onDismiss={dismissToast} />
      ))}
    </div>
  );
}

// ── Auth guard + shell ───────────────────────────────────────────────────────

function AuthenticatedShell({ children }: { children: React.ReactNode }): JSX.Element | null {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!isAuthenticated() || isTokenExpired()) {
      clearToken();
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [router]);

  if (!ready) return null;

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 overflow-hidden">
      <ToastOverlay />

      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar — always visible on md+, slide-in on mobile */}
      <div className={`
        fixed inset-y-0 left-0 z-50 md:static md:flex md:shrink-0
        transition-transform duration-200
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
      `}>
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden bg-white">
        {children}
      </main>
    </div>
  );
}

// ── Public export ─────────────────────────────────────────────────────────────

export function AppShell({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <ToastProvider>
      <AuthenticatedShell>{children}</AuthenticatedShell>
    </ToastProvider>
  );
}
