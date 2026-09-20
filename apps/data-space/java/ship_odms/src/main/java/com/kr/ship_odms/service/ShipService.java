package com.kr.ship_odms.service;

import com.kr.ship_odms.entity.Ship;
import com.kr.ship_odms.repository.ShipRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class ShipService {
    @Autowired
    private ShipRepository shipRepository;

    public List<Ship> getAllShips() {
        return shipRepository.findAll();
    }

    public Optional<Ship> getShipById(Integer id) {
        return shipRepository.findById(id);
    }

    public Ship createShip(Ship ship) {
        return shipRepository.save(ship);
    }
}
