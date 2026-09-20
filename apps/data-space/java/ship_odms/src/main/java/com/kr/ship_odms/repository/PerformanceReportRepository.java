package com.kr.ship_odms.repository;

import com.kr.ship_odms.entity.PerformanceReport;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface PerformanceReportRepository extends JpaRepository<PerformanceReport, Integer> {
	List<PerformanceReport> findByVoyageId(Integer voyageId);
}
