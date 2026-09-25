"""S-1-1 정식 러너 — GHG 의무보고 데이터 상호운용성 (vessellink → K-MDS IDS → GHG AI Agent → data-space Ship-ODMS) T0~T8.

증적: verification/evidence/C02/s11/run_NN/ (덮어쓰기 금지, 번호 증가). 판정은 consistency-report 의 측정치(M2·M3·M4)와 파일 존재로만 한다.
외부 K-MDS 단계(T2)는 apps/kr-ghg-ai-agent/.env 의 IDS_CONNECTOR_* 가 있을 때만 실행하고, 없으면 NOT_TESTED 로 기록한다(값은 기록하지 않음).

사용:
  uv run --project apps/kr-ghg-ai-agent --with pyyaml python verification/run_s11.py --dry-run
  uv run --project apps/kr-ghg-ai-agent --with pyyaml python verification/run_s11.py --run [--source <noon.json>] [--skip-ids] [--base http://localhost:8088]
판정 규칙(시나리오 v0.2 §3, 2026-09-26 확정): M4 ≥ 0.95 (채택 정합율), M3 = 1.0, M2 ≥ 0.95, Ship-ODMS HTTP 오류 0, 에이전트 evidence 무결성 ok,
  재실행(run n−1 존재 시) M2·M3·M4 동일.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AGENT = ROOT / "apps" / "kr-ghg-ai-agent"
VALIDATOR = ROOT / "apps" / "imo-compendium-mapping-validator"
EVID = HERE / "evidence" / "C02" / "s11"
DEFAULT_SOURCE = HERE / "evidence/C02/manual_S03/step-04/payloads/Noon_Report_API__e5e3be7e7a31.json"
UV = ["uv", "run", "--project", str(AGENT), "--with", "pyyaml", "python"]
sys.path.insert(0, str(AGENT / "src"))


def git(*a, cwd=ROOT):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True).stdout.strip()


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def next_run_dir() -> tuple[Path, Path | None]:
    EVID.mkdir(parents=True, exist_ok=True)
    runs = sorted(EVID.glob("run_[0-9][0-9]"))
    n = 1 + (int(runs[-1].name[4:]) if runs else 0)
    d = EVID / f"run_{n:02d}"; d.mkdir()
    return d, (runs[-1] if runs else None)


def t0_baseline(run: Path, source: Path, base: str) -> dict:
    import httpx
    from ghg_agent.config import load_settings
    from ghg_agent.governance.candidate_scope import load_candidate_inventory
    s = load_settings(); inv = load_candidate_inventory(s.candidate_inventory_path)
    cb = s.lab021_codebook_path
    try:
        odms = httpx.get(f"{base}/v3/api-docs", timeout=10).json().get("info", {})
        odms_ok = True
    except Exception as e:  # noqa: BLE001
        odms, odms_ok = {"error": str(e)[:100]}, False
    b = {"step": "T0", "executed_at": datetime.now(UTC).isoformat(), "python": platform.python_version(),
         "k_mds_commit": git("rev-parse", "HEAD"), "k_mds_dirty": git("status", "--short") != "",
         "agent_commit": git("rev-parse", "HEAD", cwd=AGENT) if (AGENT / ".git").exists() else "(k-mds 단일 저장소)",
         "validator_commit": git("rev-parse", "HEAD", cwd=VALIDATOR) if (VALIDATOR / ".git").exists() else "(k-mds 단일 저장소)",
         "fal50_xlsx_sha256": sha(ROOT / "data/raw/FAL50/IMO Compendium.xlsx"),
         "registry_db": str(s.registry_db_path), "candidate_inventory": {"version": inv.version, "element_count": inv.element_count, "sha256": inv.sha256, "load_status": inv.load_status},
         "lab021_codebook": {"path": str(cb), "sha256": sha(cb) if cb.is_file() else None},
         "source_payload": {"path": str(source), "sha256": sha(source), "bytes": source.stat().st_size},
         "ship_odms": {"base": base, "reachable": odms_ok, "info": odms},
         "llm": "mock", "skill": "real", "mcp": "off"}
    (run / "T0-baseline.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), "utf-8")
    return b


def t2_ids(run: Path, source: Path) -> dict:
    """K-MDS Consumer Connector 로 Noon Report Artifact 수신 → 원본 해시 비교. 자격증명 없으면 NOT_TESTED."""
    from dotenv import dotenv_values
    env = dotenv_values(AGENT / ".env")
    if not env.get("IDS_CONNECTOR_USER") or not env.get("IDS_CONNECTOR_PASSWORD"):
        r = {"step": "T2", "verdict": "NOT_TESTED", "reason": "IDS_CONNECTOR_* 자격증명 없음"}
    else:
        import httpx
        cons = "https://" + (env.get("IDS_CONNECTOR_BASE", "").split("//")[-1].rsplit(":", 1)[0]) + ":26414"
        aid = "f508740a-e585-45d7-a5a5-e5e3be7e7a31"  # Noon Report API artifact (Consumer, 9/12 계약)
        try:
            resp = httpx.get(f"{cons}/api/artifacts/{aid}/data", params={"download": "true"}, auth=(env["IDS_CONNECTOR_USER"], env["IDS_CONNECTOR_PASSWORD"]), verify=False, timeout=60)
            got = hashlib.sha256(resp.content).hexdigest()
            (run / "T2-received-artifact.json").write_bytes(resp.content)
            r = {"step": "T2", "http": resp.status_code, "received_sha256": got, "received_bytes": len(resp.content), "source_sha256": sha(source),
                 "identical_to_source": got == sha(source), "verdict": "PASS" if got == sha(source) else "DIFFERENT",
                 "note": "다르면 Provider 스냅샷이 바뀐 것(F-22 참조). 시험은 --source 본으로 계속 진행."}
        except Exception as e:  # noqa: BLE001
            r = {"step": "T2", "verdict": "ERROR", "error": type(e).__name__}
    (run / "T2-ids-transfer.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), "utf-8")
    return r


def t3_t5_agent(run: Path, source: Path) -> dict:
    from dataclasses import replace
    from ghg_agent.agents.orchestrator import build_pipeline
    from ghg_agent.config import load_settings
    from ghg_agent.evidence import verify_evidence
    ev = run / "agent-evidence"
    payload = json.loads(source.read_text("utf-8"))["data"]
    pipe = build_pipeline(replace(load_settings(), audit_log_dir=ev))
    rows = []
    for i, e in enumerate(sorted(payload["events"], key=lambda x: x["dateEventUtc"])):
        rec = {"correlation_id": f"LAB021-NOON-{payload['general'].get('imoNo')}-{i:03d}", "dataset_id": "LAB021/Noon Report API", **payload["general"], **e}
        st = pipe.run(json.dumps(rec, ensure_ascii=False).encode(), "application/json")
        d = ev / st.correlation_id
        mr = json.loads((d / "mapping-result.json").read_text("utf-8")) if (d / "mapping-result.json").is_file() else {}
        vr = json.loads((d / "validation-result.json").read_text("utf-8")) if (d / "validation-result.json").is_file() else {}
        rows.append({"cid": st.correlation_id, "event_key": e["eventKey"], "status": st.status.value, "error": st.error,
                     "fields": len(mr.get("fields", [])), "unmapped": mr.get("metrics", {}).get("unmapped"), "llm_invocations": mr.get("metrics", {}).get("llm_invocations"),
                     "validation": {k: sum(1 for x in vr.get("items", []) if x["verdict"] == k) for k in ("PASS", "WARNING", "FAIL", "NOT_APPLICABLE")},
                     "integrity_ok": verify_evidence(d)["ok"]})
    r = {"step": "T3-T5", "events": len(rows), "runs": rows, "all_integrity_ok": all(x["integrity_ok"] for x in rows),
         "note": "T3 은 Consumer Route 대신 러너가 이벤트 단위로 에이전트 파이프라인에 직접 투입(G-3 배치 envelope). 진해 현장 Route 검증은 W5."}
    (run / "T3-T5-agent.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), "utf-8")
    return r


def sh(cmd: list[str], out: Path) -> int:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out.write_text(f"$ {' '.join(cmd)}\n{r.stdout}\n[stderr]\n{r.stderr}\nexit={r.returncode}\n", "utf-8")
    return r.returncode


def judge(run: Path, prev: Path | None, t2: dict, agent: dict, w2_rc: int, w3_rc: int) -> dict:
    rep = json.loads((run / "shipodms" / "consistency-report.json").read_text("utf-8"))["measures"] if (run / "shipodms" / "consistency-report.json").is_file() else {}
    deliv = json.loads((run / "shipodms" / "shipodms-delivery.json").read_text("utf-8")) if (run / "shipodms" / "shipodms-delivery.json").is_file() else {}
    m = {k: (rep.get(k) or {}).get("X") for k in ("M2", "M3", "M4")}
    rules = {
        "R-M4 정합율 ≥ 0.95": m["M4"] is not None and m["M4"] >= 0.95,
        "R-M3 검증 정확성 = 1.0": m["M3"] == 1.0,
        "R-M2 매핑 완결성 ≥ 0.95": m["M2"] is not None and m["M2"] >= 0.95,
        "R-T6 Ship-ODMS HTTP 오류 0": w2_rc == 0 and not deliv.get("errors"),
        "R-T5 에이전트 evidence 무결성": agent.get("all_integrity_ok") is True,
        "R-T2 IDS 전달(수행 시)": t2.get("verdict") in ("PASS", "NOT_TESTED"),
    }
    repro = None
    if prev and (prev / "shipodms" / "consistency-report.json").is_file():
        pm = json.loads((prev / "shipodms" / "consistency-report.json").read_text("utf-8"))["measures"]
        repro = {k: (pm.get(k) or {}).get("X") == m[k] for k in ("M2", "M3", "M4")}
        rules["R-T8 재현성(직전 run 과 M2·M3·M4 동일)"] = all(repro.values())
    verdict = "PASS" if all(rules.values()) else ("FAIL" if not rules["R-M4 정합율 ≥ 0.95"] else "PARTIAL")
    if t2.get("verdict") == "NOT_TESTED" and verdict == "PASS":
        verdict = "PASS (T2 NOT_TESTED — 외부 IDS 단계는 별도 증적으로 보완)"
    res = {"verdict": verdict, "rules": rules, "measures": m, "mismatches": (rep.get("M4") or {}).get("A_mismatch") if rep else None,
           "no_target_elements": rep.get("no_target_elements"), "reproducibility_vs_prev": repro, "prev_run": prev.name if prev else None}
    (run / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), "utf-8")
    return res


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True); g.add_argument("--dry-run", action="store_true"); g.add_argument("--run", action="store_true")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE); ap.add_argument("--base", default="http://localhost:8088"); ap.add_argument("--skip-ids", action="store_true")
    a = ap.parse_args()
    checks = [("source payload", a.source.is_file()), ("registry", (AGENT / "var/registry.sqlite3").is_file()), ("candidate inventory", (AGENT / "var/candidate-inventory.json").is_file()),
              ("LAB021 codebook", (AGENT / "var/reference/lab021/noon-code-book.json").is_file())]
    try:
        import httpx; checks.append(("Ship-ODMS", httpx.get(f"{a.base}/api/ships", timeout=5).status_code == 200))
    except Exception:  # noqa: BLE001
        checks.append(("Ship-ODMS", False))
    for n, ok in checks: print(f"[{'OK' if ok else 'MISSING'}] {n}")
    if not all(ok for _, ok in checks):
        print("→ 전제 미충족 (exit 2)"); return 2
    if a.dry_run:
        print("→ --run 가능: T0 baseline → T2 IDS(옵션) → T3-T5 agent → T6 Ship-ODMS → T7 consistency → T8 judge"); return 0
    run, prev = next_run_dir(); print("run dir:", run)
    t0_baseline(run, a.source, a.base)
    t2 = {"step": "T2", "verdict": "NOT_TESTED", "reason": "--skip-ids"} if a.skip_ids else t2_ids(run, a.source)
    if a.skip_ids: (run / "T2-ids-transfer.json").write_text(json.dumps(t2, ensure_ascii=False), "utf-8")
    agent = t3_t5_agent(run, a.source)
    od = run / "shipodms"
    w2 = sh(UV + [str(HERE / "adapters/imo_to_shipodms.py"), str(run / "agent-evidence"), str(od), "--base", a.base], run / "T6-shipodms.txt")
    w3 = sh(UV + [str(HERE / "adapters/consistency_check.py"), str(run / "agent-evidence"), str(od), str(a.source), str(od), "--base", a.base], run / "T7-consistency.txt")
    res = judge(run, prev, t2, agent, w2, w3)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["verdict"].startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
