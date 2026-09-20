package com.kr.ship_odms.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class PortCallResponse {
    private Integer id;
    private Integer voyageId;
    private String portArrival;
    private String portDeparture;
    private String portAta;
    private String portAtd;
}
