package com.kr.ship_odms.service;

import com.kr.ship_odms.entity.Voyage;
import com.kr.ship_odms.entity.Ship;
import com.kr.ship_odms.repository.VoyageRepository;
import com.kr.ship_odms.repository.ShipRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class VoyageService {
    @Autowired
    private VoyageRepository voyageRepository;
    @Autowired
    private ShipRepository shipRepository;

    public List<Voyage> getVoyagesByShipId(Integer shipId) {
        return voyageRepository.findByShipId(shipId);
    }

    public Optional<Voyage> createVoyage(Integer shipId, Voyage voyage) {
        Optional<Ship> shipOpt = shipRepository.findById(shipId);
        if (shipOpt.isEmpty()) return Optional.empty();
        voyage.setShip(shipOpt.get());
        return Optional.of(voyageRepository.save(voyage));
    }
}
