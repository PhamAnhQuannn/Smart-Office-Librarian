"use client";

import { BookOpen, Menu, Plus } from "lucide-react";

interface QueryHeaderProps {
  onNewChat: () => void;
  onMenuOpen?: () => void;
}

export function QueryHeader({ onNewChat, onMenuOpen }: QueryHeaderProps): JSX.Element {
  return (
    <header className="sticky top-0 z-30 flex items-center justify-between h-14 px-4 bg-white border-b border-slate-200 shrink-0">
      {/* Left: mobile menu + brand */}
      <div className="flex items-center gap-3">
        {onMenuOpen && (
          <button
            type="button"
            onClick={onMenuOpen}
            className="md:hidden p-2 rounded-lg text-slate-500 hover:bg-slate-100 transition-colors"
            aria-label="Open menu"
          >
            <Menu size={20} />
          </button>
        )}
        <div className="flex items-center gap-2 text-slate-700">
          <BookOpen size={16} className="text-teal-500" />
          <span className="text-sm font-semibold">Smart Librarian</span>
        </div>
      </div>

      {/* Right: New Chat */}
      <button
        type="button"
        onClick={onNewChat}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 bg-slate-100 border border-slate-200 rounded-lg hover:bg-slate-200 hover:text-slate-800 transition-colors"
      >
        <Plus size={14} />
        New Chat
      </button>
    </header>
  );
}
