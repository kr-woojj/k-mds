package com.kr.ship_odms.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class VoyageResponse {
    private Integer id;
    private Integer shipId;
    private Integer yearReportId;
    private String voyageNumber;
    private String tradeServiceId;
    private Double gfiPerVoyage;
    private String inboundPortJurisdiction;
    private String outboundPortJurisdiction;
}
