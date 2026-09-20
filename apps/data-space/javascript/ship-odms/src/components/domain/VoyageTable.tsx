import React from "react";
import { Voyage } from "../../types/openapi-types";

interface VoyageTableProps {
  items: Voyage[];
  loading?: boolean;
  error?: string;
  onRowClick?: (voyage: Voyage) => void;
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
const linkBtn = {
  display: 'inline-block',
  padding: '0.3em 0.8em',
  background: '#e3e8ff',
  color: '#2a3a8c',
  borderRadius: 4,
  textDecoration: 'none',
  fontWeight: 500,
};

const VoyageTable = ({ items, loading, error, onRowClick }: VoyageTableProps) => {
  if (loading) return <div className="table-skeleton">Loading...</div>;
  if (error) return <div className="table-error">{error}</div>;
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 800, background: '#fff', borderRadius: 8, boxShadow: '0 2px 8px #eee' }}>
        <thead style={{ background: '#f5f5f5' }}>
          <tr>
            <th style={th}>ID</th>
            <th style={th}>선박 ID</th>
            <th style={th}>연차보고 ID</th>
            <th style={th}>항차번호</th>
            <th style={th}>Trade Service ID</th>
            <th style={th}>GHG Intensity</th>
            <th style={th}>입항 관할</th>
            <th style={th}>출항 관할</th>
            <th style={th}></th>
          </tr>
        </thead>
        <tbody>
          {items && items.length > 0 ? items.map((v) => (
            <tr key={v.id} style={{ borderBottom: '1px solid #eee', cursor: onRowClick ? 'pointer' : undefined }}>
              <td style={td}>{v.id}</td>
              <td style={td}>{v.ship_id}</td>
              <td style={td}>{v.year_report_id}</td>
              <td style={td}>{v.voyage_number}</td>
              <td style={td}>{v.trade_service_id}</td>
              <td style={td}>{v.gfi_per_voyage}</td>
              <td style={td}>{v.inbound_port_jurisdiction}</td>
              <td style={td}>{v.outbound_port_jurisdiction}</td>
              <td style={td}>
                <a href={`/voyages/${v.id}/port-calls`} style={linkBtn}>입출항</a>
                <a href={`/voyages/${v.id}/performance-reports`} style={{...linkBtn, marginLeft: 8}}>운항보고</a>
              </td>
            </tr>
          )) : (
            <tr><td colSpan={9} style={{ textAlign: 'center', color: '#888', padding: '2rem' }}>데이터 없음</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
};

export { VoyageTable };
