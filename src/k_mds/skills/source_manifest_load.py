"""source_manifest_load Skill — Source Manifest SHA-256 검증 Loader (ADR-0006).

source-manifest YAML을 읽어 각 source_file의 실제 SHA-256을 계산하고,
선언된 Hash와 일치하는 경우에만 verified=true, status=approved의
SourceManifestEntry를 구성한다.

핵심 원칙:
- Manifest의 verified/status 입력은 신뢰하지 않으며 존재 자체를 금지한다.
- Hash 불일치, 파일 누락, 경로 이탈, Manifest 오류는 예외 없이 FAIL이다.
- 부분 성공을 허용하지 않는다.
- Finding에는 Hash 값, 파일 경로, 입력값을 포함하지 않는다.
- Loader는 Evidence를 만들지 않는다 — Evidence 생성은 evidence_build의 책임이다.
"""

from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import yaml
from pydantic import ValidationError

from k_mds.models import (
    FindingSeverity,
    ResultStatus,
    SkillResult,
    SourceManifest,
    SourceManifestEntry,
    ValidationFinding,
)

RULE_ID = "urn:k-mds:rule:source-manifest-verification:0.1"

_CHUNK_SIZE = 1024 * 1024

#: Loader가 결정하는 필드 — Manifest 입력에서 금지한다.
_FORBIDDEN_INPUT_FIELDS = ("verified", "status")


def _finding(code: str, message: str, path: str | None = None) -> ValidationFinding:
    return ValidationFinding(
        severity=FindingSeverity.ERROR,
        code=code,
        message=message,
        rule_id=RULE_ID,
        path=path,
        actual_value=None,
    )


def _fail(errors: list[ValidationFinding]) -> SkillResult:
    return SkillResult(
        status=ResultStatus.FAIL,
        human_review_required=True,
        data={"loaded": False},
        errors=errors,
    )


def _loc_to_path(loc: tuple[int | str, ...]) -> str:
    if not loc:
        return "$"
    return "$." + ".".join(str(part) for part in loc)


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _is_escaping_relative_path(source_file: str) -> bool:
    if PureWindowsPath(source_file).is_absolute() or PurePosixPath(source_file).is_absolute():
        return True
    return ".." in source_file.replace("\\", "/").split("/")


def source_manifest_load(
    manifest_path: Path,
    *,
    base_dir: Path | None = None,
) -> SkillResult:
    """Manifest를 읽고 모든 Source의 SHA-256 일치를 검증한다."""
    if not isinstance(manifest_path, Path):
        return _fail(
            [_finding("MANIFEST_PATH_NOT_PATH", "manifest_path는 Path여야 한다", "$.manifestPath")]
        )
    if base_dir is not None and not isinstance(base_dir, Path):
        return _fail([_finding("BASE_DIR_NOT_PATH", "base_dir는 Path여야 한다", "$.baseDir")])

    if not manifest_path.is_file():
        return _fail(
            [
                _finding(
                    "MANIFEST_FILE_NOT_FOUND",
                    "Manifest 파일이 존재하지 않거나 일반 파일이 아니다",
                    "$.manifestPath",
                )
            ]
        )

    try:
        text = manifest_path.read_text(encoding="utf-8")
    except OSError:
        return _fail(
            [_finding("MANIFEST_FILE_NOT_FOUND", "Manifest 파일을 읽을 수 없다", "$.manifestPath")]
        )
    except UnicodeDecodeError:
        return _fail(
            [_finding("MANIFEST_YAML_INVALID", "Manifest는 UTF-8 Text여야 한다", "$.manifestPath")]
        )

    try:
        raw: Any = yaml.safe_load(text)
    except yaml.YAMLError:
        return _fail(
            [_finding("MANIFEST_YAML_INVALID", "Manifest가 유효한 YAML이 아니다", "$.manifestPath")]
        )

    if not isinstance(raw, dict):
        return _fail(
            [_finding("MANIFEST_ROOT_NOT_OBJECT", "Manifest Root는 Object여야 한다", "$")]
        )

    contract_errors: list[ValidationFinding] = []
    version = raw.get("version")
    if isinstance(version, bool) or not isinstance(version, int):
        contract_errors.append(
            _finding("MANIFEST_CONTRACT_INVALID", "version은 정수여야 한다", "$.version")
        )
    sources_raw = raw.get("sources")
    if not isinstance(sources_raw, list):
        contract_errors.append(
            _finding("MANIFEST_CONTRACT_INVALID", "sources는 list여야 한다", "$.sources")
        )
    if contract_errors:
        return _fail(contract_errors)
    assert isinstance(version, int)
    assert isinstance(sources_raw, list)

    effective_base = (base_dir if base_dir is not None else manifest_path.parent).resolve()

    errors: list[ValidationFinding] = []
    entries: list[SourceManifestEntry] = []
    for index, item in enumerate(sources_raw):
        if not isinstance(item, dict):
            errors.append(
                _finding(
                    "MANIFEST_CONTRACT_INVALID",
                    f"sources[{index}]는 Object여야 한다",
                    f"$.sources.{index}",
                )
            )
            continue

        forbidden = [name for name in _FORBIDDEN_INPUT_FIELDS if name in item]
        if forbidden:
            errors.append(
                _finding(
                    "MANIFEST_FORBIDDEN_FIELD",
                    f"Manifest 입력에 금지된 필드가 있다: {', '.join(forbidden)} "
                    "(verified와 status는 Loader가 결정한다)",
                    f"$.sources.{index}",
                )
            )
            continue

        source_file = item.get("source_file")
        if not isinstance(source_file, str) or not source_file:
            errors.append(
                _finding(
                    "MANIFEST_CONTRACT_INVALID",
                    f"sources[{index}].source_file은 비어 있지 않은 문자열이어야 한다",
                    f"$.sources.{index}.source_file",
                )
            )
            continue

        if _is_escaping_relative_path(source_file):
            errors.append(
                _finding(
                    "SOURCE_PATH_OUTSIDE_BASE",
                    f"sources[{index}]의 source_file이 base 디렉터리 정책을 위반한다 "
                    "(절대경로 또는 '..' Segment)",
                    f"$.sources.{index}.source_file",
                )
            )
            continue

        resolved = (effective_base / source_file).resolve()
        if not resolved.is_relative_to(effective_base):
            errors.append(
                _finding(
                    "SOURCE_PATH_OUTSIDE_BASE",
                    f"sources[{index}]의 source_file이 base 디렉터리 밖을 가리킨다",
                    f"$.sources.{index}.source_file",
                )
            )
            continue

        if not resolved.is_file():
            errors.append(
                _finding(
                    "SOURCE_FILE_NOT_FOUND",
                    f"sources[{index}]의 source_file이 존재하지 않거나 일반 파일이 아니다",
                    f"$.sources.{index}.source_file",
                )
            )
            continue

        try:
            calculated = _sha256_of(resolved)
        except OSError:
            errors.append(
                _finding(
                    "SOURCE_FILE_NOT_FOUND",
                    f"sources[{index}]의 source_file을 읽을 수 없다",
                    f"$.sources.{index}.source_file",
                )
            )
            continue

        if item.get("source_hash") != calculated:
            # 선언 Hash와 계산 Hash 값은 노출하지 않는다.
            errors.append(
                _finding(
                    "SOURCE_HASH_MISMATCH",
                    f"sources[{index}]의 선언된 SHA-256이 실제 파일과 일치하지 않는다",
                    f"$.sources.{index}.source_hash",
                )
            )
            continue

        try:
            entry = SourceManifestEntry.model_validate(
                {**item, "verified": True, "status": "approved"}
            )
        except ValidationError as exc:
            errors.extend(
                _finding(
                    "MANIFEST_ENTRY_INVALID",
                    str(error["msg"]),
                    path=_loc_to_path(("sources", index, *error["loc"])),
                )
                for error in exc.errors(
                    include_url=False, include_input=False, include_context=False
                )
            )
            continue
        entries.append(entry)

    if errors:
        return _fail(errors)

    try:
        manifest = SourceManifest(version=version, sources=entries)
    except ValidationError as exc:
        return _fail(
            [
                _finding(
                    "MANIFEST_CONTRACT_INVALID",
                    str(error["msg"]),
                    path=_loc_to_path(error["loc"]),
                )
                for error in exc.errors(
                    include_url=False, include_input=False, include_context=False
                )
            ]
        )

    return SkillResult(
        status=ResultStatus.PASS,
        human_review_required=False,
        data={
            "loaded": True,
            "manifestVersion": manifest.version,
            "sourceCount": len(manifest.sources),
            "sources": [
                entry.model_dump(by_alias=True, mode="json") for entry in manifest.sources
            ],
        },
    )
