"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Trash2, AlertTriangle } from "lucide-react";
import { getWorkspaceMe, ApiClientError, type WorkspaceInfo } from "../../../lib/api-client";
import { getToken, currentUser } from "../../../lib/auth";
import { useToast } from "../../../context/toast-context";

export default function SettingsPage(): JSX.Element {
  const router = useRouter();
  const { addToast } = useToast();
  const [workspace, setWorkspace] = useState<WorkspaceInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const user = currentUser();

  useEffect(() => {
    const token = getToken();
    if (!token) { router.replace("/login"); return; }
    getWorkspaceMe(token)
      .then(setWorkspace)
      .catch((err: unknown) => {
        if (err instanceof ApiClientError && err.status === 401) router.replace("/login");
      })
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) return (
    <div className="flex items-center justify-center h-48 text-sm text-slate-400">Loading&hellip;</div>
  );

  return (
    <div className="max-w-xl mx-auto space-y-8 py-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500 mt-1">Manage your workspace preferences.</p>
      </div>

      {/* Account */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-3">
        <h2 className="text-sm font-black text-slate-500 uppercase tracking-widest">Account</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
            <span className="text-slate-500">Email</span>
            <span className="font-medium text-slate-800">{user?.email ?? "—"}</span>
          </div>
          <div className="flex justify-between items-center py-1.5 border-b border-slate-100">
            <span className="text-slate-500">Role</span>
            <span className="font-medium text-slate-800 capitalize">{user?.role ?? "—"}</span>
          </div>
          {workspace && (
            <div className="flex justify-between items-center py-1.5">
              <span className="text-slate-500">Workspace</span>
              <span className="font-medium text-slate-800">{workspace.display_name}</span>
            </div>
          )}
        </div>
      </div>

      {/* Answer quality */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-3">
        <h2 className="text-sm font-black text-slate-500 uppercase tracking-widest">Answer quality</h2>
        <p className="text-sm text-slate-500">
          Embedlyzer automatically tunes retrieval quality. No manual configuration needed — the system will refuse to answer rather than guess when it doesn&apos;t have enough context.
        </p>
      </div>

      {/* Danger zone */}
      <div className="bg-rose-50 border border-rose-200 rounded-2xl p-5 space-y-3">
        <h2 className="text-sm font-black text-rose-600 uppercase tracking-widest">Danger zone</h2>
        {!confirmDelete ? (
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-slate-800">Clear all workspace data</p>
              <p className="text-xs text-slate-500 mt-0.5">Remove all indexed sources and vectors from your workspace. This cannot be undone.</p>
            </div>
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="shrink-0 flex items-center gap-1.5 px-4 py-2 bg-white border border-rose-300 text-rose-600 text-sm font-bold rounded-xl hover:bg-rose-50 transition-colors"
            >
              <Trash2 size={14} /> Clear data
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-rose-600 font-semibold text-sm">
              <AlertTriangle size={16} />
              Are you sure? This will permanently delete all your sources.
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  addToast("Not implemented", "Workspace wipe coming in a future release.", "info");
                  setConfirmDelete(false);
                }}
                className="px-4 py-2 bg-rose-500 hover:bg-rose-600 text-white text-sm font-bold rounded-xl transition-colors"
              >
                Yes, clear everything
              </button>
              <button
                type="button"
                onClick={() => setConfirmDelete(false)}
                className="px-4 py-2 bg-white border border-slate-200 text-slate-600 text-sm font-semibold rounded-xl hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
