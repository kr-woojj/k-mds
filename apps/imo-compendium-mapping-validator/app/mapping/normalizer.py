"""필드 정규화 (파이프라인 1단계: normalize).

- 원본 필드를 수정하지 않고 정규화 표현을 별도 생성한다 (REQ-003, REQ-027).
- 정규화는 전부 결정론적 규칙(사전·패턴)이다. 추론하지 않는다 — 신호가 없으면
  None으로 남겨 missing_context 판단의 근거가 되게 한다.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

#: 결정론적 약어 확장 사전 (토큰 단위)
ABBREVIATIONS: dict[str, list[str]] = {
    "no": ["number"],
    "nr": ["number"],
    "num": ["number"],
    "qty": ["quantity"],
    "cons": ["consumption"],
    "consump": ["consumption"],
    "temp": ["temperature"],
    "pos": ["position"],
    "lat": ["latitude"],
    "lon": ["longitude"],
    "lng": ["longitude"],
    "dt": ["datetime"],
    "utc": ["utc"],
    "fo": ["fuel", "oil"],
    "hfo": ["heavy", "fuel", "oil"],
    "mgo": ["marine", "gas", "oil"],
    "dep": ["departure"],
    "arr": ["arrival"],
    "vsl": ["ship"],
    "vessel": ["ship"],
    "nm": ["name"],
    "dist": ["distance"],
    "avg": ["average"],
}

#: 단위 표기 -> 정규 단위
UNIT_CANON: dict[str, str] = {
    "t": "t",
    "mt": "t",
    "ton": "t",
    "tons": "t",
    "tonne": "t",
    "tonnes": "t",
    "kg": "kg",
    "g": "g",
    "l": "l",
    "litre": "l",
    "litres": "l",
    "liter": "l",
    "liters": "l",
    "m3": "m3",
    "nm": "nm",
    "km": "km",
    "kn": "kn",
    "kt": "kn",
    "kts": "kn",
    "knot": "kn",
    "knots": "kn",
    "kw": "kw",
    "kwh": "kwh",
    "mwh": "mwh",
    "h": "h",
    "hr": "h",
    "hrs": "h",
    "hour": "h",
    "hours": "h",
    "%": "percent",
    "pct": "percent",
    "percent": "percent",
    "c": "celsius",
    "degc": "celsius",
}

CANONICAL_TYPES = {
    "string",
    "number",
    "integer",
    "boolean",
    "date",
    "datetime",
    "array",
    "object",
}
_TYPE_ALIASES: dict[str, str] = {
    "str": "string",
    "text": "string",
    "varchar": "string",
    "char": "string",
    "float": "number",
    "double": "number",
    "decimal": "number",
    "numeric": "number",
    "int": "integer",
    "bigint": "integer",
    "long": "integer",
    "bool": "boolean",
    "timestamp": "datetime",
    "time": "datetime",
    "list": "array",
    "dict": "object",
}

#: 단독으로는 의미 문맥이 없는 generic 토큰
GENERIC_TOKENS = {
    "value",
    "values",
    "data",
    "field",
    "fields",
    "item",
    "items",
    "col",
    "column",
    "columns",
    "attr",
    "attribute",
    "info",
    "record",
    "records",
    "x",
    "y",
    "misc",
    "etc",
}

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
_CAMEL_SPLIT = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
#: 한글(가-힣)을 토큰 문자로 포함한다 — 한국어 필드명·별칭 지원.
_NON_ALNUM = re.compile(r"[^0-9a-zA-Z%가-힣]+")


@dataclass
class NormalizedField:
    field_id: str
    raw_name: str
    tokens: list[str]
    normalized_name: str
    description_tokens: list[str] = field(default_factory=list)
    declared_type: str | None = None
    inferred_type: str | None = None
    canonical_unit: str | None = None
    declared_format: str | None = None
    path_tokens: list[str] = field(default_factory=list)
    sample_values: list[object] = field(default_factory=list)

    @property
    def effective_type(self) -> str | None:
        """선언 타입 우선, 없으면 샘플 추론 타입. 둘 다 없으면 None (추론 금지)."""
        return self.declared_type or self.inferred_type

    @property
    def meaningful_tokens(self) -> list[str]:
        return [token for token in self.tokens if token not in GENERIC_TOKENS]

    @property
    def has_context(self) -> bool:
        """missing_context 판정: 이름 외 신호가 하나도 없고 이름조차 generic이면 False."""
        if self.meaningful_tokens:
            return True
        return bool(
            self.description_tokens
            or self.path_tokens
            or self.sample_values
            or self.declared_type
            or self.canonical_unit
            or self.declared_format
        )


def tokenize(text: str | None) -> list[str]:
    if not text:
        return []
    normalized = unicodedata.normalize("NFKC", text)
    normalized = _CAMEL_SPLIT.sub(" ", normalized)
    parts = [part.lower() for part in _NON_ALNUM.split(normalized) if part]
    tokens: list[str] = []
    for part in parts:
        tokens.extend(ABBREVIATIONS.get(part, [part]))
    return tokens


def canonical_type(declared: str | None) -> str | None:
    if declared is None:
        return None
    key = declared.strip().lower()
    if key in CANONICAL_TYPES:
        return key
    return _TYPE_ALIASES.get(key)


def canonical_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    key = unit.strip().lower()
    return UNIT_CANON.get(key)


def infer_type_from_samples(samples: list[object]) -> str | None:
    """샘플이 모두 같은 범주일 때만 타입을 결론 내린다 (혼합이면 None)."""
    kinds: set[str] = set()
    for value in samples:
        if value is None:
            continue
        if isinstance(value, bool):
            kinds.add("boolean")
        elif isinstance(value, int):
            kinds.add("integer")
        elif isinstance(value, float):
            kinds.add("number")
        elif isinstance(value, str):
            text = value.strip()
            if _DATETIME_PATTERN.match(text):
                kinds.add("datetime")
            elif _DATE_PATTERN.match(text):
                kinds.add("date")
            elif re.fullmatch(r"[+-]?\d+", text):
                kinds.add("integer")
            elif re.fullmatch(r"[+-]?\d*\.\d+", text):
                kinds.add("number")
            elif text.lower() in ("true", "false"):
                kinds.add("boolean")
            else:
                kinds.add("string")
        else:
            kinds.add("object")
    if not kinds:
        return None
    if kinds == {"integer", "number"}:
        return "number"
    if len(kinds) == 1:
        return next(iter(kinds))
    return None


def normalize_field(
    field_id: str,
    name: str,
    *,
    description: str | None = None,
    declared_type: str | None = None,
    declared_unit: str | None = None,
    declared_format: str | None = None,
    path: str | None = None,
    sample_values: list[object] | None = None,
) -> NormalizedField:
    tokens = tokenize(name)
    samples = list(sample_values or [])
    return NormalizedField(
        field_id=field_id,
        raw_name=name,
        tokens=tokens,
        normalized_name=" ".join(tokens),
        description_tokens=tokenize(description),
        declared_type=canonical_type(declared_type),
        inferred_type=infer_type_from_samples(samples),
        canonical_unit=canonical_unit(declared_unit),
        declared_format=(declared_format.strip() if declared_format else None),
        path_tokens=tokenize(path),
        sample_values=samples,
    )
