"""schema_validate Skill — Pydantic 원천 모델 기반 Payload 검증 (ADR-0002).

지정된 model_name의 Pydantic 모델로 payload를 model_validate하고 항상
SkillResult를 반환한다. 예외를 외부로 던지지 않으며 LLM과 외부 API를
사용하지 않는다. Finding에는 원본 Payload 값을 포함하지 않는다.
"""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from k_mds.models import (
    BusinessRule,
    CodeList,
    Component,
    DataElement,
    Dataset,
    ElementOccurrence,
    Evidence,
    FindingSeverity,
    ResultStatus,
    SkillResult,
    ValidationFinding,
)

RULE_ID = "urn:k-mds:rule:payload-validation:0.1"

_SUPPORTED_MODELS: dict[str, type[BaseModel]] = {
    "Dataset": Dataset,
    "Component": Component,
    "DataElement": DataElement,
    "ElementOccurrence": ElementOccurrence,
    "CodeList": CodeList,
    "BusinessRule": BusinessRule,
    "Evidence": Evidence,
    "ValidationFinding": ValidationFinding,
    "SkillResult": SkillResult,
}


def _finding(code: str, message: str, path: str | None = None) -> ValidationFinding:
    return ValidationFinding(
        severity=FindingSeverity.ERROR,
        code=code,
        message=message,
        rule_id=RULE_ID,
        path=path,
        actual_value=None,
    )


def _loc_to_path(loc: tuple[int | str, ...]) -> str:
    if not loc:
        return "$"
    return "$." + ".".join(str(part) for part in loc)


def _fail(model_name: str, errors: list[ValidationFinding]) -> SkillResult:
    return SkillResult(
        status=ResultStatus.FAIL,
        human_review_required=True,
        data={"modelName": model_name, "valid": False},
        errors=errors,
    )


def schema_validate(payload: dict[str, object], model_name: str) -> SkillResult:
    """payload를 model_name의 Pydantic 모델로 검증한다.

    유효하면 PASS와 함께 normalizedPayload(model_dump(by_alias=True, mode="json"))를
    반환한다. 바깥쪽 SkillResult는 항상 Skill 실행 Contract를 유지하며,
    model_name == "SkillResult"인 경우에도 검증 대상 Payload는 normalizedPayload에만
    들어간다.
    """
    if not isinstance(payload, dict):
        return _fail(
            model_name,
            [_finding("PAYLOAD_NOT_OBJECT", "payload는 dict(JSON Object)여야 한다", path="$")],
        )

    model_cls = _SUPPORTED_MODELS.get(model_name)
    if model_cls is None:
        supported = ", ".join(sorted(_SUPPORTED_MODELS))
        return _fail(
            model_name,
            [
                _finding(
                    "UNSUPPORTED_MODEL_NAME",
                    f"지원하지 않는 model_name이다 (지원: {supported})",
                )
            ],
        )

    try:
        instance = model_cls.model_validate(payload)
    except ValidationError as exc:
        errors = [
            _finding(
                "PAYLOAD_VALIDATION_ERROR",
                str(item["msg"]),
                path=_loc_to_path(item["loc"]),
            )
            for item in exc.errors(include_url=False, include_input=False, include_context=False)
        ]
        return _fail(model_name, errors)

    return SkillResult(
        status=ResultStatus.PASS,
        human_review_required=False,
        data={
            "modelName": model_name,
            "valid": True,
            "normalizedPayload": instance.model_dump(by_alias=True, mode="json"),
        },
    )
