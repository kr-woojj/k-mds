# ADR-0001: Pydantic Source of Truth 위치 확정

- Status: Accepted
- Date: 2026-08-12

## Context

Root `AGENTS.md` §3 Repository Tree에는 Pydantic 원천 모델 위치로 `schemas/source/`가
제시되어 있다. 그러나 Core Contract 구현 과정에서 Runtime Package 기준의
Single Source of Truth(SSOT)를 `src/k_mds/models`로 확정하는 사용자 결정이 있었다.
이 ADR은 그 결정과 근거를 기록한다.

## Decision

- Pydantic Source of Truth는 `src/k_mds/models`에 둔다.
  - `k_mds.models.ontology`: Dataset, Component, DataElement, ElementOccurrence,
    CodeList, BusinessRule, GovernanceStatus
  - `k_mds.models.validation`: Evidence, ValidationFinding, SkillResult,
    ResultStatus, FindingSeverity, DataClassification
- `schemas/generated/`는 `scripts/generate_schemas.py`가 생성하는 Generated Output이며
  직접 수정하지 않는다.
- Alias 정책: 검증 Contract는 camelCase(AGENTS.md §10 JSON 예시와 일치),
  Ontology 모델은 snake_case를 사용한다.

## Rationale

- MyPy, Pytest, Skill, MCP, LangGraph, Schema Generator가 동일한 모델을 import하여
  단일 정의를 공유한다.
- Runtime Contract(Pydantic model_validator 불변조건)와 Generated Schema 간
  drift를 방지한다. Schema는 항상 모델에서 재생성된다.

## Consequences

- `schemas/source/`는 현재 사용하지 않으며 후속 Architecture 정리 대상이다.
- `schemas/generated/`는 DO_NOT_EDIT 정책을 유지한다. 수정이 필요하면
  `src/k_mds/models`를 변경하고 Generator를 재실행한다.
- Root `AGENTS.md` §3과의 차이는 본 ADR로 기록하며, Root 문서 갱신 여부는
  별도 의사결정에 따른다.

## Non-goals

- Root `AGENTS.md` 변경 없음
- IMO 원본 배치 또는 Excel Parser 구현 없음
