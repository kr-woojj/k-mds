"""W3 — S-1-1 데이터 정합성 확인기: Provider 원본 ↔ IMO 정준(에이전트) ↔ data-space 저장값 3자 대조, ISO/IEC 25023 측정치 산출.

측정 항목(시나리오 v0.2 §3; 표준 ID 는 data/raw/ISO25000/ISO_IEC_DIS_25023(E) 에서 인용):
- M1 전달 정확성  ← CIn-2-G 'Data exchange protocol conformance' 의 취지로 사용(IDS 프로토콜 경유 수신 payload 가 원본과 동일). X = A/B.
- M2 표준 매핑 완결성 ← FCp-1-G 'Functional coverage'(X = 1 − A/B, A 미구현=미매핑 필드, B 지정 함수=원본 필드).
- M3 표준 검증 정확성 ← FCr-1-G 'Functional correctness'(X = 1 − A/B, A 부정확=검증 FAIL 필드, B 고려 대상=확정 매핑 필드).
- M4 값 정합성(End-to-End, 정합율 채택) ← FCr-1-G 를 필드 단위 "기본 기능"에 적용(X = 1 − A/B, A 불일치 필드, B 표준모델 대응 필드가 있는 원본 필드).
- M5 필수 요소 충족 ← CIn-1-G 'Data exchange format conformance' 취지(스키마 required 충족). Ship-ODMS 스키마 required 가 비어 있어 N/A.
비교 규칙(T7): 숫자 상대오차 ≤ 0.1 % 또는 절대차 ≤ 1e-6 / 문자열 정확 일치(형 정규화 str() 허용) / 시각 UTC 초 단위 일치 / 결측(−9999, "")=null.

사용: uv run --project apps/kr-ghg-ai-agent python verification/adapters/consistency_check.py <agent_evidence_dir> <shipodms_out_dir> <original_payload.json> <out_dir> [--base http://localhost:8088]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from imo_to_shipodms import NONFUEL, camel, imo_field_map, load_run  # noqa: E402

ISO = "ISO/IEC DIS 25023:2014(E) (data/raw/ISO25000)"


def eq(a, b) -> bool:
    if a is None and b is None: return True
    if a is None or b is None: return False
    if isinstance(a, bool) or isinstance(b, bool): return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= max(1e-6, 1e-3 * abs(a))
    sa, sb = str(a), str(b)
    try:
        ta = datetime.fromisoformat(sa.replace("Z", "+00:00")); tb = datetime.fromisoformat(sb.replace("Z", "+00:00"))
        return ta.replace(microsecond=0) == tb.replace(microsecond=0)
    except ValueError:
        pass
    try:
        return abs(float(sa) - float(sb)) <= max(1e-6, 1e-3 * abs(float(sa)))
    except ValueError:
        return sa == sb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("agent_evidence_dir", type=Path); ap.add_argument("shipodms_out_dir", type=Path); ap.add_argument("original", type=Path); ap.add_argument("out_dir", type=Path)
    ap.add_argument("--base", default="http://localhost:8088")
    a = ap.parse_args(); a.out_dir.mkdir(parents=True, exist_ok=True)
    fmap = imo_field_map()
    deliv = json.loads((a.shipodms_out_dir / "shipodms-delivery.json").read_text("utf-8"))
    plan = json.loads((a.shipodms_out_dir / "shipodms-plan.json").read_text("utf-8"))
    runs = {r["cid"]: r for r in (load_run(d) for d in a.agent_evidence_dir.iterdir() if (d / "mapping-result.json").is_file())}
    with httpx.Client(base_url=a.base, timeout=30) as c:
        stored_reports = {r["id"]: r for r in c.get(f"/api/voyages/{deliv['voyage']['id']}/performance-reports").json()}
        stored_pcs = c.get(f"/api/voyages/{deliv['voyage']['id']}/port-calls").json()
        stored_ship = c.get(f"/api/ships/{deliv['ship']['id']}").json()
        stored_fuel = {rid: c.get(f"/api/voyages/{deliv['voyage']['id']}/performance-reports/{rid}/fuel-consumption").json() for rid in stored_reports}
        stored_weather = {rid: c.get(f"/api/voyages/{deliv['voyage']['id']}/performance-reports/{rid}/weather-details").json() for rid in stored_reports}
    # ── M2/M3 (에이전트 매핑·검증) ──
    m2_A = m2_B = m3_A = m3_B = 0
    for d in a.agent_evidence_dir.iterdir():
        if not (d / "mapping-result.json").is_file(): continue
        mr = json.loads((d / "mapping-result.json").read_text("utf-8")); vr = json.loads((d / "validation-result.json").read_text("utf-8"))
        fields = [f for f in mr["fields"]]
        m2_B += len(fields); m2_A += sum(1 for f in fields if not f.get("imo_data_number"))
        mapped_paths = {f["source_path"] for f in fields if f.get("imo_data_number")}
        m3_B += len(mapped_paths); m3_A += sum(1 for i in vr["items"] if i.get("source_path") in mapped_paths and i["verdict"] == "FAIL")
    # ── M4 (원본 ↔ 저장값) ──
    checks = []
    def add(cid, imo, target, src, stored):
        checks.append({"cid": cid, "imo": imo, "target": target, "source": src, "stored": stored, "match": eq(src, stored)})
    first = next(iter(runs.values()))["elements"] if runs else {}
    for imo, field in (("IMO0140", "imoNumber"), ("IMO0142", "shipName"), ("IMO0136", "callSign"), ("IMO0160", "shipType")):
        if imo in first: add("ship", imo, f"Ship.{field}", first[imo], stored_ship.get(field))
    for i, leg in enumerate(plan["port_calls"]):
        sp = stored_pcs[-len(plan["port_calls"]):][i] if len(stored_pcs) >= len(plan["port_calls"]) else {}
        for imo, field in (("IMO0111", "portDeparture"), ("IMO0065", "portAtd"), ("IMO0108", "portArrival"), ("IMO0063", "portAta")):
            if leg.get(field) is not None: add(f"leg{i+1}", imo, f"PortCall.{field}", leg[field], sp.get(field))
    no_target_total: set[str] = set()
    for rep in deliv["reports"]:
        cid, rid = rep["cid"], rep["report_id"]; run = runs[cid]; st = stored_reports.get(rid, {})
        planned = next(p for p in plan["reports"] if p["cid"] == cid); no_target_total |= set(planned["no_target"])
        for imo, v in run["elements"].items():
            t = fmap.get(imo)
            if not t or imo in NONFUEL or imo in ("IMO0140", "IMO0142", "IMO0136", "IMO0326", "IMO0138", "IMO0160", "IMO0191", "IMO0108", "IMO0111", "IMO0063", "IMO0065"): continue
            schema, field = t
            if schema == "PerformanceReport": add(cid, imo, f"PerformanceReport.{field}", v, st.get(field))
            elif schema == "WeatherDetails":
                w = (stored_weather.get(rid) or [{}])[0]; add(cid, imo, f"WeatherDetails.{field}", v, w.get(field))
        rows = {r.get("fuelTypeTradeName"): r for r in (stored_fuel.get(rid) or [])}
        for code, vals in run["fuel"].items():
            if not any(x not in (None, 0, 0.0) for x in vals.values()): continue
            row = rows.get(code, {}); foc = (row.get("focFuelType") or [{}])[0]
            for imo, v in vals.items():
                t = fmap.get(imo)
                if not t: continue
                schema, field = t
                add(cid, f"{imo}@{code}", f"FuelConsumption[{code}].{field}", v, (foc if schema == "FocFuelType" else row).get(field))
        nf = rows.get("_NONFUEL", {})
        for imo in NONFUEL & set(run["elements"]):
            t = fmap.get(imo)
            if t: add(cid, imo, f"FuelConsumption[_NONFUEL].{t[1]}", run["elements"][imo], nf.get(t[1]))
    m4_B = len(checks); m4_A = sum(1 for x in checks if not x["match"])
    # ── M1 (IDS 전달) ──
    orig = a.original.read_bytes(); h = hashlib.sha256(orig).hexdigest()
    m1 = {"artifact_sha256": h, "note": "Consumer 수신본 = 원본 여부는 run_s11 T2 단계가 기록(hash 비교). 여기서는 원본 해시만 기록."}
    measures = {
        "standard": ISO,
        "M1": {"iso_measure": "CIn-2-G Data exchange protocol conformance (취지 적용)", **m1},
        "M2": {"iso_measure": "FCp-1-G Functional coverage", "formula": "X = 1 - A/B", "A_unmapped": m2_A, "B_source_fields": m2_B, "X": round(1 - m2_A / m2_B, 4) if m2_B else None},
        "M3": {"iso_measure": "FCr-1-G Functional correctness", "formula": "X = 1 - A/B", "A_validation_fail": m3_A, "B_mapped_fields": m3_B, "X": round(1 - m3_A / m3_B, 4) if m3_B else None},
        "M4": {"iso_measure": "FCr-1-G Functional correctness (필드 단위 적용) — 채택 정합율", "formula": "X = 1 - A/B", "A_mismatch": m4_A, "B_fields_with_target": m4_B, "X": round(1 - m4_A / m4_B, 4) if m4_B else None, "target": 0.95},
        "M5": {"iso_measure": "CIn-1-G Data exchange format conformance (취지 적용)", "note": "Ship-ODMS openapi required 목록 없음 → N/A"},
        "no_target_elements": sorted(no_target_total),
        "checks": len(checks), "mismatches": [x for x in checks if not x["match"]],
    }
    (a.out_dir / "consistency-report.json").write_text(json.dumps({"measures": measures, "checks": checks}, ensure_ascii=False, indent=1, default=str), "utf-8")
    verdict = "PASS" if measures["M4"]["X"] is not None and measures["M4"]["X"] >= 0.95 else "FAIL"
    print(json.dumps({k: v for k, v in measures.items() if k not in ("checks", "mismatches")}, ensure_ascii=False, indent=1))
    print(f"mismatches: {m4_A}/{m4_B} → M4 X={measures['M4']['X']} verdict={verdict}")
    for x in measures["mismatches"][:20]: print("  -", x)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
