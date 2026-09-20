import React, { useEffect, useState } from 'react';
import { apiRequest } from '../api/client';
import PortCallTable from '../components/PortCallTable';
import ApiErrorBanner from '../components/ApiErrorBanner';
import Loading from '../components/Loading';

export default function PortCallPage({ voyageId }) {
  const [portCalls, setPortCalls] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!voyageId) return;
    setLoading(true);
    apiRequest(`/voyages/${voyageId}/port-calls`)
      .then(data => {
        setPortCalls(data || []);
        setError(null);
      })
      .catch(err => {
        setError(err);
        setPortCalls([]);
      })
      .finally(() => setLoading(false));
  }, [voyageId]);

  return (
    <div style={{ maxWidth: 900, margin: '2rem auto', padding: '1rem' }}>
      <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>입출항 기록</h2>
      <ApiErrorBanner error={error} />
      {loading ? <Loading /> : <PortCallTable portCalls={portCalls} />}
    </div>
  );
}
