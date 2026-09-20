package com.kr.ship_odms.repository;

import com.kr.ship_odms.entity.Ship;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ShipRepository extends JpaRepository<Ship, Integer> {
}
