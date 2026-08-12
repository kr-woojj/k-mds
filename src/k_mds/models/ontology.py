"""k-mds Core Ontology 객체 모델 (AGENTS.md §2.3, §6).

DataElement(IMO ID 기반 개념 정의)와 ElementOccurrence(Dataset 내 사용 문맥)를
별도 객체로 관리한다. 하나의 IMO ID는 여러 Dataset과 Technical Position에
존재할 수 있으므로 단일 Path로 고정하지 않는다.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GovernanceStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REVIEW_REQUIRED = "review_required"
    UNRESOLVED = "unresolved"
    DEPRECATED = "deprecated"


class _OntologyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Dataset(_OntologyModel):
    dataset_id: str = Field(min_length=1)
    fal_version: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    status: GovernanceStatus = GovernanceStatus.DRAFT


class Component(_OntologyModel):
    component_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    parent_component_id: str | None = None
    sequence: int | None = Field(default=None, ge=1)
    status: GovernanceStatus = GovernanceStatus.DRAFT


class DataElement(_OntologyModel):
    """IMO ID로 식별되는 데이터 요소의 개념 정의."""

    imo_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    definition: str | None = None
    data_format: str | None = None
    representation_term: str | None = None
    status: GovernanceStatus = GovernanceStatus.DRAFT


class ElementOccurrence(_OntologyModel):
    """특정 Dataset과 Technical Position에서의 DataElement 사용 문맥."""

    occurrence_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    # DataElement 참조는 필수다. Occurrence는 독립 표준사실이 될 수 없다.
    element_imo_id: str = Field(min_length=1)
    technical_position: str | None = None
    parent_component_id: str | None = None
    sequence: int | None = Field(default=None, ge=1)
    cardinality: str | None = None
    usage: str | None = None
    status: GovernanceStatus = GovernanceStatus.DRAFT

    @model_validator(mode="after")
    def _unverified_position_requires_review(self) -> ElementOccurrence:
        # Technical Position을 확인하지 못한 항목은 approved가 될 수 없다 (AGENTS.md §8).
        if self.technical_position is None and self.status is GovernanceStatus.APPROVED:
            raise ValueError(
                "Technical Position이 확인되지 않은 Occurrence는 approved 상태가 될 수 없다 "
                "(review_required 또는 unresolved로 기록한다)"
            )
        return self


class CodeList(_OntologyModel):
    code_list_id: str = Field(min_length=1)
    fal_version: str = Field(min_length=1)
    name: str = Field(min_length=1)
    codes: list[str] = Field(default_factory=list)
    status: GovernanceStatus = GovernanceStatus.DRAFT


class BusinessRule(_OntologyModel):
    rule_id: str = Field(min_length=1)
    profile: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    status: GovernanceStatus = GovernanceStatus.DRAFT
