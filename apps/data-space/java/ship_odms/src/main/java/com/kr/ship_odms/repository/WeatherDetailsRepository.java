package com.kr.ship_odms.repository;

import com.kr.ship_odms.entity.WeatherDetails;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface WeatherDetailsRepository extends JpaRepository<WeatherDetails, Integer> {
    List<WeatherDetails> findByReportId(Integer reportId);
}
