"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BookOpen,
  Database,
  History,
  LogOut,
  RefreshCw,
  Search,
  Settings,
  X,
  Zap,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { clearToken, currentUser } from "../../lib/auth";

const USER_NAV = [
  { id: "query",   label: "Ask",        href: "/",        icon: Search    },
  { id: "sources", label: "Sources",    href: "/sources", icon: Database  },
  { id: "sync",    label: "Sync",       href: "/sync",    icon: RefreshCw },
  { id: "history", label: "History",    href: "/history", icon: History   },
  { id: "usage",   label: "Usage",      href: "/usage",   icon: Zap       },
  { id: "settings","label": "Settings", href: "/settings",icon: Settings  },
];

export function Sidebar({ onClose }: { onClose?: () => void }): JSX.Element {
  const pathname = usePathname();
  const router = useRouter();
  const user = currentUser();

  function handleLogout(): void {
    clearToken();
    router.replace("/login");
  }

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : "??";

  return (
    <aside className="w-[260px] bg-slate-950 flex flex-col shrink-0 h-full">
      {/* Logo + optional mobile close */}
      <div className="p-6 flex items-center justify-between text-teal-400 shrink-0">
        <div className="flex items-center gap-3 font-black text-xl tracking-tighter">
          <BookOpen size={28} />
          <span>Embedlyzer</span>
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

      {/* User nav */}
      <div className="flex-1 px-4 py-2 space-y-1 overflow-y-auto">
        {USER_NAV.map((n) => {
          const isActive = n.href === "/" ? pathname === "/" : pathname === n.href || pathname.startsWith(n.href + "/");
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

      {/* User identity + logout  ─OR─  guest sign-in prompt */}
      {user ? (
        <div className="p-6 border-t border-white/5 bg-black/20 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-teal-500 rounded-full flex items-center justify-center font-black text-white text-xs shrink-0">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-white truncate">
                {user.email ?? "Unknown"}
              </p>
              {user?.role === "admin" && (
                <Link
                  href="/admin/ingestion"
                  className="text-xs font-black text-teal-500 uppercase tracking-widest hover:text-teal-400 transition-colors"
                >
                  Admin →
                </Link>
              )}
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
      ) : (
        <div className="p-5 border-t border-white/5 bg-black/20 shrink-0 space-y-2">
          <Link
            href="/login"
            className="block w-full text-center py-2.5 bg-teal-500 hover:bg-teal-400 text-white rounded-lg text-sm font-bold transition-colors"
            onClick={onClose}
          >
            Sign In
          </Link>
          <Link
            href="/register"
            className="block w-full text-center py-2 text-teal-400 hover:text-teal-300 text-xs font-semibold transition-colors"
            onClick={onClose}
          >
            Create account
          </Link>
        </div>
      )}
    </aside>
  );
}
