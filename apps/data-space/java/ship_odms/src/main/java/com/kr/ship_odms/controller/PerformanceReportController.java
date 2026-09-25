package com.kr.ship_odms.controller;

import com.kr.ship_odms.entity.Voyage;
import com.kr.ship_odms.entity.PerformanceReport;
import com.kr.ship_odms.repository.VoyageRepository;
import com.kr.ship_odms.service.PerformanceReportService;
import com.kr.ship_odms.dto.PerformanceReportResponse;
import com.kr.ship_odms.entity.WeatherDetails;
import com.kr.ship_odms.entity.CargoOnboard;
import com.kr.ship_odms.entity.ElectricConsumption;
import com.kr.ship_odms.entity.FuelConsumption;
import com.kr.ship_odms.entity.MeasuredCarbonDioxide;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/voyages/{voyageId}/performance-reports")
@RequiredArgsConstructor
public class PerformanceReportController {
    private final PerformanceReportService performanceReportService;
    private final VoyageRepository voyageRepository;


    @GetMapping
    public ResponseEntity<List<PerformanceReportResponse>> getPerformanceReports(@PathVariable Integer voyageId) {
        if (!voyageRepository.existsById(voyageId)) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }
        List<PerformanceReport> reports = performanceReportService.getReportsByVoyageId(voyageId);
        List<PerformanceReportResponse> dtos = reports.stream()
            .map(performanceReportService::toResponse)
            .toList();
        return ResponseEntity.ok(dtos);
    }

    @PostMapping
    public ResponseEntity<PerformanceReport> createPerformanceReport(@PathVariable Integer voyageId, @RequestBody PerformanceReport report) {
        Optional<Voyage> voyageOpt = voyageRepository.findById(voyageId);
        if (voyageOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }
        report.setVoyage(voyageOpt.get());
        PerformanceReport saved = performanceReportService.saveReport(report);
        return new ResponseEntity<>(saved, HttpStatus.CREATED);
    }

    // 하위 모델별 조회 엔드포인트
    @GetMapping("/{reportId}/weather-details")
    public ResponseEntity<List<com.kr.ship_odms.dto.WeatherDetailsResponse>> getWeatherDetails(@PathVariable Integer reportId) {
        List<WeatherDetails> list = performanceReportService.getWeatherDetailsByReportId(reportId);
        List<com.kr.ship_odms.dto.WeatherDetailsResponse> dtoList = list.stream().map(com.kr.ship_odms.dto.WeatherDetailsResponse::new).toList();
        return ResponseEntity.ok(dtoList);
    }

    @GetMapping("/{reportId}/cargo-onboard")
    public ResponseEntity<List<com.kr.ship_odms.dto.CargoOnboardResponse>> getCargoOnboard(@PathVariable Integer reportId) {
        List<CargoOnboard> list = performanceReportService.getCargoOnboardByReportId(reportId);
        List<com.kr.ship_odms.dto.CargoOnboardResponse> dtoList = list.stream().map(com.kr.ship_odms.dto.CargoOnboardResponse::new).toList();
        return ResponseEntity.ok(dtoList);
    }

    @GetMapping("/{reportId}/electric-consumption")
    public ResponseEntity<List<com.kr.ship_odms.dto.ElectricConsumptionResponse>> getElectricConsumption(@PathVariable Integer reportId) {
        List<ElectricConsumption> list = performanceReportService.getElectricConsumptionByReportId(reportId);
        List<com.kr.ship_odms.dto.ElectricConsumptionResponse> dtoList = list.stream().map(com.kr.ship_odms.dto.ElectricConsumptionResponse::new).toList();
        return ResponseEntity.ok(dtoList);
    }

    @GetMapping("/{reportId}/fuel-consumption")
    public ResponseEntity<List<com.kr.ship_odms.dto.FuelConsumptionResponse>> getFuelConsumption(@PathVariable Integer reportId) {
        List<FuelConsumption> list = performanceReportService.getFuelConsumptionByReportId(reportId);
        List<com.kr.ship_odms.dto.FuelConsumptionResponse> dtoList = list.stream().map(com.kr.ship_odms.dto.FuelConsumptionResponse::new).toList();
        return ResponseEntity.ok(dtoList);
    }

    @GetMapping("/{reportId}/measured-carbon-dioxide")
    public ResponseEntity<List<com.kr.ship_odms.dto.MeasuredCarbonDioxideResponse>> getMeasuredCarbonDioxide(@PathVariable Integer reportId) {
        List<MeasuredCarbonDioxide> list = performanceReportService.getMeasuredCarbonDioxideByReportId(reportId);
        List<com.kr.ship_odms.dto.MeasuredCarbonDioxideResponse> dtoList = list.stream().map(com.kr.ship_odms.dto.MeasuredCarbonDioxideResponse::new).toList();
        return ResponseEntity.ok(dtoList);
    }
}
