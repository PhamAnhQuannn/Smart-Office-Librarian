"use client";

import { Card, CardHeader, CardBody } from "../../../components/ui/card";
import { ThresholdTuner } from "../../../components/admin/ThresholdTuner";
import { useAuth } from "../../../hooks/useAuth";

export default function ThresholdsPage(): JSX.Element {
  const { token } = useAuth();

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-semibold">Threshold Configuration</h2>
        <p className="mt-1 text-sm text-slate-500">
          Tune the similarity threshold used to decide when to answer vs. refuse a query.
        </p>
      </CardHeader>
      <CardBody>
        <ThresholdTuner authToken={token ?? ""} />
      </CardBody>
    </Card>
  );
}
