"""입력 dataset에서 필드 정의를 추출한다 (원본 불변, REQ-001, REQ-003).

지원 형식: json / json-schema / csv-columns / api-sample.
추출 결과는 MappingEngine.map_field 인자 dict 목록이다. 값·설명·이름은
데이터로만 취급되며 어떤 문자열도 해석·실행되지 않는다.
"""

from __future__ import annotations

from typing import Any

from app.skill.schemas import MAX_FIELDS, FieldSpec

_SCALAR = (str, int, float, bool, type(None))


class ExtractionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _field_kwargs(
    name: str,
    *,
    path: str | None,
    description: str | None,
    declared_type: str | None = None,
    declared_unit: str | None = None,
    declared_format: str | None = None,
    samples: list[Any] | None = None,
    service_context: str | None = None,
) -> dict[str, Any]:
    merged_description = " ".join(
        part for part in (description, service_context) if part
    ) or None
    return {
        "name": name,
        "path": path,
        "description": merged_description,
        "declared_type": declared_type,
        "declared_unit": declared_unit,
        "declared_format": declared_format,
        "sample_values": list(samples or [])[:20],
    }


def _walk_json(
    node: Any, path: str, out: list[dict[str, Any]], service_context: str | None
) -> None:
    if len(out) >= MAX_FIELDS:
        return
    if isinstance(node, dict):
        for key in node:
            _walk_json(node[key], f"{path}/{key}", out, service_context)
        return
    if isinstance(node, list):
        scalars = [item for item in node if isinstance(item, _SCALAR)]
        if scalars:
            name = path.rsplit("/", 1)[-1] or "root"
            out.append(
                _field_kwargs(
                    name,
                    path=path,
                    description=None,
                    samples=scalars[:5],
                    service_context=service_context,
                )
            )
            return
        for index, item in enumerate(node[:1]):
            _walk_json(item, f"{path}/{index}", out, service_context)
        return
    name = path.rsplit("/", 1)[-1] or "root"
    out.append(
        _field_kwargs(
            name,
            path=path,
            description=None,
            samples=[node],
            service_context=service_context,
        )
    )


def _walk_json_schema(
    schema: dict[str, Any],
    path: str,
    out: list[dict[str, Any]],
    service_context: str | None,
) -> None:
    if len(out) >= MAX_FIELDS or not isinstance(schema, dict):
        return
    properties = schema.get("properties")
    if isinstance(properties, dict):
        for key, subschema in properties.items():
            _walk_json_schema(
                subschema if isinstance(subschema, dict) else {},
                f"{path}/{key}",
                out,
                service_context,
            )
        return
    if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
        _walk_json_schema(schema["items"], f"{path}[]", out, service_context)
        return
    name = path.replace("[]", "").rsplit("/", 1)[-1]
    if not name:
        return
    declared_type = schema.get("type") if isinstance(schema.get("type"), str) else None
    out.append(
        _field_kwargs(
            name,
            path=path,
            description=(
                schema.get("description")
                if isinstance(schema.get("description"), str)
                else None
            ),
            declared_type=declared_type,
            declared_unit=(
                schema.get("x-unit") if isinstance(schema.get("x-unit"), str) else None
            ),
            declared_format=(
                schema.get("format") if isinstance(schema.get("format"), str) else None
            ),
            samples=schema.get("examples") if isinstance(schema.get("examples"), list) else [],
            service_context=service_context,
        )
    )


def _csv_columns(
    columns: list[Any], service_context: str | None
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, raw in enumerate(columns[:MAX_FIELDS], start=1):
        if not isinstance(raw, dict):
            raise ExtractionError(
                "COLUMN_DEFINITION_INVALID", f"컬럼 정의 {index}가 객체가 아니다"
            )
        spec = FieldSpec.model_validate(raw)
        out.append(
            _field_kwargs(
                spec.name,
                path=spec.path,
                description=spec.description,
                declared_type=spec.declared_type,
                declared_unit=spec.declared_unit,
                declared_format=spec.declared_format,
                samples=list(spec.sample_values),
                service_context=service_context,
            )
        )
    return out


def extract_fields(
    dataset: dict | list, input_format: str, service_context: str | None
) -> list[dict[str, Any]]:
    if input_format in ("json", "api-sample"):
        if not isinstance(dataset, (dict, list)):
            raise ExtractionError("DATASET_STRUCTURE_INVALID", "JSON 구조가 아니다")
        out: list[dict[str, Any]] = []
        _walk_json(dataset, "", out, service_context)
        fields = out
    elif input_format == "json-schema":
        if not isinstance(dataset, dict):
            raise ExtractionError("DATASET_STRUCTURE_INVALID", "JSON Schema가 아니다")
        out = []
        _walk_json_schema(dataset, "", out, service_context)
        fields = out
    elif input_format == "csv-columns":
        if not isinstance(dataset, list):
            raise ExtractionError(
                "DATASET_STRUCTURE_INVALID", "csv-columns는 컬럼 정의 배열이어야 한다"
            )
        fields = _csv_columns(dataset, service_context)
    else:  # pragma: no cover - 요청 계약에서 이미 차단됨
        raise ExtractionError("UNSUPPORTED_INPUT_FORMAT", input_format)

    if not fields:
        raise ExtractionError("NO_FIELDS_EXTRACTED", "추출된 필드가 없다")
    if len(fields) > MAX_FIELDS:
        raise ExtractionError("FIELD_LIMIT_EXCEEDED", "필드 수 상한 초과")
    return fields
