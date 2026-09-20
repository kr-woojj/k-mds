package com.kr.ship_odms.repository;

import com.kr.ship_odms.entity.Voyage;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface VoyageRepository extends JpaRepository<Voyage, Integer> {
    List<Voyage> findByShipId(Integer shipId);
}
