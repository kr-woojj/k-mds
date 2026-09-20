"""후보 점수화 (파이프라인 3단계: rank).

- 8개 구성요소 점수를 전부 보존한다. 총점(final_score)만 남기지 않는다.
- 신호가 없는 구성요소는 None으로 보존하고 final_score 가중치에서 제외한다
  (모르는 것을 0.5로 위장하지 않는다).
- 전 계산이 결정론적이며 6자리로 반올림한다 (REQ-030).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.mapping.normalizer import NormalizedField
from app.mapping.retriever import (
    IndexedElement,
    RetrievedCandidate,
    trigram_dice,
)

SCORE_COMPONENTS = (
    "name_score",
    "semantic_score",
    "datatype_score",
    "format_score",
    "unit_score",
    "context_score",
    "path_score",
)

WEIGHTS: dict[str, float] = {
    "name_score": 0.30,
    "semantic_score": 0.20,
    "datatype_score": 0.15,
    "format_score": 0.10,
    "unit_score": 0.10,
    "context_score": 0.075,
    "path_score": 0.075,
}

EXACT_CHANNELS = {"exact_imo_code", "normalized_name", "alias_dictionary"}

#: integer <-> number는 호환. 나머지 범주 조합은 hard conflict.
_COMPATIBLE_TYPES: set[frozenset[str]] = {
    frozenset({"integer", "number"}),
    frozenset({"date", "datetime"}),
}


@dataclass
class ScoredCandidate:
    imo_data_number: str
    element: IndexedElement
    channels: tuple[str, ...]
    components: dict[str, float | None]
    final_score: float
    exact_channel: bool
    #: validator가 채운다
    hard_conflicts: list[str] = field(default_factory=list)
    issues: list[dict[str, str]] = field(default_factory=list)
    rejected: bool = False

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "imoDataNumber": self.imo_data_number,
            "channels": sorted(self.channels),
            "final_score": self.final_score,
            "exactChannel": self.exact_channel,
            "hardConflicts": list(self.hard_conflicts),
            "issues": list(self.issues),
            "rejected": self.rejected,
            "registryRecordRef": {
                "recordType": "data_element",
                "recordId": self.imo_data_number,
                "status": self.element.status,
            },
        }
        payload.update(self.components)
        return payload


def _dice(tokens_a: set[str], tokens_b: set[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    return round(2 * len(tokens_a & tokens_b) / (len(tokens_a) + len(tokens_b)), 6)


def type_relation(field_type: str | None, element_type: str | None) -> str:
    """'match' | 'compatible' | 'conflict' | 'unknown'"""
    if field_type is None or element_type is None:
        return "unknown"
    if field_type == element_type:
        return "match"
    if frozenset({field_type, element_type}) in _COMPATIBLE_TYPES:
        return "compatible"
    return "conflict"


def _format_family(format_spec: str | None) -> str | None:
    if not format_spec:
        return None
    spec = format_spec.strip().lower()
    if spec.startswith("an"):
        return "alphanumeric"
    if spec.startswith("a"):
        return "alpha"
    if spec.startswith("n"):
        return "numeric"
    if "date" in spec:
        return "date"
    return "other"


def _score_name(normalized: NormalizedField, candidate: RetrievedCandidate) -> float:
    if candidate.channels & {"exact_imo_code", "alias_dictionary"}:
        return 1.0
    return _dice(set(normalized.tokens), set(candidate.element.name_tokens))


def _score_semantic(normalized: NormalizedField, element: IndexedElement) -> float | None:
    field_text = " ".join(
        (*normalized.tokens, *normalized.description_tokens)
    ).strip()
    if not field_text:
        return None
    return trigram_dice(field_text, element.search_text)


def _score_datatype(normalized: NormalizedField, element: IndexedElement) -> float | None:
    relation = type_relation(normalized.effective_type, element.expected_type)
    if relation == "unknown":
        return None
    if relation == "match":
        return 1.0
    if relation == "compatible":
        return 0.8
    return 0.0


def _score_format(normalized: NormalizedField, element: IndexedElement) -> float | None:
    if normalized.declared_format is None or element.format_spec is None:
        return None
    declared = normalized.declared_format.strip().lower()
    spec = element.format_spec.strip().lower()
    if declared == spec:
        return 1.0
    if _format_family(declared) == _format_family(spec):
        return 0.6
    return 0.2


def _score_unit(normalized: NormalizedField, element: IndexedElement) -> float | None:
    if normalized.canonical_unit is None or not element.unit_hints:
        return None
    return 1.0 if normalized.canonical_unit in element.unit_hints else 0.0


def _score_context(normalized: NormalizedField, element: IndexedElement) -> float | None:
    context_tokens = set(normalized.path_tokens) | set(normalized.description_tokens)
    if not context_tokens or not element.occurrences:
        return None
    best = 0.0
    for occurrence in element.occurrences:
        dataset_tokens = set(occurrence.dataset_tokens)
        if dataset_tokens:
            best = max(best, _dice(context_tokens, dataset_tokens))
    return round(best, 6)


def _score_path(normalized: NormalizedField, element: IndexedElement) -> float | None:
    if not normalized.path_tokens or not element.occurrences:
        return None
    best = 0.0
    for occurrence in element.occurrences:
        path_tokens = set(occurrence.path_tokens)
        if path_tokens:
            best = max(best, _dice(set(normalized.path_tokens), path_tokens))
    return round(best, 6)


def compose_final(components: dict[str, float | None]) -> float:
    """관측된 구성요소만으로 가중 평균한다 (가중치 재정규화)."""
    total_weight = 0.0
    total = 0.0
    for component, weight in WEIGHTS.items():
        value = components.get(component)
        if value is None:
            continue
        total_weight += weight
        total += weight * value
    if total_weight == 0.0:
        return 0.0
    return round(total / total_weight, 6)


def rank_candidates(
    normalized: NormalizedField, retrieved: list[RetrievedCandidate]
) -> list[ScoredCandidate]:
    scored: list[ScoredCandidate] = []
    for candidate in retrieved:
        element = candidate.element
        components: dict[str, float | None] = {
            "name_score": round(_score_name(normalized, candidate), 6),
            "semantic_score": _score_semantic(normalized, element),
            "datatype_score": _score_datatype(normalized, element),
            "format_score": _score_format(normalized, element),
            "unit_score": _score_unit(normalized, element),
            "context_score": _score_context(normalized, element),
            "path_score": _score_path(normalized, element),
        }
        scored.append(
            ScoredCandidate(
                imo_data_number=element.imo_data_number,
                element=element,
                channels=tuple(sorted(candidate.channels)),
                components=components,
                final_score=compose_final(components),
                exact_channel=bool(candidate.channels & EXACT_CHANNELS),
            )
        )
    scored.sort(key=lambda item: (-item.final_score, item.imo_data_number))
    return scored
