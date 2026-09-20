"""Field Mapping Engine.

파이프라인: normalize -> retrieve -> rank -> validate -> decide

- 전 경로가 결정론적이다 (LLM 미사용, REQ-030). LLM 재순위화는 후속 모듈이
  후보 목록 '안에서만' 순서를 바꾸는 별도 boundary로 결합된다 (REQ-014).
- 후보는 Registry에 존재하는 record만 가능하며 (REQ-006, REQ-007),
  점수는 구성요소별로 전부 보존된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session, sessionmaker

from app.mapping.decision import DecisionThresholds, FieldDecision, decide
from app.mapping.normalizer import NormalizedField, normalize_field
from app.mapping.ranker import rank_candidates
from app.mapping.reranker import Reranker, apply_reranker
from app.mapping.retriever import RegistryIndex, build_index, retrieve_candidates
from app.mapping.validator import validate_candidates

__all__ = [
    "DecisionThresholds",
    "FieldDecision",
    "MappingEngine",
    "NormalizedField",
    "normalize_field",
]


@dataclass
class MappingEngine:
    """단일 Compendium version에 대한 매핑 파이프라인."""

    session_factory: sessionmaker[Session]
    version: str
    alias_dictionary: dict[str, str] = field(default_factory=dict)
    thresholds: DecisionThresholds = field(default_factory=DecisionThresholds)
    #: 선택적 LLM Re-ranker — REVIEW_REQUIRED 표시 순서에만 영향 (REQ-014)
    reranker: Reranker | None = None
    _index: RegistryIndex | None = None

    @property
    def index(self) -> RegistryIndex:
        if self._index is None:
            self._index = build_index(self.session_factory, self.version)
        return self._index

    def map_field(
        self,
        field_id: str,
        name: str,
        *,
        description: str | None = None,
        declared_type: str | None = None,
        declared_unit: str | None = None,
        declared_format: str | None = None,
        path: str | None = None,
        sample_values: list[object] | None = None,
    ) -> FieldDecision:
        normalized = normalize_field(
            field_id,
            name,
            description=description,
            declared_type=declared_type,
            declared_unit=declared_unit,
            declared_format=declared_format,
            path=path,
            sample_values=sample_values,
        )
        retrieved = retrieve_candidates(
            self.index, normalized, self.alias_dictionary
        )
        scored = rank_candidates(normalized, retrieved)
        validate_candidates(normalized, scored)
        result = decide(
            normalized, scored, self.version, thresholds=self.thresholds
        )
        apply_reranker(result, scored, self.reranker)
        return result
