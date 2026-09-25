"""LAB021(vessellink, 랩오투원) Provider payload 사전 정규화 — 결정 D2·D4·D8 (2026-09-26).

Provider 가 공개한 코드북(externalKey → IMO Data Number, eventName 컨텍스트)을 근거로 vessellink 필드명을
IMO Compendium 식별자(IMOxxxx)로 바꿔 결정론 매핑 경로(EXPLICIT_IDENTIFIER_VALIDATED)에 태운다.
코드북이 1:N 인 키는 아래 규칙으로만 좁히고, 못 좁히면 원래 이름을 남긴다(발명 금지).

규칙 출처: verification/adapters/gears_voyage_transform.py (S04, FAL50 Structure "Consumption By Fuel Type" 근거).
- 이벤트 컨텍스트: eventKey → 코드북 eventName (ARRIVAL/DEPARTURE_SBY/NOON_AT_SEA/RUP/BUNKERING)
- 연료 구조: consumption{Me,Ge,Blr,Other}{Hfo,Lsfo,Ulsfo,Do,Mgo,Ulsmgo}
  → consumption_by_fuel_type/<FAL50 fuel code>/<장비 요소 IMO ID>
- 최특정 요소: draftFore→IMO0621, draftAft→IMO0622, draftMid→IMO0357, shipCourse→IMO0332, trueWindDirection→IMO0627 …
- 이벤트 코드: FAL50 Event type (EV01 Arrival, EV02 Departure, EV16 Noon sea passage, EV10 Begin of sea passage[추정],
  EV28 Other event[BUNKERING·CARGO_WORK — 전용 코드 없음])

# ponytail: 코드북 형식(data.items[].externalKey/eventName/id)이 바뀌면 여기부터 깨진다.
#           코드북 파일은 sha256 과 함께 var/reference/lab021 에 둔다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

LAB021_MARKERS = {"eventKey", "dateEventUtc", "hourSlr", "voyNo"}  # 4개 중 3개 이상이면 LAB021 Noon 레코드
EVENT_CTX = {"ARRIVAL": "Arrival", "DEPARTURE_SBY": "Departure S/By", "NOON_AT_SEA": "Noon at sea", "RUP": "R/UP", "BUNKERING": "Bunkering"}
EVENT_CODE = {"ARRIVAL": "EV01", "DEPARTURE_SBY": "EV02", "NOON_AT_SEA": "EV16", "RUP": "EV10", "BUNKERING": "EV28", "CARGO_WORK": "EV28"}
PICK: dict[str, Any] = {
    "draftFore": "IMO0621", "draftAft": "IMO0622", "draftMid": "IMO0357", "shipCourse": "IMO0332", "trueWindDirection": "IMO0627",
    "masterName": "IMO0580", "berthName": "IMO0548", "distanceToGo": "IMO0615", "positionLat": "IMO0601", "positionLon": "IMO0602",
    "portCode": {"Arrival": "IMO0108", "Departure S/By": "IMO0111", "Bunkering": "IMO0666"},
    "portName": {"Arrival": "IMO0109", "Departure S/By": "IMO0112", "Bunkering": "IMO0667"},
    "dateEventUtc": {"Arrival": "IMO0063", "Departure S/By": "IMO0065"},
}
ENGINE_ELEMENT = {"Me": "IMO0670", "Ge": "IMO0893", "Blr": "IMO0673", "Other": "IMO0903"}
FUEL_CODE = {"Hfo": "HFO", "Lsfo": "VLSFO2020", "Ulsfo": "ULSFO2020", "Do": "MDO", "Mgo": "MGO", "Ulsmgo": "ULSMGO2020"}
CONS_RE = re.compile(r"^consumption(Me|Ge|Blr|Other)(Hfo|Lsfo|Ulsfo|Do|Mgo|Ulsmgo)$")
ROB_RE = re.compile(r"^rob(Hfo|Lsfo|Ulsfo|Do|Mgo|Ulsmgo)$")
SENTINELS = (-9999, -9999.0, "-9999", "")
IMO_ID = re.compile(r"^IMO\d{4}$")
# FAL50 registry format 이 'an..'(문자열)인데 Provider 가 숫자로 보내는 요소 (IMO0191 an..17, IMO0605 an..35, IMO0601 an..10, IMO0602 an..11)
STR_TYPED = {"IMO0191", "IMO0605", "IMO0601", "IMO0602"}


def is_lab021_record(business: dict[str, Any]) -> bool:
    return isinstance(business, dict) and len(LAB021_MARKERS & set(business.keys())) >= 3


def load_codebook(path: Path) -> dict[str, list[dict[str, Any]]]:
    js = json.loads(path.read_text(encoding="utf-8"))
    items = js["data"]["items"] if "data" in js else js["items"]
    by: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        keys = it.get("externalKey") or []
        for k in keys if isinstance(keys, list) else [keys]:
            by.setdefault(str(k), []).append(it)
    return by


def normalize_lab021(
    business: dict[str, Any], codebook: dict[str, list[dict[str, Any]]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """(정규화된 business, 변환 보고). 원본 값은 바꾸지 않고 키만 IMO ID 로 바꾼다. 결측 표기는 null."""
    event_key = str(business.get("eventKey", ""))
    ctx = EVENT_CTX.get(event_key)
    out: dict[str, Any] = {"report_type": "noon" if event_key == "NOON_AT_SEA" else "event"}
    report: dict[str, Any] = {"event_key": event_key, "mapped": {}, "kept": [], "ambiguous": {}, "sentinel_nulled": []}
    fuel_cons: dict[str, dict[str, Any]] = {}
    fuel_rob: dict[str, dict[str, Any]] = {}
    for key, value in business.items():
        if key in ("report_type", "correlation_id", "dataset_id"):
            out[key] = value
            continue
        if value in SENTINELS:
            report["sentinel_nulled"].append(key)
            value = None
        if key == "eventKey":
            code = EVENT_CODE.get(event_key)
            if code:
                out["IMO0597"] = code
                report["mapped"][key] = f"IMO0597={code}"
            else:
                out[key] = value
                report["kept"].append(key)
            continue
        # 연료 구조: FAL50 'Consumption By Fuel Type'(IMO0654 연료코드 + 장비별 요소). 연료코드는 경로(dict key)로만 둔다 —
        # registry 의 IMO0654 format(n..10) 과 공식 code list 값(HFO 등 문자열)이 충돌해(known-limitation L-3) leaf 로 두면 항상 FAIL.
        m = CONS_RE.match(key)
        if m:
            fc = FUEL_CODE[m.group(2)]
            fuel_cons.setdefault(fc, {})[ENGINE_ELEMENT[m.group(1)]] = value
            report["mapped"][key] = f"consumption_by_fuel_type/{fc}/{ENGINE_ELEMENT[m.group(1)]}"
            continue
        m = ROB_RE.match(key)
        if m:
            fc = FUEL_CODE[m.group(1)]
            fuel_rob.setdefault(fc, {})["IMO0674"] = value
            report["mapped"][key] = f"rob_by_fuel_type/{fc}/IMO0674"
            continue
        cands = codebook.get(key, [])
        ids = [c["id"] for c in cands if IMO_ID.match(str(c.get("id", "")))]
        target = None
        if len(ids) == 1:
            target = ids[0]
        elif key in PICK:
            pick = PICK[key]
            target = pick.get(ctx) if isinstance(pick, dict) else pick
            if target is None and key == "dateEventUtc":
                target = "IMO0603"
        elif len(ids) > 1 and ctx:
            narrowed = [c["id"] for c in cands if ctx in (c.get("eventName") or [])]
            target = narrowed[0] if len(narrowed) == 1 else None
        if target:
            if target in out:  # 동일 IMO ID 중복 → 첫 값 유지, 기록
                report["ambiguous"][key] = f"duplicate target {target}"
                continue
            if target in STR_TYPED and value is not None and not isinstance(value, str):
                value = str(value)  # FAL50 format 'an..' 요소: Provider 숫자값을 문자열로 형 정규화(값 불변)
                report.setdefault("type_cast", {})[key] = f"{target}: numeric→string"
            out[target] = value
            report["mapped"][key] = target
        else:
            out[key] = value
            if len(ids) > 1:
                report["ambiguous"][key] = ids
            else:
                report["kept"].append(key)
    if fuel_cons:
        out["consumption_by_fuel_type"] = fuel_cons
    if fuel_rob:
        out["rob_by_fuel_type"] = fuel_rob
    # 컨텍스트(vessel/voyage/timestamp)는 normalization._CONTEXT_KEYS/_TIMESTAMP_KEYS 가 IMO 키를 직접 읽는다 — 중복 필드 만들지 않음.
    report["mapped_count"] = len(report["mapped"])
    report["kept_count"] = len(report["kept"])
    return out, report


def _selftest() -> None:
    cb: dict[str, list[dict[str, Any]]] = {"portCode": [{"id": "IMO0108", "eventName": ["Arrival"]}, {"id": "IMO0111", "eventName": ["Departure S/By"]}], "voyNo": [{"id": "IMO0191"}], "hourSlr": [{"id": "IMO0600"}]}
    rec = {"eventKey": "DEPARTURE_SBY", "dateEventUtc": "2026-04-19T20:36:00.000Z", "voyNo": 1, "hourSlr": 0, "portCode": "PACTB",
           "consumptionMeLsfo": 0.33, "robLsfo": 898.26, "grossTonnage": -9999.0, "foo": 1}
    assert is_lab021_record(rec)
    out, rep = normalize_lab021(rec, cb)
    assert out["IMO0597"] == "EV02" and out["IMO0111"] == "PACTB" and out["IMO0065"].startswith("2026") and out["IMO0191"] == "1"
    assert out["consumption_by_fuel_type"]["VLSFO2020"]["IMO0670"] == 0.33 and out["rob_by_fuel_type"]["VLSFO2020"]["IMO0674"] == 898.26
    assert "IMO0654" not in out["consumption_by_fuel_type"]["VLSFO2020"]
    assert out["grossTonnage"] is None and "grossTonnage" in rep["sentinel_nulled"] and "foo" in rep["kept"]
    assert out["IMO0191"] == "1" and rep["type_cast"]["voyNo"].startswith("IMO0191")
    print("selftest ok")


if __name__ == "__main__":
    _selftest()
