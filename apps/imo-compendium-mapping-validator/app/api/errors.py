"""API 오류 코드 Namespace.

- MAP-xxx: 매핑 판정 오류
- VAL-xxx: 검증 오류
- VER-xxx: Registry 버전 오류
- SEC-xxx: 인증·무결성 오류
"""

from __future__ import annotations

from typing import Any

MAP_001_NO_CANDIDATE = "MAP-001"
MAP_002_AMBIGUOUS = "MAP-002"
MAP_003_CODE_NOT_FOUND = "MAP-003"
VAL_001_DATATYPE = "VAL-001"
VAL_002_FORMAT = "VAL-002"
VAL_003_UNIT = "VAL-003"
VAL_004_CODE_LIST = "VAL-004"
VAL_005_REQUIRED_MISSING = "VAL-005"
VER_001_UNSUPPORTED_VERSION = "VER-001"
SEC_001_UNAUTHORIZED = "SEC-001"
SEC_002_INTEGRITY = "SEC-002"

#: 엔진 내부 issue code -> API namespace code
INTERNAL_TO_NAMESPACE: dict[str, str] = {
    "DATATYPE_HARD_CONFLICT": VAL_001_DATATYPE,
    "FORMAT_FAMILY_MISMATCH": VAL_002_FORMAT,
    "UNIT_HARD_CONFLICT": VAL_003_UNIT,
    "CODE_LIST_VIOLATION": VAL_004_CODE_LIST,
    "ELEMENT_DEPRECATED": MAP_003_CODE_NOT_FOUND,
    "MAPPING_TARGET_NOT_IN_REGISTRY": MAP_003_CODE_NOT_FOUND,
    "REGISTRY_GATE_VIOLATION": MAP_003_CODE_NOT_FOUND,
    "VERSION_NOT_LOADED": VER_001_UNSUPPORTED_VERSION,
    "NO_ACTIVE_VERSION": VER_001_UNSUPPORTED_VERSION,
}


def to_namespace(internal_code: str) -> str | None:
    return INTERNAL_TO_NAMESPACE.get(internal_code)


class ApiError(Exception):
    """HTTP 응답으로 직렬화되는 도메인 오류 (fallback 없음)."""

    def __init__(self, status_code: int, error_code: str | None, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail

    def body(self) -> dict[str, Any]:
        return {"error_code": self.error_code, "error_detail": self.detail}
