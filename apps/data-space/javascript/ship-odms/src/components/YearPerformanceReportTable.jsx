import React from 'react';

export default function YearPerformanceReportTable({ reports }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 600, background: '#fff', borderRadius: 8, boxShadow: '0 2px 8px #eee' }}>
        <thead style={{ background: '#f5f5f5' }}>
          <tr>
            <th style={th}>ID</th>
            <th style={th}>선박 ID</th>
            <th style={th}>연간 GHG 집계</th>
          </tr>
        </thead>
        <tbody>
          {reports && reports.length > 0 ? reports.map(r => (
            <tr key={r.id} style={{ borderBottom: '1px solid #eee' }}>
              <td style={td}>{r.id}</td>
              <td style={td}>{r.ship_id}</td>
              <td style={td}>{r.total_gfi_annually}</td>
            </tr>
          )) : (
            <tr><td colSpan={3} style={{ textAlign: 'center', color: '#888', padding: '2rem' }}>데이터 없음</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

const th = {
  padding: '0.75rem 1rem',
  fontWeight: 600,
  fontSize: '1rem',
  borderBottom: '2px solid #e0e0e0',
  background: '#f5f5f5',
  textAlign: 'left',
};
const td = {
  padding: '0.75rem 1rem',
  fontSize: '0.98rem',
  background: '#fff',
};
