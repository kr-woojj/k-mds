"""IMOMapperAgent 핵심 로직 (A-4, C-7 결정론 우선).

순서: explicit IMO id → exact name → normalized name → alias → Skill rule
     → (미해결 시에만) LLM candidate → Skill validate → reference validate.

- exact/alias 로 해결된 필드에는 LLM 을 호출하지 않는다 (테스트로 검증).
- LLM 후보는 Skill validate_mapping PASS/WARNING + reference 존재 확인을
  통과해야만 imo_data_number 로 승격된다. 그 외에는 candidate_list 에만 남는다.
- confidence 는 결정론 정책값 또는 Skill final_score — LLM confidence 를
  최종 confidence 로 쓰지 않는다 (C-6).
"""

from __future__ import annotations

from dataclasses import dataclass

from ghg_agent.adapters.skill_adapter import ImoMappingSkillAdapter, SkillAdapterError
from ghg_agent.domain.models import (
    CanonicalField,
    FieldMapping,
    MappingCandidate,
    MappingMethod,
    MappingResult,
    SourceProfile,
)
from ghg_agent.llm.client import LLMClient
from ghg_agent.reference.lookup import IMO_NUMBER_PATTERN, ReferenceLookup

_METHOD_CONFIDENCE = {
    MappingMethod.EXPLICIT_IDENTIFIER_VALIDATED: 1.0,
    MappingMethod.EXACT_REFERENCE: 0.98,
    MappingMethod.NORMALIZED_EXACT_REFERENCE: 0.95,
    MappingMethod.ALIAS_REFERENCE: 0.93,
}


@dataclass
class MapperConfig:
    confidence_threshold: float = 0.90
    llm_enabled: bool = True
    #: 승인 후보 집합 (F-STEP7-2). None 이면 scope 강제 없음(단위 테스트용).
    #: frozenset 이면 이 집합 밖 IMO 는 확정하지 못한다(fail-closed).
    candidate_scope: frozenset[str] | None = None


SCOPE_ERROR_CODE = "IMO_ELEMENT_OUTSIDE_APPROVED_CANDIDATE_SCOPE"


def _code_value_ok(field, element, reference) -> tuple[bool, str | None]:
    """explicit 값이 element 의 code list 를 위반하는지 (F-STEP7-1).

    문자열 값 + code list 존재 시에만 검사. 위반이면 (False, 'CODE_VALUE_INVALID').
    """
    if element is None or not isinstance(field.value, str):
        return True, None
    resolved = reference.code_list_for_element(element)
    if resolved is None:
        return True, None
    _list_name, values = resolved
    if field.value.strip() in values:
        return True, None
    return False, "CODE_VALUE_INVALID"


def _field_spec(field: CanonicalField) -> dict:
    spec: dict = {"name": field.source_name}
    if field.description:
        spec["description"] = field.description
    if field.data_type:
        spec["declared_type"] = field.data_type
    if field.unit:
        spec["declared_unit"] = field.unit
    if field.source_path:
        spec["path"] = field.source_path
    if field.value is not None and isinstance(field.value, (str, int, float, bool)):
        spec["sample_values"] = [field.value]
    return spec


def map_fields(
    fields: list[CanonicalField],
    profile: SourceProfile,
    reference: ReferenceLookup,
    skill: ImoMappingSkillAdapter,
    llm_client: LLMClient | None,
    config: MapperConfig,
    correlation_id: str,
) -> MappingResult:
    version = reference.version
    mappings: list[FieldMapping] = []
    metrics = {
        "total_source_fields": len(fields),
        "exact_mapped": 0,
        "alias_mapped": 0,
        "skill_rule_mapped": 0,
        "llm_suggested": 0,
        "llm_suggested_and_validated": 0,
        "unmapped": 0,
        "llm_invocations": 0,
        "skill_invocations": 0,
        "fabricated_candidate_rejections": 0,
        "candidate_scope_rejected": 0,
    }

    for field in fields:
        mapping = _map_single(
            field, profile, reference, skill, llm_client, config, correlation_id, metrics
        )
        # F-STEP7-2: 확정된 IMO 가 승인 후보 집합 밖이면 거부 (fail-closed, full registry fallback 금지)
        if (
            mapping.imo_data_number
            and config.candidate_scope is not None
            and mapping.imo_data_number not in config.candidate_scope
        ):
            metrics["candidate_scope_rejected"] += 1
            mapping.candidate_list.append(
                MappingCandidate(
                    imo_data_number=mapping.imo_data_number, source="reference",
                    validator_status="OUT_OF_SCOPE", reason=SCOPE_ERROR_CODE,
                )
            )
            mapping.warnings.append(f"{SCOPE_ERROR_CODE}: {mapping.imo_data_number}")
            mapping.imo_data_number = None
            mapping.mapping_method = MappingMethod.UNMAPPED
            mapping.confidence = None
            mapping.validator_status = "OUT_OF_SCOPE"
        mapping.reference_model_version = version if mapping.imo_data_number else None
        if mapping.imo_data_number:
            element = reference.element(mapping.imo_data_number)
            mapping.imo_data_element_name = element.name if element else None
        mappings.append(mapping)

    for mapping in mappings:
        if mapping.mapping_method in (
            MappingMethod.EXPLICIT_IDENTIFIER_VALIDATED,
            MappingMethod.EXACT_REFERENCE,
            MappingMethod.NORMALIZED_EXACT_REFERENCE,
            MappingMethod.ALIAS_REFERENCE,
        ):
            metrics["exact_mapped" if mapping.mapping_method
                    != MappingMethod.ALIAS_REFERENCE else "alias_mapped"] += 1
        elif mapping.mapping_method == MappingMethod.SKILL_RULE:
            metrics["skill_rule_mapped"] += 1
        elif mapping.mapping_method == MappingMethod.LLM_SUGGESTED_AND_VALIDATED:
            metrics["llm_suggested_and_validated"] += 1
        else:
            metrics["unmapped"] += 1

    return MappingResult(
        correlation_id=correlation_id,
        profile=profile,
        reference_model_version=version,
        fields=mappings,
        metrics=metrics,
    )


def _base(field: CanonicalField) -> FieldMapping:
    return FieldMapping(
        source_path=field.source_path,
        source_name=field.source_name,
        normalized_name=field.normalized_name,
        source_value_type=field.data_type,
        source_unit=field.unit,
    )


def _map_single(
    field: CanonicalField,
    profile: SourceProfile,
    reference: ReferenceLookup,
    skill: ImoMappingSkillAdapter,
    llm_client: LLMClient | None,
    config: MapperConfig,
    correlation_id: str,
    metrics: dict,
) -> FieldMapping:
    mapping = _base(field)

    # 1) explicit IMO identifier (값 또는 필드명에 명시된 경우)
    explicit_from_value = (
        isinstance(field.value, str)
        and bool(IMO_NUMBER_PATTERN.match(field.value.strip().upper()))
    )
    explicit_from_name = bool(IMO_NUMBER_PATTERN.match(field.source_name.strip().upper()))
    explicit = None
    if explicit_from_value:
        explicit = field.value.strip().upper()
    elif explicit_from_name:
        explicit = field.source_name.strip().upper()
    if explicit is not None:
        if not reference.exists(explicit):
            # 형식은 유효하나 Registry 에 없음 — fail-closed (E2E-5)
            metrics["fabricated_candidate_rejections"] += 1
            mapping.warnings.append(f"IMO_ID_NOT_FOUND: {explicit}")
            mapping.candidate_list.append(
                MappingCandidate(
                    imo_data_number=explicit, source="input",
                    validator_status="FAIL", reason="registry에 존재하지 않는 식별자",
                )
            )
            mapping.validator_status = "FAIL"
            return mapping
        # DEFECT-3: 필드'명'이 IMO형이고 별도 업무값이 있는 경우, 그 값의 타입/형식을
        # Skill 로 검증해 PASS/WARNING 일 때만 확정한다 (registry 존재만으로 확정 금지).
        # 값 자체가 식별자인 경우(explicit_from_value)는 타입 검증 대상 값이 없으므로
        # registry 존재로 확정한다 — 이것이 문서화된 explicit-identifier 계약이다.
        if explicit_from_name and not explicit_from_value:
            metrics["skill_invocations"] += 1
            try:
                verdict = skill.invoke(
                    "validate_mapping",
                    {"mappings": [{"field": _field_spec(field), "imo_data_number": explicit}]},
                    correlation_id=correlation_id,
                )
            except SkillAdapterError as error:
                mapping.warnings.append(f"{error.code}: explicit 후보 검증 불가 — 확정 차단")
                mapping.candidate_list.append(
                    MappingCandidate(
                        imo_data_number=explicit, source="input",
                        validator_status="NOT_VERIFIED", reason="skill 검증 실패",
                    )
                )
                return mapping
            results = verdict["result"].get("results", []) if verdict.get("ok") else []
            status = str(results[0].get("status")) if results else "FAIL"
            if status not in ("PASS", "WARNING"):
                # 존재하나 값 타입/형식 검증 실패 — 확정하지 않는다 (fail-closed)
                mapping.warnings.append(
                    f"EXPLICIT_VALIDATION_FAILED: {explicit} status={status}"
                )
                mapping.candidate_list.append(
                    MappingCandidate(
                        imo_data_number=explicit, source="input",
                        validator_status=status, reason="explicit 후보 값 검증 실패",
                    )
                )
                mapping.validator_status = status
                return mapping
            # F-STEP7-1: code-list 값 검증까지 통과해야 확정 (type/format 만으로 PASS/1.0 금지)
            code_ok, code_err = _code_value_ok(field, reference.element(explicit), reference)
            if not code_ok:
                mapping.warnings.append(f"EXPLICIT_VALIDATION_FAILED: {explicit} {code_err}")
                mapping.candidate_list.append(
                    MappingCandidate(
                        imo_data_number=explicit, source="input",
                        validator_status=code_err, reason="explicit code-list 값 검증 실패",
                    )
                )
                mapping.validator_status = code_err
                return mapping
            mapping.validator_status = status
        else:
            mapping.validator_status = "PASS"
        mapping.imo_data_number = explicit
        mapping.mapping_method = MappingMethod.EXPLICIT_IDENTIFIER_VALIDATED
        mapping.confidence = _METHOD_CONFIDENCE[mapping.mapping_method]
        return mapping

    # 2~4) exact / normalized / alias reference 조회 — 단일 후보일 때만 확정
    for method, hits in (
        (MappingMethod.EXACT_REFERENCE, reference.by_exact_name(field.source_name)),
        (MappingMethod.NORMALIZED_EXACT_REFERENCE, reference.by_normalized_name(field.source_name)),
        (MappingMethod.ALIAS_REFERENCE, reference.by_alias(field.source_name)),
    ):
        if len(hits) == 1:
            mapping.imo_data_number = hits[0].imo_data_number
            mapping.mapping_method = method
            mapping.confidence = _METHOD_CONFIDENCE[method]
            mapping.validator_status = "PASS"
            return mapping
        if len(hits) > 1:
            mapping.warnings.append(
                f"AMBIGUOUS_{method.value}: {[h.imo_data_number for h in hits]}"
            )
            for hit in hits:
                mapping.candidate_list.append(
                    MappingCandidate(
                        imo_data_number=hit.imo_data_number, source="reference",
                        validator_status="NOT_VERIFIED", reason=f"다중 {method.value} 후보",
                    )
                )
            return mapping  # 경쟁 후보 — fail-closed, 자동 확정하지 않는다

    # 5) 기존 Skill rule (결정론 파이프라인 — validator map_dataset)
    metrics["skill_invocations"] += 1
    reference_candidates: list[dict[str, str]] = []
    try:
        envelope = skill.invoke(
            "list_candidates",
            {"field": _field_spec(field), "top_k": 5},
            correlation_id=correlation_id,
        )
        if envelope.get("ok"):
            result = envelope["result"]
            for candidate in result.get("candidates", []):
                reference_candidates.append(
                    {
                        "imo_data_number": str(candidate.get("imoDataNumber")),
                        "name": str(candidate.get("registryEvidence", {}).get("name", "")),
                    }
                )
                mapping.candidate_list.append(
                    MappingCandidate(
                        imo_data_number=str(candidate.get("imoDataNumber")),
                        source="skill",
                        confidence=candidate.get("final_score"),
                        validator_status="NOT_VERIFIED",
                        reason="skill list_candidates",
                    )
                )
            if result.get("status") == "MATCHED":
                top = result["candidates"][0]
                mapping.imo_data_number = str(top["imoDataNumber"])
                mapping.mapping_method = MappingMethod.SKILL_RULE
                mapping.confidence = float(top.get("final_score") or 0.0)
                mapping.validator_status = "PASS"
                mapping.evidence_refs.append(str(result.get("audit_id")))
                return mapping
    except SkillAdapterError as error:
        # Skill 장애 시 LLM 단독 진행 금지 (C-5 fail-open 방지)
        mapping.warnings.append(f"{error.code}: skill 실패 — LLM 단독 진행 차단")
        return mapping

    # 6) LLM semantic candidate 생성 — 결정론 실패 시에만
    if llm_client is None or not config.llm_enabled or not reference_candidates:
        return mapping
    metrics["llm_invocations"] += 1
    try:
        batch = llm_client.generate_candidates(
            field_name=field.source_name,
            description=field.description,
            declared_type=field.data_type,
            declared_unit=field.unit,
            report_context=field.report_context,
            reference_candidates=reference_candidates,
            correlation_id=correlation_id,
        )
    except Exception as error:
        mapping.warnings.append(f"LLM_OUTPUT_INVALID: {type(error).__name__}")
        return mapping
    metrics["llm_suggested"] += len(batch.candidates)

    allowed = {c["imo_data_number"] for c in reference_candidates}
    validated: list[tuple[MappingCandidate, float]] = []
    for candidate in batch.candidates[:5]:
        number = candidate.imo_data_number.strip().upper()
        record = MappingCandidate(
            imo_data_number=number, source="llm",
            confidence=candidate.confidence, reason=candidate.reason,
            validator_status="NOT_VERIFIED",
        )
        mapping.candidate_list.append(record)
        if number not in allowed or not reference.exists(number):
            record.validator_status = "FAIL"
            metrics["fabricated_candidate_rejections"] += 1
            continue
        # 7) Skill 검증
        metrics["skill_invocations"] += 1
        try:
            verdict = skill.invoke(
                "validate_mapping",
                {"mappings": [{"field": _field_spec(field), "imo_data_number": number}]},
                correlation_id=correlation_id,
            )
        except SkillAdapterError as error:
            record.validator_status = "NOT_VERIFIED"
            mapping.warnings.append(f"{error.code}: LLM 후보 검증 불가 — 승격 차단")
            continue
        if not verdict.get("ok"):
            record.validator_status = "FAIL"
            continue
        results = verdict["result"].get("results", [])
        status = results[0].get("status") if results else "FAIL"
        record.validator_status = str(status)
        if status in ("PASS", "WARNING"):
            score = float(results[0].get("final_score") or 0.0)
            validated.append((record, score))

    # 8) 승격 판정 — 단일 승자 + threshold + gap(0.05) 충족 시에만
    if len(validated) == 1 and validated[0][1] >= config.confidence_threshold:
        winner, score = validated[0]
        mapping.imo_data_number = winner.imo_data_number
        mapping.mapping_method = MappingMethod.LLM_SUGGESTED_AND_VALIDATED
        mapping.confidence = score
        mapping.validator_status = winner.validator_status
    elif len(validated) > 1:
        ranked = sorted(validated, key=lambda item: -item[1])
        if (
            ranked[0][1] >= config.confidence_threshold
            and ranked[0][1] - ranked[1][1] >= 0.05
        ):
            winner, score = ranked[0]
            mapping.imo_data_number = winner.imo_data_number
            mapping.mapping_method = MappingMethod.LLM_SUGGESTED_AND_VALIDATED
            mapping.confidence = score
            mapping.validator_status = winner.validator_status
        else:
            mapping.warnings.append("COMPETING_CANDIDATES: 임계값/격차 미달 — 확정하지 않음")
    return mapping
