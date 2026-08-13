"""SourceManifestEntry 불변조건 Contract Test (ADR-0003).

모든 값은 가상임이 드러나는 TEST/FALTEST 표기만 사용한다.
실제 IMO ID 또는 실제 Hash처럼 보이는 값을 사용하지 않는다.
"""

import pytest
from pydantic import ValidationError

from k_mds.models import SourceManifestEntry


def make_entry(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "source_id": "TEST-SOURCE-001",
        "fal_version": "FALTEST",
        "ontology_version": "0.0.0-test",
        "profile_version": "kr-profile-0.0.0-test",
        "source_file": "data/raw/FALTEST/test-source.xlsx",
        "source_hash": "TEST-SHA256-NOT-A-REAL-HASH",
        "resource_uri": "urn:test:source:001",
        "verified": True,
        "status": "approved",
    }
    base.update(overrides)
    return base


def test_valid_verified_approved_entry() -> None:
    entry = SourceManifestEntry.model_validate(make_entry())
    assert entry.source_id == "TEST-SOURCE-001"
    assert entry.verified is True


def test_unverified_approved_entry_raises() -> None:
    with pytest.raises(ValidationError):
        SourceManifestEntry.model_validate(make_entry(verified=False))


def test_absolute_source_file_raises() -> None:
    for absolute in ("C:/data/test-source.xlsx", "C:\\data\\test-source.xlsx", "/data/test.xlsx"):
        with pytest.raises(ValidationError):
            SourceManifestEntry.model_validate(make_entry(source_file=absolute))


def test_parent_segment_in_source_file_raises() -> None:
    with pytest.raises(ValidationError):
        SourceManifestEntry.model_validate(
            make_entry(source_file="data/raw/../secret/test-source.xlsx")
        )


def test_empty_source_hash_raises() -> None:
    with pytest.raises(ValidationError):
        SourceManifestEntry.model_validate(make_entry(source_hash=""))


def test_unverified_draft_entry_is_allowed() -> None:
    entry = SourceManifestEntry.model_validate(make_entry(verified=False, status="draft"))
    assert entry.verified is False


def test_extra_field_raises() -> None:
    with pytest.raises(ValidationError):
        SourceManifestEntry.model_validate(make_entry(unexpected_field="TEST"))
