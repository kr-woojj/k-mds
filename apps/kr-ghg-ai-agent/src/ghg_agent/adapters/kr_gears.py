"""KRGearsTransformationAgent + delivery adapter (A-6).

계약 현황 (discovery 근거):
- 실계약 확인: imo-compendium-mapping-validator/app/api/schemas.py 의
  `KrGearsReport` (검증 결과 전달 envelope, openapi.json 에 포함) → 이 부분만
  CONTRACT_VERIFIED 로 취급하며, 실제 Pydantic 모델로 검증한다.
- 미확인: KR GEARs 의 GHG 보고 제출 스키마/필드 사전/endpoint → 본 모듈의
  payload 는 PROVISIONAL 이며 실제 delivery 는 차단된다 (mock 만 허용).

Noon / Event / Performance 변환 정책은 분리된 rule id 를 갖는다.
단위 변환: canonical unit 의 권위 근거 미확인 → 변환하지 않는다
(conversion_applied=False, 한계로 문서화).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from ghg_agent.domain.models import (
    CanonicalField,
    ContractStatus,
    DeliveryResult,
    FieldProvenance,
    MappingResult,
    SourceProfile,
    TransformResult,
    ValidationResult,
    ValidationVerdict,
)

RULE_VERSION = "0.1.0"
_RULES = {
    SourceProfile.NOON_REPORT: "TR-NOON-1",
    SourceProfile.EVENT_REPORT: "TR-EVENT-1",
    SourceProfile.VESSEL_PERFORMANCE: "TR-PERF-1",
}


def _value_hash(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def transform(
    mapping_result: MappingResult,
    fields: list[CanonicalField],
    validation: ValidationResult,
    correlation_id: str,
) -> TransformResult:
    """VALIDATED 매핑만 입력으로 허용한다 (A-6)."""
    if validation.overall not in (ValidationVerdict.PASS, ValidationVerdict.WARNING):
        raise ValueError(
            f"검증 미통과 매핑은 변환할 수 없다 (overall={validation.overall.value})"
        )
    profile = mapping_result.profile
    rule_id = _RULES.get(profile)
    if rule_id is None:
        raise ValueError(f"변환 정책이 없는 profile: {profile.value}")

    fields_by_path = {field.source_path: field for field in fields}
    provenance: list[FieldProvenance] = []
    entries: list[dict[str, Any]] = []

    for m in mapping_result.fields:
        if not m.imo_data_number:
            continue
        field = fields_by_path.get(m.source_path)
        target_path = f"/data_elements/{m.imo_data_number}"
        entry: dict[str, Any] = {
            "imo_data_number": m.imo_data_number,
            "imo_data_element_name": m.imo_data_element_name,
            "value": field.value if field else None,
            "unit": field.unit if field else None,
            "source_field": m.source_name,
        }
        if profile == SourceProfile.EVENT_REPORT and field is not None:
            entry["event_timestamp"] = field.timestamp
            entry["voyage"] = field.voyage_context
        entries.append(entry)
        provenance.append(
            FieldProvenance(
                target_path=target_path,
                source_path=m.source_path,
                source_value_hash=_value_hash(field.value) if field else None,
                imo_data_number=m.imo_data_number,
                transformation_rule_id=rule_id,
                transformation_rule_version=RULE_VERSION,
                original_unit=field.unit if field else None,
                target_unit=field.unit if field else None,
                conversion_applied=False,
                contract_status=ContractStatus.PROVISIONAL,
            )
        )

    voyage_context = next(
        (f.voyage_context for f in fields if f.voyage_context), None
    )
    payload: dict[str, Any] = {
        "contract_status": ContractStatus.PROVISIONAL.value,
        "profile": profile.value,
        "reference_model_version": mapping_result.reference_model_version,
        "voyage": voyage_context,
        "data_elements": sorted(entries, key=lambda e: str(e["imo_data_number"])),
    }
    if profile == SourceProfile.EVENT_REPORT:
        payload["data_elements"] = sorted(
            entries, key=lambda e: (str(e.get("event_timestamp") or ""), str(e["imo_data_number"]))
        )

    verdict_report = _build_verdict_report(mapping_result, validation, correlation_id)

    return TransformResult(
        correlation_id=correlation_id,
        profile=profile,
        contract_status=ContractStatus.PROVISIONAL,
        payload=payload,
        provenance=provenance,
        verdict_report=verdict_report,
        warnings=(
            ["KR GEARs 제출 스키마 미확인 — payload 는 PROVISIONAL, 실제 delivery 차단"]
        ),
    )


def _build_verdict_report(
    mapping_result: MappingResult,
    validation: ValidationResult,
    correlation_id: str,
) -> dict[str, Any] | None:
    """실계약 KrGearsReport(validator Pydantic 모델)로 검증한 verdict envelope.

    validator import 가 불가능하면 None 을 반환한다 (성공 위장 금지).
    """
    try:
        from app.api.schemas import KrGearsReport  # skill adapter 가 sys.path 준비
    except ImportError:
        return None

    status = {
        ValidationVerdict.PASS: "PASS",
        ValidationVerdict.WARNING: "PASS",
        ValidationVerdict.FAIL: "FAIL",
        ValidationVerdict.NOT_VERIFIED: "REVIEW_REQUIRED",
        ValidationVerdict.NOT_APPLICABLE: "REVIEW_REQUIRED",
    }[validation.overall]

    selected = []
    for index, m in enumerate(
        (m for m in mapping_result.fields if m.imo_data_number), start=1
    ):
        selected.append(
            {
                "field_id": f"f{index:04d}",
                "field_name": m.source_name,
                "path": m.source_path,
                "imo_data_number": m.imo_data_number,
                "final_score": float(m.confidence or 0.0),
                "origin": "auto",
                "registry_record_ref": {
                    "recordType": "data_element",
                    "recordId": m.imo_data_number,
                    "compendiumVersion": mapping_result.reference_model_version,
                },
            }
        )
    errors = [
        {
            "error_code": item.code or "UNSPECIFIED",
            "error_detail": (item.message or "")[:200],
            "field_id": None,
            "imo_data_number": item.imo_data_number,
        }
        for item in validation.items
        if item.verdict == ValidationVerdict.FAIL
    ]
    body = {
        "mapping_job_id": f"GHGPOC-{correlation_id}",
        "source_dataset_id": correlation_id,
        "compendium_version": mapping_result.reference_model_version,
        "validation_status": status,
        "selected_mappings": selected,
        "errors": errors,
        "error_code": None,
        "error_detail": None,
        "timestamp": datetime.now(UTC).isoformat(),
        "payload_hash": "",
    }
    body["payload_hash"] = hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    report = KrGearsReport.model_validate(body)  # 실계약 검증 — 실패 시 예외 전파
    return report.model_dump(mode="json")


def group_events_by_voyage(results: list[TransformResult]) -> dict[str, Any]:
    """Event transform 결과를 항차 단위로 그룹화하고 결정론적으로 정렬한다 (E2E-3).

    정렬 키: (event_timestamp, correlation_id) — timestamp 동률 시에도 결정론 유지.
    """
    voyages: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        if result.profile != SourceProfile.EVENT_REPORT:
            raise ValueError("EVENT_REPORT profile 만 그룹화할 수 있다")
        voyage = str(result.payload.get("voyage") or "UNKNOWN_VOYAGE")
        timestamps = [
            str(e.get("event_timestamp"))
            for e in result.payload.get("data_elements", [])
            if e.get("event_timestamp")
        ]
        voyages.setdefault(voyage, []).append(
            {
                "correlation_id": result.correlation_id,
                "event_timestamp": min(timestamps) if timestamps else "",
                "contract_status": result.contract_status.value,
                "data_element_count": len(result.payload.get("data_elements", [])),
                "provenance_refs": [p.source_path for p in result.provenance],
            }
        )
    return {
        "contract_status": ContractStatus.PROVISIONAL.value,
        "voyages": {
            voyage: sorted(events, key=lambda e: (e["event_timestamp"], e["correlation_id"]))
            for voyage, events in sorted(voyages.items())
        },
    }


def deliver(
    transform_result: TransformResult,
    mode: str,
    api_url: str = "",
) -> DeliveryResult:
    """PROVISIONAL contract 는 실제 delivery 를 차단한다 (fail-closed)."""
    if mode == "mock":
        return DeliveryResult(
            correlation_id=transform_result.correlation_id,
            mode="mock",
            real_call=False,
            status="DELIVERED",
            detail="mock delivery — 외부 전송 없음",
        )
    if transform_result.contract_status != ContractStatus.CONTRACT_VERIFIED:
        return DeliveryResult(
            correlation_id=transform_result.correlation_id,
            mode=mode,
            real_call=False,
            status="BLOCKED",
            detail="KR GEARs 실계약 미확인 — 실제 delivery 차단 (PROVISIONAL)",
        )
    import httpx

    try:
        response = httpx.post(api_url, json=transform_result.payload, timeout=30.0)
        return DeliveryResult(
            correlation_id=transform_result.correlation_id,
            mode="http",
            real_call=True,
            status="DELIVERED" if response.status_code < 300 else "FAILED",
            detail=f"HTTP {response.status_code}",
        )
    except httpx.HTTPError as error:
        return DeliveryResult(
            correlation_id=transform_result.correlation_id,
            mode="http",
            real_call=True,
            status="FAILED",
            detail=type(error).__name__,
        )
