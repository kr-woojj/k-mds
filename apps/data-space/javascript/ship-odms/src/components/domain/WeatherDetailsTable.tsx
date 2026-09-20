import React from "react";
import { WeatherDetails } from "../../types/openapi-types";

interface WeatherDetailsTableProps {
  items: WeatherDetails[];
  loading?: boolean;
  error?: string;
  onRowClick?: (weather: WeatherDetails) => void;
}

const WeatherDetailsTable = ({ items, loading, error, onRowClick }: WeatherDetailsTableProps) => {
  if (loading) return <div className="table-skeleton">Loading...</div>;
  if (error) return <div className="table-error">{error}</div>;
  return (
    <div className="figma-table-wrapper">
      <table className="figma-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Report ID</th>
            <th>Sea State</th>
            <th>Wind Force</th>
            <th>Wind Speed</th>
            <th>Wind Dir</th>
            <th>Wind Dir Rel</th>
            <th>Wind Dir True</th>
            <th>Air Temp</th>
            <th>Atmos. Pressure</th>
            <th>Sea Dir Rel</th>
            <th>Sea Dir True</th>
            <th>Sea Height</th>
            <th>Swell Dir Rel</th>
            <th>Swell Dir True</th>
            <th>Swell Height</th>
            <th>Ocean Dir Rel</th>
            <th>Ocean Dir True</th>
            <th>Ocean Dir Provider</th>
          </tr>
        </thead>
        <tbody>
          {items.map((w) => (
            <tr
              key={w.id}
              style={{ cursor: onRowClick ? "pointer" : undefined }}
              onClick={onRowClick ? () => onRowClick(w) : undefined}
            >
              <td>{w.id}</td>
              <td>{w.report_id}</td>
              <td>{w.sea_state}</td>
              <td>{w.wind_force}</td>
              <td>{w.wind_speed}</td>
              <td>{w.wind_dir}</td>
              <td>{w.wind_dir_relative}</td>
              <td>{w.wind_dir_true}</td>
              <td>{w.air_temperature}</td>
              <td>{w.atmospheric_pressure}</td>
              <td>{w.sea_dir_relative}</td>
              <td>{w.sea_dir_true}</td>
              <td>{w.sea_height}</td>
              <td>{w.swell_dir_relative}</td>
              <td>{w.swell_dir_true}</td>
              <td>{w.swell_height}</td>
              <td>{w.ocean_dir_relative}</td>
              <td>{w.ocean_dir_true}</td>
              <td>{w.ocean_dir_weather_provider}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export { WeatherDetailsTable };
