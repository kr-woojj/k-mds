package com.kr.ship_odms.entity;


import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.Data;

@Entity
@Data
public class ElectricConsumption {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "report_id")
    @JsonIgnore
    private PerformanceReport report;

    private Double powerBoiler;
    private Double powerGenerator;
    private Double powerOffset;
    private Double powerPlant;
    private Double energyCargoCooling;
    private Double energyDischargePump;
    private Double energyReeferContainers;
    private Double energyOnshorePowerSupply;
    private Double energyZeroEmissionsTech;
    private Integer fuelTypeCargoCooling;
    private Integer fuelTypeDischargePump;
    private Integer fuelTypeReeferContainer;
    private Double sfocCargoCooling;
    private Double sfocDischargePump;
    private Double sfocCargoReefers;
}
