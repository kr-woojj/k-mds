package com.kr.ship_odms.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "ship")
public class Ship {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
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
