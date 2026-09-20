
import React from "react";
import { useApiList } from "../../hooks/useApiList";
import { useNavigate } from "react-router-dom";
import { ShipTable } from "../../components/domain/ShipTable";

export const ShipListPage: React.FC = () => {
  const { data, loading, error } = useApiList("/ships");
  const navigate = useNavigate();

  const handleRowClick = (ship) => {
    navigate(`/ships/${ship.id}/yearly-reports`);
  };

  return (
    <div style={{ maxWidth: 1200, margin: '2rem auto', padding: '1rem' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '1.5rem' }}>선박 목록</h1>
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
      <ShipTable items={data} loading={loading} error={error} onRowClick={handleRowClick} />
    </div>
  );
};
