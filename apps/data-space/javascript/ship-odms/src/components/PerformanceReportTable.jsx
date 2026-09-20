import React from 'react';

export default function PerformanceReportTable({ reports }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 1200, background: '#fff', borderRadius: 8, boxShadow: '0 2px 8px #eee' }}>
        <thead style={{ background: '#f5f5f5' }}>
          <tr>
            <th style={th}>ID</th>
            <th style={th}>항해 ID</th>
            <th style={th}>구간</th>
            <th style={th}>이벤트</th>
            <th style={th}>운항유형</th>
            <th style={th}>경과시간</th>
            <th style={th}>보고유형</th>
            <th style={th}>보고일시</th>
            <th style={th}>위도</th>
            <th style={th}>경도</th>
            <th style={th}>적재상태</th>
            <th style={th}>하위데이터</th>
          </tr>
        </thead>
        <tbody>
          {reports && reports.length > 0 ? reports.map(r => (
            <tr key={r.id} style={{ borderBottom: '1px solid #eee' }}>
              <td style={td}>{r.id}</td>
              <td style={td}>{r.voyage_id}</td>
              <td style={td}>{r.voyage_leg}</td>
              <td style={td}>{r.event_type}</td>
              <td style={td}>{r.operation_type}</td>
              <td style={td}>{r.elapsed_time}</td>
              <td style={td}>{r.report_type}</td>
              <td style={td}>{r.report_datetime}</td>
              <td style={td}>{r.latitude}</td>
              <td style={td}>{r.longitude}</td>
              <td style={td}>{r.laden_indicator ? '적재' : '공선'}</td>
              <td style={td}>
                {['weather_details','cargo_onboard','electric_consumption','fuel_consumption','measured_carbon_dioxide'].map(key => (
                  Array.isArray(r[key]) && r[key].length > 0 ? (
                    <div key={key} style={{ fontSize: '0.9em', color: '#555' }}>{key}: {r[key].length}건</div>
                  ) : null
                ))}
              </td>
            </tr>
          )) : (
            <tr><td colSpan={12} style={{ textAlign: 'center', color: '#888', padding: '2rem' }}>데이터 없음</td></tr>
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
