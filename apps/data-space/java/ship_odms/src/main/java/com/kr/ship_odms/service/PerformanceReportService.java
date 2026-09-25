package com.kr.ship_odms.service;

import com.kr.ship_odms.dto.PerformanceReportResponse;

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
        // 중첩 JSON 으로 들어온 자식 행의 부모 참조(mappedBy "report"/"fuelConsumption")를 채운다.
        // 비워 두면 report_id 가 NULL 로 저장되어 /{reportId}/… 조회가 빈 목록을 돌려준다 (S-1-1 G-4, 2026-09-26).
        if (report.getWeatherDetails() != null) report.getWeatherDetails().forEach(c -> c.setReport(report));
        if (report.getCargoOnboard() != null) report.getCargoOnboard().forEach(c -> c.setReport(report));
        if (report.getElectricConsumption() != null) report.getElectricConsumption().forEach(c -> c.setReport(report));
        if (report.getMeasuredCarbonDioxide() != null) report.getMeasuredCarbonDioxide().forEach(c -> c.setReport(report));
        if (report.getFuelConsumption() != null) {
            report.getFuelConsumption().forEach(fc -> {
                fc.setReport(report);
                if (fc.getFocFuelType() != null) fc.getFocFuelType().forEach(x -> x.setFuelConsumption(fc));
                if (fc.getFocConsumerType() != null) fc.getFocConsumerType().forEach(x -> x.setFuelConsumption(fc));
            });
        }
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

    public PerformanceReportResponse toResponse(PerformanceReport r) {
        return new PerformanceReportResponse(
                r.getId(),
                r.getVoyage() != null ? r.getVoyage().getId() : null,
                r.getVoyageLeg(),
                r.getEventType(),
                r.getOperationType(),
                r.getElapsedTime(),
                r.getReportType(),
                r.getReportDatetime(),
                r.getLatitude(),
                r.getLongitude(),
                r.getDistanceThroughWater(),
                r.getDistanceOverGround(),
                r.getDistanceSailedInIce(),
                r.getDistanceToNextPort(),
                r.getLadenIndicator(),
                r.getDistanceExcluded(),
                r.getOffHireReasons(),
                r.getShipDraught(),
                r.getDraughtForward(),
                r.getDraughtAft(),
                r.getSpeedOverGround(),
                r.getSpeedThroughWater(),
                r.getSpeedPropeller(),
                r.getSpeedProjected(),
                r.getSpeedOrder(),
                r.getCourseOverGround(),
                r.getShipTrueHeading(),
                // 하위 데이터 리스트 추가
                getWeatherDetailsByReportId(r.getId()),
                getCargoOnboardByReportId(r.getId()),
                getElectricConsumptionByReportId(r.getId()),
                getFuelConsumptionByReportId(r.getId()),
                getMeasuredCarbonDioxideByReportId(r.getId())
        );
    }
}
