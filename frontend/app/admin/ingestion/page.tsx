"use client";

import { useState } from "react";
import { Card, CardHeader, CardBody } from "../../../components/ui/card";
import { IngestForm } from "../../../components/admin/IngestForm";
import { IngestRunMonitor } from "../../../components/admin/IngestRunMonitor";
import { useAuth } from "../../../hooks/useAuth";

export default function AdminIngestionPage(): JSX.Element {
  const { token } = useAuth();
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Platform Ingestion</h1>
        <p className="text-sm text-slate-500 mt-1">
          Trigger ingestion jobs on behalf of any workspace. For your own workspace, use{" "}
          <a href="/sync" className="text-teal-600 hover:underline font-medium">Sync</a> in the main app.
        </p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold">Ingest to workspace</h2>
        </CardHeader>
        <CardBody>
          <IngestForm
            authToken={token ?? ""}
            onSuccess={() => setRefreshTrigger((n) => n + 1)}
          />
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold">All recent ingest runs</h2>
        </CardHeader>
        <CardBody>
          <IngestRunMonitor authToken={token ?? ""} refreshTrigger={refreshTrigger} />
        </CardBody>
      </Card>
    </div>
  );
}
