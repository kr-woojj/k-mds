package com.kr.ship_odms.controller;

import com.kr.ship_odms.entity.Ship;
import com.kr.ship_odms.repository.ShipRepository;
import com.kr.ship_odms.dto.ShipResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Optional;

@RestController
@RequestMapping("/api/ships")
@RequiredArgsConstructor
public class ShipController {
    private final ShipRepository shipRepository;

    @GetMapping
    public List<ShipResponse> getShips() {
        return shipRepository.findAll().stream()
            .map(s -> new ShipResponse(
                s.getId(),
                s.getImoNumber(),
                s.getShipName(),
                s.getShipType(),
                s.getShipTypeMarpol(),
                s.getFlagState(),
                s.getMmsi(),
                s.getCallSign(),
                s.getRegistryPort()
            ))
            .toList();
    }

    @PostMapping
    public ResponseEntity<Ship> createShip(@RequestBody Ship ship) {
        Ship saved = shipRepository.save(ship);
        return new ResponseEntity<>(saved, HttpStatus.CREATED);
    }

    @GetMapping("/{shipId}")
    public ResponseEntity<ShipResponse> getShip(@PathVariable Integer shipId) {
        Optional<Ship> ship = shipRepository.findById(shipId);
        return ship
            .map(s -> ResponseEntity.ok(new ShipResponse(
                s.getId(),
                s.getImoNumber(),
                s.getShipName(),
                s.getShipType(),
                s.getShipTypeMarpol(),
                s.getFlagState(),
                s.getMmsi(),
                s.getCallSign(),
                s.getRegistryPort()
            )))
            .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).build());
    }
}
