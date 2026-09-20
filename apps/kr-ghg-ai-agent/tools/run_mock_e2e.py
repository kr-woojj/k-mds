"""Mock E2E 실행기 — 재현 가능한 Evidence 패키지 생성.

integration matrix: LLM=mock, Skill=real(validator), MCP=off, delivery=mock.

사용:
  uv run python tools/run_mock_e2e.py [--evidence-dir DIR]

동일 correlation_id Evidence 가 이미 있으면 건너뛴다 (덮어쓰기 금지).
종료 코드: 0=전체 기대 상태 일치, 1=불일치 존재.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ghg_agent.agents.orchestrator import DuplicateRunError, build_pipeline  # noqa: E402
from ghg_agent.config import load_settings  # noqa: E402
from ghg_agent.evidence import verify_evidence  # noqa: E402

FIXTURES = PROJECT_ROOT / "tests" / "fixtures"

#: (fixture, 기대 최종 상태) — PROVISIONAL KR GEARs 계약 때문에 정상 흐름도
#: DELIVERED 가 아니라 REVIEW_REQUIRED 로 끝난다 (성공 위장 금지).
SCENARIOS = [
    ("vessel_performance_valid.json", "REVIEW_REQUIRED"),
    ("noon_report_valid.json", "REVIEW_REQUIRED"),
    ("event_departure.json", "REVIEW_REQUIRED"),
    ("event_bunkering.json", "REVIEW_REQUIRED"),
    ("event_anchoring.json", "REVIEW_REQUIRED"),
    ("event_arrival.json", "REVIEW_REQUIRED"),
    ("noon_report_ambiguous.json", "REVIEW_REQUIRED"),
    ("vessel_performance_negative.json", "REVIEW_REQUIRED"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, default=None)
    args = parser.parse_args()

    settings = load_settings()
    if args.evidence_dir is not None:
        from dataclasses import replace

        settings = replace(settings, audit_log_dir=args.evidence_dir)

    pipeline = build_pipeline(settings)
    ok = True
    results = []
    for name, expected in SCENARIOS:
        raw = (FIXTURES / name).read_bytes()
        try:
            state = pipeline.run(raw, "application/json")
        except DuplicateRunError as error:
            print(f"skip fixture={name} reason=duplicate correlation_id={error.correlation_id}")
            continue
        integrity = verify_evidence(settings.audit_log_dir / state.correlation_id)
        match = state.status.value == expected and integrity["ok"]
        ok = ok and match
        results.append(
            {
                "fixture": name,
                "correlation_id": state.correlation_id,
                "final_status": state.status.value,
                "expected_status": expected,
                "status_match": state.status.value == expected,
                "evidence_integrity_ok": integrity["ok"],
                "error": state.error,
            }
        )
        print(
            f"fixture={name} correlation_id={state.correlation_id} "
            f"status={state.status.value} expected={expected} "
            f"integrity={'ok' if integrity['ok'] else 'MISMATCH'}"
        )

    report_path = PROJECT_ROOT / "reports" / "mock-e2e-results.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({"ok": ok, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"overall={'PASS' if ok else 'FAIL'} report={report_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
