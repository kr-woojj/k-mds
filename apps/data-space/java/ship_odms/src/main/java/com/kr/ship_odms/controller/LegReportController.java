package com.kr.ship_odms.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.kr.ship_odms.dto.PerformanceReportResponse;
import com.kr.ship_odms.entity.FocConsumerType;
import com.kr.ship_odms.entity.FocFuelType;
import com.kr.ship_odms.entity.PortCall;
import com.kr.ship_odms.repository.PortCallRepository;
import com.kr.ship_odms.service.PerformanceReportService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 프론트엔드(Blazor)가 호출하지만 백엔드에 없던 조회 라우트 3종 (2026-09-26, S10 G-6).
 * - 항차 레그(PortCall = portAtd 출항 ~ portAta 도착) 범위의 PerformanceReport 목록/상세
 * - FuelConsumption 하위 FocFuelType / FocConsumerType 평면 목록 (fuelConsumptionId 포함)
 */
@RestController
@RequiredArgsConstructor
public class LegReportController {
    private final PerformanceReportService reports;
    private final PortCallRepository portCalls;
    private final ObjectMapper mapper = new ObjectMapper();

    @GetMapping("/api/ships/{shipId}/voyages/{voyageId}/port-calls/{portCallId}/performance-reports")
    public ResponseEntity<List<PerformanceReportResponse>> legReports(@PathVariable Integer shipId, @PathVariable Integer voyageId,
                                                                      @PathVariable Integer portCallId) {
        Optional<PortCall> pc = portCalls.findById(portCallId);
        if (pc.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        String from = pc.get().getPortAtd(), to = pc.get().getPortAta();
        // ponytail: ISO-8601 문자열 사전순 비교(같은 표기 전제). 표기가 섞이면 Instant 파싱으로 교체.
        List<PerformanceReportResponse> out = reports.getReportsByVoyageId(voyageId).stream()
            .filter(r -> inLeg(r.getReportDatetime(), from, to))
            .map(reports::toResponse)
            .toList();
        return ResponseEntity.ok(out);
    }

    @GetMapping("/api/ships/{shipId}/voyages/{voyageId}/port-calls/{portCallId}/performance-reports/{reportId}")
    public ResponseEntity<PerformanceReportResponse> legReport(@PathVariable Integer shipId, @PathVariable Integer voyageId,
                                                               @PathVariable Integer portCallId, @PathVariable Integer reportId) {
        return reports.getReport(reportId).map(reports::toResponse).map(ResponseEntity::ok)
            .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/api/voyages/{voyageId}/performance-reports/{reportId}/foc-fuel-type")
    public List<Map<String, Object>> focFuelType(@PathVariable Integer voyageId, @PathVariable Integer reportId) {
        return reports.getFuelConsumptionByReportId(reportId).stream()
            .flatMap(fc -> (fc.getFocFuelType() == null ? List.<FocFuelType>of() : fc.getFocFuelType()).stream()
                .map(f -> withParent(f, fc.getId())))
            .toList();
    }

    @GetMapping("/api/voyages/{voyageId}/performance-reports/{reportId}/foc-consumer-type")
    public List<Map<String, Object>> focConsumerType(@PathVariable Integer voyageId, @PathVariable Integer reportId) {
        return reports.getFuelConsumptionByReportId(reportId).stream()
            .flatMap(fc -> (fc.getFocConsumerType() == null ? List.<FocConsumerType>of() : fc.getFocConsumerType()).stream()
                .map(f -> withParent(f, fc.getId())))
            .toList();
    }

    private Map<String, Object> withParent(Object entity, Integer fuelConsumptionId) {
        Map<String, Object> m = mapper.convertValue(entity, new TypeReference<Map<String, Object>>() { });
        m.put("fuelConsumptionId", fuelConsumptionId);
        return m;
    }

    static boolean inLeg(String t, String from, String to) {
        if (t == null) {
            return false;
        }
        if (from != null && !from.isBlank() && t.compareTo(from) < 0) {
            return false;
        }
        return to == null || to.isBlank() || t.compareTo(to) <= 0;
    }
}
