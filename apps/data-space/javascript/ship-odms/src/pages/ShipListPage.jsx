import React, { useEffect, useState } from 'react';
import { apiRequest } from '../api/client';
import ShipListTable from '../components/ShipListTable';
import ApiErrorBanner from '../components/ApiErrorBanner';
import Loading from '../components/Loading';

export default function ShipListPage() {
  const [ships, setShips] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    apiRequest('/ships')
      .then(data => {
        setShips(data || []);
        setError(null);
      })
      .catch(err => {
        setError(err);
        setShips([]);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ maxWidth: 1200, margin: '2rem auto', padding: '1rem' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: '1.5rem' }}>선박 목록</h1>
      <ApiErrorBanner error={error} />
      {loading ? <Loading /> : <ShipListTable ships={ships} />}
    </div>
  );
}
