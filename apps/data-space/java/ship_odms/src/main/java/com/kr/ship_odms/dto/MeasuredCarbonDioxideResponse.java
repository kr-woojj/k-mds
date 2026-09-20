package com.kr.ship_odms.dto;

import lombok.Data;
import com.kr.ship_odms.entity.MeasuredCarbonDioxide;

@Data
public class MeasuredCarbonDioxideResponse {
    private Integer id;
    private Integer report_id;
    private Double totalCo2eq;
    private Double percentageCo2EmittedAtSea;
    private Double totalCo2;
    private Double totalCo2eqCaptured;
    private Double totalCh4;
    private Double totalCh4ToCo2;
    private Double totalN2o;
    private Double totalN2oToCo2;

    public MeasuredCarbonDioxideResponse(MeasuredCarbonDioxide m) {
        this.id = m.getId();
        this.report_id = m.getReport() != null ? m.getReport().getId() : null;
        this.totalCo2eq = m.getTotalCo2eq();
        this.percentageCo2EmittedAtSea = m.getPercentageCo2EmittedAtSea();
        this.totalCo2 = m.getTotalCo2();
        this.totalCo2eqCaptured = m.getTotalCo2eqCaptured();
        this.totalCh4 = m.getTotalCh4();
        this.totalCh4ToCo2 = m.getTotalCh4ToCo2();
        this.totalN2o = m.getTotalN2o();
        this.totalN2oToCo2 = m.getTotalN2oToCo2();
    }
}
