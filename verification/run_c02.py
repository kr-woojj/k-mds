"""C02 순차 시뮬레이션 러너 — GHG AI Agent 파이프라인(kr-ghg-ai-agent)로 로컬 Step 0/1/4~13 을 실행하고
EVIDENCE_DIR/C02/run_NN/ 에 증적을 남긴다. 덮어쓰기 금지(run 번호 증가). 판정은 pass_criteria R1~R5 계산으로만 한다.

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
AGENT = HERE.parent.parent / "kr-ghg-ai-agent"
CASES = HERE / "verification_cases.json"
EVID = HERE / "evidence" / "C02"
UV = ["uv", "run", "--project", str(AGENT)]

# fixture → 기대 (README §5, §16, §19; UserManual §10). 정상 fixture 는 error 없음 + PROVISIONAL 변환.
EXPECT = {
    "noon_report_valid.json": {"ok": True},
    "vessel_performance_valid.json": {"ok": True},
    "event_departure.json": {"ok": True},
    "event_arrival.json": {"ok": True},
    "event_anchoring.json": {"ok": True},
    "noon_report_ambiguous.json": {"ok": False, "status": "REVIEW_REQUIRED"},
    "vessel_performance_negative.json": {"ok": False, "error": "IMO_ID_NOT_FOUND"},
    "event_bunkering.json": {"ok": False, "status": "REVIEW_REQUIRED"},
}


def prereqs() -> list[tuple[str, bool, str]]:
    xlsx = AGENT.parent / "k-mds" / "data" / "raw" / "FAL50" / "IMO Compendium.xlsx"
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


def judge(agent_evidence: Path) -> dict:
    """R2~R4 계산: manifest/summary 만 읽는다. 기록된 텍스트('PASS' 등)를 판정으로 채택하지 않는다."""
    per: dict[str, dict] = {}
    for fixture, exp in EXPECT.items():
        runs = [m for m in agent_evidence.glob("*/manifest.json") if _fixture_of(m) == fixture]
        if not runs:
            per[fixture] = {"verdict": "NOT_TESTED", "why": "manifest 없음"}
            continue
        m = json.loads(runs[0].read_text("utf-8"))
        d = runs[0].parent
        status, err = m.get("final_status"), _error_of(d)
        mapped = (d / "mapping-result.json").is_file()
        if exp["ok"]:
            ok = err is None and mapped and (d / "kr-gears-output.json").is_file() \
                and m.get("kr_gears_contract_status") == "PROVISIONAL" and status == "REVIEW_REQUIRED"
        else:
            ok = mapped and (err or "").startswith(exp.get("error", "")) and status == exp.get("status", status) \
                and not (err or "").startswith("GOVERNANCE_")
        per[fixture] = {"verdict": "PASS" if ok else "FAIL", "status": status, "error": err, "mapped": mapped}
    n_pass = sum(v["verdict"] == "PASS" for v in per.values())
    overall = "PASS" if n_pass == len(EXPECT) else ("FAIL" if n_pass == 0 else "PARTIAL")
    return {"overall": overall, "fixtures": per}


def _fixture_of(manifest: Path) -> str | None:
    raw = manifest.parent / "raw-input.json"
    if not raw.is_file():
        return None
    cid = json.loads(raw.read_text("utf-8")).get("correlation_id", "")
    # fixture 의 correlation_id 로 역참조
    for f in (AGENT / "tests" / "fixtures").glob("*.json"):
        if json.loads(f.read_text("utf-8")).get("correlation_id") == cid:
            return f.name
    return None


def _error_of(run_dir: Path) -> str | None:
    s = (run_dir / "summary.md").read_text("utf-8") if (run_dir / "summary.md").is_file() else ""
    for line in s.splitlines():
        if line.startswith("- error:"):
            v = line.split(":", 1)[1].strip()
            return None if v in ("", "-", "None", "null") else v
    return None


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
        print("→ 전제 충족. --run 으로 실행 가능. 계획: step0 baseline → step1 pytest/ruff/mypy → mock E2E(8 fixture) → judge R2~R4 → result.json")
        return 0

    run = next_run_dir()
    (run / "run-info.json").write_text(json.dumps({
        "started_at": datetime.now(UTC).isoformat(), "agent_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=AGENT, capture_output=True, text=True).stdout.strip(),
        "agent_dirty": subprocess.run(["git", "status", "--short"], cwd=AGENT, capture_output=True, text=True).stdout != "",
        "python": sys.version, "llm": "mock", "skill": "real", "mcp": "off", "kr_gears_delivery": "mock"}, indent=2), "utf-8")
    r1 = [sh(UV + ["pytest", "-q", "-rs"], run / "step1-pytest.txt"),
          sh(UV + ["ruff", "check", "src", "tools", "tests"], run / "step1-ruff.txt"),
          sh(UV + ["mypy", "src"], run / "step1-mypy.txt")]
    ev = run / "agent-evidence"
    sh(UV + ["python", "tools/run_mock_e2e.py", "--evidence-dir", str(ev)], run / "step4-13-mock-e2e.txt")
    result = {"R1_step1_exit_codes": r1, "R1": all(c == 0 for c in r1), **judge(ev)}
    (run / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["overall"] == "PASS" and result["R1"] else 1


def selftest() -> int:
    """judge(): GOVERNANCE_ 차단 run 은 PASS 가 아니어야 하고, 정상 run 은 PASS 여야 한다."""
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        fx = json.loads((AGENT / "tests" / "fixtures" / "noon_report_valid.json").read_text("utf-8"))
        blocked = root / "blocked"; blocked.mkdir()
        (blocked / "raw-input.json").write_text(json.dumps(fx), "utf-8")
        (blocked / "manifest.json").write_text(json.dumps({"final_status": "REVIEW_REQUIRED", "kr_gears_contract_status": "NOT_TRANSFORMED"}), "utf-8")
        (blocked / "summary.md").write_text("- final_status: REVIEW_REQUIRED\n- error: GOVERNANCE_CANDIDATE_MAPPING_BLOCKED\n", "utf-8")
        assert judge(root)["fixtures"]["noon_report_valid.json"]["verdict"] == "FAIL"
        for f in ("mapping-result.json", "kr-gears-output.json"):
            (blocked / f).write_text("{}", "utf-8")
        (blocked / "manifest.json").write_text(json.dumps({"final_status": "REVIEW_REQUIRED", "kr_gears_contract_status": "PROVISIONAL"}), "utf-8")
        (blocked / "summary.md").write_text("- final_status: REVIEW_REQUIRED\n- error: -\n", "utf-8")
        assert judge(root)["fixtures"]["noon_report_valid.json"]["verdict"] == "PASS"
        assert judge(root)["overall"] == "PARTIAL"  # 나머지 7 fixture 는 NOT_TESTED
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
