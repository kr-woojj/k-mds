package com.kr.ship_odms.controller;

import com.kr.ship_odms.entity.Ship;
import com.kr.ship_odms.entity.Voyage;
import com.kr.ship_odms.repository.ShipRepository;
import com.kr.ship_odms.repository.VoyageRepository;
import com.kr.ship_odms.dto.VoyageResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/ships/{shipId}/voyages")
@RequiredArgsConstructor
public class VoyageController {
    private final VoyageRepository voyageRepository;
    private final ShipRepository shipRepository;

    @GetMapping
    public List<VoyageResponse> getVoyages(@PathVariable Integer shipId) {
        return voyageRepository.findByShipId(shipId).stream()
            .map(v -> new VoyageResponse(
                v.getId(),
                v.getShip() != null ? v.getShip().getId() : null,
                v.getYearReport() != null ? v.getYearReport().getId() : null,
                v.getVoyageNumber(),
                v.getTradeServiceId(),
                v.getGfiPerVoyage(),
                v.getInboundPortJurisdiction(),
                v.getOutboundPortJurisdiction()
            ))
            .toList();
    }

    @PostMapping
    public ResponseEntity<Voyage> createVoyage(@PathVariable Integer shipId, @RequestBody Voyage voyage) {
        Optional<Ship> shipOpt = shipRepository.findById(shipId);
        if (shipOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND).build();
        }
        voyage.setShip(shipOpt.get());
        Voyage saved = voyageRepository.save(voyage);
        return new ResponseEntity<>(saved, HttpStatus.CREATED);
    }
}
