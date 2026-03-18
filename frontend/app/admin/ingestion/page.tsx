"use client";

import { useState } from "react";
import { Card, CardHeader, CardBody } from "../../../components/ui/card";
import { IngestForm } from "../../../components/admin/IngestForm";
import { IngestRunMonitor } from "../../../components/admin/IngestRunMonitor";
import { useAuth } from "../../../hooks/useAuth";

export default function IngestionPage(): JSX.Element {
  const { token } = useAuth();
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Ingest Source</h2>
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
          <h2 className="text-lg font-semibold">Recent Ingest Runs</h2>
        </CardHeader>
        <CardBody>
          <IngestRunMonitor authToken={token ?? ""} refreshTrigger={refreshTrigger} />
        </CardBody>
      </Card>
    </div>
  );
}
