package com.kr.ship_odms.entity;


import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.Data;
import java.util.List;

@Entity
@Data
public class FuelConsumption {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "report_id")
    @JsonIgnore
    private PerformanceReport report;

    private Integer fuelType;
    private String fuelTypeTradeName;
    private String bdnNumber;
    private String bdnDatetime;
    private Double fuelBunkerReceived;
    private Double fuelMass;
    private Integer fuelDensity;
    private Integer fuelSulphurContent;
    private Integer fuelViscosity;
    private Integer fuelWaterContent;
    private Integer fuelHhv;
    private Integer fuelLfv;
    private Integer fuelGrade;
    private String fuelBunkerPort;
    private String fuelBunkerPortName;
    private Double co2Emission;
    private Double totalFuelQuantityConsumed;
    private Double fuelQuantityRob;
    private Double sludgeRob;
    private String fuelLcvReport;
    private Double fuelLcv;
    private String fuelPosRef;
    private Double ch4Cf;
    private Double n2oCf;
    private Double freshWaterBunkered;
    private Double freshWaterProduced;
    private Double freshWaterConsumed;
    private Double technicalWaterProduced;
    private Double technicalWaterConsumed;
    private Double washWaterConsumed;
    private Double freshWaterRob;
    private Double cloRob;
    private Double cloFeedRate;
    private Double cloConsumption;
    private Double cloReceived;

    @OneToMany(mappedBy = "fuelConsumption", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<FocFuelType> focFuelType;

    @OneToMany(mappedBy = "fuelConsumption", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<FocConsumerType> focConsumerType;
}
