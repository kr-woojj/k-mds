

import React from "react";
import { BrowserRouter as Router, Routes, Route, useParams } from "react-router-dom";
import { ShipListPage } from "./pages/domain/ShipListPage";
import { YearPerformanceReportPage } from "./pages/domain/YearPerformanceReportPage";
import { VoyageListPage } from "./pages/domain/VoyageListPage";
import { PortCallPage } from "./pages/domain/PortCallPage";
import { PerformanceReportPage } from "./pages/domain/PerformanceReportPage";
import { FuelConsumptionPage } from "./pages/domain/FuelConsumptionPage";
import { WeatherDetailsPage } from "./pages/domain/WeatherDetailsPage";
import { CargoOnboardPage } from "./pages/domain/CargoOnboardPage";
import { ElectricConsumptionPage } from "./pages/domain/ElectricConsumptionPage";
import { MeasuredCarbonDioxidePage } from "./pages/domain/MeasuredCarbonDioxidePage";
import { FocFuelTypePage } from "./pages/domain/FocFuelTypePage";
import { FocConsumerTypePage } from "./pages/domain/FocConsumerTypePage";


// 각 라우트 파라미터를 props로 전달하는 래퍼 컴포넌트들
function YearPerformanceReportWrapper() {
  const { shipId } = useParams();
  return <YearPerformanceReportPage shipId={Number(shipId)} />;
}
function VoyageListWrapper() {
  const { shipId, yearReportId } = useParams();
  return <VoyageListPage shipId={Number(shipId)} yearReportId={yearReportId ? Number(yearReportId) : undefined} />;
}
function PortCallWrapper() {
  const { voyageId } = useParams();
  return <PortCallPage voyageId={Number(voyageId)} />;
}
function PerformanceReportWrapper() {
  const { voyageId } = useParams();
  return <PerformanceReportPage voyageId={Number(voyageId)} />;
}
function FuelConsumptionWrapper() {
  const { reportId } = useParams();
  return <FuelConsumptionPage reportId={Number(reportId)} />;
}
function WeatherDetailsWrapper() {
  const { reportId } = useParams();
  return <WeatherDetailsPage reportId={Number(reportId)} />;
}
function CargoOnboardWrapper() {
  const { reportId } = useParams();
  return <CargoOnboardPage reportId={Number(reportId)} />;
}
function ElectricConsumptionWrapper() {
  const { reportId } = useParams();
  return <ElectricConsumptionPage reportId={Number(reportId)} />;
}
function MeasuredCarbonDioxideWrapper() {
  const { reportId } = useParams();
  return <MeasuredCarbonDioxidePage reportId={Number(reportId)} />;
}

import { Link } from "react-router-dom";

export default function AppRouter() {
  return (
    <Router>
      <nav style={{ padding: '1rem', background: '#f5f5f5', marginBottom: '2rem' }}>
        <Link to="/" style={{ fontWeight: 700, fontSize: '1.2rem', textDecoration: 'none', color: '#333' }}>Ship-ODMS</Link>
      </nav>
      <Routes>
        <Route path="/" element={<ShipListPage />} />
        <Route path="/ships/:shipId/yearly-reports" element={<YearPerformanceReportWrapper />} />
        <Route path="/ships/:shipId/voyages" element={<VoyageListWrapper />} />
        <Route path="/ships/:shipId/yearly-reports/:yearReportId/voyages" element={<VoyageListWrapper />} />
        <Route path="/voyages/:voyageId/port-calls" element={<PortCallWrapper />} />
        <Route path="/voyages/:voyageId/performance-reports" element={<PerformanceReportWrapper />} />
        <Route path="/performance-reports/:reportId/fuel-consumptions" element={<FuelConsumptionWrapper />} />
        <Route path="/performance-reports/:reportId/weather-details" element={<WeatherDetailsWrapper />} />
        <Route path="/performance-reports/:reportId/cargo-onboard" element={<CargoOnboardWrapper />} />
        <Route path="/performance-reports/:reportId/electric-consumptions" element={<ElectricConsumptionWrapper />} />
        <Route path="/performance-reports/:reportId/measured-carbon-dioxide" element={<MeasuredCarbonDioxideWrapper />} />
        <Route path="/foc-fuel-types" element={<FocFuelTypePage />} />
        <Route path="/foc-consumer-types" element={<FocConsumerTypePage />} />
      </Routes>
    </Router>
  );
}
