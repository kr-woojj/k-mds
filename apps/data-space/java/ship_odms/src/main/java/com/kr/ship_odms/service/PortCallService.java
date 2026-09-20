package com.kr.ship_odms.service;

import com.kr.ship_odms.entity.PortCall;
import com.kr.ship_odms.entity.Voyage;
import com.kr.ship_odms.repository.PortCallRepository;
import com.kr.ship_odms.repository.VoyageRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Service
public class PortCallService {
    @Autowired
    private PortCallRepository portCallRepository;
    @Autowired
    private VoyageRepository voyageRepository;

    public Optional<PortCall> createPortCall(Integer voyageId, PortCall portCall) {
        Optional<Voyage> voyageOpt = voyageRepository.findById(voyageId);
        if (voyageOpt.isEmpty()) return Optional.empty();
        portCall.setVoyage(voyageOpt.get());
        return Optional.of(portCallRepository.save(portCall));
    }
}
