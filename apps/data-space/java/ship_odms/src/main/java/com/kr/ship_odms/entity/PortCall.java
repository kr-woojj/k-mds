package com.kr.ship_odms.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Entity
@Table(name = "port_call")
public class PortCall {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "voyage_id")
    private Voyage voyage;

    private String portArrival;
    private String portDeparture;
    private String portAta;
    private String portAtd;
}
