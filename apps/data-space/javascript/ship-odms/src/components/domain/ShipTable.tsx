
import React from "react";
import { Ship } from "../../types/openapi-types";


interface ShipTableProps {
  items: Ship[];
  loading?: boolean;
  error?: string;
  onRowClick?: (ship: Ship) => void;
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
  fontSize: '0.95em',
  border: '1px solid #bfcfff',
};

const ShipTable = ({ items, loading, error, onRowClick }: ShipTableProps) => {
  if (loading) return <div className="table-skeleton">Loading...</div>;
  if (error) return <div className="table-error">{error}</div>;
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 800, background: '#fff', borderRadius: 8, boxShadow: '0 2px 8px #eee' }}>
        <thead style={{ background: '#f5f5f5' }}>
          <tr>
            <th style={th}>IMO 번호</th>
            <th style={th}>선박명</th>
            <th style={th}>선박유형</th>
            <th style={th}>MARPOL 유형</th>
            <th style={th}>국적</th>
            <th style={th}>MMSI</th>
            <th style={th}>호출부호</th>
            <th style={th}>등록항</th>
            <th style={th}></th>
          </tr>
        </thead>
        <tbody>
          {items && items.length > 0 ? items.map((ship) => (
            <tr
              key={ship.id}
              style={{ borderBottom: '1px solid #eee', cursor: onRowClick ? 'pointer' : undefined }}
              onClick={onRowClick ? () => onRowClick(ship) : undefined}
            >
              <td style={td}>{ship.imo_number}</td>
              <td style={td}>{ship.ship_name}</td>
              <td style={td}>{ship.ship_type}</td>
              <td style={td}>{ship.ship_type_marpol}</td>
              <td style={td}>{ship.flag_state}</td>
              <td style={td}>{ship.mmsi}</td>
              <td style={td}>{ship.call_sign}</td>
              <td style={td}>{ship.registry_port}</td>
              <td style={td}>
                <a href={`/ships/${ship.id}/yearly-reports`} style={linkBtn} onClick={e => { e.stopPropagation(); onRowClick && onRowClick(ship); }}>연차보고</a>
                <a href={`/ships/${ship.id}/voyages`} style={{ ...linkBtn, marginLeft: 8 }} onClick={e => { e.stopPropagation(); }}>항해이력</a>
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

export { ShipTable };