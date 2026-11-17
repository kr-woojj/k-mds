package com.kr.ship_odms;

import com.kr.ship_odms.controller.ExportController;
import com.kr.ship_odms.controller.PerformanceReportController;
import com.kr.ship_odms.controller.PortCallController;
import com.kr.ship_odms.entity.FuelConsumption;
import com.kr.ship_odms.entity.PerformanceReport;
import com.kr.ship_odms.entity.PortCall;
import com.kr.ship_odms.entity.Ship;
import com.kr.ship_odms.entity.Voyage;
import com.kr.ship_odms.repository.ShipRepository;
import com.kr.ship_odms.repository.VoyageRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.ResponseEntity;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

// 테스트는 실행 DB(ship_odms.db)를 건드리지 않고 build/ 아래 임시 DB 를 쓴다.
@SpringBootTest(properties = "spring.datasource.url=jdbc:sqlite:build/test.db")
class ExportAndUpsertTests {
    @Autowired ShipRepository ships;
    @Autowired VoyageRepository voyages;
    @Autowired PerformanceReportController reports;
    @Autowired PortCallController portCalls;
    @Autowired ExportController export;
    @Autowired com.kr.ship_odms.controller.YearPerformanceReportController yearly;

    private PerformanceReport report(String remarks) {
        PerformanceReport r = new PerformanceReport();
        r.setReportDatetime("2026-01-01T00:00:00Z");
        r.setEventType("EV16");
        r.setVoyageLegRemarks(remarks);
        FuelConsumption fc = new FuelConsumption();
        fc.setFuelTypeTradeName("HFO");
        r.setFuelConsumption(new java.util.ArrayList<>(List.of(fc)));
        return r;
    }

    @Test
    @SuppressWarnings("unchecked")
    void resendReplacesAndExportReturnsStoredData() throws Exception {
        Ship ship = new Ship();
        ship.setImoNumber("00000009");
        ship.setShipName("TEST, \"SHIP\"");
        ship = ships.save(ship);
        Voyage v = new Voyage();
        v.setShip(ship);
        v.setVoyageNumber("1");
        v = voyages.save(v);

        // 같은 보고·포트콜을 두 번 보내도 한 건만 남고, 나중 값으로 바뀐다.
        reports.createPerformanceReport(v.getId(), report("first"));
        reports.createPerformanceReport(v.getId(), report("=second"));
        for (int i = 0; i < 2; i++) {
            PortCall pc = new PortCall();
            pc.setPortDeparture("KRPUS");
            pc.setPortAtd("2026-01-01T00:00:00Z");
            portCalls.createPortCall(v.getId(), pc);
        }

        Map<String, Object> json = (Map<String, Object>) export.export(ship.getId(), "json").getBody();
        Map<String, Object> s = (Map<String, Object>) json.get("ship");
        Map<String, Object> voyage = ((List<Map<String, Object>>) s.get("voyages")).get(0);
        List<Map<String, Object>> rs = (List<Map<String, Object>>) voyage.get("performanceReports");
        assertEquals(1, rs.size());
        assertEquals("=second", rs.get(0).get("voyageLegRemarks"));
        assertEquals(1, ((List<?>) rs.get(0).get("fuelConsumption")).size());
        assertEquals(1, ((List<?>) voyage.get("portCalls")).size());

        ResponseEntity<?> csv = export.export(ship.getId(), "csv");
        Map<String, String> files = new HashMap<>();
        try (ZipInputStream zip = new ZipInputStream(new ByteArrayInputStream((byte[]) csv.getBody()))) {
            for (ZipEntry e; (e = zip.getNextEntry()) != null; ) files.put(e.getName(), new String(zip.readAllBytes(), StandardCharsets.UTF_8));
        }
        assertTrue(files.keySet().containsAll(List.of("ship.csv", "voyages.csv", "portCalls.csv", "performanceReports.csv", "fuelConsumption.csv", "weatherDetails.csv")), files.keySet().toString());
        assertTrue(files.get("ship.csv").startsWith("﻿id,"));
        assertTrue(files.get("ship.csv").contains("\"TEST, \"\"SHIP\"\"\""));          // 쉼표·따옴표 이스케이프
        assertTrue(files.get("performanceReports.csv").contains("'=second"));        // 수식 주입 방지
        assertTrue(files.get("fuelConsumption.csv").startsWith("﻿performanceReportId,id,"));
        assertEquals(2, files.get("performanceReports.csv").split("\r\n").length);   // 머리글 + 1행

        // 연차보고는 선박·연도당 한 건: 같은 연도를 다시 넣으면 값만 바뀐다.
        for (double gfi : new double[] {70.0, 71.5}) {
            com.kr.ship_odms.entity.YearPerformanceReport y = new com.kr.ship_odms.entity.YearPerformanceReport();
            y.setReportYear(2026);
            y.setTotalGfiAnnually(gfi);
            yearly.createYearlyReport(ship.getId(), y);
        }
        var years = yearly.getYearlyReports(ship.getId());
        assertEquals(1, years.size());
        assertEquals(2026, years.get(0).getReportYear());
        assertEquals(71.5, years.get(0).getTotalGfiAnnually());

        assertEquals(404, export.export(-1, "json").getStatusCode().value());
        assertEquals(400, export.export(ship.getId(), "xml").getStatusCode().value());
    }
}
