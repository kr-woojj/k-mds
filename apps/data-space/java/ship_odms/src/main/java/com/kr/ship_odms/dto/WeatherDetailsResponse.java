package com.kr.ship_odms.dto;

import lombok.Data;
import com.kr.ship_odms.entity.WeatherDetails;

@Data
public class WeatherDetailsResponse {
    private Integer id;
    private Integer report_id;
    private Integer seaState;
    private Integer windForce;
    private Integer windSpeed;
    private Integer windDir;
    private Double windDirRelative;
    private Double windDirTrue;
    private Double airTemperature;
    private Integer atmosphericPressure;
    private Integer seaDirRelative;
    private Integer seaDirTrue;
    private Integer seaHeight;
    private Integer swellDirRelative;
    private Integer swellDirTrue;
    private Integer swellHeight;
    private Integer oceanDirRelative;
    private Integer oceanDirTrue;
    private Integer oceanDirWeatherProvider;

    public WeatherDetailsResponse(WeatherDetails wd) {
        this.id = wd.getId();
        this.report_id = wd.getReport() != null ? wd.getReport().getId() : null;
        this.seaState = wd.getSeaState();
        this.windForce = wd.getWindForce();
        this.windSpeed = wd.getWindSpeed();
        this.windDir = wd.getWindDir();
        this.windDirRelative = wd.getWindDirRelative();
        this.windDirTrue = wd.getWindDirTrue();
        this.airTemperature = wd.getAirTemperature();
        this.atmosphericPressure = wd.getAtmosphericPressure();
        this.seaDirRelative = wd.getSeaDirRelative();
        this.seaDirTrue = wd.getSeaDirTrue();
        this.seaHeight = wd.getSeaHeight();
        this.swellDirRelative = wd.getSwellDirRelative();
        this.swellDirTrue = wd.getSwellDirTrue();
        this.swellHeight = wd.getSwellHeight();
        this.oceanDirRelative = wd.getOceanDirRelative();
        this.oceanDirTrue = wd.getOceanDirTrue();
        this.oceanDirWeatherProvider = wd.getOceanDirWeatherProvider();
    }
}
