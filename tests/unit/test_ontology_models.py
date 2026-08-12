"""DataElement와 ElementOccurrence 분리 Contract Test (AGENTS.md §2.3).

모든 식별자와 Technical Position은 가상임이 드러나는 TEST 표기만 사용한다.
"""

import pytest
from pydantic import ValidationError

from k_mds.models import DataElement, ElementOccurrence, GovernanceStatus


def make_occurrence(
    occurrence_id: str,
    dataset_id: str,
    technical_position: str | None,
) -> ElementOccurrence:
    return ElementOccurrence(
        occurrence_id=occurrence_id,
        dataset_id=dataset_id,
        element_imo_id="TEST-ELEMENT-001",
        technical_position=technical_position,
    )


def test_same_element_reusable_across_occurrences() -> None:
    # 지시 Test 14: 하나의 DataElement가 서로 다른 Dataset/Path의 Occurrence로 연결된다.
    element = DataElement(imo_id="TEST-ELEMENT-001", name="테스트 데이터 요소")
    occ_a = make_occurrence("occ-test-a", "ds-test-a", "TEST/PATH/A")
    occ_b = make_occurrence("occ-test-b", "ds-test-b", "TEST/PATH/B")

    assert occ_a.element_imo_id == element.imo_id == occ_b.element_imo_id
    assert occ_a.occurrence_id != occ_b.occurrence_id
    assert {occ_a.technical_position, occ_b.technical_position} == {"TEST/PATH/A", "TEST/PATH/B"}


def test_occurrence_requires_element_reference() -> None:
    # 지시 Test 15: Occurrence는 DataElement 참조 없이 독립 표준사실이 될 수 없다.
    with pytest.raises(ValidationError):
        ElementOccurrence(
            occurrence_id="occ-test-x",
            dataset_id="ds-test",
            element_imo_id="",
        )
    with pytest.raises(ValidationError):
        ElementOccurrence.model_validate(
            {"occurrence_id": "occ-test-x", "dataset_id": "ds-test"}
        )


def test_occurrence_without_position_cannot_be_approved() -> None:
    # 추가 불변조건: Technical Position 미확인 항목은 approved가 될 수 없다 (AGENTS.md §8).
    with pytest.raises(ValidationError):
        ElementOccurrence(
            occurrence_id="occ-test-y",
            dataset_id="ds-test",
            element_imo_id="TEST-ELEMENT-001",
            technical_position=None,
            status=GovernanceStatus.APPROVED,
        )
