import React from "react";
import { FocConsumerType } from "../../types/openapi-types";

interface FocConsumerTypeTableProps {
  items: FocConsumerType[];
  loading?: boolean;
  error?: string;
  onRowClick?: (focConsumerType: FocConsumerType) => void;
}

const FocConsumerTypeTable = ({ items, loading, error, onRowClick }: FocConsumerTypeTableProps) => {
  if (loading) return <div className="table-skeleton">Loading...</div>;
  if (error) return <div className="table-error">{error}</div>;
  return (
    <div className="figma-table-wrapper">
      <table className="figma-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Fuel Consumption ID</th>
            <th>Main Engine Used</th>
            <th>Main Engine Consumed</th>
            <th>Diesel Electric Used</th>
            <th>Diesel Electric Consumed</th>
            <th>Diesel Gen Used</th>
            <th>Diesel Gen Consumed</th>
            <th>Aux Boiler Used</th>
            <th>Aux Boiler Consumed</th>
            <th>Aux Engine Used</th>
            <th>Aux Engine Consumed</th>
            <th>Cargo Cooling Used</th>
            <th>Cargo Cooling Consumed</th>
            <th>Cargo Heating Used</th>
            <th>Cargo Heating Consumed</th>
            <th>Diesel Power Packs Used</th>
            <th>Diesel Power Packs Consumed</th>
            <th>Dirty Petroleum Pump Used</th>
            <th>Dirty Petroleum Pump Consumed</th>
            <th>Discharge Pump Used</th>
            <th>Discharge Pump Consumed</th>
            <th>DP Ops Used</th>
            <th>DP Ops Consumed</th>
            <th>Electrical Power Gen Used</th>
            <th>Electrical Power Gen Consumed</th>
            <th>Incinerator Used</th>
            <th>Incinerator Consumed</th>
            <th>Inert Gas Gen Used</th>
            <th>Inert Gas Gen Consumed</th>
            <th>Other Fuel Devices Used</th>
            <th>Other Fuel Devices Consumed</th>
            <th>Reefer Containers Used</th>
            <th>Reefer Containers Consumed</th>
            <th>Shuttle Tanker Ops Used</th>
            <th>Shuttle Tanker Ops Consumed</th>
            <th>STS Ops Used</th>
            <th>STS Ops Consumed</th>
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
              <td>{f.fuel_used_main_engine}</td>
              <td>{f.fuel_consumed_main_engine}</td>
              <td>{f.fuel_used_diesel_electric_propulsion}</td>
              <td>{f.fuel_consumed_diesel_electric_propulsion}</td>
              <td>{f.fuel_used_diesel_generator}</td>
              <td>{f.fuel_consumed_diesel_generator}</td>
              <td>{f.fuel_used_auxiliary_boiler}</td>
              <td>{f.fuel_consumed_auxiliary_boiler}</td>
              <td>{f.fuel_used_auxiliary_engine}</td>
              <td>{f.fuel_consumed_auxiliary_engine}</td>
              <td>{f.fuel_used_cargo_cooling}</td>
              <td>{f.fuel_consumed_cargo_cooling}</td>
              <td>{f.fuel_used_cargo_heating}</td>
              <td>{f.fuel_consumed_cargo_heating}</td>
              <td>{f.fuel_used_diesel_power_packs}</td>
              <td>{f.fuel_consumed_diesel_power_packs}</td>
              <td>{f.fuel_used_dirty_petroleum_products_cargo_pump}</td>
              <td>{f.fuel_consumed_dirty_petroleum_products_cargo_pump}</td>
              <td>{f.fuel_used_discharge_pump}</td>
              <td>{f.fuel_consumed_discharge_pump}</td>
              <td>{f.fuel_used_dp_operations}</td>
              <td>{f.fuel_consumed_dp_operations}</td>
              <td>{f.fuel_used_electrical_power_generation}</td>
              <td>{f.fuel_consumed_electrical_power_generation}</td>
              <td>{f.fuel_used_incinerator}</td>
              <td>{f.fuel_consumed_incinerator}</td>
              <td>{f.fuel_used_inert_gas_generators_gcus}</td>
              <td>{f.fuel_consumed_inert_gas_generators_gcus}</td>
              <td>{f.fuel_used_other_fuel_consuming_devices}</td>
              <td>{f.fuel_consumed_other_fuel_consuming_devices}</td>
              <td>{f.fuel_used_reefer_containers}</td>
              <td>{f.fuel_consumed_reefer_containers}</td>
              <td>{f.fuel_used_shuttle_tanker_operations}</td>
              <td>{f.fuel_consumed_shuttle_tanker_operations}</td>
              <td>{f.fuel_used_sts_operations}</td>
              <td>{f.fuel_consumed_sts_operations}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export { FocConsumerTypeTable };
