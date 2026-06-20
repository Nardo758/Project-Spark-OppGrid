// DataQualityBadge.tsx — React component for the verified data tier
// Shows real-time accuracy & freshness scores from /api/v1/verified/quality-score

import React, { useEffect, useState } from "react";

interface QualityScore {
  dataset: string;
  accuracy_score: number;
  freshness_score: number;
  total_records: number;
  stale_records: number;
}

interface QualityData {
  dataset: string;
  real_time: QualityScore;
  verified_badge: boolean;
  last_audit: {
    date: string;
    accuracy_score: number;
    freshness_score: number;
    total_records: number;
  } | null;
}

interface DataQualityBadgeProps {
  dataset: string;
}

export const DataQualityBadge: React.FC<DataQualityBadgeProps> = ({ dataset }) => {
  const [data, setData] = useState<QualityData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/v1/verified/quality-score/${dataset}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [dataset]);

  if (loading || !data) return null;

  const { real_time, verified_badge } = data;
  const accuracy = real_time?.accuracy_score ?? 0;
  const freshness = real_time?.freshness_score ?? 0;

  return (
    <span
      className={`data-quality-badge ${
        verified_badge ? "dq-verified" : "dq-unverified"
      }`}
      title={`Accuracy: ${accuracy}% · Freshness: ${freshness}% · Total: ${real_time?.total_records ?? 0} · Stale: ${real_time?.stale_records ?? 0}`}
    >
      {verified_badge
        ? `Verified Data · ${accuracy}% accurate · ${freshness}% fresh`
        : `Data Quality · ${accuracy}% accurate`}
    </span>
  );
};
