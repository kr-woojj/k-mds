"""KR GEARS 전달용 Report 조립.

- Report는 Job 결과 + Human Review 결정에서 결정론적으로 파생된다.
- payload_hash는 payload_hash 필드를 제외한 canonical JSON의 SHA-256이다.
- 오류는 MAP/VAL Namespace 코드로 표준화된다.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.api.errors import (
    MAP_001_NO_CANDIDATE,
    MAP_002_AMBIGUOUS,
    VAL_005_REQUIRED_MISSING,
    to_namespace,
)
from app.api.store import MappingJob, utc_now_iso

_PRIMARY_PRECEDENCE = ("SEC", "VER", "VAL", "MAP")


def canonical_hash(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "payload_hash"}
    return hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _primary_error(errors: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    if not errors:
        return None, None
    for prefix in _PRIMARY_PRECEDENCE:
        for entry in errors:
            if str(entry["error_code"]).startswith(prefix):
                return entry["error_code"], entry["error_detail"]
    first = errors[0]
    return first["error_code"], first["error_detail"]


def _conflict_context(rejected_candidates: list[dict[str, Any]]) -> str:
    codes: set[str] = set()
    for candidate in rejected_candidates:
        for issue in candidate.get("issues", []):
            mapped = to_namespace(str(issue.get("code")))
            if mapped is not None:
                codes.add(mapped)
    return f" (근거 충돌: {', '.join(sorted(codes))})" if codes else ""


def build_report(job: MappingJob) -> dict[str, Any]:
    result = job.result
    review = job.review

    selected: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    unresolved_review = 0

    for mapping in result["mappings"]:
        candidate = mapping["candidate"]
        selected.append(
            {
                "field_id": mapping["fieldId"],
                "field_name": mapping["fieldName"],
                "path": mapping.get("path"),
                "imo_data_number": mapping["imoDataNumber"],
                "final_score": candidate["final_score"],
                "origin": "auto",
                "registry_record_ref": {
                    "recordType": "data_element",
                    "recordId": mapping["imoDataNumber"],
                    "compendiumVersion": job.compendium_version,
                },
            }
        )

    for item in result["review_queue"]:
        field_id = item["fieldId"]
        decision = review.get(field_id)
        if decision is None:
            unresolved_review += 1
            errors.append(
                {
                    "error_code": MAP_002_AMBIGUOUS,
                    "error_detail": "복수 공식 후보가 있어 Human Review 대기 중이다",
                    "field_id": field_id,
                    "imo_data_number": None,
                }
            )
            continue
        if decision["action"] == "accept":
            number = decision["imo_data_number"]
            accepted = next(
                candidate
                for candidate in item["candidates"]
                if candidate["imoDataNumber"] == number
            )
            selected.append(
                {
                    "field_id": field_id,
                    "field_name": item["fieldName"],
                    "path": item.get("path"),
                    "imo_data_number": number,
                    "final_score": accepted["final_score"],
                    "origin": "review_accepted",
                    "registry_record_ref": {
                        "recordType": "data_element",
                        "recordId": number,
                        "compendiumVersion": job.compendium_version,
                    },
                }
            )
        else:
            errors.append(
                {
                    "error_code": MAP_002_AMBIGUOUS,
                    "error_detail": "Human Review에서 후보가 기각되었다",
                    "field_id": field_id,
                    "imo_data_number": None,
                }
            )

    for item in result["unmapped_fields"]:
        field_id = item["fieldId"]
        if item["status"] == "MISSING_CONTEXT":
            errors.append(
                {
                    "error_code": VAL_005_REQUIRED_MISSING,
                    "error_detail": "필드 문맥·필수 정보가 부족하여 매핑을 판단할 수 없다",
                    "field_id": field_id,
                    "imo_data_number": None,
                }
            )
        else:
            context = _conflict_context(item.get("rejectedCandidates", []))
            errors.append(
                {
                    "error_code": MAP_001_NO_CANDIDATE,
                    "error_detail": f"적격 Registry 후보가 없다{context}",
                    "field_id": field_id,
                    "imo_data_number": None,
                }
            )

    if unresolved_review > 0:
        validation_status = "REVIEW_REQUIRED"
    elif errors:
        validation_status = "FAIL"
    else:
        validation_status = "PASS"

    selected.sort(key=lambda item: item["field_id"])
    errors.sort(key=lambda item: (item["field_id"] or "", item["error_code"]))
    error_code, error_detail = _primary_error(errors)

    report: dict[str, Any] = {
        "mapping_job_id": job.job_id,
        "source_dataset_id": job.source_dataset_id,
        "compendium_version": job.compendium_version,
        "validation_status": validation_status,
        "selected_mappings": selected,
        "errors": errors,
        "error_code": error_code,
        "error_detail": error_detail,
        "timestamp": utc_now_iso(),
        "payload_hash": "",
    }
    report["payload_hash"] = canonical_hash(report)
    return report


def job_status(job: MappingJob) -> str:
    result = job.result
    review = job.review
    unresolved = [
        item for item in result["review_queue"] if item["fieldId"] not in review
    ]
    return "REVIEW_PENDING" if unresolved else "COMPLETED"
