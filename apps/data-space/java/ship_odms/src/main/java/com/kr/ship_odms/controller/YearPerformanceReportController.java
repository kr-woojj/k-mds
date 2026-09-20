package com.kr.ship_odms.controller;

import com.kr.ship_odms.entity.Ship;
import com.kr.ship_odms.entity.YearPerformanceReport;
import com.kr.ship_odms.repository.ShipRepository;
import com.kr.ship_odms.repository.YearPerformanceReportRepository;
import com.kr.ship_odms.dto.YearPerformanceReportResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/ships/{shipId}/yearly-reports")
@RequiredArgsConstructor
public class YearPerformanceReportController {
    private final YearPerformanceReportRepository yearPerformanceReportRepository;
    private final ShipRepository shipRepository;

    @GetMapping
    public List<YearPerformanceReportResponse> getYearlyReports(@PathVariable Integer shipId) {
        return yearPerformanceReportRepository.findByShipId(shipId)
            .stream()
            .map(r -> new YearPerformanceReportResponse(
                r.getId(),
                r.getShip() != null ? r.getShip().getId() : null,
                r.getTotalGfiAnnually()
            ))
            .toList();
    }

    @PostMapping
    public ResponseEntity<YearPerformanceReport> createYearlyReport(@PathVariable Integer shipId, @RequestBody YearPerformanceReport report) {
        Optional<Ship> shipOpt = shipRepository.findById(shipId);
        if (shipOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }
        report.setShip(shipOpt.get());
        YearPerformanceReport saved = yearPerformanceReportRepository.save(report);
        return new ResponseEntity<>(saved, HttpStatus.CREATED);
    }
}
