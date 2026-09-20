"""API 요청/응답 계약 (Pydantic v2) + OpenAPI 예시.

예시의 IMO Data Number는 REQ-028(소스 내 실제 값 하드코딩 금지)에 따라
자리표시 표기 `IMOnnnn`을 사용한다 — 실제 식별자는
`GET /api/v1/registry/elements/{imo_data_number}`로 조회한 값만 사용한다.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.skill.schemas import MAX_TOP_K, FieldSpec


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CreateMappingJobRequest(_StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "source_dataset_id": "NOON-REPORT-FEED-01",
                    "dataset": {
                        "ship_name": "TEST SHIP",
                        "fuel_oil_consumption": 123.4,
                    },
                    "input_format": "json",
                    "service_context": "noon report ingestion",
                    "auto_accept_threshold": 0.9,
                }
            ]
        },
    )

    source_dataset_id: str = Field(
        min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
    )
    dataset: dict | list
    input_format: str = Field(pattern="^(json|json-schema|csv-columns|api-sample)$")
    service_context: str | None = Field(default=None, max_length=512)
    compendium_version: str | None = Field(default=None, max_length=64)
    auto_accept_threshold: float | None = Field(default=None, ge=0.5, le=1.0)
    top_k: int = Field(default=5, ge=1, le=MAX_TOP_K)


class ReviewDecision(_StrictModel):
    field_id: str = Field(min_length=1, max_length=64)
    action: str = Field(pattern="^(accept|reject)$")
    imo_data_number: str | None = Field(default=None, max_length=16)
    note: str | None = Field(default=None, max_length=1000)


class ReviewRequest(_StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "decisions": [
                        {
                            "field_id": "f0002",
                            "action": "accept",
                            "imo_data_number": "IMOnnnn",
                            "note": "noon report dataset 후보 채택",
                        }
                    ]
                }
            ]
        },
    )

    decisions: list[ReviewDecision] = Field(min_length=1, max_length=500)


class ValidationRequestItem(_StrictModel):
    field: FieldSpec
    imo_data_number: str = Field(min_length=1, max_length=16)


class ValidationRequest(_StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "mappings": [
                        {
                            "field": {
                                "name": "fuel_oil_consumption",
                                "declared_type": "number",
                                "declared_unit": "t",
                            },
                            "imo_data_number": "IMOnnnn",
                        }
                    ]
                }
            ]
        },
    )

    mappings: list[ValidationRequestItem] = Field(min_length=1, max_length=500)
    compendium_version: str | None = Field(default=None, max_length=64)


class ErrorEntry(_StrictModel):
    error_code: str
    error_detail: str
    field_id: str | None = None
    imo_data_number: str | None = None


class SelectedMapping(_StrictModel):
    field_id: str
    field_name: str
    path: str | None = None
    imo_data_number: str
    final_score: float
    origin: str = Field(pattern="^(auto|review_accepted)$")
    registry_record_ref: dict


class KrGearsReport(_StrictModel):
    """KR GEARS 전달용 결과 계약."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "mapping_job_id": "MAPJOB-00000001",
                    "source_dataset_id": "NOON-REPORT-FEED-01",
                    "compendium_version": "FAL50",
                    "validation_status": "PASS",
                    "selected_mappings": [
                        {
                            "field_id": "f0001",
                            "field_name": "ship_name",
                            "path": "/ship_name",
                            "imo_data_number": "IMOnnnn",
                            "final_score": 1.0,
                            "origin": "auto",
                            "registry_record_ref": {
                                "recordType": "data_element",
                                "recordId": "IMOnnnn",
                                "compendiumVersion": "FAL50",
                            },
                        }
                    ],
                    "errors": [],
                    "error_code": None,
                    "error_detail": None,
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "payload_hash": "0" * 8 + "…(sha256)",
                }
            ]
        },
    )

    mapping_job_id: str
    source_dataset_id: str
    compendium_version: str
    validation_status: str = Field(pattern="^(PASS|REVIEW_REQUIRED|FAIL)$")
    selected_mappings: list[SelectedMapping]
    errors: list[ErrorEntry]
    error_code: str | None
    error_detail: str | None
    timestamp: str
    payload_hash: str
