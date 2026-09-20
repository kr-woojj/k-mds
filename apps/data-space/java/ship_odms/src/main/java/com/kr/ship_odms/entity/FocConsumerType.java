package com.kr.ship_odms.entity;

import jakarta.persistence.*;
import lombok.Data;

@Entity
@Data
public class FocConsumerType {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "fuel_consumption_id")
    @com.fasterxml.jackson.annotation.JsonIgnore
    private FuelConsumption fuelConsumption;

    private Integer fuelUsedMainEngine;
    private Double fuelConsumedMainEngine;
    private Integer fuelUsedDieselElectricPropulsion;
    private Double fuelConsumedDieselElectricPropulsion;
    private Integer fuelUsedDieselGenerator;
    private Double fuelConsumedDieselGenerator;
    private Integer fuelUsedAuxiliaryBoiler;
    private Double fuelConsumedAuxiliaryBoiler;
    private Integer fuelUsedAuxiliaryEngine;
    private Double fuelConsumedAuxiliaryEngine;
    private Integer fuelUsedCargoCooling;
    private Double fuelConsumedCargoCooling;
    private Integer fuelUsedCargoHeating;
    private Double fuelConsumedCargoHeating;
    private Integer fuelUsedDieselPowerPacks;
    private Double fuelConsumedDieselPowerPacks;
    private Integer fuelUsedDirtyPetroleumProductsCargoPump;
    private Double fuelConsumedDirtyPetroleumProductsCargoPump;
    private Integer fuelUsedDischargePump;
    private Double fuelConsumedDischargePump;
    private Integer fuelUsedDpOperations;
    private Double fuelConsumedDpOperations;
    private Integer fuelUsedElectricalPowerGeneration;
    private Double fuelConsumedElectricalPowerGeneration;
    private Integer fuelUsedIncinerator;
    private Double fuelConsumedIncinerator;
    private Integer fuelUsedInertGasGeneratorsGcus;
    private Double fuelConsumedInertGasGeneratorsGcus;
    private Integer fuelUsedOtherFuelConsumingDevices;
    private Double fuelConsumedOtherFuelConsumingDevices;
    private Integer fuelUsedReeferContainers;
    private Double fuelConsumedReeferContainers;
    private Integer fuelUsedShuttleTankerOperations;
    private Double fuelConsumedShuttleTankerOperations;
    private Integer fuelUsedStsOperations;
    private Double fuelConsumedStsOperations;
}
