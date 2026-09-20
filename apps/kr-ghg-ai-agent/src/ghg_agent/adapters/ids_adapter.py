"""IngressAgent 지원 어댑터 (D-5).

K-MDS IDS Consumer 의 표준 envelope 는 workspace 어디에서도 확인되지 않았다
(IDS-testbed 의 DSC v6 pull flow 는 artifact raw bytes 를 전달, envelope 정의 없음).
따라서 임의 표준 envelope 를 발명하지 않고 다음만 구분한다.

- RAW_JSON_BODY : JSON object body — business payload 로 처리
- FILE_REFERENCE: {"artifact_url": ...} 형태 참조만 온 경우 (미해석, 보존)
- UNKNOWN      : 그 외 — 원본 보존 후 REVIEW_REQUIRED/422

transport metadata(HTTP header 유래)와 maritime business payload 를 분리한다.
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from dataclasses import dataclass
from typing import Any

from ghg_agent.domain.models import IngressBodyType, IngressResult

MAX_PAYLOAD_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class ResourceLimits:
    """Wide payload 방어 한계 (F-STEP6-1). config 에서 clamp 된 값이 주입된다."""

    max_node_count: int = 3000
    max_array_length: int = 1000
    max_field_count: int = 2000
    max_scalar_text_length: int = 8192


DEFAULT_LIMITS = ResourceLimits()


def measure_payload(root: Any) -> tuple[int, int, int, int, bool]:
    """비재귀(iterative) 순회로 (node_count, field_count(leaves),
    max_array_length, max_scalar_text_length, has_non_finite) 를 한 번에 계산."""
    node = leaves = max_arr = max_scalar = 0
    non_finite = False
    stack = [root]
    while stack:
        obj = stack.pop()
        node += 1
        if isinstance(obj, dict):
            stack.extend(obj.values())
        elif isinstance(obj, list):
            if len(obj) > max_arr:
                max_arr = len(obj)
            stack.extend(obj)
        else:
            leaves += 1
            if isinstance(obj, str):
                if len(obj) > max_scalar:
                    max_scalar = len(obj)
            elif isinstance(obj, float) and not math.isfinite(obj):
                non_finite = True
    return node, leaves, max_arr, max_scalar, non_finite
#: JSON 중첩 깊이 상한 (DEFECT-2). 재귀 파서(json.loads)를 호출하기 전에 원본
#: bytes 를 스캔해 초과 시 파싱 자체를 하지 않는다 — RecursionError fail-open 차단.
MAX_JSON_DEPTH = 64

#: transport 성 필드 — business payload 에서 분리한다 (확인된 IDS 용어만 사용)
TRANSPORT_KEYS = {"correlation_id", "dataset_id", "resource_id", "artifact_id", "issued_at"}


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def max_json_depth(raw: bytes) -> int:
    """원본 bytes 에서 문자열 리터럴 밖 괄호 중첩의 최대 깊이 (비재귀 스캔)."""
    depth = deepest = 0
    in_string = escape = False
    for byte in raw:
        ch = chr(byte)
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            depth += 1
            deepest = max(deepest, depth)
        elif ch in "}]":
            depth -= 1
    return deepest


def classify_body(payload: Any) -> IngressBodyType:
    if isinstance(payload, dict):
        if set(payload.keys()) & {"artifact_url", "data_link"} and not payload.get("payload"):
            return IngressBodyType.FILE_REFERENCE
        return IngressBodyType.RAW_JSON_BODY
    return IngressBodyType.UNKNOWN


def ingest(
    raw: bytes,
    content_type: str | None,
    correlation_id: str | None = None,
    limits: ResourceLimits | None = None,
) -> tuple[IngressResult, dict[str, Any] | None]:
    """(IngressResult, business_payload). UNKNOWN 이면 business_payload=None."""
    lim = limits or DEFAULT_LIMITS
    errors: list[str] = []
    if len(raw) > MAX_PAYLOAD_BYTES:
        errors.append("PAYLOAD_TOO_LARGE")
    if max_json_depth(raw) > MAX_JSON_DEPTH:
        # DEFECT-2: 재귀 파서 호출 전 차단 (fail-closed). 파싱하지 않는다.
        errors.append("BODY_TOO_DEEP")
    digest = sha256_bytes(raw)
    resolved_id = correlation_id or f"run-{uuid.uuid4().hex[:12]}"

    payload: Any = None
    if not errors:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            errors.append("BODY_NOT_JSON")
        except RecursionError:
            # DEFECT-2 belt-and-suspenders: 깊이 스캔을 우회하는 병리적 입력도
            # RecursionError 를 fail-open 시키지 않고 BODY_TOO_DEEP 로 닫는다.
            errors.append("BODY_TOO_DEEP")

    # F-STEP6-1/6-3/6-4: Profile·Mapping 전에 resource limit·비유한수·body-type 을 검사한다.
    if not errors:
        node, leaves, max_arr, max_scalar, non_finite = measure_payload(payload)
        if non_finite:
            errors.append("NON_FINITE_NUMBER_NOT_ALLOWED")  # F-STEP6-4
        if max_arr > lim.max_array_length:
            errors.append("ARRAY_TOO_LARGE")
        if max_scalar > lim.max_scalar_text_length:
            errors.append("FIELD_VALUE_TOO_LARGE")
        if node > lim.max_node_count or leaves > lim.max_field_count:
            errors.append("PAYLOAD_TOO_COMPLEX")
        if not errors and not isinstance(payload, dict):
            # F-STEP6-3: 최상위 array/scalar/null 은 명시적 거부 (422 로 통일)
            errors.append("UNSUPPORTED_BODY_TYPE")

    body_type = IngressBodyType.UNKNOWN if errors else classify_body(payload)

    transport: dict[str, Any] = {}
    business: dict[str, Any] | None = None
    if body_type == IngressBodyType.RAW_JSON_BODY:
        transport = {k: payload[k] for k in TRANSPORT_KEYS if k in payload}
        business = {k: v for k, v in payload.items() if k not in TRANSPORT_KEYS}
        if not business:
            errors.append("EMPTY_BUSINESS_PAYLOAD")
            body_type = IngressBodyType.UNKNOWN
            business = None

    result = IngressResult(
        correlation_id=str(payload.get("correlation_id", resolved_id))
        if isinstance(payload, dict)
        else resolved_id,
        body_type=body_type,
        content_type=content_type,
        raw_sha256=digest,
        payload_bytes=len(raw),
        transport_metadata=transport,
        dataset_metadata={
            k: transport[k] for k in ("dataset_id", "resource_id", "artifact_id") if k in transport
        },
        validation_errors=errors,
    )
    return result, business
