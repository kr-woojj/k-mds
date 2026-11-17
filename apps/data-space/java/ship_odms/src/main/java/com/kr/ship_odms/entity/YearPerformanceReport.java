package com.kr.ship_odms.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "year_performance_report")
public class YearPerformanceReport {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "ship_id")
    private Ship ship;

    private Integer reportYear;  // 보고 연도 — K-MDS 확장(FAL50 에 대응 요소 없음, 2026-11-17 추가)
    private Double totalGfiAnnually;
}
