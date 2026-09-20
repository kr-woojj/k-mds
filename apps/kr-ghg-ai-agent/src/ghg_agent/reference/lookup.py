"""결정론 reference lookup (C-7 1~4단계).

Registry(SQLite, validator 가 적재한 FAL50 snapshot)를 read-only 로 조회한다.
- exact IMO identifier 존재 확인 (형식 유효 ≠ 의미 유효 — 존재하지 않으면 실패)
- exact name / normalized name / alias 조회
- code list 값 검증 (FAL50 'Code list' sheet 추출본)
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import create_engine, text

IMO_NUMBER_PATTERN = re.compile(r"^IMO\d{4}$")


def normalize_name(name: str) -> str:
    text_value = unicodedata.normalize("NFKC", name)
    text_value = re.sub(r"[^0-9a-zA-Z]+", " ", text_value)
    return " ".join(text_value.lower().split())


@dataclass(frozen=True)
class ReferenceElement:
    imo_data_number: str
    name: str
    definition: str | None
    format_spec: str | None
    code_list: str | None
    business_rule: str | None
    datasets: frozenset[str]


@dataclass
class ReferenceLookup:
    registry_db_path: Path
    version: str
    alias_config_path: Path | None = None
    code_lists_path: Path | None = None
    _elements: dict[str, ReferenceElement] = field(default_factory=dict)
    _by_exact_name: dict[str, list[str]] = field(default_factory=dict)
    _by_normalized: dict[str, list[str]] = field(default_factory=dict)
    _aliases: dict[str, str] = field(default_factory=dict)
    _code_lists: dict[str, set[str]] = field(default_factory=dict)
    _loaded: bool = False

    def load(self) -> None:
        if self._loaded:
            return
        if not self.registry_db_path.is_file():
            raise FileNotFoundError(f"Registry DB 없음: {self.registry_db_path}")
        engine = create_engine(f"sqlite:///{self.registry_db_path}", future=True)
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT e.imo_data_number, e.name, e.definition, e.format_spec, "
                    "e.code_list, e.business_rule "
                    "FROM data_element e WHERE e.version = :v"
                ),
                {"v": self.version},
            ).fetchall()
            occ_rows = connection.execute(
                text(
                    "SELECT imo_data_number, dataset_key FROM refmodel_occurrence "
                    "WHERE version = :v"
                ),
                {"v": self.version},
            ).fetchall()
        datasets: dict[str, set[str]] = {}
        for number, dataset_key in occ_rows:
            if dataset_key:
                datasets.setdefault(str(number), set()).add(str(dataset_key))
        for number, name, definition, format_spec, code_list, business_rule in rows:
            number = str(number)
            element = ReferenceElement(
                imo_data_number=number,
                name=str(name),
                definition=definition,
                format_spec=format_spec,
                code_list=code_list,
                business_rule=business_rule,
                datasets=frozenset(datasets.get(number, set())),
            )
            self._elements[number] = element
            self._by_exact_name.setdefault(element.name.lower(), []).append(number)
            self._by_normalized.setdefault(normalize_name(element.name), []).append(number)

        if self.alias_config_path and self.alias_config_path.is_file():
            raw = json.loads(self.alias_config_path.read_text(encoding="utf-8"))
            for alias, target in raw.get("aliases", {}).items():
                self._aliases[normalize_name(alias)] = str(target).strip()

        if self.code_lists_path and self.code_lists_path.is_file():
            raw = json.loads(self.code_lists_path.read_text(encoding="utf-8"))
            for entry in raw.get("code_lists", []):
                self._code_lists[entry["code_list"]] = {
                    str(value["code"]) for value in entry["values"]
                }
        self._loaded = True

    # --- 조회 ---

    def element(self, imo_data_number: str) -> ReferenceElement | None:
        self.load()
        return self._elements.get(imo_data_number.strip().upper())

    def exists(self, imo_data_number: str) -> bool:
        return self.element(imo_data_number) is not None

    def by_exact_name(self, name: str) -> list[ReferenceElement]:
        self.load()
        return [self._elements[n] for n in self._by_exact_name.get(name.strip().lower(), [])]

    def by_normalized_name(self, name: str) -> list[ReferenceElement]:
        self.load()
        return [self._elements[n] for n in self._by_normalized.get(normalize_name(name), [])]

    def by_alias(self, name: str) -> list[ReferenceElement]:
        """alias 대상은 element 이름 또는 IMO 번호. 대상 미존재 alias 는 무시(fail-closed)."""
        self.load()
        target = self._aliases.get(normalize_name(name))
        if target is None:
            return []
        if IMO_NUMBER_PATTERN.match(target.upper()):
            element = self._elements.get(target.upper())
            return [element] if element else []
        return self.by_normalized_name(target)

    def code_list_values(self, code_list_name: str) -> set[str] | None:
        self.load()
        return self._code_lists.get(code_list_name)

    def code_list_for_element(self, element: ReferenceElement) -> tuple[str, set[str]] | None:
        """element 에 대응하는 추출 code list 를 결정론 규칙으로 해석한다.

        CL-LINK-1: element.code_list 텍스트가 추출된 code list 이름과 정확히
        일치하면 그것을 쓴다. 아니면 element 이름의 ', coded' 접미사를 제거한
        이름으로 조회한다 (예: 'Fuel type, coded' → 'Fuel type'). 두 경우 모두
        실패하면 None — 값 검증을 수행하지 않는다 (발명 금지).
        """
        self.load()
        if element.code_list and element.code_list in self._code_lists:
            return element.code_list, self._code_lists[element.code_list]
        name = element.name
        if name.lower().endswith(", coded"):
            stripped = name[: -len(", coded")].strip()
            if stripped in self._code_lists:
                return stripped, self._code_lists[stripped]
        return None

    def element_count(self) -> int:
        self.load()
        return len(self._elements)
