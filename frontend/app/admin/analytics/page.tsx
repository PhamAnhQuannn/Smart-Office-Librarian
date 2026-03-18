"use client";

import { Card, CardHeader, CardBody } from "../../../components/ui/card";
import { AnalyticsDashboard } from "../../../components/admin/AnalyticsDashboard";
import { useAuth } from "../../../hooks/useAuth";

export default function AnalyticsPage(): JSX.Element {
  const { token } = useAuth();

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-semibold">Analytics</h2>
        <p className="mt-1 text-sm text-slate-500">
          Query volume, confidence distribution, token usage, and refusal rates.
        </p>
      </CardHeader>
      <CardBody>
        <AnalyticsDashboard authToken={token ?? ""} />
      </CardBody>
    </Card>
  );
}
