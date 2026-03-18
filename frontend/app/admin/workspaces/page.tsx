"use client";

import { useEffect, useState } from "react";
import { Building2, RefreshCw, Trash2, X } from "lucide-react";
import { Card, CardHeader, CardBody } from "../../../components/ui/card";
import { useAuth } from "../../../hooks/useAuth";
import {
  adminListWorkspaces,
  adminDeleteWorkspace,
  type AdminWorkspace,
  ApiClientError,
} from "../../../lib/api-client";
import { formatDate } from "../../../lib/utils";

function DeleteDialog({
  workspace,
  onConfirm,
  onCancel,
  loading,
}: {
  workspace: AdminWorkspace;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backdropFilter: "blur(4px)", background: "rgba(15,23,42,0.4)" }}
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl space-y-6">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs font-black text-rose-500 uppercase tracking-widest">Confirm deletion</p>
            <p className="font-black text-slate-900 text-lg">Delete workspace &ldquo;{workspace.slug}&rdquo;?</p>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-all"
          >
            <X size={20} />
          </button>
        </div>
        <p className="text-sm text-slate-500">
          This permanently removes the workspace, all {workspace.source_count} source(s), and all associated
          vector data. This action <strong>cannot be undone</strong>.
        </p>
        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 rounded-lg text-sm font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-rose-500 text-white text-sm font-bold hover:bg-rose-600 transition-colors disabled:opacity-60"
          >
            {loading ? "Deleting…" : "Delete workspace"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AdminWorkspacesPage(): JSX.Element {
  const { token } = useAuth();
  const [workspaces, setWorkspaces] = useState<AdminWorkspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<AdminWorkspace | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function loadWorkspaces(): Promise<void> {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const { workspaces: ws } = await adminListWorkspaces(token);
      setWorkspaces(ws);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Failed to load workspaces.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadWorkspaces(); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleDelete(): Promise<void> {
    if (!deleteTarget || !token) return;
    setDeleting(true);
    try {
      await adminDeleteWorkspace(deleteTarget.id, token);
      setWorkspaces((prev) => prev.filter((w) => w.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      if (err instanceof ApiClientError) {
        setError(err.message);
      } else {
        setError("Failed to delete workspace.");
      }
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      {deleteTarget && (
        <DeleteDialog
          workspace={deleteTarget}
          onConfirm={() => void handleDelete()}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Building2 size={20} className="text-slate-500" />
              <div>
                <h2 className="text-lg font-semibold">Workspaces</h2>
                <p className="mt-0.5 text-sm text-slate-500">
                  {workspaces.length} workspace{workspaces.length !== 1 ? "s" : ""}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => void loadWorkspaces()}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-all"
              title="Refresh"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
        </CardHeader>

        <CardBody>
          {error && (
            <p className="text-sm text-rose-500 mb-4" role="alert">{error}</p>
          )}

          {loading && workspaces.length === 0 ? (
            <p className="text-sm text-slate-400 py-8 text-center">Loading…</p>
          ) : workspaces.length === 0 ? (
            <p className="text-sm text-slate-400 py-8 text-center">No workspaces found.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left">
                    <th className="pb-3 pr-4 font-semibold text-slate-600">Slug</th>
                    <th className="pb-3 pr-4 font-semibold text-slate-600">Display name</th>
                    <th className="pb-3 pr-4 font-semibold text-slate-600 text-right">Sources</th>
                    <th className="pb-3 pr-4 font-semibold text-slate-600 text-right">Query cap</th>
                    <th className="pb-3 font-semibold text-slate-600">Created</th>
                    <th className="pb-3 w-10" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {workspaces.map((ws) => (
                    <tr key={ws.id} className="group">
                      <td className="py-3 pr-4">
                        <span className="font-mono text-xs bg-slate-100 px-2 py-1 rounded text-slate-700">
                          {ws.slug}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-slate-700">{ws.display_name}</td>
                      <td className="py-3 pr-4 text-right tabular-nums text-slate-600">
                        {ws.source_count}
                        <span className="text-slate-400"> / {ws.limits.max_sources}</span>
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-slate-600">
                        {ws.limits.monthly_query_cap}
                      </td>
                      <td className="py-3 text-slate-500">
                        {ws.created_at ? formatDate(ws.created_at) : "—"}
                      </td>
                      <td className="py-3">
                        <button
                          type="button"
                          onClick={() => setDeleteTarget(ws)}
                          title="Delete workspace"
                          className="p-1.5 rounded text-slate-300 hover:text-rose-500 hover:bg-rose-50 transition-colors opacity-0 group-hover:opacity-100"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </>
  );
}
