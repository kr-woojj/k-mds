import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "ship_odms.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
    DROP TABLE IF EXISTS measured_carbon_dioxide;
    DROP TABLE IF EXISTS foc_consumer_type;
    DROP TABLE IF EXISTS foc_fuel_type;
    DROP TABLE IF EXISTS fuel_consumption;
    DROP TABLE IF EXISTS electric_consumption;
    DROP TABLE IF EXISTS cargo_onboard;
    DROP TABLE IF EXISTS weather_details;
    DROP TABLE IF EXISTS performance_report;
    DROP TABLE IF EXISTS port_call;
    DROP TABLE IF EXISTS voyage;
    DROP TABLE IF EXISTS year_performance_report;
    DROP TABLE IF EXISTS ship;

    CREATE TABLE ship (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        imo_number TEXT,
        ship_name TEXT,
        ship_type TEXT,
        ship_type_marpol TEXT,
        flag_state TEXT,
        mmsi TEXT,
        call_sign TEXT,
        registry_port TEXT
    );

    CREATE TABLE year_performance_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ship_id INTEGER NOT NULL,
        total_gfi_annually INTEGER,
        FOREIGN KEY (ship_id) REFERENCES ship(id)
    );

    CREATE TABLE voyage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ship_id INTEGER NOT NULL,
        year_report_id INTEGER,
        voyage_number TEXT,
        trade_service_id TEXT,
        gfi_per_voyage REAL,
        inbound_port_jurisdiction TEXT,
        outbound_port_jurisdiction TEXT,
        FOREIGN KEY (ship_id) REFERENCES ship(id),
        FOREIGN KEY (year_report_id) REFERENCES year_performance_report(id)
    );

    CREATE TABLE port_call (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voyage_id INTEGER NOT NULL,
        port_arrival TEXT,
        port_departure TEXT,
        port_ata TEXT,
        port_atd TEXT,
        FOREIGN KEY (voyage_id) REFERENCES voyage(id)
    );

    CREATE TABLE performance_report (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voyage_id INTEGER NOT NULL,
        voyage_leg TEXT,
        event_type TEXT,
        operation_type TEXT,
        elapsed_time REAL,
        report_type TEXT,
        report_datetime TEXT,
        latitude REAL,
        longitude REAL,
        distance_through_water REAL,
        distance_over_ground REAL,
        distance_sailed_in_ice REAL,
        distance_to_next_port REAL,
        laden_indicator INTEGER,
        distance_excluded REAL,
        off_hire_reasons TEXT,
        ship_draught REAL,
        draught_forward REAL,
        draught_aft REAL,
        speed_over_ground REAL,
        speed_through_water REAL,
        speed_propeller REAL,
        speed_projected REAL,
        speed_order REAL,
        course_over_ground REAL,
        ship_true_heading REAL,
        FOREIGN KEY (voyage_id) REFERENCES voyage(id)
    );

    CREATE TABLE weather_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        sea_state INTEGER,
        wind_force INTEGER,
        wind_speed INTEGER,
        wind_dir INTEGER,
        wind_dir_relative REAL,
        wind_dir_true REAL,
        air_temperature REAL,
        atmospheric_pressure INTEGER,
        sea_dir_relative INTEGER,
        sea_dir_true INTEGER,
        sea_height INTEGER,
        swell_dir_relative INTEGER,
        swell_dir_true INTEGER,
        swell_height INTEGER,
        ocean_dir_relative INTEGER,
        ocean_dir_true INTEGER,
        ocean_dir_weather_provider INTEGER,
        FOREIGN KEY (report_id) REFERENCES performance_report(id)
    );

    CREATE TABLE cargo_onboard (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        number_containers INTEGER,
        number_full_container INTEGER,
        number_full_reefer_containers INTEGER,
        number_vehicles_onboard INTEGER,
        number_crew INTEGER,
        number_passengers INTEGER,
        number_chilled_20ft_reefer_containers INTEGER,
        number_chilled_40ft_reefer_containers INTEGER,
        number_frozen_20ft_reefer_containers INTEGER,
        number_frozen_40ft_reefer_containers INTEGER,
        goods_description TEXT,
        gross_volume REAL,
        gross_weight REAL,
        bl_ref_id TEXT,
        bl_issued_date TEXT,
        FOREIGN KEY (report_id) REFERENCES performance_report(id)
    );

    CREATE TABLE electric_consumption (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        power_boiler REAL,
        power_generator REAL,
        power_offset REAL,
        power_plant REAL,
        energy_cargo_cooling REAL,
        energy_discharge_pump REAL,
        energy_reefer_containers REAL,
        energy_onshore_power_supply REAL,
        energy_zero_emissions_tech REAL,
        fuel_type_cargo_cooling INTEGER,
        fuel_type_discharge_pump INTEGER,
        fuel_type_reefer_container INTEGER,
        sfoc_cargo_cooling REAL,
        sfoc_discharge_pump REAL,
        sfoc_cargo_reefers REAL,
        FOREIGN KEY (report_id) REFERENCES performance_report(id)
    );

    CREATE TABLE fuel_consumption (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        fuel_type INTEGER,
        fuel_type_trade_name TEXT,
        bdn_number TEXT,
        bdn_datetime TEXT,
        fuel_bunker_received REAL,
        fuel_mass REAL,
        fuel_density INTEGER,
        fuel_sulphur_content INTEGER,
        fuel_viscosity INTEGER,
        fuel_water_content INTEGER,
        fuel_hhv INTEGER,
        fuel_lfv INTEGER,
        fuel_grade INTEGER,
        fuel_bunker_port TEXT,
        fuel_bunker_port_name TEXT,
        co2_emission REAL,
        total_fuel_quantity_consumed REAL,
        fuel_quantity_rob REAL,
        sludge_rob REAL,
        fuel_lcv_report TEXT,
        fuel_lcv REAL,
        fuel_pos_ref TEXT,
        ch4_cf REAL,
        n2o_cf REAL,
        fresh_water_bunkered REAL,
        fresh_water_produced REAL,
        fresh_water_consumed REAL,
        technical_water_produced REAL,
        technical_water_consumed REAL,
        wash_water_consumed REAL,
        fresh_water_rob REAL,
        clo_rob REAL,
        clo_feed_rate REAL,
        clo_consumption REAL,
        clo_received REAL,
        FOREIGN KEY (report_id) REFERENCES performance_report(id)
    );

    CREATE TABLE foc_fuel_type (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fuel_consumption_id INTEGER NOT NULL,
        foc_main_engine REAL,
        foc_diesel_electric_propulsion REAL,
        foc_diesel_generator REAL,
        foc_auxiliary_boiler REAL,
        foc_auxiliary_engine REAL,
        foc_cargo_cooling REAL,
        foc_cargo_heating REAL,
        foc_diesel_power_packs REAL,
        foc_dirty_petroleum_products_cargo_pump REAL,
        foc_discharge_pump REAL,
        foc_dp_operations REAL,
        foc_electrical_power_generation REAL,
        foc_incinerator REAL,
        foc_inert_gas_generators_gcus REAL,
        foc_other_fuel_consuming_devices REAL,
        foc_reefer_containers REAL,
        foc_shuttle_tanker_operations REAL,
        foc_sts_operations REAL,
        FOREIGN KEY (fuel_consumption_id) REFERENCES fuel_consumption(id)
    );

    CREATE TABLE foc_consumer_type (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fuel_consumption_id INTEGER NOT NULL,
        fuel_used_main_engine INTEGER,
        fuel_consumed_main_engine REAL,
        fuel_used_diesel_electric_propulsion INTEGER,
        fuel_consumed_diesel_electric_propulsion REAL,
        fuel_used_diesel_generator INTEGER,
        fuel_consumed_diesel_generator REAL,
        fuel_used_auxiliary_boiler INTEGER,
        fuel_consumed_auxiliary_boiler REAL,
        fuel_used_auxiliary_engine INTEGER,
        fuel_consumed_auxiliary_engine REAL,
        fuel_used_cargo_cooling INTEGER,
        fuel_consumed_cargo_cooling REAL,
        fuel_used_cargo_heating INTEGER,
        fuel_consumed_cargo_heating REAL,
        fuel_used_diesel_power_packs INTEGER,
        fuel_consumed_diesel_power_packs REAL,
        fuel_used_dirty_petroleum_products_cargo_pump INTEGER,
        fuel_consumed_dirty_petroleum_products_cargo_pump REAL,
        fuel_used_discharge_pump INTEGER,
        fuel_consumed_discharge_pump REAL,
        fuel_used_dp_operations INTEGER,
        fuel_consumed_dp_operations REAL,
        fuel_used_electrical_power_generation INTEGER,
        fuel_consumed_electrical_power_generation REAL,
        fuel_used_incinerator INTEGER,
        fuel_consumed_incinerator REAL,
        fuel_used_inert_gas_generators_gcus INTEGER,
        fuel_consumed_inert_gas_generators_gcus REAL,
        fuel_used_other_fuel_consuming_devices INTEGER,
        fuel_consumed_other_fuel_consuming_devices REAL,
        fuel_used_reefer_containers INTEGER,
        fuel_consumed_reefer_containers REAL,
        fuel_used_shuttle_tanker_operations INTEGER,
        fuel_consumed_shuttle_tanker_operations REAL,
        fuel_used_sts_operations INTEGER,
        fuel_consumed_sts_operations REAL,
        FOREIGN KEY (fuel_consumption_id) REFERENCES fuel_consumption(id)
    );

    CREATE TABLE measured_carbon_dioxide (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        total_co2eq REAL,
        percentage_co2_emitted_at_sea REAL,
        total_co2 REAL,
        total_co2eq_captured REAL,
        total_ch4 REAL,
        total_ch4_to_co2 REAL,
        total_n2o REAL,
        total_n2o_to_co2 REAL,
        FOREIGN KEY (report_id) REFERENCES performance_report(id)
    );
    """)
    cur.execute("""
        INSERT INTO ship (imo_number, ship_name, ship_type, ship_type_marpol, flag_state, mmsi, call_sign, registry_port)
        VALUES ('0000001', 'KR0000001', 'Containership', 'M04', 'PANAMA', '440123000', 'HLAG2', 'KRPUS')
    """)
    conn.commit()
    conn.close()
