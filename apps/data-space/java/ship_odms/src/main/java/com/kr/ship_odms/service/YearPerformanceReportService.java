package com.kr.ship_odms.service;

import com.kr.ship_odms.entity.YearPerformanceReport;
import com.kr.ship_odms.entity.Ship;
import com.kr.ship_odms.repository.YearPerformanceReportRepository;
import com.kr.ship_odms.repository.ShipRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class YearPerformanceReportService {
    @Autowired
    private YearPerformanceReportRepository yearPerformanceReportRepository;
    @Autowired
    private ShipRepository shipRepository;

    public List<YearPerformanceReport> getReportsByShipId(Integer shipId) {
        return yearPerformanceReportRepository.findByShipId(shipId);
    }

    public Optional<YearPerformanceReport> createReport(Integer shipId, YearPerformanceReport report) {
        Optional<Ship> shipOpt = shipRepository.findById(shipId);
        if (shipOpt.isEmpty()) return Optional.empty();
        report.setShip(shipOpt.get());
        return Optional.of(yearPerformanceReportRepository.save(report));
    }
}
