import React from "react";
import { CargoOnboard } from "../../types/openapi-types";

interface CargoOnboardTableProps {
  items: CargoOnboard[];
  loading?: boolean;
  error?: string;
  onRowClick?: (cargo: CargoOnboard) => void;
}

const CargoOnboardTable = ({ items, loading, error, onRowClick }: CargoOnboardTableProps) => {
  if (loading) return <div className="table-skeleton">Loading...</div>;
  if (error) return <div className="table-error">{error}</div>;
  return (
    <div className="figma-table-wrapper">
      <table className="figma-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Report ID</th>
            <th>Containers</th>
            <th>Full Container</th>
            <th>Full Reefer</th>
            <th>Vehicles</th>
            <th>Crew</th>
            <th>Passengers</th>
            <th>Chilled 20ft</th>
            <th>Chilled 40ft</th>
            <th>Frozen 20ft</th>
            <th>Frozen 40ft</th>
            <th>Goods Desc</th>
            <th>Gross Vol</th>
            <th>Gross Wt</th>
            <th>BL Ref</th>
            <th>BL Date</th>
          </tr>
        </thead>
        <tbody>
          {items.map((c) => (
            <tr
              key={c.id}
              style={{ cursor: onRowClick ? "pointer" : undefined }}
              onClick={onRowClick ? () => onRowClick(c) : undefined}
            >
              <td>{c.id}</td>
              <td>{c.report_id}</td>
              <td>{c.number_containers}</td>
              <td>{c.number_full_container}</td>
              <td>{c.number_full_reefer_containers}</td>
              <td>{c.number_vehicles_onboard}</td>
              <td>{c.number_crew}</td>
              <td>{c.number_passengers}</td>
              <td>{c.number_chilled_20ft_reefer_containers}</td>
              <td>{c.number_chilled_40ft_reefer_containers}</td>
              <td>{c.number_frozen_20ft_reefer_containers}</td>
              <td>{c.number_frozen_40ft_reefer_containers}</td>
              <td>{c.goods_description}</td>
              <td>{c.gross_volume}</td>
              <td>{c.gross_weight}</td>
              <td>{c.bl_ref_id}</td>
              <td>{c.bl_issued_date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export { CargoOnboardTable };
