package com.kr.ship_odms.repository;

import com.kr.ship_odms.entity.PortCall;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PortCallRepository extends JpaRepository<PortCall, Integer> {
	java.util.List<PortCall> findByVoyageId(Integer voyageId);
}
