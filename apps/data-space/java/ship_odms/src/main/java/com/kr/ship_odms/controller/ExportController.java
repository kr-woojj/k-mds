package com.kr.ship_odms.controller;

import com.kr.ship_odms.service.ExportService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.util.Map;
import java.util.Optional;

/** 선박 1척의 저장 데이터 내보내기: format=json(중첩 구조) 또는 csv(표별 CSV 를 묶은 zip). */
@RestController
@RequestMapping("/api/ships/{shipId}/export")
@RequiredArgsConstructor
public class ExportController {
    private final ExportService exportService;

    @GetMapping
    public ResponseEntity<?> export(@PathVariable Integer shipId, @RequestParam(defaultValue = "json") String format) throws IOException {
        boolean csv = "csv".equals(format);
        if (!csv && !"json".equals(format)) {
            return ResponseEntity.badRequest().body(Map.of("error", "format 은 json 또는 csv 여야 합니다."));
        }
        Optional<Map<String, Object>> data = exportService.collect(shipId);
        if (data.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }
        String name = "ship-" + shipId + "-export." + (csv ? "zip" : "json");
        ResponseEntity.BodyBuilder ok = ResponseEntity.ok().header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + name + "\"");
        return csv
            ? ok.contentType(MediaType.parseMediaType("application/zip")).body(exportService.toCsvZip(data.get()))
            : ok.contentType(MediaType.APPLICATION_JSON).body(data.get());
    }
}
