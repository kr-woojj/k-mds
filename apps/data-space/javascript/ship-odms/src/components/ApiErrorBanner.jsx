import React from 'react';

export default function ApiErrorBanner({ error }) {
  if (!error) return null;
  return (
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
  );
}
