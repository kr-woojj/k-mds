package com.kr.ship_odms.repository;

import com.kr.ship_odms.entity.ElectricConsumption;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ElectricConsumptionRepository extends JpaRepository<ElectricConsumption, Integer> {
	List<ElectricConsumption> findByReportId(Integer reportId);
}
