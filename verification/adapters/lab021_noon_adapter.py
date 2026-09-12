"""랩오투원(LAB021) Noon Report API payload → GHG AI Agent 입력 변환 (ROC 표준변환 블록 모사, 2026-09-12).

Provider 가 함께 공개한 코드북(endpointDocumentation …/noon/code-book, IMO COMPENDIUM 기준 156 항목)의
externalKey → IMO Data Number 매핑만 사용한다. 코드북에 없는 키는 원래 이름 그대로 둔다(발명 금지).
externalKey 가 여러 IMO ID 에 걸리면 코드북 eventName 과 레코드 eventKey 를 대조해 하나로 좁히고, 그래도 여러 개면 미변환.

사용:
  python lab021_noon_adapter.py <payload.json> <code-book.json> <out_dir>
출력: out_dir/<cid>.json (레코드별 에이전트 입력), out_dir/adapter-report.json (커버리지·미매핑·모호 항목)

# ponytail: eventKey↔eventName 대조는 대문자·비영숫자 제거 비교. 코드북 형식이 바뀌면 여기부터 깨진다.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

IMO_ID = re.compile(r"^IMO\d{4}$")


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


def load_codebook(path: Path) -> dict[str, list[dict]]:
    js = json.loads(path.read_text("utf-8"))
    items = js["data"]["items"] if "data" in js else js["items"]
    by_key: dict[str, list[dict]] = {}
    for it in items:
        keys = it.get("externalKey") or []
        for k in (keys if isinstance(keys, list) else [keys]):
            by_key.setdefault(str(k), []).append(it)
    return by_key


def convert_record(rec: dict, general: dict, by_key: dict[str, list[dict]], cid: str, dataset_id: str) -> tuple[dict, dict]:
    event_key = str(rec.get("eventKey", ""))
    out = {"correlation_id": cid, "dataset_id": dataset_id,
           "report_type": "noon" if _norm(event_key) in ("NOON", "NOONREPORT") else "event"}
    stats = {"mapped": [], "ambiguous": [], "not_in_codebook": [], "event_key": event_key}
    merged = {**{f"general.{k}": v for k, v in general.items()}, **rec}
    for key, value in merged.items():
        src = key.split(".", 1)[-1]
        cands = by_key.get(src, [])
        if len(cands) > 1:
            narrowed = [c for c in cands if any(_norm(e) == _norm(event_key) for e in (c.get("eventName") or []))]
            cands = narrowed or cands
        if len(cands) == 1 and IMO_ID.match(str(cands[0]["id"])):
            imo = cands[0]["id"]
            if imo in out:  # 같은 IMO ID 로 두 키가 오면 첫 값 유지, 충돌 기록
                stats["ambiguous"].append({"key": src, "imo": imo, "reason": "duplicate target"})
                continue
            out[imo] = value
            stats["mapped"].append({"key": src, "imo": imo, "unit": cands[0].get("unit"), "required": cands[0].get("required")})
        elif len(cands) > 1:
            out[src] = value
            stats["ambiguous"].append({"key": src, "candidates": [c["id"] for c in cands]})
        else:
            out[src] = value
            stats["not_in_codebook"].append(src)
    return out, stats


def main(argv: list[str]) -> int:
    payload, codebook, out_dir = Path(argv[1]), Path(argv[2]), Path(argv[3])
    out_dir.mkdir(parents=True, exist_ok=True)
    js = json.loads(payload.read_text("utf-8"))
    data = js.get("data", js)
    general, events = data.get("general", {}), data.get("events", [])
    by_key = load_codebook(codebook)
    imo_no = str(general.get("imoNo") or data.get("imoNo") or "UNKNOWN")
    report = {"payload": payload.name, "codebook_items": sum(len(v) for v in by_key.values()), "codebook_external_keys": len(by_key),
              "records": len(events), "per_record": []}
    for i, rec in enumerate(events):
        cid = f"LAB021-NOON-{imo_no}-{i:03d}"
        out, stats = convert_record(rec, general, by_key, cid, "LAB021/Noon Report API")
        (out_dir / f"{cid}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8")
        report["per_record"].append({"cid": cid, "event_key": stats["event_key"], "fields_in": len(rec) + len(general),
                                     "mapped_by_codebook": len(stats["mapped"]), "ambiguous": len(stats["ambiguous"]),
                                     "not_in_codebook": len(stats["not_in_codebook"]), "detail": stats})
    tot_in = sum(r["fields_in"] for r in report["per_record"]); tot_m = sum(r["mapped_by_codebook"] for r in report["per_record"])
    report["coverage_by_codebook_pct"] = round(100 * tot_m / tot_in, 1) if tot_in else None
    report["distinct_event_keys"] = sorted({r["event_key"] for r in report["per_record"]})
    report["not_in_codebook_keys"] = sorted({k for r in report["per_record"] for k in r["detail"]["not_in_codebook"]})
    (out_dir / "adapter-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_record"}, ensure_ascii=False, indent=1))
    return 0


def _selftest() -> None:
    by_key = {"portCode": [{"id": "IMO0013", "eventName": ["Arrival"]}, {"id": "IMO0099", "eventName": ["Departure S/By"]}], "imoNo": [{"id": "IMO0140"}]}
    out, st = convert_record({"eventKey": "DEPARTURE_SBY", "portCode": "PACTB", "foo": 1}, {"imoNo": "9990001"}, by_key, "c", "d")
    assert out["IMO0099"] == "PACTB" and out["IMO0140"] == "9990001" and out["foo"] == 1 and out["report_type"] == "event"
    assert st["not_in_codebook"] == ["eventKey", "foo"] or "foo" in st["not_in_codebook"]
    print("selftest ok")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selftest":
        _selftest()
    else:
        sys.exit(main(sys.argv))
