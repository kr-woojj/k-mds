import React from "react";
import { FuelConsumption } from "../../types/openapi-types";
import { FocFuelTypeTable } from "./FocFuelTypeTable";
import { FocConsumerTypeTable } from "./FocConsumerTypeTable";

interface FuelConsumptionTableProps {
  items: FuelConsumption[];
  loading?: boolean;
  error?: string;
  onRowClick?: (fuel: FuelConsumption) => void;
}

const FuelConsumptionTable = ({ items, loading, error, onRowClick }: FuelConsumptionTableProps) => {
  if (loading) return <div className="table-skeleton">Loading...</div>;
  if (error) return <div className="table-error">{error}</div>;
  return (
    <div className="figma-table-wrapper">
      <table className="figma-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Report ID</th>
            <th>Fuel Type</th>
            <th>Trade Name</th>
            <th>BDN Number</th>
            <th>BDN Datetime</th>
            <th>Bunker Received</th>
            <th>Mass</th>
            <th>Density</th>
            <th>Sulphur</th>
            <th>Viscosity</th>
            <th>Water</th>
            <th>HHV</th>
            <th>LFV</th>
            <th>Grade</th>
            <th>Bunker Port</th>
            <th>Bunker Port Name</th>
            <th>CO2 Emission</th>
            <th>Total Consumed</th>
            <th>ROB</th>
            <th>Sludge ROB</th>
            <th>LCV Report</th>
            <th>LCV</th>
            <th>POS Ref</th>
            <th>CH4 CF</th>
            <th>N2O CF</th>
            <th>Fresh Water Bunkered</th>
            <th>Fresh Water Produced</th>
            <th>Fresh Water Consumed</th>
            <th>Technical Water Produced</th>
            <th>Technical Water Consumed</th>
            <th>Wash Water Consumed</th>
            <th>Fresh Water ROB</th>
            <th>CLO ROB</th>
            <th>CLO Feed Rate</th>
            <th>CLO Consumption</th>
            <th>CLO Received</th>
            <th>FOC Fuel Type</th>
            <th>FOC Consumer Type</th>
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
              <td>{f.report_id}</td>
              <td>{f.fuel_type}</td>
              <td>{f.fuel_type_trade_name}</td>
              <td>{f.bdn_number}</td>
              <td>{f.bdn_datetime}</td>
              <td>{f.fuel_bunker_received}</td>
              <td>{f.fuel_mass}</td>
              <td>{f.fuel_density}</td>
              <td>{f.fuel_sulphur_content}</td>
              <td>{f.fuel_viscosity}</td>
              <td>{f.fuel_water_content}</td>
              <td>{f.fuel_hhv}</td>
              <td>{f.fuel_lfv}</td>
              <td>{f.fuel_grade}</td>
              <td>{f.fuel_bunker_port}</td>
              <td>{f.fuel_bunker_port_name}</td>
              <td>{f.co2_emission}</td>
              <td>{f.total_fuel_quantity_consumed}</td>
              <td>{f.fuel_quantity_rob}</td>
              <td>{f.sludge_rob}</td>
              <td>{f.fuel_lcv_report}</td>
              <td>{f.fuel_lcv}</td>
              <td>{f.fuel_pos_ref}</td>
              <td>{f.ch4_cf}</td>
              <td>{f.n2o_cf}</td>
              <td>{f.fresh_water_bunkered}</td>
              <td>{f.fresh_water_produced}</td>
              <td>{f.fresh_water_consumed}</td>
              <td>{f.technical_water_produced}</td>
              <td>{f.technical_water_consumed}</td>
              <td>{f.wash_water_consumed}</td>
              <td>{f.fresh_water_rob}</td>
              <td>{f.clo_rob}</td>
              <td>{f.clo_feed_rate}</td>
              <td>{f.clo_consumption}</td>
              <td>{f.clo_received}</td>
              <td><FocFuelTypeTable items={f.foc_fuel_type} /></td>
              <td><FocConsumerTypeTable items={f.foc_consumer_type} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export { FuelConsumptionTable };
