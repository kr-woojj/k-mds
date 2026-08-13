"""source_manifest_load Skill Contract Test (ADR-0006).

tmp_path의 synthetic Manifest와 synthetic binary file만 사용한다.
실제 IMO 원본, 실제 Hash를 사용하지 않는다.
"""

import hashlib
import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from k_mds.models import ResultStatus, SkillResult
from k_mds.skills import source_manifest_load

SYNTH_CONTENT = b"TEST-SYNTHETIC-BINARY-CONTENT-001"


def sha256_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def make_source(
    base: Path,
    source_id: str = "TEST-SOURCE-001",
    rel: str = "files/test-source.bin",
    content: bytes = SYNTH_CONTENT,
    hash_override: str | None = None,
    create_file: bool = True,
) -> dict[str, Any]:
    if create_file:
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return {
        "source_id": source_id,
        "fal_version": "FALTEST",
        "ontology_version": "0.0.0-test",
        "profile_version": "kr-profile-0.0.0-test",
        "source_file": rel,
        "source_hash": sha256_of(content) if hash_override is None else hash_override,
        "resource_uri": "urn:test:source:001",
    }


def write_manifest(base: Path, sources: list[dict[str, Any]], version: object = 1) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    manifest_path = base / "source-manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump({"version": version, "sources": sources}, allow_unicode=True),
        encoding="utf-8",
    )
    return manifest_path


def load_valid(tmp_path: Path) -> SkillResult:
    base = tmp_path / "base"
    manifest = write_manifest(base, [make_source(base)])
    return source_manifest_load(manifest)


# --- 성공 경로 (지시 Test 1~8) ---


def test_valid_manifest_with_matching_hash_passes(tmp_path: Path) -> None:
    assert load_valid(tmp_path).status is ResultStatus.PASS


def test_success_sources_are_verified(tmp_path: Path) -> None:
    for source in load_valid(tmp_path).data["sources"]:
        assert source["verified"] is True


def test_success_sources_are_approved(tmp_path: Path) -> None:
    for source in load_valid(tmp_path).data["sources"]:
        assert source["status"] == "approved"


def test_source_count_is_accurate(tmp_path: Path) -> None:
    result = load_valid(tmp_path)
    assert result.data["sourceCount"] == 1 == len(result.data["sources"])


def test_multiple_sources_pass(tmp_path: Path) -> None:
    base = tmp_path / "base"
    manifest = write_manifest(
        base,
        [
            make_source(base),
            make_source(
                base,
                source_id="TEST-SOURCE-002",
                rel="files/test-source-2.bin",
                content=b"TEST-SYNTHETIC-BINARY-CONTENT-002",
            ),
        ],
    )
    result = source_manifest_load(manifest)
    assert result.status is ResultStatus.PASS
    assert result.data["sourceCount"] == 2


def test_source_order_is_preserved(tmp_path: Path) -> None:
    base = tmp_path / "base"
    ids = ["TEST-SOURCE-00A", "TEST-SOURCE-00B", "TEST-SOURCE-00C"]
    manifest = write_manifest(
        base,
        [
            make_source(base, source_id=sid, rel=f"files/{sid.lower()}.bin", content=sid.encode())
            for sid in ids
        ],
    )
    result = source_manifest_load(manifest)
    assert [source["source_id"] for source in result.data["sources"]] == ids


def test_same_input_produces_identical_result(tmp_path: Path) -> None:
    base = tmp_path / "base"
    manifest = write_manifest(base, [make_source(base)])
    first = source_manifest_load(manifest).model_dump(by_alias=True)
    second = source_manifest_load(manifest).model_dump(by_alias=True)
    assert first == second


def test_loader_returns_no_evidence(tmp_path: Path) -> None:
    # Evidence 생성은 evidence_build의 책임이다 (ADR-0006).
    assert load_valid(tmp_path).evidence == []


# --- 실패 경로 (지시 Test 9~16) ---


def test_hash_mismatch_fails(tmp_path: Path) -> None:
    base = tmp_path / "base"
    manifest = write_manifest(base, [make_source(base, hash_override="f" * 64)])
    result = source_manifest_load(manifest)
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "SOURCE_HASH_MISMATCH"


def test_missing_source_file_fails(tmp_path: Path) -> None:
    base = tmp_path / "base"
    manifest = write_manifest(base, [make_source(base, create_file=False)])
    result = source_manifest_load(manifest)
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "SOURCE_FILE_NOT_FOUND"


def test_missing_manifest_file_fails(tmp_path: Path) -> None:
    result = source_manifest_load(tmp_path / "missing-manifest.yaml")
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "MANIFEST_FILE_NOT_FOUND"


def test_broken_yaml_fails(tmp_path: Path) -> None:
    manifest_path = tmp_path / "source-manifest.yaml"
    manifest_path.write_text("{ broken: [yaml", encoding="utf-8")
    result = source_manifest_load(manifest_path)
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "MANIFEST_YAML_INVALID"


def test_yaml_root_list_fails(tmp_path: Path) -> None:
    manifest_path = tmp_path / "source-manifest.yaml"
    manifest_path.write_text("- a\n- b\n", encoding="utf-8")
    result = source_manifest_load(manifest_path)
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "MANIFEST_ROOT_NOT_OBJECT"


def test_sources_not_list_fails(tmp_path: Path) -> None:
    manifest_path = tmp_path / "source-manifest.yaml"
    manifest_path.write_text("version: 1\nsources: TEST\n", encoding="utf-8")
    assert source_manifest_load(manifest_path).status is ResultStatus.FAIL


def test_verified_field_in_manifest_fails(tmp_path: Path) -> None:
    base = tmp_path / "base"
    source = make_source(base)
    source["verified"] = True
    result = source_manifest_load(write_manifest(base, [source]))
    assert result.status is ResultStatus.FAIL


def test_status_field_in_manifest_fails(tmp_path: Path) -> None:
    base = tmp_path / "base"
    source = make_source(base)
    source["status"] = "approved"
    result = source_manifest_load(write_manifest(base, [source]))
    assert result.status is ResultStatus.FAIL


# --- 경로 정책 (지시 Test 17~20) ---


def test_absolute_source_file_fails(tmp_path: Path) -> None:
    base = tmp_path / "base"
    source = make_source(base)
    source["source_file"] = str((base / "files/test-source.bin").resolve())
    result = source_manifest_load(write_manifest(base, [source]))
    assert result.status is ResultStatus.FAIL


def test_parent_segment_fails(tmp_path: Path) -> None:
    base = tmp_path / "base"
    source = make_source(base)
    source["source_file"] = "files/../files/test-source.bin"
    result = source_manifest_load(write_manifest(base, [source]))
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "SOURCE_PATH_OUTSIDE_BASE"


def test_escaping_traversal_fails(tmp_path: Path) -> None:
    (tmp_path / "outside.bin").write_bytes(SYNTH_CONTENT)
    base = tmp_path / "base"
    source = make_source(base, create_file=False)
    source["source_file"] = "files/../../outside.bin"
    result = source_manifest_load(write_manifest(base, [source]))
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "SOURCE_PATH_OUTSIDE_BASE"


def test_symlink_outside_base_fails(tmp_path: Path) -> None:
    outside = tmp_path / "outside.bin"
    outside.write_bytes(SYNTH_CONTENT)
    base = tmp_path / "base"
    (base / "files").mkdir(parents=True)
    link = base / "files" / "link.bin"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("이 환경에서는 Symlink 생성이 지원되지 않는다")
    source = make_source(base, rel="files/link.bin", create_file=False)
    result = source_manifest_load(write_manifest(base, [source]))
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "SOURCE_PATH_OUTSIDE_BASE"


# --- Runtime Boundary (지시 Test 21~28) ---


def test_manifest_path_not_path_fails() -> None:
    result = source_manifest_load("TEST-MARKER-PATH")  # type: ignore[arg-type]
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "MANIFEST_PATH_NOT_PATH"


def test_base_dir_not_path_fails(tmp_path: Path) -> None:
    base = tmp_path / "base"
    manifest = write_manifest(base, [make_source(base)])
    result = source_manifest_load(manifest, base_dir="TEST-MARKER-BASE")  # type: ignore[arg-type]
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "BASE_DIR_NOT_PATH"


def test_invalid_runtime_inputs_do_not_raise(tmp_path: Path) -> None:
    inputs: list[object] = ["TEST-MARKER-PATH", None, 42, ["TEST-MARKER-LIST"]]
    for item in inputs:
        result = source_manifest_load(item)  # type: ignore[arg-type]
        assert isinstance(result, SkillResult)
        assert result.status is ResultStatus.FAIL


def test_finding_does_not_expose_input_marker(tmp_path: Path) -> None:
    result = source_manifest_load("TEST-MARKER-PATH")  # type: ignore[arg-type]
    dumped = result.model_dump_json(by_alias=True)
    assert "TEST-MARKER-PATH" not in dumped
    assert "builtins." not in dumped


def test_finding_does_not_expose_declared_hash(tmp_path: Path) -> None:
    base = tmp_path / "base"
    declared = "f" * 64
    manifest = write_manifest(base, [make_source(base, hash_override=declared)])
    dumped = source_manifest_load(manifest).model_dump_json(by_alias=True)
    assert declared not in dumped


def test_finding_does_not_expose_calculated_hash(tmp_path: Path) -> None:
    base = tmp_path / "base"
    manifest = write_manifest(base, [make_source(base, hash_override="f" * 64)])
    dumped = source_manifest_load(manifest).model_dump_json(by_alias=True)
    assert sha256_of(SYNTH_CONTENT) not in dumped


def test_finding_does_not_expose_absolute_path(tmp_path: Path) -> None:
    failures = [
        source_manifest_load(tmp_path / "missing-manifest.yaml"),
        source_manifest_load("TEST-MARKER-PATH"),  # type: ignore[arg-type]
    ]
    for result in failures:
        dumped = result.model_dump_json(by_alias=True)
        assert str(tmp_path).lower() not in dumped.lower()
        assert "c:\\" not in dumped.lower() and "c:/" not in dumped.lower()


def test_fail_finding_actual_value_is_none(tmp_path: Path) -> None:
    base = tmp_path / "base"
    failures = [
        source_manifest_load("TEST-MARKER-PATH"),  # type: ignore[arg-type]
        source_manifest_load(tmp_path / "missing-manifest.yaml"),
        source_manifest_load(write_manifest(base, [make_source(base, hash_override="f" * 64)])),
    ]
    for result in failures:
        for finding in result.errors:
            assert finding.actual_value is None


# --- 직렬화와 실행 Contract (지시 Test 29~32) ---


def test_returns_skill_result_instance(tmp_path: Path) -> None:
    assert isinstance(load_valid(tmp_path), SkillResult)


def test_serialization_contains_camel_case_alias(tmp_path: Path) -> None:
    dumped = load_valid(tmp_path).model_dump(by_alias=True)
    assert "humanReviewRequired" in dumped
    assert "human_review_required" not in dumped


def test_success_data_loaded_true(tmp_path: Path) -> None:
    result = load_valid(tmp_path)
    assert result.data["loaded"] is True
    assert result.data["manifestVersion"] == 1


def test_failure_data_loaded_false(tmp_path: Path) -> None:
    result = source_manifest_load(tmp_path / "missing-manifest.yaml")
    assert result.data == {"loaded": False}
