package com.kr.ship_odms.service;

import com.kr.ship_odms.entity.*;
import com.kr.ship_odms.repository.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class PerformanceReportService {
    private final PerformanceReportRepository performanceReportRepository;
    private final WeatherDetailsRepository weatherDetailsRepository;
    private final CargoOnboardRepository cargoOnboardRepository;
    private final ElectricConsumptionRepository electricConsumptionRepository;
    private final FuelConsumptionRepository fuelConsumptionRepository;
    private final MeasuredCarbonDioxideRepository measuredCarbonDioxideRepository;

    public List<PerformanceReport> getReportsByVoyageId(Integer voyageId) {
        return performanceReportRepository.findByVoyageId(voyageId);
    }

    public Optional<PerformanceReport> getReport(Integer reportId) {
        return performanceReportRepository.findById(reportId);
    }

    public PerformanceReport saveReport(PerformanceReport report) {
        return performanceReportRepository.save(report);
    }

    public void deleteReport(Integer reportId) {
        performanceReportRepository.deleteById(reportId);
    }

    // 하위 모델별 CRUD (예시: WeatherDetails)
    public List<WeatherDetails> getWeatherDetailsByReportId(Integer reportId) {
        return weatherDetailsRepository.findByReportId(reportId);
    }
    public List<CargoOnboard> getCargoOnboardByReportId(Integer reportId) {
        return cargoOnboardRepository.findByReportId(reportId);
    }
    public List<ElectricConsumption> getElectricConsumptionByReportId(Integer reportId) {
        return electricConsumptionRepository.findByReportId(reportId);
    }
    public List<FuelConsumption> getFuelConsumptionByReportId(Integer reportId) {
        return fuelConsumptionRepository.findByReportId(reportId);
    }
    public List<MeasuredCarbonDioxide> getMeasuredCarbonDioxideByReportId(Integer reportId) {
        return measuredCarbonDioxideRepository.findByReportId(reportId);
    }
}
