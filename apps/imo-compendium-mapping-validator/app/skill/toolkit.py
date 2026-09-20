"""Agent-facing Tool Registry와 Dispatch.

- `list_tools()`: 도구 이름·설명·입력 JSON Schema (Agent 등록용)
- `invoke(name, arguments)`: 항상 {"ok": bool, ...} envelope을 반환한다.
  실패는 예외가 아닌 오류 코드로 전달되며 fallback하지 않는다.
- 입력 필드명·설명에 포함된 지시문(prompt injection)은 데이터로만 처리된다 —
  이 계층과 하위 파이프라인 전체에 명령 해석 경로가 존재하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from app.skill.schemas import (
    CompareVersionsRequest,
    ExplainMappingRequest,
    ListCandidatesRequest,
    MapDatasetRequest,
    ValidateMappingRequest,
)
from app.skill.service import MappingSkillService, SkillError

TOOL_NAMES = (
    "map_dataset",
    "validate_mapping",
    "explain_mapping",
    "list_candidates",
    "compare_compendium_versions",
)

_TOOL_DESCRIPTIONS: dict[str, str] = {
    "map_dataset": (
        "이기종 데이터셋(JSON/JSON Schema/CSV 컬럼/API 샘플)의 필드를 "
        "IMO Compendium Registry와 매핑한다. 결과는 mappings/review_queue/"
        "unmapped_fields로 분류되고 모든 점수 구성요소와 근거가 보존된다."
    ),
    "validate_mapping": (
        "제안된 필드-IMO 매핑 목록을 Registry 정의(타입·단위·형식)에 대해 "
        "결정론적으로 검증한다."
    ),
    "explain_mapping": (
        "특정 필드-IMO 후보의 점수 구성요소·채널·순위·근거 record 요약을 "
        "반환한다 (판정 변경 없음)."
    ),
    "list_candidates": "단일 필드의 top-k Registry 후보를 점수 구성요소와 함께 반환한다.",
    "compare_compendium_versions": (
        "두 Compendium version의 added/modified/deprecated 차이를 반환한다."
    ),
}

_REQUEST_MODELS: dict[str, type[BaseModel]] = {
    "map_dataset": MapDatasetRequest,
    "validate_mapping": ValidateMappingRequest,
    "explain_mapping": ExplainMappingRequest,
    "list_candidates": ListCandidatesRequest,
    "compare_compendium_versions": CompareVersionsRequest,
}


@dataclass
class MappingToolkit:
    service: MappingSkillService

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": name,
                "description": _TOOL_DESCRIPTIONS[name],
                "inputSchema": _REQUEST_MODELS[name].model_json_schema(),
            }
            for name in TOOL_NAMES
        ]

    def invoke(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        model = _REQUEST_MODELS.get(tool_name)
        if model is None:
            return _error("UNKNOWN_TOOL", f"지원하지 않는 도구: {tool_name}")
        if not isinstance(arguments, dict):
            return _error("INVALID_ARGUMENTS", "arguments는 객체여야 한다")
        try:
            request = model.model_validate(arguments)
        except ValidationError as error:
            # 원문 입력값을 오류에 복사하지 않는다 — 위치와 오류 유형만 요약.
            locations = sorted(
                {
                    "/".join(str(part) for part in item["loc"]) or "$"
                    for item in error.errors(
                        include_url=False, include_input=False, include_context=False
                    )
                }
            )
            return _error(
                "INVALID_ARGUMENTS", "입력 계약 위반: " + ", ".join(locations)
            )

        handler: Callable[[Any], dict[str, Any]] = getattr(self.service, tool_name)
        try:
            result = handler(request)
        except SkillError as error:
            return _error(error.code, error.message)
        return {"ok": True, "tool": tool_name, "result": result}


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}
