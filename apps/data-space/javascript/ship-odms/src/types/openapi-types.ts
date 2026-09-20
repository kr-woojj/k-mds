// 이 파일은 openapi.yaml에서 자동 생성된 타입을 제공합니다.
// openapi-typescript 등으로 추후 자동화 가능. (지금은 수동 작성)

export interface Ship {
  id: number;
  imo_number: string;
  ship_name: string;
  ship_type: string;
  ship_type_marpol: string;
  flag_state: string;
  mmsi: string;
  call_sign: string;
  registry_port: string;
}

export interface YearPerformanceReport {
  id: number;
  ship_id: number;
  total_gfi_annually: number;
}

export interface Voyage {
  id: number;
  ship_id: number;
  year_report_id: number;
  voyage_number: string;
  trade_service_id: string;
  gfi_per_voyage: number;
  inbound_port_jurisdiction: string;
  outbound_port_jurisdiction: string;
}

export interface PortCall {
  id: number;
  voyage_id: number;
  port_arrival: string;
  port_departure: string;
  port_ata: string;
  port_atd: string;
}

export interface WeatherDetails {
  id: number;
  report_id: number;
  sea_state: number;
  wind_force: number;
  wind_speed: number;
  wind_dir: number;
  wind_dir_relative: number;
  wind_dir_true: number;
  air_temperature: number;
  atmospheric_pressure: number;
  sea_dir_relative: number;
  sea_dir_true: number;
  sea_height: number;
  swell_dir_relative: number;
  swell_dir_true: number;
  swell_height: number;
  ocean_dir_relative: number;
  ocean_dir_true: number;
  ocean_dir_weather_provider: number;
}

export interface CargoOnboard {
  id: number;
  report_id: number;
  number_containers: number;
  number_full_container: number;
  number_full_reefer_containers: number;
  number_vehicles_onboard: number;
  number_crew: number;
  number_passengers: number;
  number_chilled_20ft_reefer_containers: number;
  number_chilled_40ft_reefer_containers: number;
  number_frozen_20ft_reefer_containers: number;
  number_frozen_40ft_reefer_containers: number;
  goods_description: string;
  gross_volume: number;
  gross_weight: number;
  bl_ref_id: string;
  bl_issued_date: string;
}

export interface ElectricConsumption {
  id: number;
  report_id: number;
  power_boiler: number;
  power_generator: number;
  power_offset: number;
  power_plant: number;
  energy_cargo_cooling: number;
  energy_discharge_pump: number;
  energy_reefer_containers: number;
  energy_onshore_power_supply: number;
  energy_zero_emissions_tech: number;
  fuel_type_cargo_cooling: number;
  fuel_type_discharge_pump: number;
  fuel_type_reefer_container: number;
  sfoc_cargo_cooling: number;
  sfoc_discharge_pump: number;
  sfoc_cargo_reefers: number;
}

export interface FocFuelType {
  id: number;
  fuel_consumption_id: number;
  foc_main_engine: number;
  foc_diesel_electric_propulsion: number;
  foc_diesel_generator: number;
  foc_auxiliary_boiler: number;
  foc_auxiliary_engine: number;
  foc_cargo_cooling: number;
  foc_cargo_heating: number;
  foc_diesel_power_packs: number;
  foc_dirty_petroleum_products_cargo_pump: number;
  foc_discharge_pump: number;
  foc_dp_operations: number;
  foc_electrical_power_generation: number;
  foc_incinerator: number;
  foc_inert_gas_generators_gcus: number;
  foc_other_fuel_consuming_devices: number;
  foc_reefer_containers: number;
  foc_shuttle_tanker_operations: number;
  foc_sts_operations: number;
}

export interface FocConsumerType {
  id: number;
  fuel_consumption_id: number;
  fuel_used_main_engine: number;
  fuel_consumed_main_engine: number;
  fuel_used_diesel_electric_propulsion: number;
  fuel_consumed_diesel_electric_propulsion: number;
  fuel_used_diesel_generator: number;
  fuel_consumed_diesel_generator: number;
  fuel_used_auxiliary_boiler: number;
  fuel_consumed_auxiliary_boiler: number;
  fuel_used_auxiliary_engine: number;
  fuel_consumed_auxiliary_engine: number;
  fuel_used_cargo_cooling: number;
  fuel_consumed_cargo_cooling: number;
  fuel_used_cargo_heating: number;
  fuel_consumed_cargo_heating: number;
  fuel_used_diesel_power_packs: number;
  fuel_consumed_diesel_power_packs: number;
  fuel_used_dirty_petroleum_products_cargo_pump: number;
  fuel_consumed_dirty_petroleum_products_cargo_pump: number;
  fuel_used_discharge_pump: number;
  fuel_consumed_discharge_pump: number;
  fuel_used_dp_operations: number;
  fuel_consumed_dp_operations: number;
  fuel_used_electrical_power_generation: number;
  fuel_consumed_electrical_power_generation: number;
  fuel_used_incinerator: number;
  fuel_consumed_incinerator: number;
  fuel_used_inert_gas_generators_gcus: number;
  fuel_consumed_inert_gas_generators_gcus: number;
  fuel_used_other_fuel_consuming_devices: number;
  fuel_consumed_other_fuel_consuming_devices: number;
  fuel_used_reefer_containers: number;
  fuel_consumed_reefer_containers: number;
  fuel_used_shuttle_tanker_operations: number;
  fuel_consumed_shuttle_tanker_operations: number;
  fuel_used_sts_operations: number;
  fuel_consumed_sts_operations: number;
}

export interface FuelConsumption {
  id: number;
  report_id: number;
  fuel_type: number;
  fuel_type_trade_name: string;
  bdn_number: string;
  bdn_datetime: string;
  fuel_bunker_received: number;
  fuel_mass: number;
  fuel_density: number;
  fuel_sulphur_content: number;
  fuel_viscosity: number;
  fuel_water_content: number;
  fuel_hhv: number;
  fuel_lfv: number;
  fuel_grade: number;
  fuel_bunker_port: string;
  fuel_bunker_port_name: string;
  co2_emission: number;
  total_fuel_quantity_consumed: number;
  fuel_quantity_rob: number;
  sludge_rob: number;
  fuel_lcv_report: string;
  fuel_lcv: number;
  fuel_pos_ref: string;
  ch4_cf: number;
  n2o_cf: number;
  fresh_water_bunkered: number;
  fresh_water_produced: number;
  fresh_water_consumed: number;
  technical_water_produced: number;
  technical_water_consumed: number;
  wash_water_consumed: number;
  fresh_water_rob: number;
  clo_rob: number;
  clo_feed_rate: number;
  clo_consumption: number;
  clo_received: number;
  foc_fuel_type: FocFuelType[];
  foc_consumer_type: FocConsumerType[];
}

export interface MeasuredCarbonDioxide {
  id: number;
  report_id: number;
  total_co2eq: number;
  percentage_co2_emitted_at_sea: number;
  total_co2: number;
  total_co2eq_captured: number;
  total_ch4: number;
  total_ch4_to_co2: number;
  total_n2o: number;
  total_n2o_to_co2: number;
}

export interface PerformanceReport {
  id: number;
  voyage_id: number;
  voyage_leg: string;
  event_type: string;
  operation_type: string;
  elapsed_time: number;
  report_type: string;
  report_datetime: string;
  latitude: number;
  longitude: number;
  distance_through_water: number;
  distance_over_ground: number;
  distance_sailed_in_ice: number;
  distance_to_next_port: number;
  laden_indicator: boolean;
  distance_excluded: number;
  off_hire_reasons: string;
  ship_draught: number;
  draught_forward: number;
  draught_aft: number;
  speed_over_ground: number;
  speed_through_water: number;
  speed_propeller: number;
  speed_projected: number;
  speed_order: number;
  course_over_ground: number;
  ship_true_heading: number;
  weather_details: WeatherDetails[];
  cargo_onboard: CargoOnboard[];
  electric_consumption: ElectricConsumption[];
  fuel_consumption: FuelConsumption[];
  measured_carbon_dioxide: MeasuredCarbonDioxide[];
}
