import React from "react";
import { useApiList } from "../../hooks/useApiList";
import { PortCallTable } from "../../components/domain/PortCallTable";

export const PortCallPage: React.FC<{ voyageId: number }> = ({ voyageId }) => {
  const { data, loading, error } = useApiList(`/voyages/${voyageId}/port-calls`);
  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '1rem' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>입출항 기록</h2>
      {error && <div className="api-error-banner">API 서버에 연결할 수 없습니다.</div>}
      <PortCallTable items={data} loading={loading} error={error} />
    </div>
  );
};
