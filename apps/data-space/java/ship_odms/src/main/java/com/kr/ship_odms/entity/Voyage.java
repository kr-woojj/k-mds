package com.kr.ship_odms.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "voyage")
public class Voyage {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "ship_id")
    private Ship ship;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "year_report_id")
    private YearPerformanceReport yearReport;

    private String voyageNumber;
    private String tradeServiceId;
    private Double gfiPerVoyage;
    private String inboundPortJurisdiction;
    private String outboundPortJurisdiction;
}
