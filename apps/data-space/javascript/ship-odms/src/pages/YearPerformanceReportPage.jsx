import React, { useEffect, useState } from 'react';
import { apiRequest } from '../api/client';
import YearPerformanceReportTable from '../components/YearPerformanceReportTable';
import ApiErrorBanner from '../components/ApiErrorBanner';
import Loading from '../components/Loading';

export default function YearPerformanceReportPage({ shipId }) {
  const [reports, setReports] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!shipId) return;
    setLoading(true);
    apiRequest(`/ships/${shipId}/yearly-reports`)
      .then(data => {
        setReports(data || []);
        setError(null);
      })
      .catch(err => {
        setError(err);
        setReports([]);
      })
      .finally(() => setLoading(false));
  }, [shipId]);

  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '1rem' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>연차 실적 보고</h2>
      <ApiErrorBanner error={error} />
      {loading ? <Loading /> : <YearPerformanceReportTable reports={reports} />}
    </div>
  );
}
