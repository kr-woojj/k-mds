"""후보 검색 (파이프라인 2단계: retrieve).

5개 결정론 채널로 Registry 후보를 수집한다. 모든 후보는 Registry에 실재하는
record다 — 어떤 채널도 코드를 생성하지 않는다 (REQ-006, REQ-007).

채널:
- exact_imo_code:     필드명 자체가 IMO Data Number이고 Registry에 존재
- normalized_name:    정규화 필드명 == 정규화 Element명
- alias_dictionary:   별칭 사전 조회 (대상이 Registry에 존재할 때만 인정)
- definition_fulltext: Definition 토큰과의 겹침
- semantic:           문자 trigram 유사도 (결정론 — LLM·임베딩 아님)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.mapping.normalizer import (
    GENERIC_TOKENS,
    UNIT_CANON,
    NormalizedField,
    tokenize,
)
from app.registry.models import CompendiumVersion, DataElement, RefModelOccurrence
from app.registry.validator import IMO_DATA_NUMBER_PATTERN

DEFAULT_TOP_N = 10
SEMANTIC_MIN_SIMILARITY = 0.15


@dataclass(frozen=True)
class OccurrenceInfo:
    dataset_key: str | None
    refmodel_path: str | None
    dataset_tokens: tuple[str, ...]
    path_tokens: tuple[str, ...]


@dataclass
class IndexedElement:
    imo_data_number: str
    name: str
    definition: str | None
    format_spec: str | None
    code_list: str | None
    business_rule: str | None
    status: str
    name_tokens: tuple[str, ...]
    definition_tokens: tuple[str, ...]
    normalized_name: str
    unit_hints: frozenset[str]
    expected_type: str | None
    occurrences: tuple[OccurrenceInfo, ...]

    @property
    def search_text(self) -> str:
        return f"{self.normalized_name} {' '.join(self.definition_tokens)}"


@dataclass
class RegistryIndex:
    version: str
    elements: dict[str, IndexedElement] = field(default_factory=dict)
    by_normalized_name: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class RetrievedCandidate:
    element: IndexedElement
    channels: set[str] = field(default_factory=set)


class IndexError_(ValueError):
    """존재하지 않거나 미완결 버전에 대한 인덱스 구축 요청."""


def _expected_type_from_format(format_spec: str | None) -> str | None:
    """Compendium format 표기에서 타입 범주를 결정론적으로 유도한다."""
    if not format_spec:
        return None
    spec = format_spec.strip().lower()
    if spec.startswith("an"):
        return "string"
    if spec.startswith("a"):
        return "string"
    if spec.startswith("n"):
        return "number"
    if "date" in spec or "yyyymmdd" in spec:
        return "date"
    return None


def _unit_hints(name: str, definition: str | None) -> frozenset[str]:
    """Element 명칭·정의 토큰에서 알려진 단위 표기를 추출한다."""
    hints: set[str] = set()
    for token in tokenize(f"{name} {definition or ''}"):
        canonical = UNIT_CANON.get(token)
        if canonical is not None:
            hints.add(canonical)
    return frozenset(hints)


def build_index(
    session_factory: sessionmaker[Session], version: str
) -> RegistryIndex:
    with session_factory() as session:
        version_row = session.execute(
            select(CompendiumVersion).where(CompendiumVersion.version == version)
        ).scalar_one_or_none()
        if version_row is None or not version_row.loaded:
            raise IndexError_(f"버전이 적재되어 있지 않다: {version}")

        occurrences_by_number: dict[str, list[OccurrenceInfo]] = {}
        for occurrence in session.execute(
            select(RefModelOccurrence).where(RefModelOccurrence.version == version)
        ).scalars():
            occurrences_by_number.setdefault(occurrence.imo_data_number, []).append(
                OccurrenceInfo(
                    dataset_key=occurrence.dataset_key,
                    refmodel_path=occurrence.refmodel_path,
                    dataset_tokens=tuple(tokenize(occurrence.dataset_key)),
                    path_tokens=tuple(tokenize(occurrence.refmodel_path)),
                )
            )

        index = RegistryIndex(version=version)
        for element in session.execute(
            select(DataElement).where(DataElement.version == version)
        ).scalars():
            name_tokens = tuple(tokenize(element.name))
            definition_tokens = tuple(tokenize(element.definition))
            indexed = IndexedElement(
                imo_data_number=element.imo_data_number,
                name=element.name,
                definition=element.definition,
                format_spec=element.format_spec,
                code_list=element.code_list,
                business_rule=element.business_rule,
                status=element.status,
                name_tokens=name_tokens,
                definition_tokens=definition_tokens,
                normalized_name=" ".join(name_tokens),
                unit_hints=_unit_hints(element.name, element.definition),
                expected_type=_expected_type_from_format(element.format_spec),
                occurrences=tuple(
                    sorted(
                        occurrences_by_number.get(element.imo_data_number, []),
                        key=lambda item: (
                            item.dataset_key or "",
                            item.refmodel_path or "",
                        ),
                    )
                ),
            )
            index.elements[indexed.imo_data_number] = indexed
            index.by_normalized_name.setdefault(indexed.normalized_name, []).append(
                indexed.imo_data_number
            )
        for numbers in index.by_normalized_name.values():
            numbers.sort()
    return index


def trigram_dice(text_a: str, text_b: str) -> float:
    """문자 trigram Dice 계수 — 결정론적 'semantic' 유사도."""

    def trigrams(text: str) -> set[str]:
        padded = f"  {text} "
        return {padded[i : i + 3] for i in range(len(padded) - 2)}

    if not text_a or not text_b:
        return 0.0
    grams_a = trigrams(text_a)
    grams_b = trigrams(text_b)
    if not grams_a or not grams_b:
        return 0.0
    return round(2 * len(grams_a & grams_b) / (len(grams_a) + len(grams_b)), 6)


def retrieve_candidates(
    index: RegistryIndex,
    normalized: NormalizedField,
    alias_dictionary: dict[str, str] | None = None,
    top_n: int = DEFAULT_TOP_N,
) -> list[RetrievedCandidate]:
    aliases = alias_dictionary or {}
    found: dict[str, RetrievedCandidate] = {}

    def add(number: str, channel: str) -> None:
        element = index.elements.get(number)
        if element is None:
            return  # Registry에 없는 코드는 어떤 채널에서도 후보가 될 수 없다
        candidate = found.setdefault(number, RetrievedCandidate(element=element))
        candidate.channels.add(channel)

    # 1) exact IMO Code
    raw_code = normalized.raw_name.strip().upper()
    if IMO_DATA_NUMBER_PATTERN.match(raw_code):
        add(raw_code, "exact_imo_code")

    # 2) normalized field name
    for number in index.by_normalized_name.get(normalized.normalized_name, []):
        add(number, "normalized_name")

    # 3) alias dictionary (대상 미존재 alias는 무시된다)
    alias_target = aliases.get(normalized.normalized_name)
    if alias_target is not None:
        add(alias_target.strip().upper(), "alias_dictionary")

    # 4) definition full-text (generic 토큰 제외한 겹침)
    field_tokens = {
        token
        for token in (*normalized.tokens, *normalized.description_tokens)
        if token not in GENERIC_TOKENS
    }
    if field_tokens:
        overlaps: list[tuple[int, str]] = []
        for number, element in index.elements.items():
            overlap = len(field_tokens & set(element.definition_tokens))
            if overlap >= 1:
                overlaps.append((overlap, number))
        overlaps.sort(key=lambda item: (-item[0], item[1]))
        for _, number in overlaps[:top_n]:
            add(number, "definition_fulltext")

    # 5) deterministic semantic retrieval (문자 trigram)
    field_text = " ".join(
        (*normalized.tokens, *normalized.description_tokens)
    ).strip()
    if field_text:
        similarities: list[tuple[float, str]] = []
        for number, element in index.elements.items():
            similarity = trigram_dice(field_text, element.search_text)
            if similarity >= SEMANTIC_MIN_SIMILARITY:
                similarities.append((similarity, number))
        similarities.sort(key=lambda item: (-item[0], item[1]))
        for _, number in similarities[:top_n]:
            add(number, "semantic")

    return [found[number] for number in sorted(found)]
