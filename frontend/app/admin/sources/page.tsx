"use client";

import { Card, CardHeader, CardBody } from "../../../components/ui/card";
import { SourceList } from "../../../components/admin/SourceList";
import { useAuth } from "../../../hooks/useAuth";

export default function SourcesPage(): JSX.Element {
  const { token } = useAuth();

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-semibold">Ingested Sources</h2>
        <p className="mt-1 text-sm text-slate-500">
          Browse and manage all file sources that have been indexed into Embedlyzer.
        </p>
      </CardHeader>
      <CardBody>
        <SourceList authToken={token ?? ""} />
      </CardBody>
    </Card>
  );
}
