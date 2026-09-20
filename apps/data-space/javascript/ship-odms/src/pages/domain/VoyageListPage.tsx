
import React from "react";
import { useApiList } from "../../hooks/useApiList";
import { useNavigate } from "react-router-dom";
import { VoyageTable } from "../../components/domain/VoyageTable";
import { Voyage } from "../../types/openapi-types";

interface VoyageListPageProps {
  shipId: number;
  yearReportId?: number;
}

export const VoyageListPage: React.FC<VoyageListPageProps> = ({ shipId, yearReportId }) => {
  const { data, loading, error } = useApiList(`/ships/${shipId}/voyages`);
  const navigate = useNavigate();

  // yearReportId가 주어지면 해당 연차보고 ID만 필터링
  const filtered = yearReportId ? (Array.isArray(data) ? data.filter(v => v.year_report_id === yearReportId) : []) : data;

  const handleRowClick = (voyage: Voyage) => {
    navigate(`/voyages/${voyage.id}/performance-reports`);
  };

  return (
    <div style={{ maxWidth: 1200, margin: '2rem auto', padding: '1rem' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>항해 이력</h2>
      {error && <div className="api-error-banner">API 서버에 연결할 수 없습니다.</div>}
      <VoyageTable items={filtered} loading={loading} error={error} onRowClick={handleRowClick} />
    </div>
  );
};
