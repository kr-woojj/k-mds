package com.kr.ship_odms.entity;

import jakarta.persistence.*;
import lombok.Data;

@Entity
@Data
public class FocFuelType {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "fuel_consumption_id")
    @com.fasterxml.jackson.annotation.JsonIgnore
    private FuelConsumption fuelConsumption;

    private Double focMainEngine;
    private Double focDieselElectricPropulsion;
    private Double focDieselGenerator;
    private Double focAuxiliaryBoiler;
    private Double focAuxiliaryEngine;
    private Double focCargoCooling;
    private Double focCargoHeating;
    private Double focDieselPowerPacks;
    private Double focDirtyPetroleumProductsCargoPump;
    private Double focDischargePump;
    private Double focDpOperations;
    private Double focElectricalPowerGeneration;
    private Double focIncinerator;
    private Double focInertGasGeneratorsGcus;
    private Double focOtherFuelConsumingDevices;
    private Double focReeferContainers;
    private Double focShuttleTankerOperations;
    private Double focStsOperations;
}
