import React from "react";
import { PerformanceReport } from "../../types/openapi-types";
import { Link } from "react-router-dom";

interface PerformanceReportTableProps {
  items: PerformanceReport[];
  loading?: boolean;
  error?: string;
  onRowClick?: (report: PerformanceReport) => void;
}

const th = {
  padding: '0.75rem 1rem',
  fontWeight: 600,
  fontSize: '1rem',
  borderBottom: '2px solid #e0e0e0',
  background: '#f5f5f5',
  textAlign: 'left' as const,
};
const td = {
  padding: '0.75rem 1rem',
  fontSize: '0.98rem',
  background: '#fff',
};

export const PerformanceReportTable: React.FC<PerformanceReportTableProps> = ({ items, loading, error, onRowClick }) => {
  if (loading) return <div className="table-skeleton">Loading...</div>;
  if (error) return <div className="table-error">{error}</div>;
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
          {items && items.length > 0 ? items.map((r) => (
            <tr key={r.id} style={{ borderBottom: '1px solid #eee', cursor: onRowClick ? 'pointer' : undefined }} onClick={onRowClick ? () => onRowClick(r) : undefined}>
              <td style={td}>{r.id}</td>
              <td style={td}>{r.voyage_id}</td>
              <td style={td}>{r.voyage_leg ?? r.leg}</td>
              <td style={td}>{r.event_type ?? r.event}</td>
              <td style={td}>{r.operation_type ?? r.operation}</td>
              <td style={td}>{r.elapsed_time ?? r.elapsed}</td>
              <td style={td}>{r.report_type ?? r.type}</td>
              <td style={td}>{r.report_datetime ?? r.datetime}</td>
              <td style={td}>{r.latitude}</td>
              <td style={td}>{r.longitude}</td>
              <td style={td}>{r.laden_indicator !== undefined ? (r.laden_indicator ? '적재' : '공선') : (r.laden ?? '')}</td>
              <td style={td}>
                {Array.isArray(r.weather_details) && r.weather_details.length > 0 && (
                  <Link to={`/performance-reports/${r.id}/weather-details`} style={subBtnStyle} onClick={e => e.stopPropagation()}>기상 {r.weather_details.length}건</Link>
                )}
                {Array.isArray(r.cargo_onboard) && r.cargo_onboard.length > 0 && (
                  <Link to={`/performance-reports/${r.id}/cargo-onboard`} style={subBtnStyle} onClick={e => e.stopPropagation()}>적재화물 {r.cargo_onboard.length}건</Link>
                )}
                {Array.isArray(r.electric_consumption) && r.electric_consumption.length > 0 && (
                  <Link to={`/performance-reports/${r.id}/electric-consumptions`} style={subBtnStyle} onClick={e => e.stopPropagation()}>전력 {r.electric_consumption.length}건</Link>
                )}
                {Array.isArray(r.fuel_consumption) && r.fuel_consumption.length > 0 && (
                  <Link to={`/performance-reports/${r.id}/fuel-consumptions`} style={subBtnStyle} onClick={e => e.stopPropagation()}>연료 {r.fuel_consumption.length}건</Link>
                )}
                {Array.isArray(r.measured_carbon_dioxide) && r.measured_carbon_dioxide.length > 0 && (
                  <Link to={`/performance-reports/${r.id}/measured-carbon-dioxide`} style={subBtnStyle} onClick={e => e.stopPropagation()}>CO₂ {r.measured_carbon_dioxide.length}건</Link>
                )}
              </td>
            </tr>
          )) : (
            <tr><td colSpan={12} style={{ textAlign: 'center', color: '#888', padding: '2rem' }}>데이터 없음</td></tr>
          )}
        </tbody>
      </table>
    </div>

  );
};

const subBtnStyle: React.CSSProperties = {
  display: 'inline-block',
  marginRight: 6,
  marginBottom: 4,
  padding: '0.2em 0.7em',
  background: '#f0f4ff',
  color: '#2a3a8c',
  borderRadius: 4,
  textDecoration: 'none',
  fontWeight: 500,
  fontSize: '0.95em',
};
