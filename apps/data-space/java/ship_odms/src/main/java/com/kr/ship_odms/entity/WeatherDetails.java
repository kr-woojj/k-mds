package com.kr.ship_odms.entity;


import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import lombok.Data;

@Entity
@Data
public class WeatherDetails {
    // DTO에서 report_id를 올바르게 가져오기 위한 getter
    public PerformanceReport getReport() {
        return this.report;
    }
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "report_id")
    @JsonIgnore
    private PerformanceReport report;

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
}
