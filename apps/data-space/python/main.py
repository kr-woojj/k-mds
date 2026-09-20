import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.openapi.docs import get_swagger_ui_html
from typing import List
from models import *
from database import init_db, get_connection

# 표준 모델 단일 원본: k-mds/shared/standard-model/openapi.yaml (앱 안에 사본을 두지 않는다)
OPENAPI_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared", "standard-model", "openapi.yaml")

app = FastAPI(
    title="Ship-ODMS API (IMO Compendium 기반)",
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()

# --- Ship Endpoints ---
@app.get("/api/ships", response_model=List[Ship])
def get_ships():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ship")
    rows = cur.fetchall()
    result = [Ship(**dict(zip([c[0] for c in cur.description], row))) for row in rows]
    conn.close()
    return result

@app.post("/api/ships", response_model=Ship, status_code=201)
def create_ship(ship: Ship):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ship (imo_number, ship_name, ship_type, ship_type_marpol, flag_state, mmsi, call_sign, registry_port)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ship.imo_number, ship.ship_name, ship.ship_type, ship.ship_type_marpol, ship.flag_state, ship.mmsi, ship.call_sign, ship.registry_port)
    )
    ship_id = cur.lastrowid
    conn.commit()
    conn.close()
    ship.id = ship_id
    return ship

@app.get("/api/ships/{shipId}", response_model=Ship)
def get_ship(shipId: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ship WHERE id = ?", (shipId,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="선박을 찾을 수 없음")
    result = Ship(**dict(zip([c[0] for c in cur.description], row)))
    conn.close()
    return result

# --- YearPerformanceReport Endpoints ---
@app.get("/api/ships/{shipId}/yearly-reports", response_model=List[YearPerformanceReport])
def get_yearly_reports(shipId: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM year_performance_report WHERE ship_id = ?", (shipId,))
    rows = cur.fetchall()
    result = [YearPerformanceReport(**dict(zip([c[0] for c in cur.description], row))) for row in rows]
    conn.close()
    return result

@app.post("/api/ships/{shipId}/yearly-reports", response_model=YearPerformanceReport, status_code=201)
def create_yearly_report(shipId: int, report: YearPerformanceReport):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO year_performance_report (ship_id, total_gfi_annually)
        VALUES (?, ?)
        """,
        (shipId, report.total_gfi_annually)
    )
    report_id = cur.lastrowid
    conn.commit()
    conn.close()
    report.id = report_id
    report.ship_id = shipId
    return report

# --- Voyage Endpoints ---
@app.get("/api/ships/{shipId}/voyages", response_model=List[Voyage])
def get_voyages(shipId: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM voyage WHERE ship_id = ?", (shipId,))
    rows = cur.fetchall()
    result = [Voyage(**dict(zip([c[0] for c in cur.description], row))) for row in rows]
    conn.close()
    return result

@app.post("/api/ships/{shipId}/voyages", response_model=Voyage, status_code=201)
def create_voyage(shipId: int, voyage: Voyage):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO voyage (ship_id, year_report_id, voyage_number, trade_service_id, gfi_per_voyage, inbound_port_jurisdiction, outbound_port_jurisdiction)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            shipId,
            voyage.year_report_id,
            voyage.voyage_number,
            voyage.trade_service_id,
            voyage.gfi_per_voyage,
            voyage.inbound_port_jurisdiction,
            voyage.outbound_port_jurisdiction
        )
    )
    voyage_id = cur.lastrowid
    conn.commit()
    conn.close()
    voyage.id = voyage_id
    voyage.ship_id = shipId
    return voyage


# --- PortCall Endpoints ---
@app.get("/api/voyages/{voyageId}/port-calls", response_model=List[PortCall])
def get_port_calls(voyageId: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM port_call WHERE voyage_id = ?", (voyageId,))
    rows = cur.fetchall()
    result = [PortCall(**dict(zip([c[0] for c in cur.description], row))) for row in rows]
    conn.close()
    return result

@app.post("/api/voyages/{voyageId}/port-calls", response_model=PortCall, status_code=201)
def create_port_call(voyageId: int, port_call: PortCall):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO port_call (voyage_id, port_arrival, port_departure, port_ata, port_atd)
        VALUES (?, ?, ?, ?, ?)
        """,
        (voyageId, port_call.port_arrival, port_call.port_departure, port_call.port_ata, port_call.port_atd)
    )
    port_call_id = cur.lastrowid
    conn.commit()
    conn.close()
    port_call.id = port_call_id
    port_call.voyage_id = voyageId
    return port_call

# --- PerformanceReport Endpoints (중첩 객체 포함) ---
@app.get("/api/voyages/{voyageId}/performance-reports", response_model=List[PerformanceReport])
def get_performance_reports(voyageId: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM performance_report WHERE voyage_id = ?", (voyageId,))
    reports = cur.fetchall()
    result = []
    for row in reports:
        report_dict = dict(zip([c[0] for c in cur.description], row))
        report_id = report_dict['id']
        # 중첩 데이터 조회
        report_dict['weather_details'] = _fetch_nested(conn, 'weather_details', report_id, WeatherDetails)
        report_dict['cargo_onboard'] = _fetch_nested(conn, 'cargo_onboard', report_id, CargoOnboard)
        report_dict['electric_consumption'] = _fetch_nested(conn, 'electric_consumption', report_id, ElectricConsumption)
        report_dict['fuel_consumption'] = _fetch_fuel_consumption(conn, report_id)
        report_dict['measured_carbon_dioxide'] = _fetch_nested(conn, 'measured_carbon_dioxide', report_id, MeasuredCarbonDioxide)
        result.append(PerformanceReport(**report_dict))
    conn.close()
    return result

def _fetch_nested(conn, table, report_id, model):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table} WHERE report_id = ?", (report_id,))
    rows = cur.fetchall()
    return [model(**dict(zip([c[0] for c in cur.description], row))) for row in rows]

def _fetch_fuel_consumption(conn, report_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM fuel_consumption WHERE report_id = ?", (report_id,))
    fuel_rows = cur.fetchall()
    result = []
    for fuel_row in fuel_rows:
        fuel_dict = dict(zip([c[0] for c in cur.description], fuel_row))
        fuel_id = fuel_dict['id']
        # 연료별 소비량, 소비원별 소비량
        fuel_dict['foc_fuel_type'] = _fetch_nested_fuel(conn, 'foc_fuel_type', fuel_id, FocFuelType)
        fuel_dict['foc_consumer_type'] = _fetch_nested_fuel(conn, 'foc_consumer_type', fuel_id, FocConsumerType)
        result.append(FuelConsumption(**fuel_dict))
    return result

def _fetch_nested_fuel(conn, table, fuel_id, model):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table} WHERE fuel_consumption_id = ?", (fuel_id,))
    rows = cur.fetchall()
    return [model(**dict(zip([c[0] for c in cur.description], row))) for row in rows]

@app.post("/api/voyages/{voyageId}/performance-reports", response_model=PerformanceReport, status_code=201)
def create_performance_report(voyageId: int, report: PerformanceReport):
    conn = get_connection()
    cur = conn.cursor()
    # 1. 성능보고서 본문 저장
    cur.execute(
        """
        INSERT INTO performance_report (
            voyage_id, voyage_leg, event_type, operation_type, elapsed_time, report_type, report_datetime, latitude, longitude,
            distance_through_water, distance_over_ground, distance_sailed_in_ice, distance_to_next_port, laden_indicator, distance_excluded,
            off_hire_reasons, ship_draught, draught_forward, draught_aft, speed_over_ground, speed_through_water, speed_propeller, speed_projected,
            speed_order, course_over_ground, ship_true_heading
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            voyageId, report.voyage_leg, report.event_type, report.operation_type, report.elapsed_time, report.report_type, report.report_datetime,
            report.latitude, report.longitude, report.distance_through_water, report.distance_over_ground, report.distance_sailed_in_ice,
            report.distance_to_next_port, int(report.laden_indicator), report.distance_excluded, report.off_hire_reasons, report.ship_draught,
            report.draught_forward, report.draught_aft, report.speed_over_ground, report.speed_through_water, report.speed_propeller,
            report.speed_projected, report.speed_order, report.course_over_ground, report.ship_true_heading
        )
    )
    report_id = cur.lastrowid
    # 2. 중첩 데이터 저장
    def _insert_nested(table, items, model_fields):
        for item in items:
            fields = ','.join(model_fields)
            placeholders = ','.join(['?'] * len(model_fields))
            values = tuple(getattr(item, f) for f in model_fields)
            cur.execute(f"INSERT INTO {table} ({fields}) VALUES ({placeholders})", values)
    # WeatherDetails
    _insert_nested('weather_details', report.weather_details, [
        'report_id','sea_state','wind_force','wind_speed','wind_dir','wind_dir_relative','wind_dir_true','air_temperature','atmospheric_pressure','sea_dir_relative','sea_dir_true','sea_height','swell_dir_relative','swell_dir_true','swell_height','ocean_dir_relative','ocean_dir_true','ocean_dir_weather_provider'])
    # CargoOnboard
    _insert_nested('cargo_onboard', report.cargo_onboard, [
        'report_id','number_containers','number_full_container','number_full_reefer_containers','number_vehicles_onboard','number_crew','number_passengers','number_chilled_20ft_reefer_containers','number_chilled_40ft_reefer_containers','number_frozen_20ft_reefer_containers','number_frozen_40ft_reefer_containers','goods_description','gross_volume','gross_weight','bl_ref_id','bl_issued_date'])
    # ElectricConsumption
    _insert_nested('electric_consumption', report.electric_consumption, [
        'report_id','power_boiler','power_generator','power_offset','power_plant','energy_cargo_cooling','energy_discharge_pump','energy_reefer_containers','energy_onshore_power_supply','energy_zero_emissions_tech','fuel_type_cargo_cooling','fuel_type_discharge_pump','fuel_type_reefer_container','sfoc_cargo_cooling','sfoc_discharge_pump','sfoc_cargo_reefers'])
    # FuelConsumption (중첩)
    for fc in report.fuel_consumption:
        cur.execute(
            """
            INSERT INTO fuel_consumption (
                report_id, fuel_type, fuel_type_trade_name, bdn_number, bdn_datetime, fuel_bunker_received, fuel_mass, fuel_density, fuel_sulphur_content, fuel_viscosity, fuel_water_content, fuel_hhv, fuel_lfv, fuel_grade, fuel_bunker_port, fuel_bunker_port_name, co2_emission, total_fuel_quantity_consumed, fuel_quantity_rob, sludge_rob, fuel_lcv_report, fuel_lcv, fuel_pos_ref, ch4_cf, n2o_cf, fresh_water_bunkered, fresh_water_produced, fresh_water_consumed, technical_water_produced, technical_water_consumed, wash_water_consumed, fresh_water_rob, clo_rob, clo_feed_rate, clo_consumption, clo_received
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                report_id, fc.fuel_type, fc.fuel_type_trade_name, fc.bdn_number, fc.bdn_datetime, fc.fuel_bunker_received, fc.fuel_mass, fc.fuel_density, fc.fuel_sulphur_content, fc.fuel_viscosity, fc.fuel_water_content, fc.fuel_hhv, fc.fuel_lfv, fc.fuel_grade, fc.fuel_bunker_port, fc.fuel_bunker_port_name, fc.co2_emission, fc.total_fuel_quantity_consumed, fc.fuel_quantity_rob, fc.sludge_rob, fc.fuel_lcv_report, fc.fuel_lcv, fc.fuel_pos_ref, fc.ch4_cf, fc.n2o_cf, fc.fresh_water_bunkered, fc.fresh_water_produced, fc.fresh_water_consumed, fc.technical_water_produced, fc.technical_water_consumed, fc.wash_water_consumed, fc.fresh_water_rob, fc.clo_rob, fc.clo_feed_rate, fc.clo_consumption, fc.clo_received
            )
        )
        fuel_id = cur.lastrowid
        _insert_nested('foc_fuel_type', fc.foc_fuel_type, [
            'fuel_consumption_id','foc_main_engine','foc_diesel_electric_propulsion','foc_diesel_generator','foc_auxiliary_boiler','foc_auxiliary_engine','foc_cargo_cooling','foc_cargo_heating','foc_diesel_power_packs','foc_dirty_petroleum_products_cargo_pump','foc_discharge_pump','foc_dp_operations','foc_electrical_power_generation','foc_incinerator','foc_inert_gas_generators_gcus','foc_other_fuel_consuming_devices','foc_reefer_containers','foc_shuttle_tanker_operations','foc_sts_operations'])
        _insert_nested('foc_consumer_type', fc.foc_consumer_type, [
            'fuel_consumption_id','fuel_used_main_engine','fuel_consumed_main_engine','fuel_used_diesel_electric_propulsion','fuel_consumed_diesel_electric_propulsion','fuel_used_diesel_generator','fuel_consumed_diesel_generator','fuel_used_auxiliary_boiler','fuel_consumed_auxiliary_boiler','fuel_used_auxiliary_engine','fuel_consumed_auxiliary_engine','fuel_used_cargo_cooling','fuel_consumed_cargo_cooling','fuel_used_cargo_heating','fuel_consumed_cargo_heating','fuel_used_diesel_power_packs','fuel_consumed_diesel_power_packs','fuel_used_dirty_petroleum_products_cargo_pump','fuel_consumed_dirty_petroleum_products_cargo_pump','fuel_used_discharge_pump','fuel_consumed_discharge_pump','fuel_used_dp_operations','fuel_consumed_dp_operations','fuel_used_electrical_power_generation','fuel_consumed_electrical_power_generation','fuel_used_incinerator','fuel_consumed_incinerator','fuel_used_inert_gas_generators_gcus','fuel_consumed_inert_gas_generators_gcus','fuel_used_other_fuel_consuming_devices','fuel_consumed_other_fuel_consuming_devices','fuel_used_reefer_containers','fuel_consumed_reefer_containers','fuel_used_shuttle_tanker_operations','fuel_consumed_shuttle_tanker_operations','fuel_used_sts_operations','fuel_consumed_sts_operations'])

# --- WeatherDetails 단일 조회 엔드포인트 ---
@app.get("/api/performance-reports/{reportId}/weather-details", response_model=List[WeatherDetails])
def get_weather_details_by_report(reportId: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM weather_details WHERE report_id = ?", (reportId,))
    rows = cur.fetchall()
    result = [WeatherDetails(**dict(zip([c[0] for c in cur.description], row))) for row in rows]
    conn.close()
    return result

# --- CargoOnboard 단일 조회 엔드포인트 ---
@app.get("/api/performance-reports/{reportId}/cargo-onboard", response_model=List[CargoOnboard])
def get_cargo_onboard_by_report(reportId: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cargo_onboard WHERE report_id = ?", (reportId,))
    rows = cur.fetchall()
    result = [CargoOnboard(**dict(zip([c[0] for c in cur.description], row))) for row in rows]
    conn.close()
    return result

# --- ElectricConsumption 단일 조회 엔드포인트 ---
@app.get("/api/performance-reports/{reportId}/electric-consumptions", response_model=List[ElectricConsumption])
def get_electric_consumptions_by_report(reportId: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM electric_consumption WHERE report_id = ?", (reportId,))
    rows = cur.fetchall()
    result = [ElectricConsumption(**dict(zip([c[0] for c in cur.description], row))) for row in rows]
    conn.close()
    return result

# --- FuelConsumption 단일 조회 엔드포인트 ---
@app.get("/api/performance-reports/{reportId}/fuel-consumptions", response_model=List[FuelConsumption])
def get_fuel_consumptions_by_report(reportId: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM fuel_consumption WHERE report_id = ?", (reportId,))
    fuel_rows = cur.fetchall()
    result = []
    for fuel_row in fuel_rows:
        fuel_dict = dict(zip([c[0] for c in cur.description], fuel_row))
        fuel_id = fuel_dict['id']
        fuel_dict['foc_fuel_type'] = _fetch_nested_fuel(conn, 'foc_fuel_type', fuel_id, FocFuelType)
        fuel_dict['foc_consumer_type'] = _fetch_nested_fuel(conn, 'foc_consumer_type', fuel_id, FocConsumerType)
        result.append(FuelConsumption(**fuel_dict))
    conn.close()
    return result

# --- MeasuredCarbonDioxide 단일 조회 엔드포인트 ---
@app.get("/api/performance-reports/{reportId}/measured-carbon-dioxide", response_model=List[MeasuredCarbonDioxide])
def get_measured_carbon_dioxide_by_report(reportId: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM measured_carbon_dioxide WHERE report_id = ?", (reportId,))
    rows = cur.fetchall()
    result = [MeasuredCarbonDioxide(**dict(zip([c[0] for c in cur.description], row))) for row in rows]
    conn.close()
    return result