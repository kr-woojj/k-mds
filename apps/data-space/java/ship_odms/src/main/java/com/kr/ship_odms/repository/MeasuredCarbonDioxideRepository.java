package com.kr.ship_odms.repository;

import com.kr.ship_odms.entity.MeasuredCarbonDioxide;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface MeasuredCarbonDioxideRepository extends JpaRepository<MeasuredCarbonDioxide, Integer> {
	List<MeasuredCarbonDioxide> findByReportId(Integer reportId);
}
