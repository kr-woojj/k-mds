package com.kr.ship_odms.dto;

import java.util.List;
import java.util.stream.Collectors;
import com.kr.ship_odms.entity.FocFuelType;
import com.kr.ship_odms.entity.FocConsumerType;
import com.kr.ship_odms.entity.FuelConsumption;
import lombok.Data;

@Data
public class FuelConsumptionResponse {
    private Integer id;
    private Integer report_id;
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

    private List<FocFuelType> focFuelType;
    private List<FocConsumerType> focConsumerType;

    public FuelConsumptionResponse(FuelConsumption f) {
        this.id = f.getId();
        this.report_id = f.getReport() != null ? f.getReport().getId() : null;
        this.fuelType = f.getFuelType();
        this.fuelTypeTradeName = f.getFuelTypeTradeName();
        this.bdnNumber = f.getBdnNumber();
        this.bdnDatetime = f.getBdnDatetime();
        this.fuelBunkerReceived = f.getFuelBunkerReceived();
        this.fuelMass = f.getFuelMass();
        this.fuelDensity = f.getFuelDensity();
        this.fuelSulphurContent = f.getFuelSulphurContent();
        this.fuelViscosity = f.getFuelViscosity();
        this.fuelWaterContent = f.getFuelWaterContent();
        this.fuelHhv = f.getFuelHhv();
        this.fuelLfv = f.getFuelLfv();
        this.fuelGrade = f.getFuelGrade();
        this.fuelBunkerPort = f.getFuelBunkerPort();
        this.fuelBunkerPortName = f.getFuelBunkerPortName();
        this.co2Emission = f.getCo2Emission();
        this.totalFuelQuantityConsumed = f.getTotalFuelQuantityConsumed();
        this.fuelQuantityRob = f.getFuelQuantityRob();
        this.sludgeRob = f.getSludgeRob();
        this.fuelLcvReport = f.getFuelLcvReport();
        this.fuelLcv = f.getFuelLcv();
        this.fuelPosRef = f.getFuelPosRef();
        this.ch4Cf = f.getCh4Cf();
        this.n2oCf = f.getN2oCf();
        this.freshWaterBunkered = f.getFreshWaterBunkered();
        this.freshWaterProduced = f.getFreshWaterProduced();
        this.freshWaterConsumed = f.getFreshWaterConsumed();
        this.technicalWaterProduced = f.getTechnicalWaterProduced();
        this.technicalWaterConsumed = f.getTechnicalWaterConsumed();
        this.washWaterConsumed = f.getWashWaterConsumed();
        this.freshWaterRob = f.getFreshWaterRob();
        this.cloRob = f.getCloRob();
        this.cloFeedRate = f.getCloFeedRate();
        this.cloConsumption = f.getCloConsumption();
        this.cloReceived = f.getCloReceived();

        // 연관 데이터 포함
        this.focFuelType = f.getFocFuelType();
        this.focConsumerType = f.getFocConsumerType();
    }
}
