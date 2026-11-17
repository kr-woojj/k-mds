package com.kr.ship_odms.service;

import com.kr.ship_odms.entity.FuelConsumption;
import com.kr.ship_odms.entity.PerformanceReport;
import com.kr.ship_odms.entity.Ship;
import com.kr.ship_odms.entity.Voyage;
import com.kr.ship_odms.repository.PerformanceReportRepository;
import com.kr.ship_odms.repository.PortCallRepository;
import com.kr.ship_odms.repository.ShipRepository;
import com.kr.ship_odms.repository.VoyageRepository;
import com.kr.ship_odms.repository.YearPerformanceReportRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * 선박 1척의 저장 데이터를 통째로 내보낸다 (정합성 검증용, 2026-11-17).
 * JSON 은 중첩 구조 그대로, CSV 는 표(엔터티)별 파일을 zip 으로 묶는다. 값은 DB 저장값 그대로이며 가공하지 않는다.
 */
@Service
@RequiredArgsConstructor
public class ExportService {
    private final ShipRepository shipRepository;
    private final VoyageRepository voyageRepository;
    private final PortCallRepository portCallRepository;
    private final PerformanceReportRepository performanceReportRepository;
    private final YearPerformanceReportRepository yearPerformanceReportRepository;
    private final PerformanceReportService performanceReportService;

    @Transactional(readOnly = true)
    public Optional<Map<String, Object>> collect(Integer shipId) {
        Optional<Ship> shipOpt = shipRepository.findById(shipId);
        if (shipOpt.isEmpty()) return Optional.empty();
        Map<String, Object> ship = scalars(shipOpt.get());
        List<Map<String, Object>> voyages = new ArrayList<>();
        for (Voyage v : voyageRepository.findByShipId(shipId)) {
            Map<String, Object> vm = scalars(v);
            vm.put("portCalls", portCallRepository.findByVoyageId(v.getId()).stream().map(ExportService::scalars).toList());
            List<Map<String, Object>> reports = new ArrayList<>();
            for (PerformanceReport r : performanceReportRepository.findByVoyageId(v.getId())) {
                Map<String, Object> rm = scalars(r);
                Integer rid = r.getId();
                rm.put("weatherDetails", performanceReportService.getWeatherDetailsByReportId(rid).stream().map(ExportService::scalars).toList());
                rm.put("cargoOnboard", performanceReportService.getCargoOnboardByReportId(rid).stream().map(ExportService::scalars).toList());
                rm.put("electricConsumption", performanceReportService.getElectricConsumptionByReportId(rid).stream().map(ExportService::scalars).toList());
                List<Map<String, Object>> fuels = new ArrayList<>();
                for (FuelConsumption fc : performanceReportService.getFuelConsumptionByReportId(rid)) {
                    Map<String, Object> fm = scalars(fc);
                    fm.put("focFuelType", fc.getFocFuelType() == null ? List.of() : fc.getFocFuelType().stream().map(ExportService::scalars).toList());
                    fm.put("focConsumerType", fc.getFocConsumerType() == null ? List.of() : fc.getFocConsumerType().stream().map(ExportService::scalars).toList());
                    fuels.add(fm);
                }
                rm.put("fuelConsumption", fuels);
                rm.put("measuredCarbonDioxide", performanceReportService.getMeasuredCarbonDioxideByReportId(rid).stream().map(ExportService::scalars).toList());
                reports.add(rm);
            }
            vm.put("performanceReports", reports);
            voyages.add(vm);
        }
        ship.put("voyages", voyages);
        ship.put("yearPerformanceReports", yearPerformanceReportRepository.findByShipId(shipId).stream().map(ExportService::scalars).toList());
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("exportedAt", Instant.now().toString());
        out.put("ship", ship);
        return Optional.of(out);
    }

    /** 표별 CSV(UTF-8 BOM, CRLF)를 zip 으로 묶는다. 자식 표의 첫 열은 부모 id. */
    @SuppressWarnings("unchecked")
    public byte[] toCsvZip(Map<String, Object> export) throws IOException {
        Map<String, List<Map<String, Object>>> tables = new LinkedHashMap<>();
        walk("ship", (Map<String, Object>) export.get("ship"), null, null, tables);
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (ZipOutputStream zip = new ZipOutputStream(bytes, StandardCharsets.UTF_8)) {
            for (Map.Entry<String, List<Map<String, Object>>> t : tables.entrySet()) {
                zip.putNextEntry(new ZipEntry(t.getKey() + ".csv"));
                zip.write(toCsv(t.getValue()).getBytes(StandardCharsets.UTF_8));
                zip.closeEntry();
            }
        }
        return bytes.toByteArray();
    }

    @SuppressWarnings("unchecked")
    private static void walk(String table, Map<String, Object> node, String parentCol, Object parentId,
                             Map<String, List<Map<String, Object>>> tables) {
        Map<String, Object> row = new LinkedHashMap<>();
        if (parentCol != null) row.put(parentCol, parentId);
        tables.computeIfAbsent(table, t -> new ArrayList<>()).add(row);
        String childParentCol = table.replaceAll("s$", "") + "Id";
        node.forEach((k, v) -> {
            if (v instanceof List<?> list) {
                tables.computeIfAbsent(k, t -> new ArrayList<>());  // 행이 없어도 빈 표는 만든다
                list.forEach(c -> walk(k, (Map<String, Object>) c, childParentCol, node.get("id"), tables));
            } else {
                row.put(k, v);
            }
        });
    }

    static String toCsv(List<Map<String, Object>> rows) {
        StringBuilder sb = new StringBuilder("﻿");  // 엑셀이 UTF-8 로 읽도록 BOM
        if (rows.isEmpty()) return sb.toString();
        List<String> header = new ArrayList<>(rows.get(0).keySet());
        sb.append(String.join(",", header)).append("\r\n");
        for (Map<String, Object> row : rows) {
            sb.append(String.join(",", header.stream().map(h -> cell(row.get(h))).toList())).append("\r\n");
        }
        return sb.toString();
    }

    static String cell(Object v) {
        if (v == null) return "";
        String s = v.toString();
        // 엑셀 수식 주입 방지: 문자열 값이 = + - @ 로 시작하면 작은따옴표를 붙인다(숫자형은 해당 없음).
        if (v instanceof String && !s.isEmpty() && "=+-@".indexOf(s.charAt(0)) >= 0) s = "'" + s;
        return s.matches("(?s).*[\",\\r\\n].*") ? "\"" + s.replace("\"", "\"\"") + "\"" : s;
    }

    /** 엔터티의 단순값 필드(문자열·숫자·불리언)만 선언 순서대로 뽑는다. 연관 필드는 호출부가 붙인다. */
    static Map<String, Object> scalars(Object entity) {
        Map<String, Object> m = new LinkedHashMap<>();
        for (Field f : entity.getClass().getDeclaredFields()) {
            Class<?> t = f.getType();
            if (Modifier.isStatic(f.getModifiers()) || !(t == String.class || Number.class.isAssignableFrom(t) || t == Boolean.class)) continue;
            try {
                f.setAccessible(true);
                m.put(f.getName(), f.get(entity));
            } catch (IllegalAccessException e) {
                throw new IllegalStateException(e);
            }
        }
        return m;
    }
}
