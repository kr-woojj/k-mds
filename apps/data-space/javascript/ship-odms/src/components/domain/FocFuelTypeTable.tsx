import React from "react";
import { FocFuelType } from "../../types/openapi-types";

interface FocFuelTypeTableProps {
  items: FocFuelType[];
  loading?: boolean;
  error?: string;
  onRowClick?: (focFuelType: FocFuelType) => void;
}

const FocFuelTypeTable = ({ items, loading, error, onRowClick }: FocFuelTypeTableProps) => {
  if (loading) return <div className="table-skeleton">Loading...</div>;
  if (error) return <div className="table-error">{error}</div>;
  return (
    <div className="figma-table-wrapper">
      <table className="figma-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Fuel Consumption ID</th>
            <th>Main Engine</th>
            <th>Diesel Electric Propulsion</th>
            <th>Diesel Generator</th>
            <th>Aux Boiler</th>
            <th>Aux Engine</th>
            <th>Cargo Cooling</th>
            <th>Cargo Heating</th>
            <th>Diesel Power Packs</th>
            <th>Dirty Petroleum Pump</th>
            <th>Discharge Pump</th>
            <th>DP Operations</th>
            <th>Electrical Power Gen</th>
            <th>Incinerator</th>
            <th>Inert Gas Gen/GCUs</th>
            <th>Other Fuel Devices</th>
            <th>Reefer Containers</th>
            <th>Shuttle Tanker Ops</th>
            <th>STS Operations</th>
          </tr>
        </thead>
        <tbody>
          {items.map((f) => (
            <tr
              key={f.id}
              style={{ cursor: onRowClick ? "pointer" : undefined }}
              onClick={onRowClick ? () => onRowClick(f) : undefined}
            >
              <td>{f.id}</td>
              <td>{f.fuel_consumption_id}</td>
              <td>{f.foc_main_engine}</td>
              <td>{f.foc_diesel_electric_propulsion}</td>
              <td>{f.foc_diesel_generator}</td>
              <td>{f.foc_auxiliary_boiler}</td>
              <td>{f.foc_auxiliary_engine}</td>
              <td>{f.foc_cargo_cooling}</td>
              <td>{f.foc_cargo_heating}</td>
              <td>{f.foc_diesel_power_packs}</td>
              <td>{f.foc_dirty_petroleum_products_cargo_pump}</td>
              <td>{f.foc_discharge_pump}</td>
              <td>{f.foc_dp_operations}</td>
              <td>{f.foc_electrical_power_generation}</td>
              <td>{f.foc_incinerator}</td>
              <td>{f.foc_inert_gas_generators_gcus}</td>
              <td>{f.foc_other_fuel_consuming_devices}</td>
              <td>{f.foc_reefer_containers}</td>
              <td>{f.foc_shuttle_tanker_operations}</td>
              <td>{f.foc_sts_operations}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export { FocFuelTypeTable };
