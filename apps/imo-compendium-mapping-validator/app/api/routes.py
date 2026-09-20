"""API Router (7 endpoints)."""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from app.api.errors import (
    ApiError,
    MAP_003_CODE_NOT_FOUND,
    SEC_001_UNAUTHORIZED,
    SEC_002_INTEGRITY,
    to_namespace,
)
from app.api.report import build_report, job_status
from app.api.schemas import (
    CreateMappingJobRequest,
    KrGearsReport,
    ReviewRequest,
    ValidationRequest,
)
from app.api.store import create_job, get_job, save_review
from app.registry.models import CompendiumVersion, DataElement, RefModelOccurrence
from app.registry.validator import IMO_DATA_NUMBER_PATTERN
from app.skill.schemas import MapDatasetRequest, ValidateMappingRequest
from app.skill.service import MappingSkillService, SkillError

router = APIRouter(prefix="/api/v1")


# --- 보안 의존성 ---


async def require_api_key(request: Request) -> None:
    """SEC-001: API Key 인증 (app.state.api_key 설정 시 필수)."""
    expected = getattr(request.app.state, "api_key", None)
    if expected is None:
        return
    provided = request.headers.get("X-API-Key")
    if provided != expected:
        raise ApiError(401, SEC_001_UNAUTHORIZED, "인증되지 않은 요청이다")


async def verify_integrity(request: Request) -> None:
    """SEC-002: 선택적 Payload 무결성 검증 (X-Payload-SHA256 헤더)."""
    declared = request.headers.get("X-Payload-SHA256")
    if declared is None:
        return
    body = await request.body()
    actual = hashlib.sha256(body).hexdigest()
    if declared.strip().lower() != actual:
        raise ApiError(400, SEC_002_INTEGRITY, "Payload 무결성 검증에 실패했다")


def _service(request: Request) -> MappingSkillService:
    return request.app.state.service


def _raise_from_skill_error(error: SkillError) -> None:
    namespace = to_namespace(error.code)
    status = 404 if namespace == MAP_003_CODE_NOT_FOUND else 400
    raise ApiError(status, namespace or error.code, error.message)


# --- Mapping Jobs ---


@router.post(
    "/mapping/jobs",
    status_code=201,
    dependencies=[Depends(require_api_key), Depends(verify_integrity)],
    summary="매핑 Job 생성 (동기 처리 후 저장)",
)
def create_mapping_job(
    payload: CreateMappingJobRequest, request: Request
) -> dict[str, Any]:
    service = _service(request)
    try:
        result = service.map_dataset(
            MapDatasetRequest(
                dataset=payload.dataset,
                input_format=payload.input_format,
                service_context=payload.service_context,
                compendium_version=payload.compendium_version,
                auto_accept_threshold=payload.auto_accept_threshold,
                top_k=payload.top_k,
            )
        )
    except SkillError as error:
        _raise_from_skill_error(error)
        raise AssertionError("unreachable")  # pragma: no cover

    job = create_job(
        service.session_factory,
        source_dataset_id=payload.source_dataset_id,
        compendium_version=result["provenance"]["compendiumVersion"],
        request_hash=result["provenance"]["inputHash"],
        audit_id=result["audit_id"],
        result=result,
    )
    return {
        "mapping_job_id": job.job_id,
        "status": job_status(job),
        "source_dataset_id": job.source_dataset_id,
        "compendium_version": job.compendium_version,
        "created_at": job.created_at,
        "summary": result["summary"],
        "audit_id": job.audit_id,
    }


def _load_job(request: Request, job_id: str):
    job = get_job(_service(request).session_factory, job_id)
    if job is None:
        raise ApiError(404, None, "매핑 Job을 찾을 수 없다")
    return job


@router.get(
    "/mapping/jobs/{job_id}",
    dependencies=[Depends(require_api_key)],
    summary="매핑 Job 상태 조회",
)
def get_mapping_job(job_id: str, request: Request) -> dict[str, Any]:
    job = _load_job(request, job_id)
    result = job.result
    return {
        "mapping_job_id": job.job_id,
        "status": job_status(job),
        "source_dataset_id": job.source_dataset_id,
        "compendium_version": job.compendium_version,
        "created_at": job.created_at,
        "summary": result["summary"],
        "review_queue": result["review_queue"],
        "unmapped_fields": result["unmapped_fields"],
        "resolved_reviews": job.review,
        "audit_id": job.audit_id,
    }


@router.get(
    "/mapping/jobs/{job_id}/report",
    dependencies=[Depends(require_api_key)],
    response_model=KrGearsReport,
    summary="KR GEARS 전달용 결과 Report",
)
def get_mapping_report(job_id: str, request: Request) -> dict[str, Any]:
    job = _load_job(request, job_id)
    return build_report(job)


@router.post(
    "/mapping/jobs/{job_id}/review",
    dependencies=[Depends(require_api_key), Depends(verify_integrity)],
    summary="Review 대기 필드에 대한 Human Decision 제출",
)
def submit_review(
    job_id: str, payload: ReviewRequest, request: Request
) -> dict[str, Any]:
    job = _load_job(request, job_id)
    result = job.result
    queue = {item["fieldId"]: item for item in result["review_queue"]}
    review = dict(job.review)

    for decision in payload.decisions:
        item = queue.get(decision.field_id)
        if item is None:
            raise ApiError(
                422, None, f"review 대상이 아닌 field_id: {decision.field_id}"
            )
        if decision.action == "accept":
            number = (decision.imo_data_number or "").strip().upper()
            allowed = {
                candidate["imoDataNumber"] for candidate in item["candidates"]
            }
            if not IMO_DATA_NUMBER_PATTERN.match(number) or number not in allowed:
                raise ApiError(
                    422,
                    MAP_003_CODE_NOT_FOUND,
                    "승인 대상 코드가 해당 필드의 Registry 후보 목록에 없다",
                )
            review[decision.field_id] = {
                "action": "accept",
                "imo_data_number": number,
                "note": decision.note,
            }
        else:
            review[decision.field_id] = {
                "action": "reject",
                "imo_data_number": None,
                "note": decision.note,
            }

    save_review(_service(request).session_factory, job_id, review)
    job = _load_job(request, job_id)
    return {
        "mapping_job_id": job.job_id,
        "status": job_status(job),
        "resolved_reviews": job.review,
        "remaining_review_count": sum(
            1 for item in result["review_queue"] if item["fieldId"] not in job.review
        ),
    }


# --- Validation ---


@router.post(
    "/validation",
    dependencies=[Depends(require_api_key), Depends(verify_integrity)],
    summary="제안 매핑에 대한 결정론 검증",
)
def validate(payload: ValidationRequest, request: Request) -> dict[str, Any]:
    service = _service(request)
    try:
        outcome = service.validate_mapping(
            ValidateMappingRequest(
                mappings=[
                    {"field": item.field, "imo_data_number": item.imo_data_number}
                    for item in payload.mappings
                ],
                compendium_version=payload.compendium_version,
            )
        )
    except SkillError as error:
        _raise_from_skill_error(error)
        raise AssertionError("unreachable")  # pragma: no cover

    for entry in outcome["results"]:
        for issue in entry.get("issues", []):
            issue["error_code"] = to_namespace(str(issue["code"]))
    return outcome


# --- Registry ---


@router.get(
    "/registry/versions",
    dependencies=[Depends(require_api_key)],
    summary="적재된 Compendium version 목록",
)
def registry_versions(request: Request) -> dict[str, Any]:
    service = _service(request)
    with service.session_factory() as session:
        rows = session.execute(
            select(CompendiumVersion).where(CompendiumVersion.loaded.is_(True))
        ).scalars().all()
    return {
        "versions": [
            {
                "version": row.version,
                "element_count": row.element_count,
                "occurrence_count": row.occurrence_count,
                "source_hash": row.source_hash,
            }
            for row in sorted(rows, key=lambda item: item.version)
        ]
    }


@router.get(
    "/registry/elements/{imo_data_number}",
    dependencies=[Depends(require_api_key)],
    summary="단일 Data Element 근거 record 조회",
)
def registry_element(
    imo_data_number: str, request: Request, version: str | None = None
) -> dict[str, Any]:
    service = _service(request)
    try:
        resolved, used_active = service.resolve_version(version)
    except SkillError as error:
        _raise_from_skill_error(error)
        raise AssertionError("unreachable")  # pragma: no cover

    number = imo_data_number.strip().upper()
    with service.session_factory() as session:
        element = session.execute(
            select(DataElement).where(
                DataElement.version == resolved,
                DataElement.imo_data_number == number,
            )
        ).scalar_one_or_none()
        occurrences = session.execute(
            select(RefModelOccurrence).where(
                RefModelOccurrence.version == resolved,
                RefModelOccurrence.imo_data_number == number,
            )
        ).scalars().all()
    if not IMO_DATA_NUMBER_PATTERN.match(number) or element is None:
        raise ApiError(
            404, MAP_003_CODE_NOT_FOUND, "해당 버전 Registry에 존재하지 않는 코드다"
        )
    return {
        "compendium_version": resolved,
        "used_active_version": used_active,
        "imo_data_number": element.imo_data_number,
        "name": element.name,
        "definition": element.definition,
        "format": element.format_spec,
        "code_list": element.code_list,
        "business_rule": element.business_rule,
        "status": element.status,
        "occurrences": [
            {"dataset": occ.dataset_key, "path": occ.refmodel_path}
            for occ in sorted(
                occurrences,
                key=lambda occ: (occ.dataset_key or "", occ.refmodel_path or ""),
            )
        ],
    }
