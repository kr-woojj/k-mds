"""S-1-1 검증 하네스 — n8n 워크플로가 호출하는 단계별 HTTP 엔드포인트 (run_s11.py 의 T0/T2/T5~T8 을 그대로 재사용).

역할 분리: 시험 대상(GHG AI Agent 컨테이너)과 독립된 컨테이너에서 증적 생성·전송·정합성 판정을 수행한다.
n8n 이 T3~T5 (이벤트 단위 에이전트 ingress 호출) 를 오케스트레이션하고, 나머지 단계는 여기로 위임한다.

  POST /runs                      T0 baseline + T2 IDS 전달(자격증명 있을 때) → run_NN 생성, 이벤트 레코드 목록 반환
  POST /runs/{id}/collect         T5 에이전트 증적(inbox)을 run_NN/agent-evidence 로 복사 + T3-T5 요약
  POST /runs/{id}/deliver         T6 Ship-ODMS 전송 (adapters/imo_to_shipodms.py)
  POST /runs/{id}/consistency     T7 정합성 확인 (adapters/consistency_check.py)
  POST /runs/{id}/judge           T8 판정 + REPORT.md
  GET  /runs, /runs/{id}, /runs/{id}/report (HTML, 평가단 열람용), /health
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import run_s11 as s11  # noqa: E402

SHIP_ODMS = os.environ.get("SHIP_ODMS_BASE", "http://localhost:8088")
AGENT_BASE = os.environ.get("AGENT_BASE", "http://localhost:8001")
INBOX = Path(os.environ.get("AGENT_INBOX", str(s11.AGENT / "evidence")))
PY = [sys.executable]
app = FastAPI(title="K-MDS S-1-1 verification harness", version="0.1.0")


def run_dir(run_id: str) -> Path:
    d = s11.EVID / run_id
    if not d.is_dir():
        raise HTTPException(404, f"run not found: {run_id}")
    return d


def rjson(p: Path, default=None):
    return json.loads(p.read_text("utf-8")) if p.is_file() else default


def rc_of(p: Path) -> int:
    """sh() 가 남긴 T6/T7 로그 마지막 줄 'exit=N'."""
    return int(p.read_text("utf-8").rstrip().rsplit("exit=", 1)[-1]) if p.is_file() else -1


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "evidence_root": str(s11.EVID), "inbox": str(INBOX), "ship_odms": SHIP_ODMS, "agent": AGENT_BASE}


@app.get("/runs")
def list_runs() -> list[dict]:
    return [{"run_id": d.name, "verdict": (rjson(d / "result.json") or {}).get("verdict")} for d in sorted(s11.EVID.glob("run_[0-9][0-9]"))]


@app.post("/runs")
def create_run(body: dict | None = None) -> dict:
    body = body or {}
    source = Path(body["source"]) if body.get("source") else s11.DEFAULT_SOURCE
    if not source.is_file():
        raise HTTPException(400, f"source not found: {source}")
    run, prev = s11.next_run_dir()
    try:
        llm = httpx.get(f"{AGENT_BASE}/ready", timeout=30).json()["components"]["llm"]
    except Exception as e:  # noqa: BLE001
        llm = {"status": "UNREACHABLE", "error": type(e).__name__}
    s11.t0_baseline(run, source, SHIP_ODMS, llm)
    if body.get("skip_ids"):
        t2 = {"step": "T2", "verdict": "NOT_TESTED", "reason": "skip_ids"}
        (run / "T2-ids-transfer.json").write_text(json.dumps(t2, ensure_ascii=False), "utf-8")
    else:
        t2 = s11.t2_ids(run, source)
    prefix = f"S11-{run.name.upper()}-"
    events = s11.prepare_events(source, prefix)
    meta = {"run_id": run.name, "prev_run": prev.name if prev else None, "source": str(source), "source_sha256": s11.sha(source),
            "created_at": datetime.now(UTC).isoformat(), "orchestrator": "n8n",
            "n8n": {k: body.get(k) for k in ("n8n_execution_id", "n8n_workflow_id")}, "llm": llm, "correlation_prefix": prefix}
    (run / "run-meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    return {**meta, "t2": t2, "events": events, "agent_ingress": f"{AGENT_BASE}/api/v1/ids/events"}


@app.post("/runs/{run_id}/collect")
def collect(run_id: str, body: dict) -> dict:
    run = run_dir(run_id)
    ev = run / "agent-evidence"; ev.mkdir(exist_ok=True)
    rows = []
    for r in body.get("results", []):
        src, dst = INBOX / r["cid"], ev / r["cid"]
        if src.is_dir() and not dst.exists():
            shutil.copytree(src, dst)  # inbox 는 그대로 둔다(증적 삭제 금지)
        rows.append({**s11.summarize_agent_run(ev, r["cid"], r.get("event_key"), r.get("final_status") or "HTTP_ERROR", r.get("error")),
                     "http_status": r.get("http_status")})
    res = {"step": "T3-T5", "events": len(rows), "runs": rows, "all_integrity_ok": bool(rows) and all(x["integrity_ok"] for x in rows),
           "http_errors": [x["cid"] for x in rows if x.get("http_status") not in (200, 422)],
           "note": "T3 은 n8n 워크플로가 이벤트 단위로 에이전트 HTTP ingress(/api/v1/ids/events)에 투입(G-3 배치 envelope). 진해 현장 Route 검증은 W5."}
    (run / "T3-T5-agent.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    return {"run_id": run_id, **res}


@app.post("/runs/{run_id}/deliver")
def deliver(run_id: str) -> dict:
    run = run_dir(run_id); od = run / "shipodms"
    rc = s11.sh(PY + [str(s11.HERE / "adapters/imo_to_shipodms.py"), str(run / "agent-evidence"), str(od), "--base", SHIP_ODMS], run / "T6-shipodms.txt")
    d = rjson(od / "shipodms-delivery.json", {})
    return {"run_id": run_id, "step": "T6", "exit": rc, "summary": {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in d.items() if k != "errors"}, "errors": d.get("errors"), "log": (run / "T6-shipodms.txt").read_text("utf-8")[-1500:]}


@app.post("/runs/{run_id}/consistency")
def consistency(run_id: str) -> dict:
    run = run_dir(run_id); od = run / "shipodms"
    source = Path(rjson(run / "run-meta.json")["source"])
    rc = s11.sh(PY + [str(s11.HERE / "adapters/consistency_check.py"), str(run / "agent-evidence"), str(od), str(source), str(od), "--base", SHIP_ODMS], run / "T7-consistency.txt")
    rep = rjson(od / "consistency-report.json", {})
    return {"run_id": run_id, "step": "T7", "exit": rc, "measures": {k: (rep.get("measures", {}).get(k) or {}).get("X") for k in ("M1", "M2", "M3", "M4", "M5")},
            "log": (run / "T7-consistency.txt").read_text("utf-8")[-1500:]}


@app.post("/runs/{run_id}/judge")
def judge(run_id: str, body: dict | None = None) -> dict:
    run = run_dir(run_id)
    meta = rjson(run / "run-meta.json", {})
    if body and body.get("n8n_execution_id"):
        meta["n8n"] = {**meta.get("n8n", {}), "n8n_execution_id": body["n8n_execution_id"]}
        (run / "run-meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    prev = s11.EVID / meta["prev_run"] if meta.get("prev_run") else None
    res = s11.judge(run, prev, rjson(run / "T2-ids-transfer.json", {}), rjson(run / "T3-T5-agent.json", {}), rc_of(run / "T6-shipodms.txt"), rc_of(run / "T7-consistency.txt"))
    (run / "REPORT.md").write_text(report_md(run), "utf-8")
    return {"run_id": run_id, "step": "T8", **res, "report_url": f"http://localhost:8090/runs/{run_id}/report", "evidence_dir": str(run)}


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    run = run_dir(run_id)
    return {"run_id": run_id, "meta": rjson(run / "run-meta.json"), "result": rjson(run / "result.json"), "files": sorted(str(p.relative_to(run)) for p in run.rglob("*") if p.is_file())}


def report_md(run: Path) -> str:
    meta, t0, t2, ag, res = (rjson(run / f, {}) for f in ("run-meta.json", "T0-baseline.json", "T2-ids-transfer.json", "T3-T5-agent.json", "result.json"))
    rep = rjson(run / "shipodms/consistency-report.json", {}); ms = rep.get("measures", {}); deliv = rjson(run / "shipodms/shipodms-delivery.json", {})
    iso = {"M1": "CIn-2-G 취지(전달 정확성)", "M2": "FCp-1-G 매핑 완결성", "M3": "FCr-1-G 검증 정확성", "M4": "FCr-1-G 필드 단위 값 정합성(채택 정합율)", "M5": "CIn-1-G 취지(필수 요소)"}
    n8n = meta.get("n8n") or {}
    exec_url = f"http://localhost:5678/workflow/{n8n.get('n8n_workflow_id')}/executions/{n8n.get('n8n_execution_id')}" if n8n.get("n8n_execution_id") else "(수동 실행)"
    L = [f"# S-1-1 실증 자동화 결과 — {run.name}", "",
         f"- 판정: **{res.get('verdict')}**", f"- 실행: {meta.get('created_at')} / 오케스트레이터 n8n 실행 로그: {exec_url}",
         f"- LLM: {json.dumps(meta.get('llm'), ensure_ascii=False)} / 코드 commit {t0.get('k_mds_commit')} (dirty={t0.get('k_mds_dirty')})",
         f"- 원본 payload: `{meta.get('source')}` sha256 {meta.get('source_sha256')}",
         f"- 판정 기준: 시나리오 v0.2 §3 (ISO/IEC DIS 25023:2014(E)), M4 ≥ 0.95 채택", "",
         "## 측정치 (ISO/IEC 25023)", "", "| 측정 | 25023 | X | A | B |", "|---|---|---|---|---|"]
    for k in ("M1", "M2", "M3", "M4", "M5"):
        m = ms.get(k) or {}
        a = next((f"{kk}={vv}" for kk, vv in m.items() if kk.startswith("A_")), "")
        b = next((f"{kk}={vv}" for kk, vv in m.items() if kk.startswith("B_")), "")
        L.append(f"| {k} | {iso[k]} | {m.get('X') if m.get('X') is not None else 'N/A'} | {a} | {b} |")
    L += ["", "## 판정 규칙", "", "| 규칙 | 결과 |", "|---|---|"] + [f"| {k} | {'PASS' if v else 'FAIL'} |" for k, v in (res.get("rules") or {}).items()]
    L += ["", "## 단계별 결과", "",
          f"- T0 baseline: Ship-ODMS reachable={((t0.get('ship_odms') or {}).get('reachable'))}, 후보집합 {((t0.get('candidate_inventory') or {}).get('version'))}({((t0.get('candidate_inventory') or {}).get('element_count'))})",
          f"- T2 IDS 전달: {t2.get('verdict')} {('— ' + str(t2.get('reason') or t2.get('note') or '')) if t2.get('verdict') != 'PASS' else ''}".rstrip(),
          f"- T3~T5 에이전트: 이벤트 {ag.get('events')}건, 증적 무결성 {'OK' if ag.get('all_integrity_ok') else 'NG'}, HTTP 오류 {len(ag.get('http_errors') or [])}건",
          f"- T6 Ship-ODMS 전송: {json.dumps({k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in deliv.items() if k not in ('errors', 'base')}, ensure_ascii=False)}, 오류 {len(deliv.get('errors') or [])}건 (UI http://localhost:3030)",
          f"- T7 정합성: 대조 {ms.get('checks')}건 중 불일치 {(ms.get('M4') or {}).get('A_mismatch')}건, 표준모델 대상 없음 요소 {len(ms.get('no_target_elements') or [])}개",
          f"- T8 재현성(직전 run {res.get('prev_run')}): {json.dumps(res.get('reproducibility_vs_prev'), ensure_ascii=False)}", "",
          "## 이벤트별 에이전트 결과", "", "| # | correlation_id | event | HTTP | status | fields | unmapped | LLM 호출 | PASS/WARN/FAIL | 무결성 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(ag.get("runs") or []):
        v = r.get("validation") or {}
        L.append(f"| {i} | {r['cid']} | {r.get('event_key')} | {r.get('http_status', '')} | {r.get('status')} | {r.get('fields')} | {r.get('unmapped')} | {r.get('llm_invocations')} | {v.get('PASS')}/{v.get('WARNING')}/{v.get('FAIL')} | {'OK' if r.get('integrity_ok') else 'NG'} |")
    mm = ms.get("mismatches") or []
    if mm:
        L += ["", "## M4 불일치 목록 (G-5: Ship-ODMS 정수형 절삭 등)", "", "| cid | IMO | target | source | stored |", "|---|---|---|---|---|"]
        L += [f"| {x.get('cid')} | {x.get('imo')} | {x.get('target')} | {x.get('source')} | {x.get('stored')} |" for x in mm[:50]]
    if t2.get("verdict") == "DIFFERENT":
        art = run / "T2-received-artifact.json"
        L += ["", "## T2 수신 아티팩트 (원본과 다름 — F-22 Provider 스냅샷 변경)", "", f"- 수신 {t2.get('received_bytes')} B sha256 {t2.get('received_sha256')} / 원본 sha256 {t2.get('source_sha256')}",
              "```", art.read_text("utf-8", errors="replace")[:600] if art.is_file() else "(없음)", "```"]
    L += ["", "## 증적 파일 (sha256)", ""]
    for f in ("T0-baseline.json", "T2-ids-transfer.json", "T3-T5-agent.json", "shipodms/shipodms-delivery.json", "shipodms/consistency-report.json", "result.json"):
        if (run / f).is_file():
            L.append(f"- `{f}` {hashlib.sha256((run / f).read_bytes()).hexdigest()}")
    L += ["", f"증적 디렉터리: `{run}` (덮어쓰기 금지, run 번호 증가) — 생성 {datetime.now(UTC).isoformat()}", ""]
    return "\n".join(L)


@app.get("/runs/{run_id}/report", response_class=HTMLResponse)
def report_html(run_id: str) -> str:
    run = run_dir(run_id)
    md = (run / "REPORT.md").read_text("utf-8") if (run / "REPORT.md").is_file() else report_md(run)
    verdict = ((rjson(run / "result.json") or {}).get("verdict") or "")
    color = "#1a7f37" if verdict.startswith("PASS") else ("#9a6700" if verdict == "PARTIAL" else "#cf222e")
    # ponytail: 마크다운 렌더러 없이 <pre> 로 보여준다 — 평가단 열람에는 충분, 필요 시 marked.js 추가.
    return (f"<!doctype html><meta charset='utf-8'><title>S-1-1 {run_id}</title>"
            f"<body style='font-family:ui-monospace,Consolas,monospace;max-width:1100px;margin:24px auto;padding:0 16px'>"
            f"<h2 style='color:{color}'>{html.escape(run_id)} — {html.escape(verdict)}</h2>"
            f"<p><a href='/runs'>run 목록(JSON)</a> · <a href='/runs/{run_id}'>파일 목록(JSON)</a> · <a href='http://localhost:3030' target='_blank'>Ship-ODMS UI</a> · <a href='http://localhost:5678' target='_blank'>n8n</a></p>"
            f"<pre style='white-space:pre-wrap;background:#f6f8fa;padding:16px;border-radius:8px'>{html.escape(md)}</pre></body>")
