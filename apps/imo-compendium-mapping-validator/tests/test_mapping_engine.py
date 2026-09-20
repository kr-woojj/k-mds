"""Field Mapping Engine 테스트.

정책 (REQ-028): 샘플 IMO 값은 tests/fixtures/에서만 읽는다. 기대 번호는 전부
fixture 행에서 유도하며, 존재하지 않는 번호가 필요한 테스트는 fixture의 최대
번호에서 런타임에 구성한다.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.mapping import MappingEngine
from app.mapping.decision import (
    STATUS_MATCHED,
    STATUS_MISSING_CONTEXT,
    STATUS_NO_MATCH,
    STATUS_REVIEW_REQUIRED,
)
from app.mapping.normalizer import normalize_field
from app.mapping.ranker import SCORE_COMPONENTS
from app.registry.database import init_db, make_session_factory
from app.registry.loader import run_import

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_NAME = "mapping_registry.csv"

NUMBER_COLUMN = "IMO Data Number"
NAME_COLUMN = "Data Element"
DATASET_COLUMN = "Dataset"
STATUS_COLUMN = "Status"
VERSION_COLUMN = "Version"


def read_rows() -> list[dict[str, str]]:
    with (FIXTURES / FIXTURE_NAME).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def number_of(rows: list[dict[str, str]], name: str, dataset: str | None = None) -> str:
    matches = [
        row[NUMBER_COLUMN]
        for row in rows
        if row[NAME_COLUMN].lower() == name.lower()
        and (dataset is None or row[DATASET_COLUMN] == dataset)
    ]
    assert len(matches) == 1, f"fixture에서 유일하게 결정되지 않음: {name}/{dataset}"
    return matches[0]


def nonexistent_number(rows: list[dict[str, str]]) -> str:
    highest = max(int(row[NUMBER_COLUMN][3:]) for row in rows)
    return f"IMO{highest + 1:04d}"


@pytest.fixture(scope="module")
def rows() -> list[dict[str, str]]:
    return read_rows()


@pytest.fixture(scope="module")
def engine(tmp_path_factory: pytest.TempPathFactory, rows) -> MappingEngine:
    db_path = tmp_path_factory.mktemp("mapping") / "registry.sqlite3"
    sql_engine = init_db(db_path)
    session_factory = make_session_factory(sql_engine)
    version = rows[0][VERSION_COLUMN]
    result = run_import(session_factory, FIXTURES / FIXTURE_NAME, version)
    assert result.ok, result.issue_codes
    return MappingEngine(session_factory=session_factory, version=version)


def candidate_numbers(decision) -> list[str]:
    return [candidate["imoDataNumber"] for candidate in decision.candidates]


# --- 성분 점수 보존 ---


def test_all_score_components_preserved(engine, rows) -> None:
    decision = engine.map_field(
        "f-components",
        "ship name",
        declared_type="string",
        path="/vessel/ship_name",
    )
    assert decision.candidates, "후보가 있어야 한다"
    for candidate in decision.candidates:
        for component in SCORE_COMPONENTS:
            assert component in candidate, f"{component} 누락"
        assert "final_score" in candidate
        assert 0.0 <= candidate["final_score"] <= 1.0


# --- 자동 승인 경로 ---


def test_exact_name_match_approved(engine, rows) -> None:
    expected = number_of(rows, "Ship name")
    decision = engine.map_field(
        "f-ship", "ship_name", declared_type="string", path="/vessel/ship_name"
    )
    assert decision.status == STATUS_MATCHED
    assert decision.selected_imo_data_number == expected
    top = decision.candidates[0]
    assert top["name_score"] == 1.0
    assert "normalized_name" in top["channels"]


def test_exact_imo_code_channel(engine, rows) -> None:
    expected = number_of(rows, "Ship name")
    decision = engine.map_field("f-code", expected)
    assert decision.status == STATUS_MATCHED
    assert decision.selected_imo_data_number == expected
    assert "exact_imo_code" in decision.candidates[0]["channels"]


def test_alias_dictionary_channel(engine, rows) -> None:
    expected = number_of(rows, "Ship name")
    alias_key = normalize_field("tmp", "vsl_nm_official").normalized_name
    aliased = MappingEngine(
        session_factory=engine.session_factory,
        version=engine.version,
        alias_dictionary={alias_key: expected},
    )
    decision = aliased.map_field("f-alias", "vsl_nm_official")
    assert decision.status == STATUS_MATCHED
    assert decision.selected_imo_data_number == expected
    assert "alias_dictionary" in decision.candidates[0]["channels"]


def test_alias_to_unknown_number_is_ignored(engine, rows) -> None:
    ghost = nonexistent_number(rows)
    alias_key = normalize_field("tmp", "ghost_field_zz").normalized_name
    aliased = MappingEngine(
        session_factory=engine.session_factory,
        version=engine.version,
        alias_dictionary={alias_key: ghost},
    )
    decision = aliased.map_field("f-ghost", "ghost_field_zz")
    # Registry에 없는 코드는 어떤 채널로도 후보가 될 수 없다 (REQ-007).
    assert ghost not in candidate_numbers(decision)
    assert decision.status != STATUS_MATCHED


# --- 상위 후보 간 0.05 미만 gap: 자동 승인 금지 ---


def test_ambiguous_candidates_not_auto_approved(engine, rows) -> None:
    voyage = number_of(rows, "Fuel oil consumption", "TEST-DS-VOYAGE")
    noon = number_of(rows, "Fuel oil consumption", "TEST-DS-NOON")
    decision = engine.map_field("f-fuel", "fuel oil consumption")
    numbers = candidate_numbers(decision)
    assert voyage in numbers and noon in numbers
    assert decision.status == STATUS_REVIEW_REQUIRED
    assert decision.selected_imo_data_number is None

    eligible = [c for c in decision.candidates if not c["rejected"]]
    gap = eligible[0]["final_score"] - eligible[1]["final_score"]
    assert gap < 0.05
    assert any("TOP_GAP_BELOW_MINIMUM" in reason for reason in decision.reasons)
    # 복수 공식 후보 → 차이 설명이 제공되어야 한다.
    assert decision.comparisons
    assert any(voyage in note or noon in note for note in decision.comparisons)


def test_context_orders_ambiguous_candidates(engine, rows) -> None:
    noon = number_of(rows, "Fuel oil consumption", "TEST-DS-NOON")
    decision = engine.map_field(
        "f-fuel-noon",
        "fuel oil consumption",
        path="/test/noon/fuel_oil_consumption",
    )
    assert candidate_numbers(decision)[0] == noon
    assert decision.status in (STATUS_MATCHED, STATUS_REVIEW_REQUIRED)


# --- hard conflict: semantic이 높아도 거절 ---


def test_datatype_hard_conflict_rejected(engine, rows) -> None:
    target = number_of(rows, "Distance travelled")
    decision = engine.map_field(
        "f-distance",
        "distance travelled",
        declared_type="string",
        sample_values=["around ten miles"],
    )
    assert decision.status != STATUS_MATCHED
    target_candidate = next(
        candidate
        for candidate in decision.candidates
        if candidate["imoDataNumber"] == target
    )
    # 이름은 정확히 일치하지만 타입 충돌로 거절된다.
    assert target_candidate["name_score"] == 1.0
    assert target_candidate["rejected"] is True
    assert "datatype" in target_candidate["hardConflicts"]
    assert any(
        issue["code"] == "DATATYPE_HARD_CONFLICT"
        for issue in target_candidate["issues"]
    )


def test_unit_hard_conflict_rejected(engine, rows) -> None:
    decision = engine.map_field(
        "f-fuel-kg",
        "fuel oil consumption",
        declared_type="number",
        declared_unit="kg",
    )
    assert decision.status == STATUS_NO_MATCH
    fuel_candidates = [
        candidate
        for candidate in decision.candidates
        if candidate["name_score"] == 1.0
    ]
    assert fuel_candidates, "이름 일치 후보가 존재해야 한다"
    for candidate in fuel_candidates:
        assert candidate["rejected"] is True
        assert "unit" in candidate["hardConflicts"]
        assert any(
            issue["code"] == "UNIT_HARD_CONFLICT" for issue in candidate["issues"]
        )


def test_deprecated_element_not_approved(engine, rows) -> None:
    deprecated_number = next(
        row[NUMBER_COLUMN]
        for row in rows
        if row[STATUS_COLUMN].strip().lower() == "deprecated"
    )
    decision = engine.map_field("f-anchorage", "time at anchorage")
    assert decision.status != STATUS_MATCHED
    candidate = next(
        item
        for item in decision.candidates
        if item["imoDataNumber"] == deprecated_number
    )
    assert candidate["rejected"] is True
    assert any(
        issue["code"] == "ELEMENT_DEPRECATED" for issue in candidate["issues"]
    )


# --- missing context ---


def test_generic_field_without_context_returns_missing_context(engine) -> None:
    decision = engine.map_field("f-generic", "value")
    assert decision.status == STATUS_MISSING_CONTEXT
    assert decision.missing_context is True
    assert decision.selected_imo_data_number is None


def test_generic_field_with_description_is_processed(engine) -> None:
    decision = engine.map_field(
        "f-generic-desc", "value", description="fuel oil consumption for the voyage"
    )
    assert decision.status != STATUS_MISSING_CONTEXT


# --- 결정론 ---


def test_decisions_are_deterministic(engine) -> None:
    first = engine.map_field(
        "f-repeat", "fuel oil consumption", path="/test/noon/fuel_oil_consumption"
    )
    second = engine.map_field(
        "f-repeat", "fuel oil consumption", path="/test/noon/fuel_oil_consumption"
    )
    assert first.to_dict() == second.to_dict()
