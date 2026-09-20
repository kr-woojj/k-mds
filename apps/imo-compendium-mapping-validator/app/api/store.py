"""매핑 Job 저장소 (SQLite, migrations/0002)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column, sessionmaker

from app.registry.models import Base


class MappingJob(Base):
    __tablename__ = "mapping_job"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    source_dataset_id: Mapped[str] = mapped_column(String(128), nullable=False)
    compendium_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    audit_id: Mapped[str] = mapped_column(String(64), nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    review_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def result(self) -> dict[str, Any]:
        return json.loads(self.result_json)

    @property
    def review(self) -> dict[str, Any]:
        return json.loads(self.review_json) if self.review_json else {}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_job(
    session_factory: sessionmaker[Session],
    *,
    source_dataset_id: str,
    compendium_version: str,
    request_hash: str,
    audit_id: str,
    result: dict[str, Any],
) -> MappingJob:
    with session_factory() as session, session.begin():
        job = MappingJob(
            job_id="PENDING",
            source_dataset_id=source_dataset_id,
            compendium_version=compendium_version,
            created_at=utc_now_iso(),
            request_hash=request_hash,
            audit_id=audit_id,
            result_json=json.dumps(result, ensure_ascii=False, sort_keys=True),
        )
        session.add(job)
        session.flush()
        job.job_id = f"MAPJOB-{job.seq:08d}"
    return job


def get_job(
    session_factory: sessionmaker[Session], job_id: str
) -> MappingJob | None:
    with session_factory() as session:
        return (
            session.query(MappingJob).filter(MappingJob.job_id == job_id).one_or_none()
        )


def save_review(
    session_factory: sessionmaker[Session], job_id: str, review: dict[str, Any]
) -> None:
    with session_factory() as session, session.begin():
        job = (
            session.query(MappingJob).filter(MappingJob.job_id == job_id).one_or_none()
        )
        if job is not None:
            job.review_json = json.dumps(review, ensure_ascii=False, sort_keys=True)
