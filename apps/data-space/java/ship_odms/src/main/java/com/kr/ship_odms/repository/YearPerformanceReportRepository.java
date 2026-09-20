package com.kr.ship_odms.repository;

import com.kr.ship_odms.entity.YearPerformanceReport;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface YearPerformanceReportRepository extends JpaRepository<YearPerformanceReport, Integer> {
    List<YearPerformanceReport> findByShipId(Integer shipId);
}
