package com.kr.ship_odms.dto;

import com.kr.ship_odms.entity.WeatherDetails;
import com.kr.ship_odms.entity.CargoOnboard;
import com.kr.ship_odms.entity.ElectricConsumption;
import com.kr.ship_odms.entity.FuelConsumption;
import com.kr.ship_odms.entity.MeasuredCarbonDioxide;
import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class PerformanceReportResponse {
    private Integer id;
    private Integer voyageId;
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

    // 하위 데이터 리스트 추가
    private List<WeatherDetails> weatherDetails;
    private List<CargoOnboard> cargoOnboard;
    private List<ElectricConsumption> electricConsumption;
    private List<FuelConsumption> fuelConsumption;
    private List<MeasuredCarbonDioxide> measuredCarbonDioxide;
}
