"""KR GHG Candidate Inventory 생성 (F-STEP7-2).

검증된 Noon/Event/Vessel-Performance fixture 를 실제 매핑 파이프라인에 통과시켜
확정(PASS/WARNING)된 IMO element 만 모아 승인 후보 집합(PROVISIONAL)을 만든다.

- 위조 ID / unknown 후보 / LLM 미검증 후보 / profile 부적용 element / full registry 전체 /
  자동추론 required element 는 포함하지 않는다.
- 결정론적: 동일 fixture → 동일 정렬 목록 → 동일 SHA-256.

출력: var/candidate-inventory.json (+ .sha256)
사용: uv run python tools/build_candidate_inventory.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "src"))

from ghg_agent.adapters.skill_adapter import ImoMappingSkillAdapter  # noqa: E402
from ghg_agent.config import load_settings  # noqa: E402
from ghg_agent.domain.mapping import MapperConfig, map_fields  # noqa: E402
from ghg_agent.domain.models import SourceProfile  # noqa: E402
from ghg_agent.domain.normalization import normalize_payload  # noqa: E402
from ghg_agent.llm.client import MockLLMClient  # noqa: E402
from ghg_agent.reference.lookup import ReferenceLookup  # noqa: E402

FIXTURES = PROJECT / "tests" / "fixtures"
SOURCE_FIXTURES = [
    ("noon_report_valid.json", SourceProfile.NOON_REPORT),
    ("vessel_performance_valid.json", SourceProfile.VESSEL_PERFORMANCE),
    ("event_departure.json", SourceProfile.EVENT_REPORT),
    ("event_anchoring.json", SourceProfile.EVENT_REPORT),
    ("event_arrival.json", SourceProfile.EVENT_REPORT),
]
CANDIDATE_SET_ID = "kr-ghg-candidate-inventory"
VERSION = "0.2.0-provisional"  # 0.2.0: LAB021 코드북 IMO ID 합집합 (결정 D2, 2026-09-26)
LAB021_CODEBOOK = PROJECT / "var" / "reference" / "lab021" / "noon-code-book.json"


def main() -> int:
    s = load_settings()
    ref = ReferenceLookup(
        registry_db_path=s.registry_db_path, version="FAL50",
        alias_config_path=s.alias_config_path, code_lists_path=s.code_lists_path,
    )
    ref.load()

    ids: set[str] = set()
    used = []
    for name, profile in SOURCE_FIXTURES:
        path = FIXTURES / name
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.pop("_comment", None)
        fields = normalize_payload(payload, profile)
        skill = ImoMappingSkillAdapter(
            skill_path=s.imo_mapping_skill_path, registry_db_path=s.registry_db_path
        )
        result = map_fields(
            fields, profile, ref, skill, MockLLMClient(), MapperConfig(), f"inv-{name}"
        )
        for f in result.fields:
            # 확정 매핑 + registry 실존 element 만 (LLM 미검증/위조 제외)
            if (
                f.imo_data_number
                and f.validator_status in ("PASS", "WARNING")
                and ref.exists(f.imo_data_number)
            ):
                ids.add(f.imo_data_number)
        used.append(name)

    # D2(2026-09-26): 랩오투원 코드북(Provider 공개)의 IMO ID 를 승인 후보로 합집합. registry 실존 ID 만.
    codebook_ids: set[str] = set()
    codebook_meta: dict = {}
    if LAB021_CODEBOOK.is_file():
        raw = LAB021_CODEBOOK.read_bytes()
        items = json.loads(raw)["data"]["items"]
        for it in items:
            imo = str(it.get("id", ""))
            if imo.startswith("IMO") and ref.exists(imo):
                codebook_ids.add(imo)
        # 코드북 1:N 을 FAL50 'Consumption By Fuel Type' 구조로 풀 때 쓰는 요소(lab021_ingress.ENGINE_ELEMENT/IMO0654/IMO0674)
        for imo in ("IMO0654", "IMO0670", "IMO0893", "IMO0673", "IMO0903", "IMO0674"):
            if ref.exists(imo):
                codebook_ids.add(imo)
        codebook_meta = {"path": str(LAB021_CODEBOOK.relative_to(PROJECT)), "sha256": hashlib.sha256(raw).hexdigest(),
                         "items": len(items), "imo_ids_in_registry": len(codebook_ids)}
        ids |= codebook_ids
        used.append("var/reference/lab021/noon-code-book.json")

    sorted_ids = sorted(ids)
    inventory = {
        "lab021_codebook": codebook_meta,
        "decision_ref": "pm/decisions.md 2026-09-26 D2·D4·D8 승인 (연구책임자)",
        "candidate_set_id": CANDIDATE_SET_ID,
        "version": VERSION,
        "status": "PROVISIONAL",
        "approved": False,
        "requiredness_profile_approved": False,
        "reference_model_version": "FAL50",
        "source_artifacts": used,
        "element_count": len(sorted_ids),
        "imo_data_numbers": sorted_ids,
        "generated_from": "verified Noon/Event/Vessel-Performance fixture mappings (PASS/WARNING)",
    }
    # SHA-256 은 imo 목록의 정규 표현으로 계산 (generated_at 등 변동 필드 제외 → 결정론).
    canonical = json.dumps(
        {"candidate_set_id": CANDIDATE_SET_ID, "version": VERSION,
         "imo_data_numbers": sorted_ids},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    inventory["sha256"] = digest
    inventory["generated_at"] = datetime.now(UTC).isoformat()

    out_dir = PROJECT / "var"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "candidate-inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    (out_dir / "candidate-inventory.sha256").write_text(digest + "\n", encoding="utf-8")
    print(f"candidate_set_id={CANDIDATE_SET_ID} version={VERSION}")
    print(f"element_count={len(sorted_ids)} sha256={digest}")
    print(f"source_artifacts={used}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
