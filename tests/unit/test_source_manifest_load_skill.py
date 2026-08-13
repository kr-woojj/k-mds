"""source_manifest_load Skill Contract Test (ADR-0006).

tmp_path의 synthetic Manifest와 synthetic binary file만 사용한다.
실제 IMO 원본, 실제 Hash를 사용하지 않는다.
"""

import hashlib
import importlib
import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from k_mds.models import ResultStatus, SkillResult
from k_mds.skills import source_manifest_load

# 패키지 __init__의 함수 재수출이 동명 하위 모듈 속성을 가리므로 모듈을 직접 가져온다.
loader_module = importlib.import_module("k_mds.skills.source_manifest_load")

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


# --- Amendment: YAML 중복 Key 차단 (지시 Test 1~5) ---


def write_text_manifest(base: Path, text: str) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    manifest_path = base / "source-manifest.yaml"
    manifest_path.write_text(text, encoding="utf-8")
    return manifest_path


def make_source_yaml_block(base: Path, extra_line: str = "") -> str:
    source = make_source(base)
    extra = f"    {extra_line}\n" if extra_line else ""
    return (
        "sources:\n"
        "  - source_id: TEST-SOURCE-001\n"
        f"{extra}"
        "    fal_version: FALTEST\n"
        "    ontology_version: 0.0.0-test\n"
        "    profile_version: kr-profile-0.0.0-test\n"
        "    source_file: files/test-source.bin\n"
        f"    source_hash: {source['source_hash']}\n"
        "    resource_uri: urn:test:source:001\n"
    )


def test_duplicate_root_version_key_fails(tmp_path: Path) -> None:
    base = tmp_path / "base"
    text = "version: 1\nversion: 2\n" + make_source_yaml_block(base)
    result = source_manifest_load(write_text_manifest(base, text))
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "MANIFEST_DUPLICATE_KEY"


def test_duplicate_source_id_key_fails(tmp_path: Path) -> None:
    base = tmp_path / "base"
    text = "version: 1\n" + make_source_yaml_block(base, "source_id: TEST-SOURCE-DUP")
    result = source_manifest_load(write_text_manifest(base, text))
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "MANIFEST_DUPLICATE_KEY"


def test_duplicate_source_hash_key_fails(tmp_path: Path) -> None:
    base = tmp_path / "base"
    text = "version: 1\n" + make_source_yaml_block(base, f"source_hash: {'f' * 64}")
    result = source_manifest_load(write_text_manifest(base, text))
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "MANIFEST_DUPLICATE_KEY"


def test_duplicate_key_error_does_not_expose_key_name(tmp_path: Path) -> None:
    base = tmp_path / "base"
    text = "version: 1\n" + make_source_yaml_block(base, "source_id: TEST-SOURCE-DUP")
    dumped = source_manifest_load(write_text_manifest(base, text)).model_dump_json(by_alias=True)
    assert "source_id" not in dumped


def test_duplicate_key_error_does_not_expose_duplicate_value(tmp_path: Path) -> None:
    base = tmp_path / "base"
    text = "version: 1\n" + make_source_yaml_block(base, "source_id: TEST-SOURCE-DUP")
    dumped = source_manifest_load(write_text_manifest(base, text)).model_dump_json(by_alias=True)
    assert "TEST-SOURCE-DUP" not in dumped


# --- Amendment: Hash Format과 Entry Contract 분리 (지시 Test 6~14) ---


def load_with_hash(tmp_path: Path, declared_hash: str) -> SkillResult:
    base = tmp_path / "base"
    manifest = write_manifest(base, [make_source(base, hash_override=declared_hash)])
    return source_manifest_load(manifest)


def test_short_hash_is_format_invalid(tmp_path: Path) -> None:
    result = load_with_hash(tmp_path, "0" * 63)
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "SOURCE_HASH_FORMAT_INVALID"


def test_uppercase_hash_is_format_invalid(tmp_path: Path) -> None:
    result = load_with_hash(tmp_path, "A" * 64)
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "SOURCE_HASH_FORMAT_INVALID"


def test_non_hex_hash_is_format_invalid(tmp_path: Path) -> None:
    result = load_with_hash(tmp_path, "z" * 64)
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "SOURCE_HASH_FORMAT_INVALID"


def test_sha256_prefix_is_format_invalid(tmp_path: Path) -> None:
    result = load_with_hash(tmp_path, f"sha256:{'0' * 57}")
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "SOURCE_HASH_FORMAT_INVALID"


def test_empty_source_id_is_entry_invalid(tmp_path: Path) -> None:
    base = tmp_path / "base"
    source = make_source(base)
    source["source_id"] = ""
    result = source_manifest_load(write_manifest(base, [source]))
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "MANIFEST_ENTRY_INVALID"


def test_missing_source_id_is_entry_invalid(tmp_path: Path) -> None:
    base = tmp_path / "base"
    source = make_source(base)
    del source["source_id"]
    result = source_manifest_load(write_manifest(base, [source]))
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "MANIFEST_ENTRY_INVALID"


def test_extra_field_is_entry_invalid(tmp_path: Path) -> None:
    base = tmp_path / "base"
    source = make_source(base)
    source["unexpected_field"] = "TEST"
    result = source_manifest_load(write_manifest(base, [source]))
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "MANIFEST_ENTRY_INVALID"


def test_verified_input_keeps_forbidden_field_code(tmp_path: Path) -> None:
    base = tmp_path / "base"
    source = make_source(base)
    source["verified"] = True
    result = source_manifest_load(write_manifest(base, [source]))
    assert result.errors[0].code == "MANIFEST_FORBIDDEN_FIELD"


def test_status_input_keeps_forbidden_field_code(tmp_path: Path) -> None:
    base = tmp_path / "base"
    source = make_source(base)
    source["status"] = "approved"
    result = source_manifest_load(write_manifest(base, [source]))
    assert result.errors[0].code == "MANIFEST_FORBIDDEN_FIELD"


# --- Amendment: 파일 접근 전 Contract 검증 (지시 Test 15~16) ---


def test_sha256_not_called_for_invalid_hash_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = tmp_path / "base"
    # 파일은 실제로 존재하지만 Hash Format이 잘못된 경우 파일을 읽으면 안 된다.
    manifest = write_manifest(base, [make_source(base, hash_override="X" * 64)])

    def _must_not_be_called(path: Path) -> str:
        raise AssertionError("_sha256_of는 Entry Contract 검증 전에 호출되면 안 된다")

    monkeypatch.setattr(loader_module, "_sha256_of", _must_not_be_called)
    result = source_manifest_load(manifest)
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "SOURCE_HASH_FORMAT_INVALID"


def test_invalid_entry_returns_no_partial_source_data(tmp_path: Path) -> None:
    result = load_with_hash(tmp_path, "0" * 63)
    assert result.data == {"loaded": False}


# --- Amendment: 기존 정책 Regression (지시 Test 17~23) ---


def test_valid_format_wrong_hash_keeps_mismatch_code(tmp_path: Path) -> None:
    result = load_with_hash(tmp_path, "f" * 64)
    assert result.status is ResultStatus.FAIL
    assert result.errors[0].code == "SOURCE_HASH_MISMATCH"


def test_valid_manifest_still_passes(tmp_path: Path) -> None:
    assert load_valid(tmp_path).status is ResultStatus.PASS


def test_multiple_source_order_still_preserved(tmp_path: Path) -> None:
    base = tmp_path / "base"
    ids = ["TEST-SOURCE-01A", "TEST-SOURCE-01B"]
    manifest = write_manifest(
        base,
        [
            make_source(base, source_id=sid, rel=f"files/{sid.lower()}.bin", content=sid.encode())
            for sid in ids
        ],
    )
    result = source_manifest_load(manifest)
    assert [source["source_id"] for source in result.data["sources"]] == ids


def test_amendment_failures_have_none_actual_value(tmp_path: Path) -> None:
    base = tmp_path / "base"
    text = "version: 1\nversion: 2\n" + make_source_yaml_block(base)
    failures = [
        source_manifest_load(write_text_manifest(base, text)),
        load_with_hash(tmp_path, "0" * 63),
    ]
    for result in failures:
        for finding in result.errors:
            assert finding.actual_value is None


def test_amendment_failures_do_not_expose_hashes(tmp_path: Path) -> None:
    declared = "A" * 64
    dumped = load_with_hash(tmp_path, declared).model_dump_json(by_alias=True)
    assert declared not in dumped
    assert sha256_of(SYNTH_CONTENT) not in dumped


def test_amendment_failures_do_not_expose_absolute_path(tmp_path: Path) -> None:
    dumped = load_with_hash(tmp_path, "0" * 63).model_dump_json(by_alias=True)
    assert str(tmp_path).lower() not in dumped.lower()
    assert "c:\\" not in dumped.lower() and "c:/" not in dumped.lower()


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
