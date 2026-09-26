package com.kr.ship_odms.service;

import com.kr.ship_odms.entity.PortCall;
import com.kr.ship_odms.entity.PerformanceReport;
import com.kr.ship_odms.entity.Ship;
import com.kr.ship_odms.entity.Voyage;
import com.kr.ship_odms.entity.YearPerformanceReport;
import com.kr.ship_odms.repository.PerformanceReportRepository;
import com.kr.ship_odms.repository.PortCallRepository;
import com.kr.ship_odms.repository.ShipRepository;
import com.kr.ship_odms.repository.VoyageRepository;
import com.kr.ship_odms.repository.YearPerformanceReportRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Service
public class ShipService {
    @Autowired
    private ShipRepository shipRepository;
    @Autowired
    private VoyageRepository voyageRepository;
    @Autowired
    private PortCallRepository portCallRepository;
    @Autowired
    private PerformanceReportRepository performanceReportRepository;
    @Autowired
    private YearPerformanceReportRepository yearPerformanceReportRepository;

    public List<Ship> getAllShips() {
        return shipRepository.findAll();
    }

    public Optional<Ship> getShipById(Integer id) {
        return shipRepository.findById(id);
    }

    public Ship createShip(Ship ship) {
        return shipRepository.save(ship);
    }

    /**
     * 선박과 하위 데이터를 모두 삭제한다 (2026-09-26 추가).
     * 순서: 항차별 PerformanceReport(자식은 JPA cascade) → PortCall → Voyage(year_report FK 보유) → YearPerformanceReport → Ship.
     * Ship/Voyage 엔터티에 cascade 가 없고 SQLite FK 도 강제되지 않아 서비스에서 명시적으로 지운다. 삭제 건수를 돌려준다.
     */
    @Transactional
    public Optional<Map<String, Integer>> deleteShipCascade(Integer shipId) {
        Optional<Ship> shipOpt = shipRepository.findById(shipId);
        if (shipOpt.isEmpty()) {
            return Optional.empty();
        }
        Map<String, Integer> deleted = new LinkedHashMap<>();
        int reports = 0, portCalls = 0;
        List<Voyage> voyages = voyageRepository.findByShipId(shipId);
        for (Voyage v : voyages) {
            List<PerformanceReport> rs = performanceReportRepository.findByVoyageId(v.getId());
            performanceReportRepository.deleteAll(rs);
            reports += rs.size();
            List<PortCall> pcs = portCallRepository.findByVoyageId(v.getId());
            portCallRepository.deleteAll(pcs);
            portCalls += pcs.size();
        }
        voyageRepository.deleteAll(voyages);
        List<YearPerformanceReport> yrs = yearPerformanceReportRepository.findByShipId(shipId);
        yearPerformanceReportRepository.deleteAll(yrs);
        shipRepository.delete(shipOpt.get());
        deleted.put("ship", 1);
        deleted.put("voyages", voyages.size());
        deleted.put("port_calls", portCalls);
        deleted.put("performance_reports", reports);
        deleted.put("yearly_reports", yrs.size());
        return Optional.of(deleted);
    }
}
