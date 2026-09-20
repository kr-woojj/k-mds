import React from "react";
import { useApiList } from "../../hooks/useApiList";
import { WeatherDetailsTable } from "../../components/domain/WeatherDetailsTable";

export const WeatherDetailsPage: React.FC<{ reportId: number }> = ({ reportId }) => {
  const { data, loading, error } = useApiList(`/performance-reports/${reportId}/weather-details`);
  return (
    <div style={{ maxWidth: 1400, margin: '2rem auto', padding: '1rem' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>기상 정보</h2>
      {error && <div className="api-error-banner">API 서버에 연결할 수 없습니다.</div>}
      <WeatherDetailsTable items={data} loading={loading} error={error} />
    </div>
  );
};
