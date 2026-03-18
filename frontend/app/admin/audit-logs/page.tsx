"use client";

import { getToken } from "../../../lib/auth";
import { AuditLogTable } from "../../../components/admin/AuditLogTable";

export default function AuditLogsPage(): JSX.Element {
  const token = getToken();
  return (
    <div className="p-8 space-y-6">
      <div>
        <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-1">Operate</p>
        <h1 className="text-2xl font-black text-slate-900">Audit Log</h1>
        <p className="text-sm text-slate-500 mt-1">Every query, answer, and source citation — immutable.</p>
      </div>
      <AuditLogTable authToken={token ?? undefined} />
    </div>
  );
}
