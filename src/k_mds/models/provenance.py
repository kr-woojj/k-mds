"""Source Provenance 모델 (ADR-0003).

Evidence는 임의 문자열이 아니라 검증된 SourceManifestEntry에서만 생성한다.
이 모델은 Hash를 계산하거나 실제 파일 존재 여부를 검사하지 않는다 —
Hash 알고리즘 강제와 파일 검사는 이번 단계의 범위가 아니다.
"""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath

from pydantic import BaseModel, ConfigDict, Field, model_validator

from k_mds.models.ontology import GovernanceStatus


class SourceManifestEntry(BaseModel):
    """source-manifest.yaml의 검증된 단일 항목."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    fal_version: str = Field(min_length=1)
    ontology_version: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    source_file: str = Field(min_length=1)
    source_hash: str = Field(min_length=1)
    resource_uri: str | None = None
    verified: bool
    status: GovernanceStatus

    @model_validator(mode="after")
    def _enforce_provenance_invariants(self) -> SourceManifestEntry:
        if self.status is GovernanceStatus.APPROVED and not self.verified:
            raise ValueError("verified=true가 아닌 Entry는 approved 상태가 될 수 없다")

        if PureWindowsPath(self.source_file).is_absolute() or PurePosixPath(
            self.source_file
        ).is_absolute():
            raise ValueError("source_file은 Repository 상대경로여야 한다 (절대경로 금지)")

        segments = self.source_file.replace("\\", "/").split("/")
        if ".." in segments:
            raise ValueError("source_file에 '..' 경로 Segment를 사용할 수 없다")
        return self
