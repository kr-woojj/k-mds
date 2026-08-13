# ADR-0002: Schema 검증 책임 분리

- Status: Accepted
- Date: 2026-08-13

## Context

기존 `schema_validate` Skill은 payload가 dict인지 확인한 뒤 generated Schema
artifact(schemas/generated)의 구조만 검사했다. Payload의 필드 자체는 검증하지
않았으므로 함수명이 시사하는 책임("payload를 schema로 검증한다")과 실제 동작이
일치하지 않았다. 이 상태로 MCP Tool 또는 Agent에 노출되면 잘못된 검증 의미가
전파될 위험이 있다.

## Decision

- `schema_contract_check(schema_name, schema_dir=None)`:
  generated Schema artifact의 구조 무결성 검사를 담당한다.
  (`$defs` 존재, 필수 정의, alias 정책 property 존재·부재)
  성공 data에 `validationLevel: "contract-structure"`를 명시한다.
- `schema_validate(payload, model_name)`:
  Pydantic Source of Truth(`src/k_mds/models`, ADR-0001)의
  `model_validate` 기반 실제 Payload 검증을 담당한다.
  유효 시 `normalizedPayload`(`model_dump(by_alias=True, mode="json")`)를 반환한다.
- Rule ID를 책임별로 분리한다.
  - `urn:k-mds:rule:schema-contract-check:0.1`
  - `urn:k-mds:rule:payload-validation:0.1`

## Rationale

- 함수명과 실제 책임이 일치한다.
- Pydantic SSOT를 재사용하여 Runtime 불변조건(model_validator)과 Payload 검증이
  단일 정의를 공유한다.
- jsonschema 등 신규 의존성을 회피한다.
- MCP 또는 Agent에 잘못된 검증 의미가 노출되는 것을 방지한다.
- Finding에는 원본 Payload 값을 포함하지 않는다
  (`actual_value=None`, Pydantic 정규화 메시지만 사용).

## Compatibility

이 Repository는 초기 단계이며 외부 안정 API로 배포되지 않았다. 따라서 기존
`schema_validate(payload, schema_name, schema_dir)` 호출 형태를 모호하게
유지하지 않고 명시적으로 책임을 분리한다. 구조 검사 호출자는
`schema_contract_check`로 이동한다.

## Non-goals

- JSON Schema 전체 유효성 검사(full validator) 미구현
- OpenAPI Generator 미구현
- MCP Server 미구현
- Evidence Builder 미구현
