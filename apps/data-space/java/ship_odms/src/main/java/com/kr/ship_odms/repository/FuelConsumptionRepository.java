package com.kr.ship_odms.repository;

import com.kr.ship_odms.entity.FuelConsumption;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface FuelConsumptionRepository extends JpaRepository<FuelConsumption, Integer> {
	List<FuelConsumption> findByReportId(Integer reportId);
}
