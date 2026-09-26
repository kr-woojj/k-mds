"""GHG AI Agent 추가 서비스 (2026-09-26 사용자 요청) — 하네스 도구로 노출.

1) 선박 조회·연간 GHG 집계: Ship-ODMS 에 저장된 PerformanceReport 를 IMO 번호로 조회해 연간 연료·CO2·거리·GFI(TtW)를 집계하고,
   요청 시 YearPerformanceReport(totalGfiAnnually) 로 입력한다. Ship-ODMS 모델에는 CII 필드가 없고(연차보고 = totalGfiAnnually 뿐),
   Ship 에 DWT/용량 필드도 없어 CII 는 사용자가 capacity_dwt 를 줄 때만 참고값으로 계산한다.
2) 매핑 증적 대시보드: run_NN 의 agent-evidence(mapping-result·pre-normalization)와 consistency-report 를 집계해 시각화 데이터를 만든다.

표준 근거: CF·LCV 는 data/raw/MEPC/MEPC.308(73).pdf Annex 5 (2018 EEDI 계산 지침) 표(5쪽)에서 인용. 그 외 조항은 인용하지 않는다.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import httpx

# MEPC.308(73) Annex 5, 5쪽 표 — (LCV kJ/kg, CF t-CO2/t-fuel). 확인된 행만 수록(LNG·메탄올 등은 표 뒷부분 미추출 → 미확인).
CF_TABLE = {
    "Diesel/Gas Oil": (42_700, 3.206),
    "Light Fuel Oil": (41_200, 3.151),
    "Heavy Fuel Oil": (40_200, 3.114),
    "LPG (Propane)": (46_300, 3.000),
    "LPG (Butane)": (45_700, 3.030),
}
CF_SOURCE = "MEPC.308(73) Annex 5 (2018 Guidelines on the method of calculation of the attained EEDI), 표 p.5 — data/raw/MEPC/MEPC.308(73).pdf"
# FAL50 'Fuel type' 코드 → 표의 연료 구분. 가정(사람 확인 필요): VLSFO/ULSFO 는 잔류유(ISO 8217 RME~RMK)로 취급.
FAL50_TO_CF = {"HFO": "Heavy Fuel Oil", "VLSFO2020": "Heavy Fuel Oil", "ULSFO2020": "Heavy Fuel Oil", "LFO": "Light Fuel Oil",
               "MDO": "Diesel/Gas Oil", "MGO": "Diesel/Gas Oil", "ULSMGO2020": "Diesel/Gas Oil", "LPGP": "LPG (Propane)", "LPGB": "LPG (Butane)"}
ASSUMPTIONS = ["VLSFO2020/ULSFO2020 → Heavy Fuel Oil 행(CF 3.114) 적용 — 잔류유 가정, 사람 확인 필요",
               "연료 소비량은 FocFuelType 의 장비별 값(ME/AE/Boiler/기타) 합 = 보고 기간 소비량(t)으로 취급",
               "동일 (voyageId, reportDatetime, eventType) 보고는 반복 전송 중복으로 보고 1건만 집계",
               "GFI 는 TtW(연료 연소분) 만 — WtW 계수(LCA 지침)는 근거 자료 미배치로 미적용"]


def _get(base: str, path: str):
    r = httpx.get(f"{base}/api{path}", timeout=30); r.raise_for_status(); return r.json()


def find_ship(base: str, imo: str) -> dict | None:
    imo = str(imo).strip()
    for s in _get(base, "/ships"):
        if str(s.get("imoNumber") or "").strip() in (imo, imo.lstrip("0")) or str(s.get("imoNumber") or "").lstrip("0") == imo.lstrip("0"):
            return s
    return None


def ship_overview(base: str, imo: str) -> dict:
    ship = find_ship(base, imo)
    if not ship:
        return {"ok": False, "imo": imo, "message": f"Ship-ODMS 에 IMO {imo} 선박이 없다. 등록된 IMO: {[s.get('imoNumber') for s in _get(base, '/ships')]}"}
    voyages = _get(base, f"/ships/{ship['id']}/voyages"); out_v = []
    for v in voyages:
        reps = _get(base, f"/voyages/{v['id']}/performance-reports")
        uniq = {(r.get("reportDatetime"), r.get("eventType")) for r in reps}
        out_v.append({"voyage_id": v["id"], "voyage_number": v.get("voyageNumber"), "gfi_per_voyage": v.get("gfiPerVoyage"), "reports": len(reps), "unique_reports": len(uniq),
                      "period": [min((r.get("reportDatetime") or "" for r in reps), default=None), max((r.get("reportDatetime") or "" for r in reps), default=None)],
                      "port_calls": len(_get(base, f"/voyages/{v['id']}/port-calls"))})
    yearly = _get(base, f"/ships/{ship['id']}/yearly-reports")
    return {"ok": True, "ship": ship, "voyages": out_v, "yearly_reports": yearly,
            "cii": {"value": None, "note": "Ship-ODMS 표준모델(openapi.yaml)에는 CII 필드가 없다. 연차보고는 YearPerformanceReport.totalGfiAnnually(GFI) 뿐이며, 선박 용량(DWT/GT)도 저장되지 않아 CII 는 capacity_dwt 를 지정할 때만 참고값으로 계산한다."},
            "ui": f"http://localhost:3031/ships/{ship['id']}/yearly-reports"}


def annual_ghg(base: str, imo: str, capacity_dwt: float | None = None, write: bool = False, evidence_dir: Path | None = None) -> dict:
    ship = find_ship(base, imo)
    if not ship:
        return {"ok": False, "imo": imo, "message": f"Ship-ODMS 에 IMO {imo} 선박이 없다."}
    seen: set = set(); used: list[dict] = []; dup = 0
    for v in _get(base, f"/ships/{ship['id']}/voyages"):
        for r in _get(base, f"/voyages/{v['id']}/performance-reports"):
            key = (v["id"], r.get("reportDatetime"), r.get("eventType"))
            if key in seen: dup += 1; continue
            seen.add(key); used.append(r)
    fuel_t: Counter = Counter(); unknown_fuel: Counter = Counter()
    for r in used:
        for fc in r.get("fuelConsumption") or []:
            code = fc.get("fuelTypeTradeName")
            if not code or code == "_NONFUEL": continue
            mass = sum(float(val) for ff in (fc.get("focFuelType") or []) for k, val in ff.items() if k.startswith("foc") and isinstance(val, (int, float)))
            (fuel_t if code in FAL50_TO_CF else unknown_fuel)[code] += mass
    rows = []; co2_t = 0.0; energy_mj = 0.0
    for code, mass in sorted(fuel_t.items()):
        lcv, cf = CF_TABLE[FAL50_TO_CF[code]]
        rows.append({"fuel_code": code, "cf_row": FAL50_TO_CF[code], "mass_t": round(mass, 3), "cf": cf, "lcv_kj_per_kg": lcv, "co2_t": round(mass * cf, 3), "energy_mj": round(mass * lcv, 1)})
        co2_t += mass * cf; energy_mj += mass * lcv
    distance_nm = sum(float(r["distanceOverGround"]) for r in used if isinstance(r.get("distanceOverGround"), (int, float)))
    gfi_ttw = (co2_t * 1e6 / energy_mj) if energy_mj else None
    cii = (co2_t * 1e6 / (float(capacity_dwt) * distance_nm)) if capacity_dwt and distance_nm else None
    period = [min((r.get("reportDatetime") or "" for r in used), default=None), max((r.get("reportDatetime") or "" for r in used), default=None)]
    res = {"ok": True, "imo": ship.get("imoNumber"), "ship_id": ship["id"], "ship_name": ship.get("shipName"), "period": period,
           "reports_used": len(used), "duplicates_excluded": dup, "fuel": rows, "unknown_fuel_codes": dict(unknown_fuel),
           "totals": {"fuel_t": round(sum(fuel_t.values()), 3), "co2_t": round(co2_t, 3), "energy_mj": round(energy_mj, 1), "distance_nm": round(distance_nm, 1)},
           "gfi_ttw_gco2_per_mj": round(gfi_ttw, 3) if gfi_ttw else None,
           "cii_attained_g_per_t_nm": round(cii, 4) if cii else None,
           "cii_note": None if cii else "CII 미산출 — 선박 용량(DWT) 없음(Provider grossTonnage=-9999, Ship-ODMS 에 용량 필드 없음). capacity_dwt 를 주면 참고값 계산.",
           "cf_source": CF_SOURCE, "assumptions": ASSUMPTIONS, "written": None}
    if write and gfi_ttw:
        same = [y for y in _get(base, f"/ships/{ship['id']}/yearly-reports") if y.get("totalGfiAnnually") is not None and abs(float(y["totalGfiAnnually"]) - round(gfi_ttw, 3)) < 1e-6]
        if same:  # 멱등: 같은 값의 연차보고가 이미 있으면 다시 넣지 않는다(에이전트 재호출로 중복 행 생성 방지)
            res["written"] = {"skipped": True, "existing_ids": [y["id"] for y in same], "field": "YearPerformanceReport.totalGfiAnnually", "ui": f"http://localhost:3031/ships/{ship['id']}/yearly-reports"}
            write = False
    if write and gfi_ttw:
        r = httpx.post(f"{base}/api/ships/{ship['id']}/yearly-reports", json={"totalGfiAnnually": round(gfi_ttw, 3)}, timeout=30)
        res["written"] = {"http": r.status_code, "body": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:200],
                          "field": "YearPerformanceReport.totalGfiAnnually (GFI TtW, gCO2/MJ)", "ui": f"http://localhost:3031/ships/{ship['id']}/yearly-reports"}
    if evidence_dir:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        p = evidence_dir / f"annual-ghg_{ship.get('imoNumber')}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
        p.write_text(json.dumps({**res, "report_ids": [r["id"] for r in used], "computed_at": datetime.now(UTC).isoformat()}, ensure_ascii=False, indent=1), "utf-8")
        res["evidence"] = {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    return res


# ---------------------------------------------------------------- dashboard
def _rjson(p: Path, default=None):
    return json.loads(p.read_text("utf-8")) if p.is_file() else default


def dashboard_data(run: Path) -> dict:
    ev = run / "agent-evidence"; events = []
    methods: Counter = Counter(); unmapped_paths: Counter = Counter(); ambiguous: Counter = Counter(); codebook_mapped = 0; total = 0
    for d in sorted(p for p in ev.iterdir() if p.is_dir()) if ev.is_dir() else []:
        mr = _rjson(d / "mapping-result.json", {}); pn = _rjson(d / "pre-normalization.json", {})
        m = Counter(f["mapping_method"] for f in mr.get("fields", [])); methods += m; total += len(mr.get("fields", []))
        for f in mr.get("fields", []):
            if not f.get("imo_data_number"): unmapped_paths[f["source_path"]] += 1
        for k, v in (pn.get("ambiguous") or {}).items(): ambiguous[f"{k}: {v}"] += 1
        codebook_mapped += pn.get("mapped_count", 0)
        events.append({"cid": d.name, "event": pn.get("event_key"), "fields": len(mr.get("fields", [])), "unmapped": m.get("UNMAPPED", 0),
                       "codebook_mapped": pn.get("mapped_count", 0), "codebook_ambiguous": len(pn.get("ambiguous") or {}), "sentinel_nulled": len(pn.get("sentinel_nulled") or [])})
    cr = _rjson(run / "shipodms/consistency-report.json", {}); ms = cr.get("measures", {}); checks = cr.get("checks", [])
    deliv = _rjson(run / "shipodms/shipodms-delivery.json", {}); res = _rjson(run / "result.json", {}); meta = _rjson(run / "run-meta.json", {})
    mapped = total - methods.get("UNMAPPED", 0)
    delivered_ok = sum(1 for c in checks if c.get("match")); delivered_ng = sum(1 for c in checks if c.get("match") is False)
    no_target = ms.get("no_target_elements") or []
    return {"run_id": run.name, "verdict": res.get("verdict"), "llm": meta.get("llm"), "orchestrator": meta.get("orchestrator"), "created_at": meta.get("created_at"),
            "summary": {"total_fields": total, "mapped": mapped, "unmapped": methods.get("UNMAPPED", 0),
                        "delivered_checked": len(checks), "delivered_ok": delivered_ok, "delivered_mismatch": delivered_ng,
                        "no_target_in_shipodms": len(no_target), "codebook_converted": codebook_mapped, "codebook_unresolved": sum(ambiguous.values()),
                        "delivery_http_errors": len(deliv.get("errors") or [])},
            "methods": dict(methods), "measures": {k: (ms.get(k) or {}).get("X") for k in ("M2", "M3", "M4")},
            "unmapped_paths": dict(unmapped_paths), "codebook_unresolved_items": dict(ambiguous), "no_target_elements": no_target,
            "mismatches": ms.get("mismatches") or [], "events": events}


DASH_HTML = """<!doctype html><html lang="ko"><meta charset="utf-8"><title>K-MDS 매핑 증적 대시보드</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>body{font-family:system-ui,'Malgun Gothic',sans-serif;max-width:1200px;margin:24px auto;padding:0 16px;color:#1f2328}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.card{background:#f6f8fa;border-radius:10px;padding:14px}
.card b{display:block;font-size:26px}.card span{font-size:12px;color:#57606a}.row{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:24px}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{border-bottom:1px solid #d0d7de;padding:6px 8px;text-align:left}code{background:#eef;padding:1px 4px;border-radius:4px}
.pass{color:#1a7f37}.fail{color:#cf222e}</style>
<body><h2>K-MDS S-1-1 매핑 증적 대시보드 <small id="run"></small></h2>
<p>K-MDS IDS Consumer 수신 데이터 → GHG AI Agent(IMO Compendium 매핑 스킬) → Ship-ODMS 전달 결과. 수치는 run 증적(mapping-result·pre-normalization·consistency-report)에서 그대로 집계.
 run 선택: <select id="sel"></select> · <a id="rep" target="_blank">판정 보고서</a> · <a href="/dashboard/data" id="raw" target="_blank">원시 JSON</a></p>
<div class="cards" id="cards"></div>
<div class="row"><div><canvas id="c1"></canvas></div><div><canvas id="c2"></canvas></div></div>
<div class="row"><div><h3>IMO Compendium 코드화 필요·미해결 항목 (랩오투원 코드북 기준)</h3><table id="t1"><tr><th>항목</th><th>건수</th></tr></table>
<h3>표준 매핑은 됐으나 Ship-ODMS 대상 필드 없음</h3><p id="nt"></p></div>
<div><h3>이벤트별</h3><table id="t2"><tr><th>#</th><th>이벤트</th><th>필드</th><th>미매핑</th><th>코드북 변환</th><th>코드북 미해결</th><th>결측→null</th></tr></table></div></div>
<h3>전달 불일치 (M4)</h3><table id="t3"><tr><th>보고</th><th>IMO</th><th>대상</th><th>원본</th><th>저장</th></tr></table>
<script>
const q=new URLSearchParams(location.search);let charts=[];
async function load(run){const d=await (await fetch('/dashboard/data'+(run?'?run='+run:'')).json();const s=d.summary;
document.getElementById('run').textContent=d.run_id+' · '+(d.verdict||'')+' · LLM '+(d.llm&&d.llm.provider||'-');document.getElementById('rep').href='/runs/'+d.run_id+'/report';document.getElementById('raw').href='/dashboard/data?run='+d.run_id;
const cards=[['총 데이터 항목(원본 필드)',s.total_fields],['IMO code 변환 성공',s.mapped],['변환 실패(미매핑)',s.unmapped],['Ship-ODMS 전달·대조 항목',s.delivered_checked],['전달 성공(값 일치)',s.delivered_ok],['전달 불일치',s.delivered_mismatch],['대상 필드 없음(미전달)',s.no_target_in_shipodms],['코드북으로 code화한 항목',s.codebook_converted],['코드북 미해결(코드화 필요)',s.codebook_unresolved],['M2 / M3 / M4',[d.measures.M2,d.measures.M3,d.measures.M4].join(' / ')]];
document.getElementById('cards').innerHTML=cards.map(c=>`<div class="card"><b>${c[1]}</b><span>${c[0]}</span></div>`).join('');
charts.forEach(c=>c.destroy());charts=[];
charts.push(new Chart(document.getElementById('c1'),{type:'doughnut',data:{labels:['변환 성공','미매핑'],datasets:[{data:[s.mapped,s.unmapped],backgroundColor:['#1a7f37','#cf222e']}]},options:{plugins:{title:{display:true,text:'IMO Compendium code 변환 ('+s.total_fields+' 항목)'}}}}));
charts.push(new Chart(document.getElementById('c2'),{type:'bar',data:{labels:d.events.map((e,i)=>i+' '+(e.event||'')),datasets:[{label:'매핑',data:d.events.map(e=>e.fields-e.unmapped),backgroundColor:'#1a7f37'},{label:'미매핑',data:d.events.map(e=>e.unmapped),backgroundColor:'#cf222e'},{label:'코드북 미해결',data:d.events.map(e=>e.codebook_ambiguous),backgroundColor:'#9a6700'}]},options:{plugins:{title:{display:true,text:'이벤트별 변환 결과'}},scales:{x:{stacked:true},y:{stacked:true}}}}));
const t1=document.getElementById('t1');t1.innerHTML='<tr><th>항목</th><th>건수</th></tr>'+Object.entries(d.codebook_unresolved_items).map(([k,v])=>`<tr><td><code>${k}</code></td><td>${v}</td></tr>`).join('')+Object.entries(d.unmapped_paths).map(([k,v])=>`<tr><td>미매핑 <code>${k}</code></td><td>${v}</td></tr>`).join('');
document.getElementById('nt').innerHTML=d.no_target_elements.map(x=>`<code>${x}</code>`).join(' ')||'-';
document.getElementById('t2').innerHTML='<tr><th>#</th><th>이벤트</th><th>필드</th><th>미매핑</th><th>코드북 변환</th><th>코드북 미해결</th><th>결측→null</th></tr>'+d.events.map((e,i)=>`<tr><td>${i}</td><td>${e.event||''}</td><td>${e.fields}</td><td>${e.unmapped}</td><td>${e.codebook_mapped}</td><td>${e.codebook_ambiguous}</td><td>${e.sentinel_nulled}</td></tr>`).join('');
document.getElementById('t3').innerHTML='<tr><th>보고</th><th>IMO</th><th>대상</th><th>원본</th><th>저장</th></tr>'+d.mismatches.map(m=>`<tr><td>${m.cid}</td><td>${m.imo}</td><td>${m.target}</td><td>${m.source}</td><td>${m.stored}</td></tr>`).join('');}
(async()=>{const runs=await (await fetch('/runs')).json();const sel=document.getElementById('sel');runs.slice().reverse().forEach(r=>{const o=document.createElement('option');o.value=r.run_id;o.textContent=r.run_id+(r.verdict?' — '+r.verdict:'');sel.appendChild(o)});
sel.value=q.get('run')||sel.options[0].value;sel.onchange=()=>load(sel.value);load(sel.value);})();
</script></body></html>"""
