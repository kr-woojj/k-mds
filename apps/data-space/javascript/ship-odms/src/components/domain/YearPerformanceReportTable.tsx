import React from "react";
import { Link } from "react-router-dom";
import { YearPerformanceReport } from "../../types/openapi-types";

interface YearPerformanceReportTableProps {
  items: YearPerformanceReport[];
  loading?: boolean;
  error?: string;
  onRowClick?: (report: YearPerformanceReport) => void;
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

const YearPerformanceReportTable = ({ items, loading, error, onRowClick }: YearPerformanceReportTableProps) => {
  if (loading) return <div className="table-skeleton">Loading...</div>;
  if (error) return <div className="table-error">{error}</div>;
  return (
    <div style={{ overflowX: 'auto', borderRadius: 8, boxShadow: '0 2px 8px #eee', background: '#fff' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 600, background: '#fff' }}>
        <thead style={{ background: '#f5f5f5' }}>
          <tr>
            <th style={th}>ID</th>
            <th style={th}>선박 ID</th>
            <th style={th}>연간 GHG 집계</th>
            <th style={th}></th>
          </tr>
        </thead>
        <tbody>
          {items && items.length > 0 ? items.map((r) => (
            <tr
              key={r.id}
              style={{ borderBottom: '1px solid #eee', cursor: onRowClick ? 'pointer' : undefined }}
              onClick={onRowClick ? () => onRowClick(r) : undefined}
            >
              <td style={td}>{r.id}</td>
              <td style={td}>{r.ship_id}</td>
              <td style={td}>{r.total_gfi_annually}</td>
              <td style={td}>
                <Link
                  to={`/ships/${r.ship_id}/voyages`}
                  style={{
                    display: 'inline-block',
                    padding: '0.3em 0.8em',
                    background: '#e3e8ff',
                    color: '#2a3a8c',
                    borderRadius: 4,
                    textDecoration: 'none',
                    fontWeight: 500,
                  }}
                >
                  항해이력
                </Link>
              </td>
            </tr>
          )) : (
            <tr><td colSpan={4} style={{ textAlign: 'center', color: '#888', padding: '2rem' }}>데이터 없음</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export { YearPerformanceReportTable };
