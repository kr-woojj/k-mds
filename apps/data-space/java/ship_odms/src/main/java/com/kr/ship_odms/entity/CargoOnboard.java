package com.kr.ship_odms.entity;


import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.Data;

@Entity
@Data
public class CargoOnboard {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "report_id")
    @JsonIgnore
    private PerformanceReport report;

    private Integer numberContainers;
    private Integer numberFullContainer;
    private Integer numberFullReeferContainers;
    private Integer numberVehiclesOnboard;
    private Integer numberCrew;
    private Integer numberPassengers;
    private Integer numberChilled20ftReeferContainers;
    private Integer numberChilled40ftReeferContainers;
    private Integer numberFrozen20ftReeferContainers;
    private Integer numberFrozen40ftReeferContainers;
    private String goodsDescription;
    private Double grossVolume;
    private Double grossWeight;
    private String blRefId;
    private String blIssuedDate;
}
