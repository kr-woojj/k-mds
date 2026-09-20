package com.kr.ship_odms.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class YearPerformanceReportResponse {
    private Integer id;
    private Integer shipId;
    private Double totalGfiAnnually;
}
