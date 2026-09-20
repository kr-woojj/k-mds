"""Candidate Inventory (승인 후보 집합) 로더 및 Scope 강제 (F-STEP7-2).

- Full FAL50 registry 와 KR GHG 승인 후보 집합을 분리한다.
- Inventory 파일 부재 또는 SHA-256 불일치 시 BOUND 되지 않는다(INVALID/UNBOUND) —
  Full Registry fallback 을 하지 않고 fail-closed 한다.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

SCOPE_ERROR_CODE = "IMO_ELEMENT_OUTSIDE_APPROVED_CANDIDATE_SCOPE"


@dataclass(frozen=True)
class CandidateInventory:
    candidate_set_id: str
    version: str
    status: str
    sha256: str
    element_count: int
    ids: frozenset[str]
    approved: bool = False
    load_status: str = "BOUND"  # BOUND | INVALID | UNBOUND

    @property
    def bound(self) -> bool:
        return self.load_status == "BOUND"

    def in_scope(self, imo_data_number: str) -> bool:
        return imo_data_number.strip().upper() in self.ids

    def metadata(self) -> dict:
        return {
            "candidate_set_id": self.candidate_set_id,
            "version": self.version,
            "status": self.status,
            "approved": self.approved,
            "sha256": self.sha256,
            "element_count": self.element_count,
            "load_status": self.load_status,
            "candidate_scope_enforcement": self.bound,
        }


def _unbound(reason: str) -> CandidateInventory:
    return CandidateInventory(
        candidate_set_id="", version="", status=reason, sha256="",
        element_count=0, ids=frozenset(), approved=False, load_status="UNBOUND",
    )


def load_candidate_inventory(path: Path) -> CandidateInventory:
    """파일 부재/파싱 오류 → UNBOUND. Hash 불일치 → INVALID. 정상 → BOUND.

    어떤 경우에도 Full Registry fallback 을 하지 않는다 (fail-closed).
    """
    if not path.is_file():
        return _unbound("FILE_NOT_FOUND")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _unbound("UNREADABLE")

    ids = sorted(str(x).strip().upper() for x in data.get("imo_data_numbers", []))
    recorded = str(data.get("sha256", ""))
    canonical = json.dumps(
        {"candidate_set_id": data.get("candidate_set_id"), "version": data.get("version"),
         "imo_data_numbers": ids},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    computed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if not recorded or computed != recorded:
        return CandidateInventory(
            candidate_set_id=str(data.get("candidate_set_id", "")),
            version=str(data.get("version", "")), status="HASH_MISMATCH",
            sha256=recorded, element_count=len(ids), ids=frozenset(ids),
            approved=False, load_status="INVALID",
        )
    return CandidateInventory(
        candidate_set_id=str(data.get("candidate_set_id", "")),
        version=str(data.get("version", "")), status=str(data.get("status", "")),
        sha256=recorded, element_count=len(ids), ids=frozenset(ids),
        approved=bool(data.get("approved", False)), load_status="BOUND",
    )
