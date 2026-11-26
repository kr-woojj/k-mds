import React, { useEffect, useState } from 'react';
import { apiRequest } from '../api/client';
import YearPerformanceReportTable from '../components/YearPerformanceReportTable';
import ApiErrorBanner from '../components/ApiErrorBanner';
import Loading from '../components/Loading';

export default function YearPerformanceReportPage({ shipId }) {
  const [reports, setReports] = useState([]);
  const [error, setError] = useState(null);
  // 마지막으로 불러오기를 마친 shipId. 현재 shipId와 다르면 로딩 중이다.
  const [loadedKey, setLoadedKey] = useState(null);

  useEffect(() => {
    if (!shipId) return;
    apiRequest(`/ships/${shipId}/yearly-reports`)
      .then(data => {
        setReports(data || []);
        setError(null);
      })
      .catch(err => {
        setError(err);
        setReports([]);
      })
      .finally(() => setLoadedKey(shipId));
  }, [shipId]);

  const loading = loadedKey !== shipId;

  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '1rem' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>연차 실적 보고</h2>
      <ApiErrorBanner error={error} />
      {loading ? <Loading /> : <YearPerformanceReportTable reports={reports} />}
    </div>
  );
}
