"""SourceManifest 모델 Contract Test (ADR-0006).

모든 Hash는 synthetic 값("0"*64 등)이며 실제 IMO Hash가 아니다.
"""

import pytest
from pydantic import ValidationError

from k_mds.models import SourceManifest, SourceManifestEntry

# synthetic hash — 실제 파일 Hash가 아닌 테스트 전용 상수다.
SYNTH_HASH = "0" * 64


def make_entry(**overrides: object) -> SourceManifestEntry:
    base: dict[str, object] = {
        "source_id": "TEST-SOURCE-001",
        "fal_version": "FALTEST",
        "ontology_version": "0.0.0-test",
        "profile_version": "kr-profile-0.0.0-test",
        "source_file": "files/test-source.bin",
        "source_hash": SYNTH_HASH,
        "resource_uri": "urn:test:source:001",
        "verified": True,
        "status": "approved",
    }
    base.update(overrides)
    return SourceManifestEntry.model_validate(base)


def test_valid_source_manifest() -> None:
    manifest = SourceManifest(version=1, sources=[make_entry()])
    assert manifest.version == 1
    assert len(manifest.sources) == 1


def test_empty_sources_raises() -> None:
    with pytest.raises(ValidationError):
        SourceManifest(version=1, sources=[])


def test_duplicate_source_id_raises() -> None:
    with pytest.raises(ValidationError):
        SourceManifest(
            version=1,
            sources=[
                make_entry(),
                make_entry(source_file="files/test-source-2.bin"),
            ],
        )


def test_duplicate_source_file_raises() -> None:
    with pytest.raises(ValidationError):
        SourceManifest(
            version=1,
            sources=[
                make_entry(),
                make_entry(source_id="TEST-SOURCE-002"),
            ],
        )


def test_extra_field_raises() -> None:
    with pytest.raises(ValidationError):
        SourceManifest.model_validate(
            {"version": 1, "sources": [make_entry()], "unexpected_field": "TEST"}
        )


def test_lowercase_64_hex_hash_is_valid() -> None:
    entry = make_entry(source_hash="abcdef0123456789" * 4)
    assert len(entry.source_hash) == 64


def test_short_hash_raises() -> None:
    with pytest.raises(ValidationError):
        make_entry(source_hash="0" * 63)


def test_uppercase_hash_raises() -> None:
    with pytest.raises(ValidationError):
        make_entry(source_hash="A" * 64)


def test_non_hex_hash_raises() -> None:
    with pytest.raises(ValidationError):
        make_entry(source_hash="z" * 64)
