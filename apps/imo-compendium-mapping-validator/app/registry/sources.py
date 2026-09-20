"""공식 export 파일(Excel/CSV/JSON) 파서.

- 원본 파일은 절대 수정하지 않는다 (REQ-003). Excel은 read-only로 연다.
- 컬럼 헤더는 별칭 사전으로 정규화한다. 알 수 없는 컬럼은 무시하되
  보고용으로 수집한다.
- 파서는 검증 판정을 하지 않는다 — 구조화된 레코드와 파싱 이슈만 반환하고,
  패턴·중복·버전 규칙은 validator가 담당한다 (책임 분리).
"""

from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

#: 정규화된 헤더 -> 내부 필드명
HEADER_ALIASES: dict[str, str] = {
    "imo_data_number": "imo_data_number",
    "data_number": "imo_data_number",
    "imo_data_no": "imo_data_number",
    "data_element": "name",
    "element_name": "name",
    "name": "name",
    "definition": "definition",
    "format": "format_spec",
    "format_spec": "format_spec",
    "code_list": "code_list",
    "code_lists": "code_list",
    "business_rule": "business_rule",
    "business_rules": "business_rule",
    "dataset": "dataset_key",
    "dataset_key": "dataset_key",
    "sub_model": "dataset_key",
    "submodel": "dataset_key",
    "dataset_sub_model": "dataset_key",
    "reference_model_path": "refmodel_path",
    "refmodel_path": "refmodel_path",
    "path": "refmodel_path",
    "status": "status",
    "version": "declared_version",
}

SUPPORTED_SUFFIXES = {".csv", ".json", ".xlsx"}


class RegistryRecordInput(BaseModel):
    """파일에서 추출된 단일 레코드 (검증 전 상태)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    imo_data_number: str | None = None
    name: str | None = None
    definition: str | None = None
    format_spec: str | None = None
    code_list: str | None = None
    business_rule: str | None = None
    dataset_key: str | None = None
    refmodel_path: str | None = None
    status: str = "active"
    declared_version: str | None = None
    #: 원본 파일 내 행 위치 (오류 보고용, 1-based 데이터 행 번호)
    source_row: int = 0


@dataclass(frozen=True)
class ParseIssue:
    code: str
    row: int
    message: str


@dataclass(frozen=True)
class ParsedSource:
    source_format: str
    records: list[RegistryRecordInput]
    issues: list[ParseIssue]
    unknown_columns: list[str]


def _normalize_header(header: object) -> str:
    text = unicodedata.normalize("NFKC", str(header or ""))
    text = text.strip().lower()
    text = re.sub(r"[\s/\-]+", "_", text)
    return text


def _map_headers(raw_headers: list[object]) -> tuple[dict[int, str], list[str]]:
    mapping: dict[int, str] = {}
    unknown: list[str] = []
    for index, header in enumerate(raw_headers):
        normalized = _normalize_header(header)
        if not normalized:
            continue
        field = HEADER_ALIASES.get(normalized)
        if field is None:
            unknown.append(normalized)
        else:
            mapping[index] = field
    return mapping, sorted(set(unknown))


def _cell_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _build_record(
    field_values: dict[str, str | None], row_number: int
) -> tuple[RegistryRecordInput | None, ParseIssue | None]:
    payload: dict[str, object] = {
        key: value for key, value in field_values.items() if value is not None
    }
    payload["source_row"] = row_number
    try:
        return RegistryRecordInput.model_validate(payload), None
    except ValidationError:
        return None, ParseIssue(
            code="ROW_PARSE_ERROR",
            row=row_number,
            message="행을 레코드 구조로 해석할 수 없다",
        )


def _rows_to_records(
    header_map: dict[int, str], rows: list[list[object]]
) -> tuple[list[RegistryRecordInput], list[ParseIssue]]:
    records: list[RegistryRecordInput] = []
    issues: list[ParseIssue] = []
    for row_number, row in enumerate(rows, start=1):
        values = {field: None for field in HEADER_ALIASES.values()}
        non_empty = False
        for index, field in header_map.items():
            cell = _cell_text(row[index]) if index < len(row) else None
            if cell is not None:
                non_empty = True
                values[field] = cell
        if not non_empty:
            continue  # 완전 빈 행은 건너뛴다
        record, issue = _build_record(values, row_number)
        if issue is not None:
            issues.append(issue)
        elif record is not None:
            records.append(record)
    return records, issues


def _parse_csv(raw: bytes) -> ParsedSource:
    text_stream = io.StringIO(raw.decode("utf-8-sig"))
    reader = csv.reader(text_stream)
    table = list(reader)
    if not table:
        return ParsedSource(
            "csv", [], [ParseIssue("EMPTY_SOURCE", 0, "빈 CSV 파일이다")], []
        )
    header_map, unknown = _map_headers(list(table[0]))
    if not header_map:
        return ParsedSource(
            "csv",
            [],
            [ParseIssue("HEADER_NOT_RECOGNIZED", 0, "인식 가능한 헤더가 없다")],
            unknown,
        )
    records, issues = _rows_to_records(header_map, [list(row) for row in table[1:]])
    return ParsedSource("csv", records, issues, unknown)


def _parse_json(raw: bytes) -> ParsedSource:
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ParsedSource(
            "json", [], [ParseIssue("JSON_PARSE_ERROR", 0, "JSON을 해석할 수 없다")], []
        )
    if isinstance(document, dict):
        items = document.get("records")
    else:
        items = document
    if not isinstance(items, list):
        return ParsedSource(
            "json",
            [],
            [ParseIssue("JSON_STRUCTURE_INVALID", 0, "records 배열이 없다")],
            [],
        )
    records: list[RegistryRecordInput] = []
    issues: list[ParseIssue] = []
    unknown: set[str] = set()
    for row_number, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            issues.append(
                ParseIssue("ROW_PARSE_ERROR", row_number, "레코드가 객체가 아니다")
            )
            continue
        values: dict[str, str | None] = {
            field: None for field in HEADER_ALIASES.values()
        }
        for key, value in item.items():
            normalized = _normalize_header(key)
            field = HEADER_ALIASES.get(normalized)
            if field is None:
                if normalized:
                    unknown.add(normalized)
                continue
            values[field] = _cell_text(value)
        if all(value is None for value in values.values()):
            continue
        record, issue = _build_record(values, row_number)
        if issue is not None:
            issues.append(issue)
        elif record is not None:
            records.append(record)
    return ParsedSource("json", records, issues, sorted(unknown))


def _parse_xlsx(path: Path) -> ParsedSource:
    import openpyxl

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
    try:
        best: ParsedSource | None = None
        for sheet in workbook.worksheets:
            rows_iter = sheet.iter_rows(values_only=True)
            try:
                header_row = next(rows_iter)
            except StopIteration:
                continue
            header_map, unknown = _map_headers(list(header_row))
            if "imo_data_number" not in header_map.values():
                continue
            data_rows = [list(row) for row in rows_iter]
            records, issues = _rows_to_records(header_map, data_rows)
            candidate = ParsedSource("xlsx", records, issues, unknown)
            if best is None or len(candidate.records) > len(best.records):
                best = candidate
        if best is None:
            return ParsedSource(
                "xlsx",
                [],
                [ParseIssue("HEADER_NOT_RECOGNIZED", 0, "인식 가능한 Sheet가 없다")],
                [],
            )
        return best
    finally:
        workbook.close()


def parse_source(path: Path) -> ParsedSource:
    """확장자에 따라 파일을 해석한다. 원본은 읽기 전용으로만 접근한다."""
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        return ParsedSource(
            suffix.lstrip(".") or "unknown",
            [],
            [ParseIssue("UNSUPPORTED_FORMAT", 0, "지원하지 않는 파일 형식이다")],
            [],
        )
    if suffix == ".xlsx":
        return _parse_xlsx(path)
    raw = path.read_bytes()
    if suffix == ".csv":
        return _parse_csv(raw)
    return _parse_json(raw)
