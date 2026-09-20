package com.kr.ship_odms.dto;

import lombok.Data;
import com.kr.ship_odms.entity.ElectricConsumption;

@Data
public class ElectricConsumptionResponse {
    private Integer id;
    private Integer report_id;
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

    public ElectricConsumptionResponse(ElectricConsumption e) {
        this.id = e.getId();
        this.report_id = e.getReport() != null ? e.getReport().getId() : null;
        this.powerBoiler = e.getPowerBoiler();
        this.powerGenerator = e.getPowerGenerator();
        this.powerOffset = e.getPowerOffset();
        this.powerPlant = e.getPowerPlant();
        this.energyCargoCooling = e.getEnergyCargoCooling();
        this.energyDischargePump = e.getEnergyDischargePump();
        this.energyReeferContainers = e.getEnergyReeferContainers();
        this.energyOnshorePowerSupply = e.getEnergyOnshorePowerSupply();
        this.energyZeroEmissionsTech = e.getEnergyZeroEmissionsTech();
        this.fuelTypeCargoCooling = e.getFuelTypeCargoCooling();
        this.fuelTypeDischargePump = e.getFuelTypeDischargePump();
        this.fuelTypeReeferContainer = e.getFuelTypeReeferContainer();
        this.sfocCargoCooling = e.getSfocCargoCooling();
        this.sfocDischargePump = e.getSfocDischargePump();
        this.sfocCargoReefers = e.getSfocCargoReefers();
    }
}
