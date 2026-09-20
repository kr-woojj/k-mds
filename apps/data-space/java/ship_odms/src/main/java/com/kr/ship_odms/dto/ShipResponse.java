package com.kr.ship_odms.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class ShipResponse {
    private Integer id;
    private String imoNumber;
    private String shipName;
    private String shipType;
    private String shipTypeMarpol;
    private String flagState;
    private String mmsi;
    private String callSign;
    private String registryPort;
}
