"""Tool 입력 계약 (Pydantic v2, extra=forbid).

Agent가 보내는 인자는 전부 여기서 검증된다. 계약 위반은 실행 없이
INVALID_ARGUMENTS 오류로 반환된다 (fail-closed, REQ-002).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

MAX_FIELDS = 500
MAX_TOP_K = 10


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FieldSpec(_StrictModel):
    """단일 필드 기술 — 이름·설명은 신뢰되지 않는 데이터로 취급된다."""

    name: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=2000)
    declared_type: str | None = Field(default=None, max_length=32)
    declared_unit: str | None = Field(default=None, max_length=64)
    declared_format: str | None = Field(default=None, max_length=256)
    path: str | None = Field(default=None, max_length=1024)
    sample_values: list[str | int | float | bool | None] = Field(
        default_factory=list, max_length=20
    )


class MapDatasetRequest(_StrictModel):
    dataset: dict | list = Field(
        description="input_format에 따른 원본 정의 (JSON 문서/JSON Schema/CSV 컬럼 목록/API 샘플)"
    )
    input_format: str = Field(
        pattern="^(json|json-schema|csv-columns|api-sample)$"
    )
    service_context: str | None = Field(default=None, max_length=512)
    compendium_version: str | None = Field(default=None, max_length=64)
    auto_accept_threshold: float | None = Field(default=None, ge=0.5, le=1.0)
    top_k: int = Field(default=5, ge=1, le=MAX_TOP_K)


class ValidateMappingItem(_StrictModel):
    field: FieldSpec
    imo_data_number: str = Field(min_length=1, max_length=16)


class ValidateMappingRequest(_StrictModel):
    mappings: list[ValidateMappingItem] = Field(min_length=1, max_length=MAX_FIELDS)
    compendium_version: str | None = Field(default=None, max_length=64)


class ExplainMappingRequest(_StrictModel):
    field: FieldSpec
    imo_data_number: str = Field(min_length=1, max_length=16)
    compendium_version: str | None = Field(default=None, max_length=64)


class ListCandidatesRequest(_StrictModel):
    field: FieldSpec
    compendium_version: str | None = Field(default=None, max_length=64)
    top_k: int = Field(default=5, ge=1, le=MAX_TOP_K)


class CompareVersionsRequest(_StrictModel):
    from_version: str = Field(min_length=1, max_length=64)
    to_version: str = Field(min_length=1, max_length=64)
