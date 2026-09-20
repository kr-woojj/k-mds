import React from 'react';

export default function PortCallTable({ portCalls }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 700, background: '#fff', borderRadius: 8, boxShadow: '0 2px 8px #eee' }}>
        <thead style={{ background: '#f5f5f5' }}>
          <tr>
            <th style={th}>ID</th>
            <th style={th}>항해 ID</th>
            <th style={th}>입항지</th>
            <th style={th}>출항지</th>
            <th style={th}>입항일시</th>
            <th style={th}>출항일시</th>
          </tr>
        </thead>
        <tbody>
          {portCalls && portCalls.length > 0 ? portCalls.map(p => (
            <tr key={p.id} style={{ borderBottom: '1px solid #eee' }}>
              <td style={td}>{p.id}</td>
              <td style={td}>{p.voyage_id}</td>
              <td style={td}>{p.port_arrival}</td>
              <td style={td}>{p.port_departure}</td>
              <td style={td}>{p.port_ata}</td>
              <td style={td}>{p.port_atd}</td>
            </tr>
          )) : (
            <tr><td colSpan={6} style={{ textAlign: 'center', color: '#888', padding: '2rem' }}>데이터 없음</td></tr>
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
