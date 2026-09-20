package com.kr.ship_odms.entity;


import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.Data;

@Entity
@Data
public class MeasuredCarbonDioxide {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "report_id")
    @JsonIgnore
    private PerformanceReport report;

    private Double totalCo2eq;
    private Double percentageCo2EmittedAtSea;
    private Double totalCo2;
    private Double totalCo2eqCaptured;
    private Double totalCh4;
    private Double totalCh4ToCo2;
    private Double totalN2o;
    private Double totalN2oToCo2;
}
