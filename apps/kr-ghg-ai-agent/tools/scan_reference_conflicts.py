"""DEFECT-4 진단 — FAL50 reference 의 format/code-list 불일치 스캔.

배경: 일부 coded 요소(예: IMO0654 Fuel type)는 원본 format 이 숫자(n..)인데
공식 code list 값은 alphanumeric(HFO, VLSFO...). 이 경우 유효한 코드값이
validator 의 DATATYPE_HARD_CONFLICT 로 FAIL 된다.

정책: 권위 validator/reference 를 약화시키지 않는다(C-3/C-5/C-6). 대신 상류
데이터 불일치를 결정론적으로 탐지해 reports/reference-conflicts.json 에 기록하고,
해당 요소 매핑은 REVIEW_REQUIRED(상류 reference 정정 필요)로 분류한다.

사용: uv run python tools/scan_reference_conflicts.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))

from ghg_agent.config import load_settings  # noqa: E402
from ghg_agent.reference.lookup import ReferenceLookup  # noqa: E402

#: 원본 format 이 '숫자 전용'임을 뜻하는 접두 (an.. 은 alphanumeric 이므로 제외)
_NUMERIC_FORMAT = re.compile(r"^n\.?\.?\d")


def is_numeric_only_format(fmt: str | None) -> bool:
    if not fmt:
        return False
    f = fmt.strip().lower()
    return f.startswith("n") and not f.startswith("an")


def value_is_numeric(code: str) -> bool:
    return bool(re.fullmatch(r"[0-9]+(\.[0-9]+)?", code.strip()))


def main() -> int:
    s = load_settings()
    ref = ReferenceLookup(
        registry_db_path=s.registry_db_path, version="FAL50",
        alias_config_path=s.alias_config_path, code_lists_path=s.code_lists_path,
    )
    ref.load()

    conflicts = []
    for number, el in sorted(ref._elements.items()):
        resolved = ref.code_list_for_element(el)
        if resolved is None:
            continue
        list_name, values = resolved
        if not is_numeric_only_format(el.format_spec):
            continue
        # 코드값 중 하나라도 비숫자면 numeric-format 과 충돌
        alnum = sorted(v for v in values if not value_is_numeric(v))
        if alnum:
            conflicts.append({
                "imo_data_number": number,
                "element_name": el.name,
                "format_spec": el.format_spec,
                "code_list": list_name,
                "code_value_count": len(values),
                "non_numeric_value_examples": alnum[:5],
                "classification": "REVIEW_REQUIRED",
                "root_cause": "UPSTREAM_REFERENCE_FORMAT_CODELIST_CONFLICT",
                "impact": "유효 코드값이 validator DATATYPE_HARD_CONFLICT 로 FAIL",
            })

    report = {
        "generated_at": "2026-08-24",
        "reference_model_version": "FAL50",
        "source_sha256": None,
        "policy": ("권위 validator/reference 를 약화시키지 않는다. 아래 요소들의 매핑은 "
                   "상류 reference 정정 전까지 REVIEW_REQUIRED 로 분류한다."),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "ghg_relevant": [c for c in conflicts if "fuel" in c["element_name"].lower()],
    }
    out = PROJECT / "reports" / "reference-conflicts.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"conflict_count={len(conflicts)} ghg_relevant={len(report['ghg_relevant'])}")
    for c in conflicts:
        print(f"  {c['imo_data_number']} {c['element_name']} format={c['format_spec']} "
              f"examples={c['non_numeric_value_examples']}")
    print(f"report={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
