
import React from "react";
import { useApiList } from "../../hooks/useApiList";
import { useNavigate } from "react-router-dom";
import { PerformanceReportTable } from "../../components/domain/PerformanceReportTable";
import { PerformanceReport } from "../../types/openapi-types";

export const PerformanceReportPage: React.FC = () => {
  const voyageId = 1; // TODO: 실제 param 연동 필요
  const { data, loading, error } = useApiList(`/voyages/${voyageId}/performance-reports`);
  const navigate = useNavigate();

  const handleRowClick = (report: PerformanceReport) => {
    navigate(`/performance-reports/${report.id}/fuel-consumptions`);
  };

  return (
    <div style={{ maxWidth: 1400, margin: '2rem auto', padding: '1rem' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>운항 성능 보고</h2>
      {error && <div className="api-error-banner">API 서버에 연결할 수 없습니다.</div>}
      <PerformanceReportTable items={data} loading={loading} error={error} onRowClick={handleRowClick} />
    </div>
  );
};
