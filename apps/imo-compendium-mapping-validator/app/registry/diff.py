"""버전 간 변경사항 Diff (요구사항 6).

분류 규칙:
- added:      to 버전에만 존재하는 IMO Data Number
- deprecated: from 버전에만 존재하거나, 양쪽에 존재하되 to에서 status가
              deprecated/superseded로 전환된 IMO Data Number
- modified:   양쪽에 존재하고 핵심 필드 또는 Occurrence 집합이 달라졌으며
              deprecated로 분류되지 않은 IMO Data Number

두 버전 모두 loaded=True snapshot이어야 한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.registry.models import CompendiumVersion, DataElement, RefModelOccurrence

DEPRECATED_STATUSES = {"deprecated", "superseded"}

_COMPARABLE_FIELDS = (
    "name",
    "definition",
    "format_spec",
    "code_list",
    "business_rule",
    "status",
)


class DiffError(ValueError):
    """존재하지 않거나 미완결 버전에 대한 diff 요청."""


@dataclass
class VersionDiff:
    from_version: str
    to_version: str
    added: list[str] = field(default_factory=list)
    modified: list[dict[str, object]] = field(default_factory=list)
    deprecated: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "fromVersion": self.from_version,
            "toVersion": self.to_version,
            "addedCount": len(self.added),
            "modifiedCount": len(self.modified),
            "deprecatedCount": len(self.deprecated),
            "added": self.added,
            "modified": self.modified,
            "deprecated": self.deprecated,
        }


def _load_snapshot(
    session: Session, version: str
) -> dict[str, dict[str, object]]:
    row = session.execute(
        select(CompendiumVersion).where(CompendiumVersion.version == version)
    ).scalar_one_or_none()
    if row is None or not row.loaded:
        raise DiffError(f"버전이 적재되어 있지 않다: {version}")

    elements: dict[str, dict[str, object]] = {}
    for element in session.execute(
        select(DataElement).where(DataElement.version == version)
    ).scalars():
        elements[element.imo_data_number] = {
            "name": element.name,
            "definition": element.definition,
            "format_spec": element.format_spec,
            "code_list": element.code_list,
            "business_rule": element.business_rule,
            "status": element.status,
            "occurrences": set(),
        }
    for occurrence in session.execute(
        select(RefModelOccurrence).where(RefModelOccurrence.version == version)
    ).scalars():
        entry = elements.get(occurrence.imo_data_number)
        if entry is not None:
            occurrences = entry["occurrences"]
            assert isinstance(occurrences, set)
            occurrences.add((occurrence.dataset_key, occurrence.refmodel_path))
    return elements


def diff_versions(
    session_factory: sessionmaker[Session], from_version: str, to_version: str
) -> VersionDiff:
    with session_factory() as session:
        source = _load_snapshot(session, from_version)
        target = _load_snapshot(session, to_version)

    source_numbers = set(source)
    target_numbers = set(target)

    added = sorted(target_numbers - source_numbers)
    removed = source_numbers - target_numbers

    deprecated: set[str] = set(removed)
    modified: list[dict[str, object]] = []
    for number in sorted(source_numbers & target_numbers):
        before = source[number]
        after = target[number]
        after_status = str(after["status"]).lower()
        before_status = str(before["status"]).lower()
        if after_status in DEPRECATED_STATUSES and before_status not in DEPRECATED_STATUSES:
            deprecated.add(number)
            continue
        changed_fields = [
            fieldname
            for fieldname in _COMPARABLE_FIELDS
            if before[fieldname] != after[fieldname]
        ]
        if before["occurrences"] != after["occurrences"]:
            changed_fields.append("occurrences")
        if changed_fields:
            modified.append(
                {"imoDataNumber": number, "changedFields": sorted(changed_fields)}
            )

    return VersionDiff(
        from_version=from_version,
        to_version=to_version,
        added=added,
        modified=modified,
        deprecated=sorted(deprecated),
    )
