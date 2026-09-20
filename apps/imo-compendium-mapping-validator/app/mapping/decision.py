"""최종 판정 (파이프라인 5단계: decide).

규칙:
- 문맥이 부족하면 추론하지 않고 MISSING_CONTEXT를 반환한다.
- 거절되지 않은 후보 중 1위가 임계값을 넘고, 2위와의 final_score 차이가
  min_gap(기본 0.05) 이상일 때만 자동 승인(MATCHED)한다.
- exact 채널(정확 IMO Code·정규화 이름·별칭)은 결정론 exact match로서
  임계값 없이 승인 가능하지만, gap 규칙과 hard conflict 검증은 그대로
  적용된다.
- 복수의 공식 후보가 남으면 후보 목록과 구성요소·문맥 차이를 설명한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.mapping.normalizer import NormalizedField
from app.mapping.ranker import SCORE_COMPONENTS, ScoredCandidate

STATUS_MATCHED = "MATCHED"
STATUS_REVIEW_REQUIRED = "REVIEW_REQUIRED"
STATUS_NO_MATCH = "NO_MATCH"
STATUS_MISSING_CONTEXT = "MISSING_CONTEXT"

_COMPONENT_DIFF_THRESHOLD = 0.1


@dataclass(frozen=True)
class DecisionThresholds:
    matched: float = 0.90
    review: float = 0.40
    min_gap: float = 0.05


@dataclass
class FieldDecision:
    field_id: str
    compendium_version: str
    status: str
    missing_context: bool
    selected_imo_data_number: str | None
    candidates: list[dict[str, object]]
    comparisons: list[str]
    reasons: list[str]
    thresholds: DecisionThresholds
    #: LLM 재순위화 경계 표시 (표시 순서에만 영향, 판정 불변 — REQ-014)
    reranked_by_llm: bool = False
    rerank_failed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "fieldId": self.field_id,
            "compendiumVersion": self.compendium_version,
            "status": self.status,
            "missing_context": self.missing_context,
            "selectedImoDataNumber": self.selected_imo_data_number,
            "candidates": self.candidates,
            "comparisons": self.comparisons,
            "reasons": self.reasons,
            "rerankedByLlm": self.reranked_by_llm,
            "rerankFailed": self.rerank_failed,
            "thresholds": {
                "matched": self.thresholds.matched,
                "review": self.thresholds.review,
                "minGap": self.thresholds.min_gap,
            },
        }


def _compare_pair(top: ScoredCandidate, other: ScoredCandidate) -> str:
    """두 공식 후보의 차이를 결정론적으로 요약한다."""
    differences: list[str] = []
    for component in SCORE_COMPONENTS:
        left = top.components.get(component)
        right = other.components.get(component)
        if left is None and right is None:
            continue
        left_value = left if left is not None else 0.0
        right_value = right if right is not None else 0.0
        if abs(left_value - right_value) >= _COMPONENT_DIFF_THRESHOLD:
            differences.append(f"{component} {left_value:.2f} vs {right_value:.2f}")

    top_datasets = sorted(
        {occ.dataset_key or "-" for occ in top.element.occurrences}
    )
    other_datasets = sorted(
        {occ.dataset_key or "-" for occ in other.element.occurrences}
    )
    if top_datasets != other_datasets:
        differences.append(
            f"dataset {','.join(top_datasets)} vs {','.join(other_datasets)}"
        )
    if (top.element.format_spec or "") != (other.element.format_spec or ""):
        differences.append(
            f"format {top.element.format_spec or '-'} vs {other.element.format_spec or '-'}"
        )
    if not differences:
        differences.append("구성요소 점수 차이가 기준 미만 — 문맥 검토 필요")
    return (
        f"{top.imo_data_number} vs {other.imo_data_number}: "
        + "; ".join(differences)
    )


def decide(
    normalized: NormalizedField,
    scored: list[ScoredCandidate],
    compendium_version: str,
    *,
    thresholds: DecisionThresholds | None = None,
) -> FieldDecision:
    limits = thresholds or DecisionThresholds()
    reasons: list[str] = []
    comparisons: list[str] = []

    def build(
        status: str,
        selected: str | None,
        *,
        missing: bool = False,
    ) -> FieldDecision:
        return FieldDecision(
            field_id=normalized.field_id,
            compendium_version=compendium_version,
            status=status,
            missing_context=missing,
            selected_imo_data_number=selected,
            candidates=[candidate.to_dict() for candidate in scored],
            comparisons=comparisons,
            reasons=reasons,
            thresholds=limits,
        )

    # 1) missing context — 추론하지 않는다
    if not normalized.has_context:
        reasons.append("MISSING_CONTEXT: 필드명이 generic이고 보조 신호가 없다")
        return build(STATUS_MISSING_CONTEXT, None, missing=True)

    eligible = [candidate for candidate in scored if not candidate.rejected]
    rejected = [candidate for candidate in scored if candidate.rejected]
    for candidate in rejected:
        codes = ",".join(sorted({issue["code"] for issue in candidate.issues}))
        reasons.append(f"REJECTED {candidate.imo_data_number}: {codes}")

    if not eligible:
        reasons.append(
            "NO_MATCH: 적격 후보 없음"
            + (" (hard conflict로 전 후보 거절)" if rejected else "")
        )
        return build(STATUS_NO_MATCH, None)

    top = eligible[0]
    runner_up = eligible[1] if len(eligible) > 1 else None
    gap = top.final_score - runner_up.final_score if runner_up else None

    # 복수 공식 후보 — 차이 설명 생성 (상위 3개까지)
    if len(eligible) > 1:
        for other in eligible[1:3]:
            comparisons.append(_compare_pair(top, other))

    gap_ok = gap is None or gap >= limits.min_gap
    score_ok = top.final_score >= limits.matched or top.exact_channel

    if score_ok and gap_ok:
        reasons.append(
            f"MATCHED: final={top.final_score:.6f}"
            + (" exact-channel" if top.exact_channel else "")
            + (f" gap={gap:.6f}" if gap is not None else " sole-candidate")
        )
        return build(STATUS_MATCHED, top.imo_data_number)

    if not gap_ok:
        reasons.append(
            f"TOP_GAP_BELOW_MINIMUM: gap={gap:.6f} < {limits.min_gap} — 자동 승인 금지"
        )
    if top.final_score >= limits.review or top.exact_channel:
        if top.final_score < limits.matched and not top.exact_channel:
            reasons.append(
                f"CONFIDENCE_BELOW_MATCHED: final={top.final_score:.6f}"
            )
        return build(STATUS_REVIEW_REQUIRED, None)

    reasons.append(f"NO_MATCH: final={top.final_score:.6f} < review 임계값")
    return build(STATUS_NO_MATCH, None)
