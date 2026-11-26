import React, { useEffect, useState } from 'react';
import { apiRequest } from '../api/client';
import PerformanceReportTable from '../components/PerformanceReportTable';
import ApiErrorBanner from '../components/ApiErrorBanner';
import Loading from '../components/Loading';

export default function PerformanceReportPage({ voyageId }) {
  const [reports, setReports] = useState([]);
  const [error, setError] = useState(null);
  // 마지막으로 불러오기를 마친 voyageId. 현재 voyageId와 다르면 로딩 중이다.
  const [loadedKey, setLoadedKey] = useState(null);

  useEffect(() => {
    if (!voyageId) return;
    apiRequest(`/voyages/${voyageId}/performance-reports`)
      .then(data => {
        setReports(data || []);
        setError(null);
      })
      .catch(err => {
        setError(err);
        setReports([]);
      })
      .finally(() => setLoadedKey(voyageId));
  }, [voyageId]);

  const loading = loadedKey !== voyageId;

  return (
    <div style={{ maxWidth: 1400, margin: '2rem auto', padding: '1rem' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>운항 성능 보고</h2>
      <ApiErrorBanner error={error} />
      {loading ? <Loading /> : <PerformanceReportTable reports={reports} />}
    </div>
  );
}
