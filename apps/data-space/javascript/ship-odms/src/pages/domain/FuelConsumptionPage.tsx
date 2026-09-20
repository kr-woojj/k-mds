

import React from "react";
import { useApiList } from "../../hooks/useApiList";
import { useNavigate } from "react-router-dom";
import { FuelConsumptionTable } from "../../components/domain/FuelConsumptionTable";
import type { FuelConsumption } from "../../types/openapi-types";

export const FuelConsumptionPage: React.FC<{ reportId: number }> = ({ reportId }) => {
  const { data, loading, error } = useApiList(`/performance-reports/${reportId}/fuel-consumptions`);
  const navigate = useNavigate();

  const handleRowClick = (fuel: FuelConsumption) => {
    navigate(`/foc-fuel-types`);
  };

  return (
    <div style={{ maxWidth: 1400, margin: '2rem auto', padding: '1rem' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>연료 소모 내역</h2>
      {error && <div className="api-error-banner">API 서버에 연결할 수 없습니다.</div>}
      <FuelConsumptionTable items={data} loading={loading} error={error} onRowClick={handleRowClick} />
    </div>
  );
};
