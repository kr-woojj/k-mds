"""LLM Re-ranker Boundary (REQ-014).

계약:
- Re-ranker는 **적격(비거절) 후보 id 집합 안에서의 순열**만 반환할 수 있다.
- 집합 밖 id·중복 id는 폐기되고, 누락 id는 결정론 순서로 뒤에 붙는다.
- 거절(hard conflict) 후보는 어떤 재순위로도 부활하지 않는다.
- MATCHED 판정은 재순위 이전의 결정론 규칙으로 이미 확정되며, 재순위는
  REVIEW_REQUIRED 후보 목록의 표시 순서에만 영향을 준다.
- Re-ranker 실패(예외·시간초과)는 결정론 결과로 안전하게 되돌아간다
  (fail-closed, REQ-016).
"""

from __future__ import annotations

from typing import Callable, Sequence

from app.mapping.decision import STATUS_REVIEW_REQUIRED, FieldDecision
from app.mapping.ranker import ScoredCandidate

#: 후보 요약 목록을 받아 후보 id 순열을 반환하는 호출 가능 객체.
#: (LLM 어댑터는 이 서명만 구현하면 된다 — 후보 밖 정보 접근 불가)
Reranker = Callable[[Sequence[dict[str, object]]], Sequence[str]]


def _candidate_summaries(eligible: list[ScoredCandidate]) -> list[dict[str, object]]:
    """Re-ranker에 전달되는 최소 요약 — Registry 전체 원문·샘플 값 미포함."""
    return [
        {
            "candidateId": candidate.imo_data_number,
            "name": candidate.element.name,
            "final_score": candidate.final_score,
            "channels": list(candidate.channels),
        }
        for candidate in eligible
    ]


def sanitize_ranking(
    ranking: Sequence[str], eligible_ids: list[str]
) -> list[str]:
    """집합 밖 id·중복 제거 후, 누락 id를 결정론 순서로 보충한다."""
    allowed = set(eligible_ids)
    cleaned: list[str] = []
    for item in ranking:
        candidate_id = str(item).strip().upper()
        if candidate_id in allowed and candidate_id not in cleaned:
            cleaned.append(candidate_id)
    for candidate_id in eligible_ids:
        if candidate_id not in cleaned:
            cleaned.append(candidate_id)
    return cleaned


def apply_reranker(
    decision: FieldDecision,
    scored: list[ScoredCandidate],
    reranker: Reranker | None,
) -> None:
    """REVIEW_REQUIRED 후보 목록의 표시 순서만 재정렬한다 (in-place)."""
    if reranker is None:
        return
    if decision.status != STATUS_REVIEW_REQUIRED:
        return  # MATCHED/NO_MATCH/MISSING_CONTEXT 판정은 재순위 대상이 아니다
    eligible = [candidate for candidate in scored if not candidate.rejected]
    if len(eligible) < 2:
        return
    eligible_ids = [candidate.imo_data_number for candidate in eligible]

    try:
        ranking = reranker(_candidate_summaries(eligible))
    except Exception:
        decision.rerank_failed = True
        return  # 결정론 순서 유지 (fail-closed)

    order = sanitize_ranking(list(ranking), eligible_ids)
    position = {candidate_id: index for index, candidate_id in enumerate(order)}

    eligible_dicts = [
        candidate for candidate in decision.candidates if not candidate["rejected"]
    ]
    rejected_dicts = [
        candidate for candidate in decision.candidates if candidate["rejected"]
    ]
    eligible_dicts.sort(
        key=lambda candidate: position[str(candidate["imoDataNumber"])]
    )
    decision.candidates = eligible_dicts + rejected_dicts
    decision.reranked_by_llm = True
