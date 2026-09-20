package com.kr.ship_odms.dto;

import lombok.Data;
import com.kr.ship_odms.entity.CargoOnboard;

@Data
public class CargoOnboardResponse {
    private Integer id;
    private Integer report_id;
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
    private Double grossVolume;
    private Double grossWeight;
    private String goodsDescription;
    private String blRefId;
    private String blIssuedDate;

    public CargoOnboardResponse(CargoOnboard c) {
        this.id = c.getId();
        this.report_id = c.getReport() != null ? c.getReport().getId() : null;
        this.numberContainers = c.getNumberContainers();
        this.numberFullContainer = c.getNumberFullContainer();
        this.numberFullReeferContainers = c.getNumberFullReeferContainers();
        this.numberVehiclesOnboard = c.getNumberVehiclesOnboard();
        this.numberCrew = c.getNumberCrew();
        this.numberPassengers = c.getNumberPassengers();
        this.numberChilled20ftReeferContainers = c.getNumberChilled20ftReeferContainers();
        this.numberChilled40ftReeferContainers = c.getNumberChilled40ftReeferContainers();
        this.numberFrozen20ftReeferContainers = c.getNumberFrozen20ftReeferContainers();
        this.numberFrozen40ftReeferContainers = c.getNumberFrozen40ftReeferContainers();
        this.grossVolume = c.getGrossVolume();
        this.grossWeight = c.getGrossWeight();
        this.goodsDescription = c.getGoodsDescription();
        this.blRefId = c.getBlRefId();
        this.blIssuedDate = c.getBlIssuedDate();
    }
}
