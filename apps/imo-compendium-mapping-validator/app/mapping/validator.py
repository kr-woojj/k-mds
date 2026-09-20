"""후보 검증 (파이프라인 4단계: validate).

- 타입 또는 단위 hard conflict가 있으면 semantic 점수가 아무리 높아도
  해당 후보를 거절한다 (rejected=True). 목록에는 사유와 함께 보존한다.
- deprecated/superseded Element는 자동 승인 대상이 될 수 없다.
- 방어적 Registry 게이트: 후보 번호가 패턴·Registry 인덱스와 불일치하면
  거절한다 (REQ-007 — 구조상 발생하지 않아야 하며, 발생 자체가 결함 신호다).
"""

from __future__ import annotations

from app.mapping.normalizer import NormalizedField
from app.mapping.ranker import ScoredCandidate, type_relation
from app.registry.validator import IMO_DATA_NUMBER_PATTERN

DEPRECATED_STATUSES = {"deprecated", "superseded"}


def _issue(code: str, severity: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def validate_candidate(
    normalized: NormalizedField, candidate: ScoredCandidate
) -> None:
    """후보에 issues/hard_conflicts/rejected를 채운다 (in-place, 결정론)."""
    element = candidate.element

    # 방어적 Registry 게이트
    if not IMO_DATA_NUMBER_PATTERN.match(candidate.imo_data_number):
        candidate.hard_conflicts.append("registry_gate")
        candidate.issues.append(
            _issue(
                "REGISTRY_GATE_VIOLATION",
                "ERROR",
                "IMO Data Number 패턴을 벗어난 후보는 반환될 수 없다",
            )
        )

    # 타입 hard conflict
    relation = type_relation(normalized.effective_type, element.expected_type)
    if relation == "conflict":
        candidate.hard_conflicts.append("datatype")
        candidate.issues.append(
            _issue(
                "DATATYPE_HARD_CONFLICT",
                "ERROR",
                "필드 타입과 Registry format 타입 범주가 충돌한다",
            )
        )

    # 단위 hard conflict
    if (
        normalized.canonical_unit is not None
        and element.unit_hints
        and normalized.canonical_unit not in element.unit_hints
    ):
        candidate.hard_conflicts.append("unit")
        candidate.issues.append(
            _issue(
                "UNIT_HARD_CONFLICT",
                "ERROR",
                "필드 단위가 Registry 정의 단위와 충돌한다",
            )
        )

    # 수명주기: deprecated Element는 승인 불가
    if element.status.lower() in DEPRECATED_STATUSES:
        candidate.hard_conflicts.append("lifecycle")
        candidate.issues.append(
            _issue(
                "ELEMENT_DEPRECATED",
                "ERROR",
                "deprecated/superseded Element는 자동 승인 대상이 아니다",
            )
        )

    # 형식 계열 불일치는 경고 (hard 아님 — 점수에 이미 반영됨)
    format_score = candidate.components.get("format_score")
    if format_score is not None and format_score <= 0.2:
        candidate.issues.append(
            _issue(
                "FORMAT_FAMILY_MISMATCH",
                "WARNING",
                "선언 형식과 Registry format 계열이 다르다",
            )
        )

    candidate.rejected = bool(candidate.hard_conflicts)


def validate_candidates(
    normalized: NormalizedField, candidates: list[ScoredCandidate]
) -> None:
    for candidate in candidates:
        validate_candidate(normalized, candidate)
