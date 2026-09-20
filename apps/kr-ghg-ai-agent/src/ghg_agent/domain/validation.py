"""MappingValidationAgent 핵심 로직 (A-5) — 전부 결정론.

검증 항목과 오류 코드는 지시서 표준 코드를 사용한다.
- Skill validate_mapping: 타입·단위·형식 대 Registry 정의 (실제 validator 호출)
- reference 존재·이름 일관성·버전 확인 (registry snapshot)
- code list 값 검증 (FAL50 'Code list' sheet 추출본)
- profile 적용성 (dataset occurrence 기반 — 구성 정책, WARNING 수준)
- 필수 필드 정책 (PoC 정책 — policy id 기록)
- provenance 완전성 / confidence threshold
"""

from __future__ import annotations

from dataclasses import dataclass

from ghg_agent.adapters.skill_adapter import ImoMappingSkillAdapter, SkillAdapterError
from ghg_agent.domain.models import (
    CanonicalField,
    MappingMethod,
    MappingResult,
    SourceProfile,
    ValidationItem,
    ValidationResult,
    ValidationVerdict,
)
from ghg_agent.reference.lookup import ReferenceLookup

#: profile → FAL50 dataset key 적용성 (구성 정책 P-PROFILE-1; 권위 규범 아님)
PROFILE_DATASETS: dict[SourceProfile, frozenset[str]] = {
    SourceProfile.NOON_REPORT: frozenset({"Noon Data Report"}),
    SourceProfile.EVENT_REPORT: frozenset({"Noon Data Report", "Ship Reporting Systems", "Just In Time Arrival"}),
    SourceProfile.VESSEL_PERFORMANCE: frozenset(
        {"Noon Data Report", "[Fuel Oil Consumption and CII Reporting]"}
    ),
}

#: profile 필수 매핑 정책 (PoC 정책 P-REQ-1): IMO 번호 존재는 registry로 확인됨
REQUIRED_ELEMENTS: dict[SourceProfile, frozenset[str]] = {
    SourceProfile.NOON_REPORT: frozenset({"IMO0603"}),   # Ship reporting date time
    SourceProfile.EVENT_REPORT: frozenset({"IMO0597"}),  # Event type, coded
    SourceProfile.VESSEL_PERFORMANCE: frozenset(),
}


#: validator MappingToolkit.validate_mapping 의 mappings max_length (DEFECT-5)
SKILL_BATCH_SIZE = 500


def _chunks(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


@dataclass
class ValidationConfig:
    confidence_threshold: float = 0.90


def validate_mapping_result(
    mapping_result: MappingResult,
    fields: list[CanonicalField],
    reference: ReferenceLookup,
    skill: ImoMappingSkillAdapter,
    config: ValidationConfig,
) -> ValidationResult:
    items: list[ValidationItem] = []
    fields_by_path = {field.source_path: field for field in fields}
    known_versions = set(reference_versions(skill))

    mapped = [m for m in mapping_result.fields if m.imo_data_number]

    # --- Skill 검증 (배치, DEFECT-5: validator max 500 → 청크 분할) ---
    skill_status: dict[str, str] = {}
    for chunk in _chunks(mapped, SKILL_BATCH_SIZE):
        payload = {
            "mappings": [
                {
                    "field": _field_spec(fields_by_path.get(m.source_path), m),
                    "imo_data_number": m.imo_data_number,
                }
                for m in chunk
            ]
        }
        try:
            envelope = skill.invoke(
                "validate_mapping", payload, correlation_id=mapping_result.correlation_id
            )
            if envelope.get("ok"):
                for m, result in zip(chunk, envelope["result"]["results"], strict=False):
                    skill_status[m.source_path] = str(result.get("status", "FAIL"))
                    for issue in result.get("issues", []):
                        items.append(
                            ValidationItem(
                                source_path=m.source_path,
                                imo_data_number=m.imo_data_number,
                                check="skill_registry_validation",
                                verdict=ValidationVerdict.FAIL
                                if issue.get("severity") == "ERROR"
                                else ValidationVerdict.WARNING,
                                code=str(issue.get("code")),
                                message=str(issue.get("message", ""))[:200],
                            )
                        )
            else:
                # 해당 청크만 NOT_VERIFIED (fail-closed, 다른 청크 결과는 유지)
                _mark_skill_unverified(
                    items, chunk, str(envelope.get("error", {}).get("code")), skill_status
                )
        except SkillAdapterError as error:
            _mark_skill_unverified(items, chunk, error.code, skill_status)

    for m in mapping_result.fields:
        field = fields_by_path.get(m.source_path)

        if m.imo_data_number is None:
            items.append(
                ValidationItem(
                    source_path=m.source_path,
                    check="mapping_presence",
                    verdict=ValidationVerdict.NOT_APPLICABLE,
                    code="UNMAPPED",
                    message="확정 매핑 없음 — review 대상",
                )
            )
            continue

        number = m.imo_data_number
        element = reference.element(number)

        # IMO_ID_NOT_FOUND / IMO_NAME_MISMATCH
        if element is None:
            items.append(
                ValidationItem(
                    source_path=m.source_path, imo_data_number=number,
                    check="reference_existence", verdict=ValidationVerdict.FAIL,
                    code="IMO_ID_NOT_FOUND", message="Registry 에 없는 식별자",
                )
            )
            continue
        if m.imo_data_element_name and m.imo_data_element_name != element.name:
            items.append(
                ValidationItem(
                    source_path=m.source_path, imo_data_number=number,
                    check="element_name_consistency", verdict=ValidationVerdict.FAIL,
                    code="IMO_NAME_MISMATCH",
                    message=f"기대 {element.name!r} 와 불일치",
                )
            )

        # REFERENCE_VERSION_UNKNOWN
        if m.reference_model_version not in known_versions:
            items.append(
                ValidationItem(
                    source_path=m.source_path, imo_data_number=number,
                    check="reference_version", verdict=ValidationVerdict.FAIL,
                    code="REFERENCE_VERSION_UNKNOWN",
                    message=str(m.reference_model_version),
                )
            )

        # Skill 배치 결과 반영 (NOT_VERIFIED 는 성공 아님)
        status = skill_status.get(m.source_path)
        if status is None:
            items.append(
                ValidationItem(
                    source_path=m.source_path, imo_data_number=number,
                    check="skill_registry_validation",
                    verdict=ValidationVerdict.NOT_VERIFIED,
                    code="SKILL_EXECUTION_ERROR",
                    message="Skill 검증 미수행",
                )
            )
        elif status == "PASS" and not any(
            i.source_path == m.source_path and i.check == "skill_registry_validation"
            for i in items
        ):
            items.append(
                ValidationItem(
                    source_path=m.source_path, imo_data_number=number,
                    check="skill_registry_validation", verdict=ValidationVerdict.PASS,
                )
            )

        # CODE_VALUE_INVALID (code list 값 검증 — CL-LINK-1 해석 규칙)
        if field is not None and isinstance(field.value, str):
            resolved = reference.code_list_for_element(element)
            if resolved is not None:
                list_name, values = resolved
                verdict = (
                    ValidationVerdict.PASS
                    if field.value.strip() in values
                    else ValidationVerdict.FAIL
                )
                items.append(
                    ValidationItem(
                        source_path=m.source_path, imo_data_number=number,
                        check="code_list_value", verdict=verdict,
                        code=None if verdict == ValidationVerdict.PASS else "CODE_VALUE_INVALID",
                        message=None if verdict == ValidationVerdict.PASS
                        else f"code list {list_name!r} 에 없는 값",
                    )
                )

        # PROFILE_NOT_APPLICABLE (구성 정책 — WARNING)
        applicable = PROFILE_DATASETS.get(mapping_result.profile)
        if applicable and element.datasets and not (element.datasets & applicable):
            items.append(
                ValidationItem(
                    source_path=m.source_path, imo_data_number=number,
                    check="profile_applicability", verdict=ValidationVerdict.WARNING,
                    code="PROFILE_NOT_APPLICABLE",
                    message=f"{sorted(element.datasets)} ∌ {sorted(applicable)} (정책 P-PROFILE-1)",
                )
            )

        # LOW_CONFIDENCE / PROVENANCE_MISSING
        if m.confidence is None or m.confidence < config.confidence_threshold:
            items.append(
                ValidationItem(
                    source_path=m.source_path, imo_data_number=number,
                    check="confidence_threshold", verdict=ValidationVerdict.FAIL,
                    code="LOW_CONFIDENCE", message=str(m.confidence),
                )
            )
        if m.mapping_method == MappingMethod.UNMAPPED or not m.reference_model_version:
            items.append(
                ValidationItem(
                    source_path=m.source_path, imo_data_number=number,
                    check="provenance", verdict=ValidationVerdict.FAIL,
                    code="PROVENANCE_MISSING", message="mapping_method/version 누락",
                )
            )

    # REQUIRED_FIELD_MISSING (정책 P-REQ-1)
    mapped_numbers = {m.imo_data_number for m in mapped}
    for required in sorted(REQUIRED_ELEMENTS.get(mapping_result.profile, frozenset())):
        if required not in mapped_numbers:
            items.append(
                ValidationItem(
                    source_path="$",
                    imo_data_number=required,
                    check="required_elements_policy",
                    verdict=ValidationVerdict.FAIL,
                    code="REQUIRED_FIELD_MISSING",
                    message=f"정책 P-REQ-1: {mapping_result.profile.value} 필수 요소 미매핑",
                )
            )

    counts = {
        ValidationVerdict.PASS: 0,
        ValidationVerdict.WARNING: 0,
        ValidationVerdict.FAIL: 0,
        ValidationVerdict.NOT_APPLICABLE: 0,
        ValidationVerdict.NOT_VERIFIED: 0,
    }
    for item in items:
        counts[item.verdict] += 1

    if counts[ValidationVerdict.FAIL]:
        overall = ValidationVerdict.FAIL
    elif counts[ValidationVerdict.NOT_VERIFIED]:
        overall = ValidationVerdict.NOT_VERIFIED
    elif counts[ValidationVerdict.WARNING]:
        overall = ValidationVerdict.WARNING
    else:
        overall = ValidationVerdict.PASS

    return ValidationResult(
        correlation_id=mapping_result.correlation_id,
        overall=overall,
        items=items,
        pass_count=counts[ValidationVerdict.PASS],
        warning_count=counts[ValidationVerdict.WARNING],
        fail_count=counts[ValidationVerdict.FAIL],
        not_verified_count=counts[ValidationVerdict.NOT_VERIFIED],
    )


def _mark_skill_unverified(items, mapped, code: str | None, skill_status=None) -> None:
    for m in mapped:
        # F-STEP7-3: skill_status 에 NOT_VERIFIED 를 기록해 per-field 루프의 중복 표기를 막는다.
        if skill_status is not None:
            skill_status[m.source_path] = "NOT_VERIFIED"
        items.append(
            ValidationItem(
                source_path=m.source_path,
                imo_data_number=m.imo_data_number,
                check="skill_registry_validation",
                verdict=ValidationVerdict.NOT_VERIFIED,
                code=code or "SKILL_EXECUTION_ERROR",
                message="Skill 검증 실패 — 성공으로 취급하지 않음",
            )
        )


def _field_spec(field: CanonicalField | None, mapping) -> dict:
    if field is None:
        return {"name": mapping.source_name}
    spec: dict = {"name": field.source_name}
    if field.description:
        spec["description"] = field.description
    if field.data_type:
        spec["declared_type"] = field.data_type
    if field.unit:
        spec["declared_unit"] = field.unit
    if field.source_path:
        spec["path"] = field.source_path
    return spec


def reference_versions(skill: ImoMappingSkillAdapter) -> list[str]:
    try:
        return skill.registry_versions()
    except Exception:
        return []
