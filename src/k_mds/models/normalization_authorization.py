"""Normalization Authorization 모델 (ADR-0010).

Restricted Review를 통해 Sheet별 역할·Header 승인·Finding 처분·Output Storage를
명시적으로 승인하는 Contract다. Actual Authorization은 Restricted Artifact이며
Public Git에 Commit하지 않는다 — Public Repository에는 이 Contract와 Synthetic
Fixture만 포함한다. 실제 Sheet 이름, Header Text, Hash, Path 필드는 금지된다.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

#: Controlled Reason Code Pattern (자유서술 Text 금지, ADR-0010 Amendment)
REASON_CODE_PATTERN = "^[A-Z][A-Z0-9_]{2,63}$"
#: Logical Root ID Pattern (Path Separator 불허)
ROOT_ID_PATTERN = "^[A-Z][A-Z0-9_-]{2,63}$"


class SheetClassification(StrEnum):
    DATA_TABLE = "data_table"
    CODE_LIST = "code_list"
    METADATA_OR_README = "metadata_or_readme"
    EXCLUDED_NON_DATA = "excluded_non_data"
    #: Mapping·Semantic Review의 참조 자산 — 직접 Record Mapping 대상이 아니다.
    MODEL_REFERENCE = "model_reference"


class DrawingReviewCategory(StrEnum):
    """Restricted Drawing Review가 결정한 Drawing 의미 Category."""

    IMO_COMPENDIUM_MODEL_REFERENCE = "imo_compendium_model_reference"
    DOCUMENTATION = "documentation"
    OUT_OF_SCOPE_VISUAL = "out_of_scope_visual"
    SEPARATE_VISUAL_REVIEW_REQUIRED = "separate_visual_review_required"
    UNDECIDED = "undecided"


class HeaderConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class FindingDisposition(StrEnum):
    RESOLVED = "resolved"
    ACCEPTED_FOR_REVIEWED_SCOPE = "accepted_for_reviewed_scope"
    REMAINS_BLOCKING = "remains_blocking"


class _AuthorizationModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class SheetAuthorization(_AuthorizationModel):
    """sheetOrdinal로 식별하는 Sheet별 승인 — Sheet 이름은 저장하지 않는다."""

    sheet_ordinal: int = Field(ge=0)
    classification: SheetClassification
    normalize: bool
    header_row: int | None = Field(default=None, ge=1)
    header_confidence: HeaderConfidence
    medium_confidence_approved: bool = False
    exclusion_reason_code: str | None = Field(default=None, pattern=REASON_CODE_PATTERN)

    @model_validator(mode="after")
    def _enforce_sheet_invariants(self) -> SheetAuthorization:
        if self.classification is SheetClassification.DATA_TABLE:
            if not self.normalize:
                raise ValueError("data_table Sheet는 normalize=true여야 한다")
            if self.header_row is None:
                raise ValueError("data_table Sheet는 header_row가 필요하다")
            if self.header_confidence not in (
                HeaderConfidence.HIGH,
                HeaderConfidence.MEDIUM,
            ):
                raise ValueError("data_table은 high 또는 medium Confidence만 허용된다")
            if (
                self.header_confidence is HeaderConfidence.MEDIUM
                and not self.medium_confidence_approved
            ):
                raise ValueError(
                    "medium Confidence는 medium_confidence_approved=true가 필요하다"
                )
            if self.exclusion_reason_code is not None:
                raise ValueError("data_table Sheet는 exclusion_reason_code를 가질 수 없다")
        else:
            if self.normalize:
                raise ValueError(
                    f"{self.classification.value} Sheet는 normalize 대상이 될 수 없다"
                )
            if self.classification in (
                SheetClassification.METADATA_OR_README,
                SheetClassification.EXCLUDED_NON_DATA,
            ) and not self.exclusion_reason_code:
                raise ValueError("제외 Sheet는 exclusion_reason_code가 필요하다")
            if self.classification is SheetClassification.MODEL_REFERENCE:
                if self.header_row is not None:
                    raise ValueError("model_reference Sheet는 header_row=null이어야 한다")
                if self.header_confidence is not HeaderConfidence.NONE:
                    raise ValueError(
                        "model_reference Sheet는 header_confidence=none이어야 한다"
                    )
                if self.medium_confidence_approved:
                    raise ValueError(
                        "model_reference Sheet는 medium_confidence_approved=false여야 한다"
                    )
                if self.exclusion_reason_code is not None:
                    raise ValueError(
                        "model_reference Sheet는 exclusion_reason_code를 가질 수 없다"
                    )
        if (
            self.header_confidence in (HeaderConfidence.LOW, HeaderConfidence.NONE)
            and self.normalize
        ):
            raise ValueError("low 또는 none Confidence Sheet는 normalize할 수 없다")
        return self


class OutputRootBinding(_AuthorizationModel):
    """Logical Root ID를 실제 Restricted Path에 결합하는 Local Binding.

    Actual Runtime에서는 Restricted Artifact이며 Public Repository에는
    Model과 Synthetic Fixture만 존재한다. root_path는 Validator 결과에
    복사하지 않는다.
    """

    version: int = Field(ge=1)
    root_id: str = Field(pattern=ROOT_ID_PATTERN)
    storage_class: Literal["internal-restricted"]
    root_path: str = Field(min_length=1)

    @field_validator("root_path")
    @classmethod
    def _require_absolute_path(cls, value: str) -> str:
        if not (
            PureWindowsPath(value).is_absolute() or PurePosixPath(value).is_absolute()
        ):
            raise ValueError("root_path는 Absolute Path여야 한다")
        return value


class FindingAuthorization(_AuthorizationModel):
    code: str = Field(min_length=1)
    sheet_ordinal: int | None = Field(default=None, ge=0)
    disposition: FindingDisposition
    reason_code: str = Field(pattern=REASON_CODE_PATTERN)


class ModelReferenceReview(_AuthorizationModel):
    """Drawing-only Sheet의 Drawing 의미에 대한 Restricted Review 결과 선언.

    UML 내용, Class·Attribute·Association 이름, Drawing Target, Image 이름은
    저장하지 않는다 — Controlled Boolean·Enum·Logical Evidence ID만 허용한다.
    `external_verification_technically_confirmed`는 외부 Audit System Connector가
    실제 Evidence 실재를 확인한 경우에만 true가 될 수 있다. Public Validator에는
    Connector가 없으므로 Assertion(`external_verification_asserted`)과 분리한다.
    """

    sheet_ordinal: int = Field(ge=0)
    drawing_review_category: DrawingReviewCategory
    completed: bool
    reference_model_alignment_approved: bool = False
    model_reference_scope_approved: bool = False
    model_reference_reviewer_recorded: bool = False
    evidence_reference_id: str | None = Field(default=None, pattern=ROOT_ID_PATTERN)
    external_verification_asserted: bool = False
    external_verification_technically_confirmed: bool = False


class NormalizationAuthorization(_AuthorizationModel):
    """sourceId와 Inspection Report Identity에 결합된 Normalize 승인."""

    version: int = Field(ge=1)
    source_id: str = Field(min_length=1)
    # Inspection Report 원 Byte의 SHA-256 lowercase hex (sha256: Prefix 금지)
    inspection_report_id: str = Field(pattern="^[0-9a-f]{64}$")
    output_storage_class: Literal["internal-restricted"]
    # Logical ID만 허용한다 — 실제 Path는 별도 Local Runtime Binding으로 주입한다.
    approved_output_root_id: str = Field(pattern=ROOT_ID_PATTERN)
    sheets: list[SheetAuthorization] = Field(min_length=1)
    acknowledged_findings: list[FindingAuthorization] = Field(default_factory=list)
    model_reference_reviews: list[ModelReferenceReview] = Field(default_factory=list)
    human_review_completed: bool

    @model_validator(mode="after")
    def _enforce_authorization_invariants(self) -> NormalizationAuthorization:
        ordinals = [sheet.sheet_ordinal for sheet in self.sheets]
        if len(ordinals) != len(set(ordinals)):
            raise ValueError("중복 sheet_ordinal은 허용되지 않는다")

        keys = [
            (item.code, item.sheet_ordinal) for item in self.acknowledged_findings
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("동일 code와 sheet_ordinal의 중복 Finding 승인은 허용되지 않는다")

        review_ordinals = [
            review.sheet_ordinal for review in self.model_reference_reviews
        ]
        if len(review_ordinals) != len(set(review_ordinals)):
            raise ValueError("중복 sheet_ordinal의 Model Reference Review는 허용되지 않는다")
        return self
