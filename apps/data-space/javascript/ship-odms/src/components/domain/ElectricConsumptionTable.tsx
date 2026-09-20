import React from "react";
import { ElectricConsumption } from "../../types/openapi-types";

interface ElectricConsumptionTableProps {
  items: ElectricConsumption[];
  loading?: boolean;
  error?: string;
  onRowClick?: (electric: ElectricConsumption) => void;
}

export const ElectricConsumptionTable: React.FC<ElectricConsumptionTableProps> = ({ items, loading, error, onRowClick }) => {
  if (loading) return <div className="table-skeleton">Loading...</div>;
  if (error) return <div className="table-error">{error}</div>;
  return (
    <div className="figma-table-wrapper">
      <table className="figma-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Report ID</th>
            <th>Boiler</th>
            <th>Generator</th>
            <th>Offset</th>
            <th>Plant</th>
            <th>Energy Cargo Cooling</th>
            <th>Energy Discharge Pump</th>
            <th>Energy Reefer</th>
            <th>Onshore Power</th>
            <th>Zero Emissions</th>
            <th>Fuel Type Cargo Cooling</th>
            <th>Fuel Type Discharge Pump</th>
            <th>Fuel Type Reefer</th>
            <th>SFOC Cargo Cooling</th>
            <th>SFOC Discharge Pump</th>
            <th>SFOC Cargo Reefers</th>
          </tr>
        </thead>
        <tbody>
          {items && items.map((e) => (
            <tr
              key={e.id}
              style={{ cursor: onRowClick ? "pointer" : undefined }}
              onClick={onRowClick ? () => onRowClick(e) : undefined}
            >
              <td>{e.id}</td>
              <td>{e.report_id}</td>
              <td>{e.power_boiler}</td>
              <td>{e.power_generator}</td>
              <td>{e.power_offset}</td>
              <td>{e.power_plant}</td>
              <td>{e.energy_cargo_cooling}</td>
              <td>{e.energy_discharge_pump}</td>
              <td>{e.energy_reefer_containers}</td>
              <td>{e.energy_onshore_power_supply}</td>
              <td>{e.energy_zero_emissions_tech}</td>
              <td>{e.fuel_type_cargo_cooling}</td>
              <td>{e.fuel_type_discharge_pump}</td>
              <td>{e.fuel_type_reefer_container}</td>
              <td>{e.sfoc_cargo_cooling}</td>
              <td>{e.sfoc_discharge_pump}</td>
              <td>{e.sfoc_cargo_reefers}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
