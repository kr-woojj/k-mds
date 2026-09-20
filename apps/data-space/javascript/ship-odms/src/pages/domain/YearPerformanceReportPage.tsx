
import React from "react";
import { useApiList } from "../../hooks/useApiList";
import { useNavigate } from "react-router-dom";
import { YearPerformanceReportTable } from "../../components/domain/YearPerformanceReportTable";

import { Link } from "react-router-dom";

interface YearPerformanceReportPageProps {
  shipId: number;
}

export const YearPerformanceReportPage: React.FC<YearPerformanceReportPageProps> = ({ shipId }) => {
  const { data, loading, error } = useApiList(`/ships/${shipId}/yearly-reports`);
  const navigate = useNavigate();

  const handleRowClick = (report) => {
    navigate(`/ships/${report.ship_id}/voyages`);
  };

  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '1rem' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>연차 실적 보고</h2>
      {error && (
        <div style={{
          background: '#ffe0e0',
          color: '#b00020',
          padding: '1rem',
          borderRadius: '4px',
          marginBottom: '1rem',
          border: '1px solid #b00020',
          fontWeight: 'bold',
        }}>
          <span>백엔드 API 서버에 연결할 수 없습니다.</span>
          <div style={{ fontSize: '0.9em', marginTop: '0.5em' }}>{error.message || String(error)}</div>
        </div>
      )}
      <YearPerformanceReportTable items={data} loading={loading} error={error} onRowClick={handleRowClick} />
    </div>
  );
};
