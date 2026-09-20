import React from "react";
import { MeasuredCarbonDioxide } from "../../types/openapi-types";

interface MeasuredCarbonDioxideTableProps {
  items: MeasuredCarbonDioxide[];
  loading?: boolean;
  error?: string;
  onRowClick?: (measured: MeasuredCarbonDioxide) => void;
}

const MeasuredCarbonDioxideTable = ({ items, loading, error, onRowClick }: MeasuredCarbonDioxideTableProps) => {
  if (loading) return <div className="table-skeleton">Loading...</div>;
  if (error) return <div className="table-error">{error}</div>;
  return (
    <div className="figma-table-wrapper">
      <table className="figma-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Report ID</th>
            <th>Total CO2eq</th>
            <th>% CO2 at Sea</th>
            <th>Total CO2</th>
            <th>Total CO2eq Captured</th>
            <th>Total CH4</th>
            <th>Total CH4 to CO2</th>
            <th>Total N2O</th>
            <th>Total N2O to CO2</th>
          </tr>
        </thead>
        <tbody>
          {items.map((m) => (
            <tr
              key={m.id}
              style={{ cursor: onRowClick ? "pointer" : undefined }}
              onClick={onRowClick ? () => onRowClick(m) : undefined}
            >
              <td>{m.id}</td>
              <td>{m.report_id}</td>
              <td>{m.total_co2eq}</td>
              <td>{m.percentage_co2_emitted_at_sea}</td>
              <td>{m.total_co2}</td>
              <td>{m.total_co2eq_captured}</td>
              <td>{m.total_ch4}</td>
              <td>{m.total_ch4_to_co2}</td>
              <td>{m.total_n2o}</td>
              <td>{m.total_n2o_to_co2}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export { MeasuredCarbonDioxideTable };
