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
    private final com.kr.ship_odms.service.ShipService shipService;

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

    /** 선박과 하위 항차·포트콜·보고·연차보고를 함께 삭제한다. 응답: 삭제 건수. 없으면 404. */
    @DeleteMapping("/{shipId}")
    public ResponseEntity<java.util.Map<String, Integer>> deleteShip(@PathVariable Integer shipId) {
        return shipService.deleteShipCascade(shipId)
            .map(ResponseEntity::ok)
            .orElseGet(() -> ResponseEntity.status(HttpStatus.NOT_FOUND).build());
    }
}
