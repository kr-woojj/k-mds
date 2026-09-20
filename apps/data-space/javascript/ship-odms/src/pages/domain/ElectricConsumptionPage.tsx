import React from "react";
import { useApiList } from "../../hooks/useApiList";
import { ElectricConsumptionTable } from "../../components/domain/ElectricConsumptionTable";

export const ElectricConsumptionPage: React.FC<{ reportId: number }> = ({ reportId }) => {
  const { data, loading, error } = useApiList(`/performance-reports/${reportId}/electric-consumptions`);
  return (
    <div style={{ maxWidth: 1400, margin: '2rem auto', padding: '1rem' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>전력 소모 내역</h2>
      {error && <div className="api-error-banner">API 서버에 연결할 수 없습니다.</div>}
      <ElectricConsumptionTable items={data} loading={loading} error={error} />
    </div>
  );
};
