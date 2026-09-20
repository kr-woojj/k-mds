"""C02 순차 시뮬레이션 러너 — GHG AI Agent 파이프라인(kr-ghg-ai-agent)로 로컬 Step 0/1/4~13 을 실행하고
EVIDENCE_DIR/C02/run_NN/ 에 증적을 남긴다. 덮어쓰기 금지(run 번호 증가). 판정은 pass_criteria R1~R5 계산으로만 한다.

judge v2 (2026-09-12): R3 의 기대 코드는 summary error 뿐 아니라 mapping-result warnings / validation codes 에서도 찾는다
(run_01 에서 IMO_ID_NOT_FOUND 가 warnings 에만 기록되어 판정기 v1 이 FAIL 로 오판). R2 의 "error 없음" 은 확정 문구 그대로
유지하되, 에이전트가 정상 흐름에 기록하는 KR_GEARS_CONTRACT_PROVISIONAL 은 별도 필드 r2_error_is_provisional_marker 로 노출한다.

사용:
  python run_c02.py --dry-run     전제(P1~P3)·기준 확정 여부 점검, 실행 계획 출력. 실행 안 함.
  python run_c02.py --run         전제 충족 + pass_criteria.confirmed=true 일 때만 실행.
  python run_c02.py --selftest    판정 로직 자체 점검.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent / "apps" / "kr-ghg-ai-agent"
CASES = HERE / "verification_cases.json"
EVID = HERE / "evidence" / "C02"
UV = ["uv", "run", "--project", str(AGENT)]
JUDGE_VERSION = "v2"

# fixture → 기대 (README §5, §16, §19; UserManual §10). 정상 fixture 는 매핑 완료 + PROVISIONAL 변환 + mock delivery.
# code: summary error / mapping warnings / validation codes 어디든 등장해야 하는 코드(접두 일치).
EXPECT = {
    "noon_report_valid.json": {"ok": True},
    "vessel_performance_valid.json": {"ok": True},
    "event_departure.json": {"ok": True},
    "event_arrival.json": {"ok": True},
    "event_anchoring.json": {"ok": True},
    "noon_report_ambiguous.json": {"ok": False, "status": "REVIEW_REQUIRED", "code": "COMPETING_CANDIDATES", "transformed": False},
    "vessel_performance_negative.json": {"ok": False, "status": "REVIEW_REQUIRED", "code": "IMO_ID_NOT_FOUND", "transformed": False},
    "event_bunkering.json": {"ok": False, "status": "REVIEW_REQUIRED", "code": "CODE_VALUE_INVALID", "transformed": False},
    "noon_report_mandatory_missing.json": {"ok": False, "status": "REVIEW_REQUIRED", "transformed": False},  # R3 4항: 변환 차단
}
EXTRA_FIXTURES = ["noon_report_mandatory_missing.json"]  # tools/run_mock_e2e.py 8종에 없는 fixture — 직접 파이프라인 투입


def prereqs() -> list[tuple[str, bool, str]]:
    xlsx = HERE.parent / "data" / "raw" / "FAL50" / "IMO Compendium.xlsx"
    confirmed = False
    try:
        c02 = next(c for c in json.loads(CASES.read_text("utf-8"))["cases"] if c["case_id"] == "C02")
        confirmed = bool(c02["pass_criteria"]["confirmed"])
    except (OSError, KeyError, StopIteration):
        pass
    return [
        ("P1 validator repo", (AGENT.parent / "imo-compendium-mapping-validator").is_dir(), str(AGENT.parent / "imo-compendium-mapping-validator")),
        ("P2 FAL50 xlsx", xlsx.is_file(), str(xlsx)),
        ("P3 registry db", (AGENT / "var" / "registry.sqlite3").is_file(), "uv run python tools/prepare_registry.py"),
        ("P3 candidate inventory", (AGENT / "var" / "candidate-inventory.json").is_file(), "uv run python tools/build_candidate_inventory.py"),
        ("pass_criteria.confirmed", confirmed, str(CASES)),
    ]


def next_run_dir() -> Path:
    EVID.mkdir(parents=True, exist_ok=True)
    n = 1 + max((int(p.name[4:]) for p in EVID.glob("run_[0-9][0-9]")), default=0)
    d = EVID / f"run_{n:02d}"
    d.mkdir()  # 존재하면 FileExistsError — 덮어쓰기 금지
    return d


def sh(cmd: list[str], out: Path) -> int:
    r = subprocess.run(cmd, cwd=AGENT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out.write_text(f"$ {' '.join(cmd)}\n{r.stdout}\n[stderr]\n{r.stderr}\nexit={r.returncode}\n", "utf-8")
    return r.returncode


def _load(p: Path):
    try:
        return json.loads(p.read_text("utf-8"))
    except (OSError, ValueError):
        return None


def _codes(run_dir: Path) -> set[str]:
    """summary error + mapping warnings + validation codes 에 등장한 코드 토큰."""
    out: set[str] = set()
    err = _error_of(run_dir)
    if err:
        out.add(err.split(";")[0].split(":")[0].strip())
    mr = _load(run_dir / "mapping-result.json") or {}
    for f in mr.get("fields", []):
        for w in f.get("warnings", []) or []:
            out.add(str(w).split(":")[0].strip())
    vr = _load(run_dir / "validation-result.json") or {}
    for it in vr.get("items", []):
        if it.get("code"):
            out.add(str(it["code"]))
    return out


def judge(agent_evidence: Path) -> dict:
    """R2~R4 계산: manifest/summary/mapping/validation 만 읽는다. 기록된 텍스트('PASS' 등)를 판정으로 채택하지 않는다."""
    per: dict[str, dict] = {}
    for fixture, exp in EXPECT.items():
        runs = [m for m in agent_evidence.glob("*/manifest.json") if _fixture_of(m) == fixture]
        if not runs:
            per[fixture] = {"verdict": "NOT_TESTED", "why": "manifest 없음"}
            continue
        m = _load(runs[0]) or {}
        d = runs[0].parent
        status, err = m.get("final_status"), _error_of(d)
        mapped = (d / "mapping-result.json").is_file()
        mr = _load(d / "mapping-result.json") or {}
        metrics = mr.get("metrics", {})
        codes = _codes(d)
        transformed = (d / "kr-gears-output.json").is_file()
        rec = {"status": status, "error": err, "mapped": mapped, "codes": sorted(codes), "llm_invocations": metrics.get("llm_invocations"),
               "unmapped": metrics.get("unmapped"), "transformed": transformed, "contract": m.get("kr_gears_contract_status")}
        if exp["ok"]:
            core = mapped and metrics.get("unmapped") == 0 and metrics.get("llm_invocations") == 0 and "IMO_ID_NOT_FOUND" not in codes \
                and transformed and m.get("kr_gears_contract_status") == "PROVISIONAL" and status == "REVIEW_REQUIRED" \
                and not (err or "").startswith("GOVERNANCE_")
            rec["r2_error_is_provisional_marker"] = err == "KR_GEARS_CONTRACT_PROVISIONAL"
            ok = core and err is None  # R2 확정 문구 "error 코드 없음" 그대로
            rec["verdict_if_provisional_marker_allowed"] = "PASS" if core and (err is None or rec["r2_error_is_provisional_marker"]) else "FAIL"
        else:
            ok = mapped and status == exp.get("status", status) and (exp.get("code") in codes if exp.get("code") else True) \
                and transformed == exp.get("transformed", transformed) and not (err or "").startswith("GOVERNANCE_")
        rec["verdict"] = "PASS" if ok else "FAIL"
        per[fixture] = rec
    n_pass = sum(v["verdict"] == "PASS" for v in per.values())
    overall = "PASS" if n_pass == len(EXPECT) else ("FAIL" if n_pass == 0 else "PARTIAL")
    return {"judge_version": JUDGE_VERSION, "overall": overall, "fixtures": per}


def _fixture_of(manifest: Path) -> str | None:
    raw = manifest.parent / "raw-input.json"
    if not raw.is_file():
        return None
    cid = (_load(raw) or {}).get("correlation_id", "")
    for f in (AGENT / "tests" / "fixtures").glob("*.json"):
        if (_load(f) or {}).get("correlation_id") == cid:
            return f.name
    return None


def _error_of(run_dir: Path) -> str | None:
    s = (run_dir / "summary.md").read_text("utf-8") if (run_dir / "summary.md").is_file() else ""
    for line in s.splitlines():
        if line.startswith("- error:"):
            v = line.split(":", 1)[1].strip()
            return None if v in ("", "-", "None", "null") else v
    return None


def run_extra_fixtures(evidence_dir: Path, out: Path) -> int:
    code = f"""
import sys, json
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, r"{AGENT / 'src'}")
from ghg_agent.config import load_settings
from ghg_agent.agents.orchestrator import build_pipeline, DuplicateRunError
s = replace(load_settings(), audit_log_dir=Path(r"{evidence_dir}"))
p = build_pipeline(s)
for name in {EXTRA_FIXTURES!r}:
    raw = (Path(r"{AGENT / 'tests' / 'fixtures'}") / name).read_bytes()
    try:
        st = p.run(raw, "application/json"); print(f"fixture={{name}} correlation_id={{st.correlation_id}} status={{st.status.value}} error={{st.error}}")
    except DuplicateRunError as e:
        print(f"skip fixture={{name}} duplicate {{e.correlation_id}}")
"""
    return sh(UV + ["python", "-c", code], out)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 콘솔 cp949 깨짐 방지
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    checks = prereqs()
    for name, ok, hint in checks:
        print(f"[{'OK' if ok else 'MISSING'}] {name}  ({hint})")
    if not all(ok for _, ok, _ in checks):
        print("→ 전제 미충족. 실행하지 않음 (exit 2).")
        return 2
    if a.dry_run:
        print("→ 전제 충족. --run 으로 실행 가능. 계획: step0 baseline → step1 pytest/ruff/mypy → mock E2E(8 fixture) + extra(1) → judge R2~R4 → result.json")
        return 0

    run = next_run_dir()
    (run / "run-info.json").write_text(json.dumps({
        "started_at": datetime.now(UTC).isoformat(), "judge_version": JUDGE_VERSION,
        "agent_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=AGENT, capture_output=True, text=True).stdout.strip(),
        "agent_dirty": subprocess.run(["git", "status", "--short"], cwd=AGENT, capture_output=True, text=True).stdout != "",
        "python": sys.version, "llm": "mock", "skill": "real", "mcp": "off", "kr_gears_delivery": "mock"}, indent=2), "utf-8")
    r1 = [sh(UV + ["pytest", "-q", "-rs"], run / "step1-pytest.txt"),
          sh(UV + ["ruff", "check", "src", "tools", "tests"], run / "step1-ruff.txt"),
          sh(UV + ["mypy", "src"], run / "step1-mypy.txt")]
    ev = run / "agent-evidence"
    sh(UV + ["python", "tools/run_mock_e2e.py", "--evidence-dir", str(ev)], run / "step4-13-mock-e2e.txt")
    run_extra_fixtures(ev, run / "step4-13-extra-fixtures.txt")
    result = {"R1_step1_exit_codes": r1, "R1": all(c == 0 for c in r1), **judge(ev)}
    (run / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["overall"] == "PASS" and result["R1"] else 1


def selftest() -> int:
    """judge(): GOVERNANCE_ 차단 run 은 PASS 가 아니어야 하고, 정상 run 은 PROVISIONAL 마커 허용 시 PASS, 확정 문구로는 FAIL 이어야 한다."""
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        fx = _load(AGENT / "tests" / "fixtures" / "noon_report_valid.json")
        d = root / "r1"; d.mkdir()
        (d / "raw-input.json").write_text(json.dumps(fx), "utf-8")
        (d / "manifest.json").write_text(json.dumps({"final_status": "REVIEW_REQUIRED", "kr_gears_contract_status": "NOT_TRANSFORMED"}), "utf-8")
        (d / "summary.md").write_text("- final_status: REVIEW_REQUIRED\n- error: GOVERNANCE_CANDIDATE_MAPPING_BLOCKED\n", "utf-8")
        assert judge(root)["fixtures"]["noon_report_valid.json"]["verdict"] == "FAIL"
        (d / "mapping-result.json").write_text(json.dumps({"fields": [], "metrics": {"unmapped": 0, "llm_invocations": 0}}), "utf-8")
        (d / "kr-gears-output.json").write_text("{}", "utf-8")
        (d / "manifest.json").write_text(json.dumps({"final_status": "REVIEW_REQUIRED", "kr_gears_contract_status": "PROVISIONAL"}), "utf-8")
        (d / "summary.md").write_text("- final_status: REVIEW_REQUIRED\n- error: KR_GEARS_CONTRACT_PROVISIONAL\n", "utf-8")
        r = judge(root)["fixtures"]["noon_report_valid.json"]
        assert r["verdict"] == "FAIL" and r["verdict_if_provisional_marker_allowed"] == "PASS" and r["r2_error_is_provisional_marker"]
        (d / "summary.md").write_text("- final_status: REVIEW_REQUIRED\n- error: -\n", "utf-8")
        assert judge(root)["fixtures"]["noon_report_valid.json"]["verdict"] == "PASS"
        # R3: IMO_ID_NOT_FOUND 가 warnings 에만 있어도 인정
        neg = _load(AGENT / "tests" / "fixtures" / "vessel_performance_negative.json")
        d2 = root / "r2"; d2.mkdir()
        (d2 / "raw-input.json").write_text(json.dumps(neg), "utf-8")
        (d2 / "manifest.json").write_text(json.dumps({"final_status": "REVIEW_REQUIRED", "kr_gears_contract_status": "NOT_TRANSFORMED"}), "utf-8")
        (d2 / "summary.md").write_text("- final_status: REVIEW_REQUIRED\n- error: VALIDATION_FAIL; unmapped=2\n", "utf-8")
        (d2 / "mapping-result.json").write_text(json.dumps({"fields": [{"warnings": ["IMO_ID_NOT_FOUND: IMO9999"]}], "metrics": {}}), "utf-8")
        assert judge(root)["fixtures"]["vessel_performance_negative.json"]["verdict"] == "PASS"
        assert judge(root)["overall"] == "PARTIAL"
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
