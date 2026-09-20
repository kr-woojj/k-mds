package com.kr.ship_odms.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "performance_report")
public class PerformanceReport {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "voyage_id")
    private Voyage voyage;

    private String voyageLeg;
    private String eventType;
    private String operationType;
    private Double elapsedTime;
    private String reportType;
    private String reportDatetime;
    private Double latitude;
    private Double longitude;
    private Double distanceThroughWater;
    private Double distanceOverGround;
    private Double distanceSailedInIce;
    private Double distanceToNextPort;
    private Boolean ladenIndicator;
    private Double distanceExcluded;
    private String offHireReasons;
    private Double shipDraught;
    private Double draughtForward;
    private Double draughtAft;
    private Double speedOverGround;
    private Double speedThroughWater;
    private Double speedPropeller;
    private Double speedProjected;
    private Double speedOrder;
    private Double courseOverGround;
    private Double shipTrueHeading;

    @OneToMany(mappedBy = "report", cascade = CascadeType.ALL, orphanRemoval = true)
    private java.util.List<WeatherDetails> weatherDetails;

    @OneToMany(mappedBy = "report", cascade = CascadeType.ALL, orphanRemoval = true)
    private java.util.List<CargoOnboard> cargoOnboard;

    @OneToMany(mappedBy = "report", cascade = CascadeType.ALL, orphanRemoval = true)
    private java.util.List<ElectricConsumption> electricConsumption;

    @OneToMany(mappedBy = "report", cascade = CascadeType.ALL, orphanRemoval = true)
    private java.util.List<FuelConsumption> fuelConsumption;

    @OneToMany(mappedBy = "report", cascade = CascadeType.ALL, orphanRemoval = true)
    private java.util.List<MeasuredCarbonDioxide> measuredCarbonDioxide;
}
