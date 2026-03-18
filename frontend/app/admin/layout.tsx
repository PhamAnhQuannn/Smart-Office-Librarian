import type { ReactNode } from "react";
import { AdminShell } from "../../components/layout/AdminShell";

export const dynamic = "force-dynamic";

export default function AdminLayout({ children }: { children: ReactNode }): JSX.Element {
  return (
    <AdminShell>
      <div className="p-6">
        <div className="mx-auto max-w-5xl">{children}</div>
      </div>
    </AdminShell>
  );
}
