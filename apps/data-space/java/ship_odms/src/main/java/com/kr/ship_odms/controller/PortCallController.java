package com.kr.ship_odms.controller;

import com.kr.ship_odms.entity.Voyage;
import com.kr.ship_odms.entity.PortCall;
import com.kr.ship_odms.repository.VoyageRepository;
import com.kr.ship_odms.repository.PortCallRepository;
import com.kr.ship_odms.dto.PortCallResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Optional;

@RestController
@RequestMapping("/api/voyages/{voyageId}/port-calls")
@RequiredArgsConstructor
public class PortCallController {
    private final PortCallRepository portCallRepository;
    private final VoyageRepository voyageRepository;

    @GetMapping
    public java.util.List<PortCallResponse> getPortCalls(@PathVariable Integer voyageId) {
        return portCallRepository.findByVoyageId(voyageId).stream()
            .map(p -> new PortCallResponse(
                p.getId(),
                p.getVoyage() != null ? p.getVoyage().getId() : null,
                p.getPortArrival(),
                p.getPortDeparture(),
                p.getPortAta(),
                p.getPortAtd()
            ))
            .toList();
    }

    @PostMapping
    public ResponseEntity<PortCall> createPortCall(@PathVariable Integer voyageId, @RequestBody PortCall portCall) {
        Optional<Voyage> voyageOpt = voyageRepository.findById(voyageId);
        if (voyageOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }
        // 같은 항차·출항항·출항시각의 포트콜이 이미 있으면 그 행을 갱신한다(재전송 누적 방지, 2026-11-17).
        if (portCall.getId() == null && portCall.getPortAtd() != null) {
            portCallRepository.findByVoyageIdAndPortDepartureAndPortAtd(voyageId, portCall.getPortDeparture(), portCall.getPortAtd())
                .stream().findFirst().ifPresent(existing -> portCall.setId(existing.getId()));
        }
        portCall.setVoyage(voyageOpt.get());
        PortCall saved = portCallRepository.save(portCall);
        return new ResponseEntity<>(saved, HttpStatus.CREATED);
    }
}
