"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ArrowLeft,
  BarChart3,
  BookOpen,
  Building2,
  Clock,
  CreditCard,
  Database,
  LogOut,
  Menu,
  Plus,
  Sliders,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "../../lib/utils";
import { clearToken, currentUser, isAuthenticated, isTokenExpired } from "../../lib/auth";
import { ToastProvider, useToast, type ToastItem } from "../../context/toast-context";
import { CheckCircle2, Info, XCircle } from "lucide-react";

// ── Toast ────────────────────────────────────────────────────────────────────

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
      {toasts.map((t) => <ToastBubble key={t.id} t={t} onDismiss={dismissToast} />)}
    </div>
  );
}

// ── Admin nav items ───────────────────────────────────────────────────────────

const MANAGE_NAV = [
  { id: "ingestion",   label: "Ingest",      href: "/admin/ingestion",   icon: Plus },
  { id: "sources",     label: "Sources",     href: "/admin/sources",     icon: Database },
  { id: "workspaces",  label: "Workspaces",  href: "/admin/workspaces",  icon: Building2 },
  { id: "thresholds",  label: "Thresholds",  href: "/admin/thresholds",  icon: Sliders },
];

const OPERATE_NAV = [
  { id: "analytics",  label: "Analytics",  href: "/admin/analytics",  icon: BarChart3 },
  { id: "audit",      label: "Audit Log",  href: "/admin/audit-logs", icon: Clock },
  { id: "budget",     label: "Budget",     href: "/admin/budget",     icon: CreditCard },
];

// ── Admin sidebar ─────────────────────────────────────────────────────────────

function AdminSidebar({ onClose }: { onClose?: () => void }): JSX.Element {
  const pathname = usePathname();
  const router = useRouter();
  const user = currentUser();

  function handleLogout(): void {
    clearToken();
    router.replace("/login");
  }

  const initials = user?.email ? user.email.slice(0, 2).toUpperCase() : "??";

  function NavGroup({ label, items }: { label: string; items: typeof MANAGE_NAV }): JSX.Element {
    return (
      <div className="space-y-1">
        <p className="px-4 text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-2">
          {label}
        </p>
        {items.map((n) => {
          const isActive = pathname === n.href || pathname.startsWith(n.href + "/");
          return (
            <Link
              key={n.id}
              href={n.href}
              onClick={onClose}
              className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-lg transition-all text-sm font-semibold",
                isActive
                  ? "bg-teal-500/10 text-teal-400 border-l-4 border-teal-500 rounded-l-none"
                  : "text-slate-400 hover:text-white hover:bg-white/5",
              )}
            >
              <n.icon size={18} className={isActive ? "text-teal-400" : "text-slate-500"} />
              {n.label}
            </Link>
          );
        })}
      </div>
    );
  }

  return (
    <aside className="w-[260px] bg-slate-950 flex flex-col shrink-0 h-full">
      {/* Header */}
      <div className="p-6 flex items-center justify-between shrink-0 border-b border-white/5">
        <div className="flex items-center gap-2">
          <BookOpen size={22} className="text-teal-400" />
          <div>
            <p className="text-sm font-black text-teal-400 tracking-tighter">Embedlyzer</p>
            <p className="text-xs font-black text-slate-500 uppercase tracking-widest">Admin Panel</p>
          </div>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="md:hidden p-2.5 rounded-lg text-slate-500 hover:text-white hover:bg-white/10 transition-colors"
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        )}
      </div>

      {/* Back to app */}
      <div className="px-4 pt-4">
        <Link
          href="/"
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white hover:bg-white/5 transition-all"
        >
          <ArrowLeft size={14} />
          Back to App
        </Link>
      </div>

      {/* Nav */}
      <div className="flex-1 px-4 py-4 space-y-6 overflow-y-auto">
        <NavGroup label="Manage" items={MANAGE_NAV} />
        <NavGroup label="Operate" items={OPERATE_NAV} />
      </div>

      {/* User footer */}
      <div className="p-6 border-t border-white/5 bg-black/20 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-teal-500 rounded-full flex items-center justify-center font-black text-white text-xs shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-bold text-white truncate">{user?.email ?? "Unknown"}</p>
            <p className="text-xs font-black text-slate-500 uppercase tracking-widest">admin</p>
          </div>
          <button
            onClick={handleLogout}
            className="text-slate-500 hover:text-red-400 transition-colors"
            title="Sign out"
            type="button"
          >
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </aside>
  );
}

// ── Auth guard ────────────────────────────────────────────────────────────────

function AdminAuthShell({ children }: { children: React.ReactNode }): JSX.Element | null {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!isAuthenticated() || isTokenExpired()) {
      clearToken();
      router.replace("/login");
      return;
    }
    const user = currentUser();
    if (user?.role !== "admin") {
      router.replace("/");
      return;
    }
    setReady(true);
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

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-50 md:static md:flex md:shrink-0
        transition-transform duration-200
        ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
      `}>
        <AdminSidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col overflow-hidden bg-white">
        {/* Admin top bar */}
        <header className="sticky top-0 z-30 flex items-center h-14 px-4 bg-slate-950 border-b border-white/5 shrink-0">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors mr-3"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
          <span className="text-sm font-semibold text-slate-300">Admin Panel</span>
        </header>

        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

// ── Public export ─────────────────────────────────────────────────────────────

export function AdminShell({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <ToastProvider>
      <AdminAuthShell>{children}</AdminAuthShell>
    </ToastProvider>
  );
}
