```mermaid
erDiagram
    %% =========================================================
    %% 1. SHIP (선박 기준 정보 - Static Data)
    %% =========================================================
    SHIP {
        int id PK
        string imo_number "IMO0140:	Ship IMO number"
        string ship_name "IMO0142: Ship name"
        string ship_type "IMO0160: Ship type, coded"
        string ship_type_marpol "IMO0859: Ship type MARPOL Annex VI, coded"
        string flag_state "IMO0138: Ship flag State, coded"
        string mmsi "IMO0326: Ship MMSI number"
        string call_sign "IMO0136: Ship call sign"
        string registry_port "IMO0147: Ship registry port, coded"
    }

    %% =========================================================
    %% 2. YEAR PERFORMANCE REPORT (연차 집계 - DCS/CII Report)
    %% =========================================================
    YEAR_PERFORMANCE_REPORT {
        int id PK
        int ship_id FK
        int total_gfi_annually "IMO0854: Fuel, Total GHG intensity (IMO), annually [gCO2eq/MJ]"
    }

    %% =========================================================
    %% 3. VOYAGE (항차 정보 - Voyage Header)
    %% =========================================================
    VOYAGE {
        int id PK
        int ship_id FK
        int year_report_id FK
        string voyage_number "IMO0191: Voyage number"
        string trade_service_id "IMO0536: Trade service identifier"
        float gfi_per_voyage "IMO0855: Fuel, GHG intensity (IMO), per voyage [gCO2eq/MJ]"
        string inbound_port_jurisdiction "IMO0856: Inbound Port jurisdiction, coded"
        string outbound_port_jurisdiction "IMO0857: Outbound Port jurisdiction, coded"
    }


    %% =========================================================
    %% 4. PORT CALL (입출항 정보 - SVD Port Data)
    %% =========================================================
    PORT_CALL {
        int id PK
        int voyage_id FK
        string port_arrival "IMO0108: Port of arrival, coded"
        string port_departure "IMO0111: Port of departure, coded"
        string port_ata "IMO0063: Date and time of arrival - actual"
        string port_atd "IMO0065: Date and time of departure - actual"
    }

    %% =========================================================
    %% 5. PERFORMANCE REPORT (일일 운항 보고서 - SVD Noon Report)
    %% =========================================================
    PERFORMANCE_REPORT {
        int id PK
        int voyage_id FK
        string voyage_leg "IMO0605: Voyage leg identifier"
        string event_type "IMO0597: Event type, coded"
        string operation_type "IMO0598: Operation type, coded"
        float elapsed_time "IMO0600: Elapsed time"

        %% Report Metadata
        string report_type "IMO0879: Performance report type, coded"
        datetime report_datetime "IMO0603: Ship reporting date time"

        %% Position & Navigation (SVD Navigation)
        float latitude "IMO0601: Ship position when reporting, latitude"
        float longitude "IMO0602: Ship position when reporting, longitude"

        %% Performance Data
        float distance_through_water "IMO0612: Distance through water [nm]"
        float distance_over_ground "IMO0613: Distance over ground [nm]"
        float distance_sailed_in_ice "IMO0614: Distance sailed in ice [nm]"
        float distance_to_next_port "IMO0615: Distance to next port [nm]"
        bool laden_indicator "IMO0860: Laden indicator"
        float distance_excluded "IMO0861: Distance excluded [nm]"
        string off_hire_reasons "IMO0862: Off hire Reasons"

        %% Ship dynamics
        float ship_draught "IMO0357: Ship draught"
        float draught_forward "IMO0621: Draught forward"
        float draught_aft "IMO0622: Draught aft"
        float speed_over_ground "IMO0333: Speed over ground"
        float speed_through_water "IMO0616: Speed through water"
        float speed_propeller "IMO0617: Speed propeller"
        float speed_projected "IMO0618: Speed projected"
        float speed_order "IMO0619: Speed order"
        float course_over_ground "IMO0332: Course over ground"
        float ship_true_heading "IMO0620: Ship true heading"
    }

    %% =========================================================
    %% 6. WEATHER DETAILS (기상 정보 - SVD Weather Data)
    %% =========================================================
    WEATHER_DETAILS {
        int id PK
        int report_id FK
        int sea_state "IMO0363: State of the sea, coded"
        int wind_force "IMO0625: Wind force"
        int wind_speed "IMO0359: Wind speed, coded"
        int wind_dir "IMO0360: Wind direction, coded"
        float wind_dir_relative "IMO0626: Wind direction, estimated, relative"
        float wind_dir_true "IMO0627: Wind direction, estimated, true"
        float air_temperature "IMO0628: Air temperature"
        int atmospheric_pressure "IMO0629: Atmospheric pressure"
        int sea_dir_relative "IMO0630: Sea direction, relative"
        int sea_dir_true "IMO0631: Sea direction, true"
        int sea_height "IMO0632: Sea height"
        int swell_dir_relative "IMO0633: Swell direction, relative"
        int swell_dir_true "IMO0634: Swell direction, true"
        int swell_height "IMO0635: Swell height"
        int ocean_dir_relative "IMO0636: Ocean current direction, relative"
        int ocean_dir_true "IMO0637: Ocean current direction, true"
        int ocean_dir_weather_provider "IMO0638: Ocean current direction, weather provider"
    }

    %% =========================================================
    %% 7. CARGO ONBOARD (적재 화물 정보 - SVD Cargo Data)
    %% =========================================================
    CARGO_ONBOARD {
        int id PK
        int report_id FK
        int number_containers "IMO0650: Total numbers of containers, TEU"
        int number_full_container "IMO0651: Total number of full containers, TEU"
        int number_full_reefer_containers "IMO0652: Total number of full reefer containers in use, TEU"
        int number_vehicles_onboard "IMO0653: Total number of vehicles onboard, CEU"
        int number_crew "IMO0086: Number of crew"
        int number_passengers "IMO0087: Number of passengers"
        int number_chilled_20ft_reefer_containers "IMO0864: Number of chilled 20 ft reefer containers"
        int number_chilled_40ft_reefer_containers "IMO0865: Number of chilled 40 ft reefer containers"
        int number_frozen_20ft_reefer_containers "IMO0866: Number of frozen 20 ft reefer containers"
        int number_frozen_40ft_reefer_containers "IMO0867: Number of frozen 40 ft reefer containers"
        
        %% Cargo Item Details
        string goods_description "IMO0022: Cargo item description of goods"
        float gross_volume "IMO0023: Cargo item gross volume"
        float gross_weight "IMO0024: Cargo item gross weight"

        %% Bill of Lading
        string bl_ref_id "IMO0734: Bill of Lading reference identifier"
        string bl_issued_date "IMO0738: Bill of Lading issued date"
    }

    %% =========================================================
    %% 8. ELECTRIC POWER GENERATION & CONSUMPTION (전기생산 및 소비 - SVD 2.0 Electric Power Data)
    %% =========================================================
    ELECTRIC_CONSUMPTION {
        int id PK
        int report_id FK

        %% Power Item Details
        float power_boiler "IMO0646: Boiler electricity consumption [kwh]"
        float power_generator "IMO0647: Generator production [kwh]"
        float power_offset "IMO0648: Offset electricity consumption [kwh]"
        float power_plant "IMO0649: Power consumption for plant [kwh]"

        %% Energy Item Details
        float energy_cargo_cooling "IMO0868: Electrical work generated for Cargo Cooling [kwh]"
        float energy_discharge_pump "IMO0869: Electrical work generated for discharge pump [kwh]"
        float energy_reefer_containers "IMO0870: Electrical work generated for reefer containers [kwh]"
        float energy_onshore_power_supply "IMO0871: Electrical work received from On Shore Power Supply [kwh]"
        float energy_zero_emissions_tech "IMO0872: Electrical work received from zero emissions technologies [kwh]"

        %% Fuel Type for Energy Item Details
        int fuel_type_cargo_cooling "IMO0873: Fuel type used for electrical work generated for cargo cooling, coded"
        int fuel_type_discharge_pump "IMO0874: Fuel type used for electrical work generated for discharge pump, coded"
        int fuel_type_reefer_container "IMO0875: Fuel type used for electrical work generated for reefers container, coded"
        
        %% SFOC for Energy Item Details
        float sfoc_cargo_cooling "IMO0876: Specific fuel oil consumption for electrical work generated for cargo cooling [g/kWh]"
        float sfoc_discharge_pump "IMO0877: Specific fuel oil consumption for electrical work generated for discharge pump [g/kWh]"
        float sfoc_cargo_reefers "IMO0878: Specific fuel oil consumption for electrical work generated for cargo reefers [g/kWh]"
    }

    %% =========================================================
    %% 9. FUEL AND BUNKER INFORMATION (연료 및 벙커링 정보 - SVD 2.0 Fuel Consumption Data)
    %% =========================================================
    FUEL_CONSUMPTION {
        int id PK
        int report_id FK
        int fuel_type "IMO0654: Fuel type, coded"
        string fuel_type_trade_name "IMO0680: Fuel type trade name, coded"

        %% Fuel Item Details
        string bdn_number "IMO0655: Bunker delivery note number"
        string bdn_datetime "IMO0656: Bunker delivery date time"
        float fuel_bunker_received "IMO0657: Fuel bunker received"
        float fuel_mass "IMO0658: Fuel, mass"
        int fuel_density "IMO0659: Fuel, density"
        int fuel_sulphur_content "IMO0660: Fuel, sulphur content"
        int fuel_viscosity "IMO0661: Fuel, viscosity"
        int fuel_water_content "IMO0662: Fuel, water content"
        int fuel_hhv "IMO0663: Fuel, higher heating value"
        int fuel_lfv "IMO0664: Fuel, lower heating value"
        int fuel_grade "IMO0665: Fuel grade, coded"
        string fuel_bunker_port "IMO0666: Fuel bunker port, coded"
        string fuel_bunker_port_name "IMO0667: Fuel bunker port, name"
        float co2_emission "IMO0668: Fuel Carbon Dioxide emission [gCO2/g]"
        float total_fuel_quantity_consumed "IMO0669: Total fuel quantity consumed"

        %% ROB (Remaining Onboard)
        float fuel_quantity_rob "IMO0674: Fuel quantity remaining onboard"
        float sludge_rob "IMO0675: Sludge remaining onboard"
        string fuel_lcv_report "IMO0880: Fuel Lower Calorific Value reporting scheme, coded"
        float fuel_lcv "IMO0881: Fuel, lower calorific value (LCV)"
        string fuel_pos_ref "IMO0882: Fuel, Proof of Sustainability reference"

        %% Conversion Factor
        float ch4_cf "IMO0891: CH4 emission conversion factor (Methane) [gCH4/gFuel]"
        float n2o_cf "IMO0892: N2O emission conversion factor (Nitrous Oxide) [gN2O/gFuel]"

        %% Water Information
        float fresh_water_bunkered "IMO0639: Fresh water bunkered"
        float fresh_water_produced "IMO0640: Fresh water produced"
        float fresh_water_consumed "IMO0641: Fresh water consumed"
        float technical_water_produced "IMO0642: Technical water produced"
        float technical_water_consumed "IMO0643: Technical water consumed"
        float wash_water_consumed "IMO0644: Wash water consumed"
        float fresh_water_rob "IMO0645: Fresh water remaining onboard"
        
        %% Cylinder Lube Oil Information
        float clo_rob "IMO0676: Cylinder lube oil remaining onboard"
        float clo_feed_rate "IMO0677: Cylinder lube oil, Feed Rate"
        float clo_consumption "IMO0678: Cylinder lube oil, consumption"
        float clo_received "IMO0679: Cylinder lube oil, received"
    }

    %% =========================================================
    %% 9-1. FOC by Fuel Type (연료별 소비량)
    %% =========================================================
    FOC_FUEL_TYPE {
        int id PK
        int fuel_consumption_id FK
        float foc_main_engine "IMO0670: Fuel consumed, by Main Engine"
        float foc_diesel_electric_propulsion "IMO0671: Fuel consumed, by Diesel Electric Propulsion"
        float foc_diesel_generator "IMO0672: Fuel consumed, by Diesel Generator"
        float foc_auxiliary_boiler "IMO0673: Fuel consumed, by Auxiliary Boiler"
        float foc_auxiliary_engine "IMO0893: Fuel consumed, by Auxiliary Engine"
        float foc_cargo_cooling "IMO0894: Fuel consumed, by Cargo Cooling"
        float foc_cargo_heating "IMO0895: Fuel consumed, by Cargo Heating"
        float foc_diesel_power_packs "IMO0896: Fuel consumed, by Diesel Power Packs"
        float foc_dirty_petroleum_products_cargo_pump "IMO0897: Fuel consumed, by Dirty Petroleum Products Cargo Pump"
        float foc_discharge_pump "IMO0898: Fuel consumed, by Discharge Pump"
        float foc_dp_operations "IMO0899: Fuel consumed, by DP Operations"
        float foc_electrical_power_generation "IMO0900: Fuel consumed, by Electrical Power Generation"
        float foc_incinerator "IMO0901: Fuel consumed, by Incinerator"
        float foc_inert_gas_generators_gcus "IMO0902: Fuel consumed, by Inert gas generators / GCUs"
        float foc_other_fuel_consuming_devices "IMO0903: Fuel consumed, by Other Fuel Consuming Devices"
        float foc_reefer_containers "IMO0904: Fuel consumed, by Reefer Containers"
        float foc_shuttle_tanker_operations "IMO0905: Fuel consumed, by Shuttle Tanker Operations"
        float foc_sts_operations "IMO0906: Fuel consumed, by STS Operations"
    }

    %% =========================================================
    %% 9-2. FOC by Consumer Type (소비원별 소비량)
    %% =========================================================
    FOC_CONSUMER_TYPE {
        int id PK
        int fuel_consumption_id FK
        int fuel_used_main_engine "IMO0907: Fuel used by Main Engine, coded"
        float fuel_consumed_main_engine "IMO0908: Fuel consumed by Main Engine, by fuel type"
        int fuel_used_diesel_electric_propulsion "IMO0909: Fuel used by Diesel Electric Propulsion, coded"
        float fuel_consumed_diesel_electric_propulsion "IMO0910: Fuel consumed by Diesel Electric Propulsion, by fuel type"
        int fuel_used_diesel_generator "IMO0911: Fuel used by Diesel Generator, coded"
        float fuel_consumed_diesel_generator "IMO0912: Fuel consumed by Diesel Generator, by fuel type"
        int fuel_used_auxiliary_boiler "IMO0913: Fuel used by Auxillary Boiler, coded"
        float fuel_consumed_auxiliary_boiler "IMO0914: Fuel consumed by Auxiliary Boiler, by fuel type"
        int fuel_used_auxiliary_engine "IMO0915: Fuel used by Auxillary Engine, coded"
        float fuel_consumed_auxiliary_engine "IMO0916: Fuel consumed by Auxiliary Engine, by fuel type"
        int fuel_used_cargo_cooling "IMO0917: Fuel used by Cargo Cooling, coded"
        float fuel_consumed_cargo_cooling "IMO0918: Fuel consumed by Cargo Cooling, by fuel type"
        int fuel_used_cargo_heating "IMO0919: Fuel used by Cargo Heating, coded"
        float fuel_consumed_cargo_heating "IMO0920: Fuel consumed by Cargo Heating, by fuel type"
        int fuel_used_diesel_power_packs "IMO0921: Fuel used by Diesel Power Packs, coded"
        float fuel_consumed_diesel_power_packs "IMO0922: Fuel consumed by Diesel Power Packs, by fuel type"
        int fuel_used_dirty_petroleum_products_cargo_pump "IMO0923: Fuel used by Dirty Petroleum Products Cargo Pump, coded"
        float fuel_consumed_dirty_petroleum_products_cargo_pump "IMO0924: Fuel consumed by Dirty Petroleum Products Cargo Pump, by fuel type"
        int fuel_used_discharge_pump "IMO0925: Fuel used by Discharge Pump, coded"
        float fuel_consumed_discharge_pump "IMO0926: Fuel consumed by Discharge Pump, by fuel type"
        int fuel_used_dp_operations "IMO0927: Fuel used by DP Operations, coded"
        float fuel_consumed_dp_operations "IMO0928: Fuel consumed by DP Operations, by fuel type"
        int fuel_used_electrical_power_generation "IMO0929: Fuel used by Electrical Power Generation, coded"
        float fuel_consumed_electrical_power_generation "IMO0930: Fuel consumed by Electrical Power Generation, by fuel type"
        int fuel_used_incinerator "IMO0931: Fuel used by Incinerator, coded"
        float fuel_consumed_incinerator "IMO0932: Fuel consumed by Incinerator, by fuel type"
        int fuel_used_inert_gas_generators_gcus "IMO0933: Fuel used by Inert gas generators / GCUs, coded"
        float fuel_consumed_inert_gas_generators_gcus "IMO0934: Fuel consumed by Inert gas generators / GCUs, by fuel type"
        int fuel_used_other_fuel_consuming_devices "IMO0935: Fuel used by Other Fuel Consuming Devices, coded"
        float fuel_consumed_other_fuel_consuming_devices "IMO0936: Fuel consumed by Other Fuel Consuming Devices, by fuel type"
        int fuel_used_reefer_containers "IMO0937: Fuel used by Reefers Containers, coded"
        float fuel_consumed_reefer_containers "IMO0938: Fuel consumed by Reefer Containers, by fuel type"
        int fuel_used_shuttle_tanker_operations "IMO0939: Fuel used by Shuttle Tanker Operations, coded"
        float fuel_consumed_shuttle_tanker_operations "IMO0940: Fuel consumed by Shuttle Tanker Operations, by fuel type"
        int fuel_used_sts_operations "IMO0941: Fuel used by STS Operations, coded"
        float fuel_consumed_sts_operations "IMO0942: Fuel consumed by STS Operations, by fuel type"
    }

    %% =========================================================
    %% 10. EMISSIONS (탄소배출 정보 - SVD 2.0 Emissions Data)
    %% =========================================================
    MEASURED_CARBON_DIOXIDE {
        int id PK
        int report_id FK
        float total_co2eq "IMO0883: Total CO2, including equivalent [tCO2eq]"
        float percentage_co2_emitted_at_sea "IMO0884: Percentage of Total CO2 emitted at sea"
        float total_co2 "IMO0885: Total CO2 (tank-to-wake) [tCO2]"
        float total_co2eq_captured "IMO0886: Total CO2 equivalent Captured [tCO2eq]"
        float total_ch4 "IMO0887: Total CH4 [tCH4]"
        float total_ch4_to_co2 "IMO0888: Total CH4 converted to CO2 [tCH4]"
        float total_n2o "IMO0889: Total N2O [tN20]"
        float total_n2o_to_co2 "IMO0890: Total N20 converted to CO2 [tN20]"
    }

    %% =========================================================
    %% RELATIONSHIPS
    %% =========================================================
    
    SHIP ||--o{ YEAR_PERFORMANCE_REPORT : "IMO0140_reports"
    SHIP ||--o{ VOYAGE : "IMO0140_voyages"
    YEAR_PERFORMANCE_REPORT ||--o{ VOYAGE : "aggregates"
    VOYAGE ||--o{ PORT_CALL : "IMO0191_port_call"
    VOYAGE ||--o{ PERFORMANCE_REPORT : "IMO0191_reports"
    PERFORMANCE_REPORT ||--|{ WEATHER_DETAILS : 
    "IMO0605_weather"
    PERFORMANCE_REPORT ||--|{ CARGO_ONBOARD : 
    "IMO0605_cargo"
    PERFORMANCE_REPORT ||--|{ ELECTRIC_CONSUMPTION : 
    "IMO0605_consumption"
    PERFORMANCE_REPORT ||--|{ FUEL_CONSUMPTION : 
    "IMO0605_consumption"
    FUEL_CONSUMPTION ||--|{ FOC_FUEL_TYPE : "IMO0604_fuel_types"
    FUEL_CONSUMPTION ||--|{ FOC_CONSUMER_TYPE : "IMO0604_consumer_types"
    PERFORMANCE_REPORT ||--|{ MEASURED_CARBON_DIOXIDE : "IMO0605_emissions"
```