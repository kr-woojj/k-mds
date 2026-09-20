package com.kr.ship_odms.repository;

import com.kr.ship_odms.entity.CargoOnboard;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface CargoOnboardRepository extends JpaRepository<CargoOnboard, Integer> {
    List<CargoOnboard> findByReportId(Integer reportId);
}
