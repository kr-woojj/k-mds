"""W2 — GHG AI Agent 실행 증적(IMO 정준 필드) → data-space Ship-ODMS(GHG 표준모델 API, KR GEARs 대역) 전송.

입력: 에이전트 run 디렉터리들(각각 normalized-input.json + mapping-result.json + validation-result.json). 하나의 run = 하나의 이벤트.
필드 대응 근거: shared/standard-model/openapi.yaml 의 각 속성 description 에 적힌 "IMOxxxx: …" (snake_case → Ship-ODMS Java camelCase).
전송 순서: Ship(IMO0140) → Voyage(IMO0191) → PortCall(레그: EV02 출항 → 다음 EV01 도착) → PerformanceReport(이벤트별, 중첩 weather/fuelConsumption).

알려진 갭(보고서에 기록, 발명하지 않음):
- G-1 Ship-ODMS FuelConsumption.fuelType 은 int32, FAL50 'Fuel type' code list 는 문자열(HFO, VLSFO2020…) → fuelType 은 null, 연료 식별은
  fuelTypeTradeName(IMO0680, an..10)에 FAL50 코드를 넣어 유지 [WORKAROUND 표시].
- G-2 담수·실린더유(IMO0639~0641, 0645, 0676, 0678)는 스키마상 FuelConsumption 하위 → 연료와 무관하므로 fuelTypeTradeName="_NONFUEL" 행에 저장.
- 대상 필드가 없는 IMO 요소(다음항 ETA·코드·명, 밸러스트, 선석, ETD/ETB, GT/NT, 등록항, 선장명 등)는 전송하지 않고 목록으로 남긴다.

사용: uv run --project apps/kr-ghg-ai-agent python verification/adapters/imo_to_shipodms.py <agent_evidence_dir> <out_dir> [--base http://localhost:8088] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[2]
OPENAPI = ROOT / "shared/standard-model/openapi.yaml"
NONFUEL = {"IMO0639", "IMO0640", "IMO0641", "IMO0645", "IMO0676", "IMO0678"}
FUEL_ROW_ELEMENTS = {"IMO0674", "IMO0670", "IMO0893", "IMO0673", "IMO0903"}  # rob + 장비별 소비(FocFuelType)


def camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


def imo_field_map() -> dict[str, tuple[str, str]]:
    """IMO ID → (schema, camelCase field). openapi description 'IMOxxxx: …' 기준."""
    o = yaml.safe_load(OPENAPI.read_text("utf-8"))
    out: dict[str, tuple[str, str]] = {}
    for schema, s in o["components"]["schemas"].items():
        for prop, v in (s.get("properties") or {}).items():
            m = re.match(r"(IMO\d{4})", str(v.get("description") or ""))
            if m and m.group(1) not in out:
                out[m.group(1)] = (schema, camel(prop))
    return out


def load_run(d: Path) -> dict:
    ni = json.loads((d / "normalized-input.json").read_text("utf-8"))
    mr = json.loads((d / "mapping-result.json").read_text("utf-8"))
    vr = json.loads((d / "validation-result.json").read_text("utf-8")) if (d / "validation-result.json").is_file() else {"items": []}
    pn = json.loads((d / "pre-normalization.json").read_text("utf-8")) if (d / "pre-normalization.json").is_file() else {}
    value_by_path = {f["source_path"]: f["value"] for f in ni}
    verdict_by_path = {i["source_path"]: i["verdict"] for i in vr.get("items", []) if i.get("source_path")}
    elems: dict[str, object] = {}       # 평면 IMO → 값 (검증 PASS/WARNING 만)
    fuel: dict[str, dict[str, object]] = {}  # 연료코드 → {IMO: 값}
    skipped = []
    for f in mr["fields"]:
        imo, path = f.get("imo_data_number"), f["source_path"]
        if not imo:
            skipped.append({"path": path, "reason": f.get("mapping_method")}); continue
        if verdict_by_path.get(path) not in (None, "PASS", "WARNING"):
            skipped.append({"path": path, "reason": f"validation {verdict_by_path.get(path)}"}); continue
        v = value_by_path.get(path)
        m = re.match(r"^/(consumption|rob)_by_fuel_type/([A-Z0-9]+)/(IMO\d{4})$", path)
        if m:
            fuel.setdefault(m.group(2), {})[m.group(3)] = v
        else:
            elems[imo] = v
    return {"cid": d.name, "event_key": pn.get("event_key"), "elements": elems, "fuel": fuel, "skipped": skipped,
            "time": elems.get("IMO0603") or elems.get("IMO0063") or elems.get("IMO0065")}


def build_report(ev: dict, fmap: dict[str, tuple[str, str]]) -> tuple[dict, dict, list[str]]:
    """(performanceReport body, provenance{IMO: target}, no_target[IMO])."""
    body: dict = {}; weather: dict = {}; prov: dict = {}; no_target: list[str] = []
    for imo, v in ev["elements"].items():
        if imo in NONFUEL or imo in ("IMO0140", "IMO0142", "IMO0136", "IMO0326", "IMO0138", "IMO0160", "IMO0191",
                                     "IMO0108", "IMO0111", "IMO0063", "IMO0065"):
            continue  # Ship/Voyage/PortCall 로 감
        t = fmap.get(imo)
        if not t:
            no_target.append(imo); continue
        schema, field = t
        if schema == "PerformanceReport":
            body[field] = v; prov[imo] = f"PerformanceReport.{field}"
        elif schema == "WeatherDetails":
            weather[field] = v; prov[imo] = f"WeatherDetails.{field}"
        else:
            no_target.append(imo)
    body["reportDatetime"] = ev["time"]
    body["reportType"] = "1"  # FAL50 'Performance report type' 1 = Noon data report (파생값, M4 제외)
    if weather:
        body["weatherDetails"] = [weather]
    rows = []
    for code, vals in sorted(ev["fuel"].items()):
        if not any(x not in (None, 0, 0.0) for x in vals.values()):
            continue  # 해당 연료 미보유(전부 0) → 행 생성 안 함
        row: dict = {"fuelType": None, "fuelTypeTradeName": code}  # G-1 WORKAROUND
        foc: dict = {}
        for imo, v in vals.items():
            t = fmap.get(imo)
            if not t: no_target.append(imo); continue
            schema, field = t
            (foc if schema == "FocFuelType" else row)[field] = v
            prov[f"{imo}@{code}"] = f"FuelConsumption[{code}].{field}" if schema != "FocFuelType" else f"FuelConsumption[{code}].focFuelType[0].{field}"
        if foc: row["focFuelType"] = [foc]
        rows.append(row)
    nonfuel = {}
    for imo in NONFUEL & set(ev["elements"]):
        t = fmap.get(imo)
        if t: nonfuel[t[1]] = ev["elements"][imo]; prov[imo] = f"FuelConsumption[_NONFUEL].{t[1]}"
    if nonfuel:
        rows.append({"fuelType": None, "fuelTypeTradeName": "_NONFUEL", **nonfuel})  # G-2
    if rows:
        body["fuelConsumption"] = rows
    return body, prov, sorted(set(no_target))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_evidence_dir", type=Path); ap.add_argument("out_dir", type=Path)
    ap.add_argument("--base", default="http://localhost:8088"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    fmap = imo_field_map()
    runs = sorted((load_run(d) for d in a.agent_evidence_dir.iterdir() if (d / "mapping-result.json").is_file()), key=lambda r: str(r["time"]))
    if not runs:
        print("no agent runs with mapping-result.json"); return 2
    first = runs[0]["elements"]
    ship = {"imoNumber": first.get("IMO0140"), "shipName": first.get("IMO0142"), "callSign": first.get("IMO0136"),
            "mmsi": (str(first["IMO0326"]) if first.get("IMO0326") not in (None, 0) else None), "flagState": first.get("IMO0138") or None, "shipType": first.get("IMO0160")}
    voyage = {"voyageNumber": str(first.get("IMO0191"))}
    # 레그 → PortCall
    legs, cur = [], None
    for r in runs:
        e = r["elements"]
        if r["event_key"] == "DEPARTURE_SBY":
            if cur: legs.append(cur)
            cur = {"portDeparture": e.get("IMO0111"), "portAtd": e.get("IMO0065"), "portArrival": None, "portAta": None}
        elif r["event_key"] == "ARRIVAL" and cur and cur["portAta"] is None:
            cur["portArrival"] = e.get("IMO0108"); cur["portAta"] = e.get("IMO0063")
    if cur: legs.append(cur)
    reports = []
    for r in runs:
        body, prov, no_target = build_report(r, fmap)
        reports.append({"cid": r["cid"], "event_key": r["event_key"], "body": body, "provenance": prov, "no_target": no_target, "skipped": r["skipped"]})
    plan = {"generated_at": datetime.now(UTC).isoformat(), "base": a.base, "ship": ship, "voyage": voyage, "port_calls": legs, "reports": reports,
            "gaps": {"G-1": "fuelType int32 vs FAL50 code list string → fuelTypeTradeName WORKAROUND", "G-2": "담수·CLO 를 _NONFUEL 행에 저장"}}
    (a.out_dir / "shipodms-plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), "utf-8")
    print(f"plan: ship {ship['imoNumber']} voyage {voyage['voyageNumber']} port_calls {len(legs)} reports {len(reports)} → {a.out_dir/'shipodms-plan.json'}")
    if a.dry_run:
        return 0
    log = []
    with httpx.Client(base_url=a.base, timeout=30) as c:
        def call(method, url, body):
            r = c.request(method, url, json=body); js = r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text
            log.append({"method": method, "url": url, "status": r.status_code, "request": body, "response": js}); r.raise_for_status(); return js
        ships = call("GET", "/api/ships", None)
        found = next((s for s in ships if s.get("imoNumber") == ship["imoNumber"]), None)
        ship_rec = found or call("POST", "/api/ships", ship)
        voys = call("GET", f"/api/ships/{ship_rec['id']}/voyages", None)
        voy_rec = next((v for v in voys if str(v.get("voyageNumber")) == voyage["voyageNumber"]), None) or call("POST", f"/api/ships/{ship_rec['id']}/voyages", voyage)
        pcs = [call("POST", f"/api/voyages/{voy_rec['id']}/port-calls", leg) for leg in legs]
        stored = []
        for rep in reports:
            res = call("POST", f"/api/voyages/{voy_rec['id']}/performance-reports", rep["body"])
            stored.append({"cid": rep["cid"], "report_id": res.get("id"), "response": res})
    result = {"ship": ship_rec, "voyage": voy_rec, "port_calls": pcs, "reports": stored, "calls": len(log), "errors": [x for x in log if x["status"] >= 400]}
    (a.out_dir / "shipodms-delivery.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=str), "utf-8")
    (a.out_dir / "shipodms-http-log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1, default=str), "utf-8")
    print(f"delivered: ship id {ship_rec['id']}, voyage id {voy_rec['id']}, port_calls {len(pcs)}, reports {len(stored)}, http errors {len(result['errors'])}")
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
