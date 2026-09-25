"""Business payload → canonical source field 목록 (A-3 normalization).

- 중첩 JSON 을 평탄화한다 (source_path = /a/b/0/c).
- {"value": ..., "unit": ...} 패턴과 형제 `*_unit` 키에서 unit 을 추출한다.
- vessel/voyage/report context 는 확인된 키에서만 채운다 — 추측하지 않는다.
"""

from __future__ import annotations

from typing import Any

from ghg_agent.domain.models import CanonicalField, SourceProfile
from ghg_agent.reference.lookup import normalize_name

#: 평탄화 최대 중첩 깊이 (DEFECT-1). ingest 가 이미 원본을 차단하지만,
#: 파싱된 dict 를 직접 받는 경로(/api/v1/map)를 위한 방어심층. 초과 시
#: RecursionError 대신 통제된 예외로 fail-closed 한다.
MAX_FIELD_DEPTH = 64


class NormalizationError(Exception):
    """정규화 실패 — 호출부가 REVIEW_REQUIRED/422 로 닫을 수 있는 통제된 오류."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

_CONTEXT_KEYS = {
    # IMO0140/IMO0191: LAB021 사전 정규화(lab021_ingress)가 IMO 키로 바꾼 payload 의 컨텍스트 (D4, 2026-09-26)
    "vessel_context": ("vessel_id", "ship_id", "imo_no", "vessel_imo_number", "ship_name", "IMO0140"),
    "voyage_context": ("voyage_no", "voyage_id", "voyage_number", "voyage_leg", "IMO0191"),
}
_TIMESTAMP_KEYS = ("report_datetime", "event_timestamp", "timestamp", "reported_at", "IMO0603", "IMO0063", "IMO0065")

_SKIP_KEYS = {
    "report_type", "_comment",
    # transport metadata — ids_adapter 가 분리하지만 직접 호출 경로에서도 방어
    "correlation_id", "dataset_id", "resource_id", "artifact_id", "issued_at",
}


def _python_type(value: Any) -> str | None:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) or isinstance(value, float):
        return "numeric"
    if isinstance(value, str):
        return "string"
    return None


def _flatten(prefix: str, node: Any, out: list[tuple[str, str, Any]], depth: int = 0) -> None:
    if depth > MAX_FIELD_DEPTH:
        raise NormalizationError(
            "PAYLOAD_TOO_DEEP", f"중첩 깊이 {MAX_FIELD_DEPTH} 초과 — 정규화 거부"
        )
    if isinstance(node, dict):
        keys = set(node.keys())
        if "value" in keys and keys <= {"value", "unit", "description"}:
            out.append((prefix, prefix.rsplit("/", 1)[-1], node))
            return
        for key, value in node.items():
            _flatten(f"{prefix}/{key}", value, out, depth + 1)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _flatten(f"{prefix}/{index}", item, out, depth + 1)
    else:
        out.append((prefix, prefix.rsplit("/", 1)[-1], node))


def normalize_payload(
    business: dict[str, Any], profile: SourceProfile
) -> list[CanonicalField]:
    contexts: dict[str, str | None] = {"vessel_context": None, "voyage_context": None}
    for context_name, keys in _CONTEXT_KEYS.items():
        for key in keys:
            if key in business and business[key] is not None:
                contexts[context_name] = str(business[key])
                break
    timestamp = None
    for key in _TIMESTAMP_KEYS:
        if key in business and business[key] is not None:
            timestamp = str(business[key])
            break

    flat: list[tuple[str, str, Any]] = []
    _flatten("", business, flat)

    unit_siblings = {
        path: value
        for path, name, value in flat
        if name.endswith("_unit") and isinstance(value, str)
    }

    fields: list[CanonicalField] = []
    for path, name, value in flat:
        if name in _SKIP_KEYS or name.endswith("_unit"):
            continue
        unit = None
        description = None
        actual_value = value
        if isinstance(value, dict):  # {"value","unit","description"} 패턴
            actual_value = value.get("value")
            unit = value.get("unit")
            description = value.get("description")
        sibling = unit_siblings.get(f"{path}_unit")
        if unit is None and sibling is not None:
            unit = sibling
        fields.append(
            CanonicalField(
                source_path=path,
                source_name=name,
                normalized_name=normalize_name(name),
                description=description,
                value=actual_value,
                unit=unit,
                data_type=_python_type(actual_value),
                timestamp=timestamp,
                vessel_context=contexts["vessel_context"],
                voyage_context=contexts["voyage_context"],
                report_context=profile.value,
            )
        )
    return fields
