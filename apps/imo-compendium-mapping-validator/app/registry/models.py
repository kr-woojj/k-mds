"""Registry SQLAlchemy ORM 모델.

스키마의 원천 DDL은 `migrations/0001_initial.sql`이며 이 모델과 1:1로
동기화한다 (마이그레이션 정책은 migrations/README.md 참조).

설계 규칙:
- `compendium_version` 단위 immutable snapshot (REQ-008). 어떤 코드 경로도
  기존 버전 행을 UPDATE/DELETE 하지 않는다.
- 동일 버전 안에서 IMO Data Number는 Data Element 1행으로 유일하고
  (UNIQUE 제약), Reference Model 상 반복 위치는 `refmodel_occurrence`로
  분리 저장한다 (Dataset Member와 Occurrence 혼동 금지).
- `audit_event`는 append-only이며 결과 재현성을 위해 timestamp를 본문
  결과에 사용하지 않는다 — 순서는 seq로만 표현한다 (REQ-026, REQ-030).
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CompendiumVersion(Base):
    __tablename__ = "compendium_version"

    version: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_format: Mapped[str] = mapped_column(String(16), nullable=False)
    element_count: Mapped[int] = mapped_column(Integer, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    #: 적재 트랜잭션이 끝까지 성공했을 때만 True. False 행은 존재하지 않아야
    #: 정상이다 (전체 트랜잭션 rollback 정책, 요구사항 7).
    loaded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DataElement(Base):
    __tablename__ = "data_element"
    __table_args__ = (
        UniqueConstraint("version", "imo_data_number", name="uq_element_version_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(
        String(64), ForeignKey("compendium_version.version"), nullable=False
    )
    imo_data_number: Mapped[str] = mapped_column(String(7), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    format_spec: Mapped[str | None] = mapped_column(String(256), nullable=True)
    code_list: Mapped[str | None] = mapped_column(String(256), nullable=True)
    business_rule: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class RefModelOccurrence(Base):
    __tablename__ = "refmodel_occurrence"
    __table_args__ = (
        UniqueConstraint(
            "version",
            "imo_data_number",
            "dataset_key",
            "refmodel_path",
            name="uq_occurrence_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(
        String(64), ForeignKey("compendium_version.version"), nullable=False
    )
    imo_data_number: Mapped[str] = mapped_column(String(7), nullable=False)
    dataset_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    refmodel_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_event"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    #: 요약 정보(JSON 직렬화 문자열). 원본 payload는 저장하지 않는다 (REQ-026).
    detail: Mapped[str] = mapped_column(Text, nullable=False)
