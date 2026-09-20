package com.kr.ship_odms.config;

import com.kr.ship_odms.entity.Ship;
import com.kr.ship_odms.repository.ShipRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.annotation.Transactional;

@Configuration
@RequiredArgsConstructor
public class DatabaseInitializer {
    private final ShipRepository shipRepository;

    // 샘플 데이터 자동 입력 제거
}
