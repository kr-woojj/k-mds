# ADR-0004: Result Classification — SkillResult와 GovernanceResult 분리

- Status: Accepted
- Date: 2026-08-13

## Context

`SkillResult.FAIL`은 두 가지 서로 다른 실패를 모두 표현할 수 있다.

- Technical Failure: 잘못된 입력 타입, 깨진 Schema 파일 등 실행 수준 오류.
  공식 FAL source가 존재하지 않을 수 있어 Evidence를 강제할 수 없다.
- Governance Failure: 표준·Mapping·규제 판단에서의 거부 또는 보류.
  추적성을 위해 Evidence가 반드시 필요하다.

두 유형은 Evidence 요구조건이 다르므로 하나의 Contract로 강제할 수 없다.

## Decision

- `SkillResult`는 Low-level Skill 실행 결과 Contract로 유지한다 (Evidence 선택).
- `GovernanceResult`(`src/k_mds/models/governance.py`)를 별도 Composition Model로
  정의하고 Governance Decision에만 사용한다.
- `GovernanceResult`에는 Evidence가 최소 1개 반드시 존재한다.
- Technical Failure는 `SkillResult`로 반환하며 Evidence는 선택이다.
- Decision 상태는 `GovernanceDecisionStatus`(APPROVED / REVIEW_REQUIRED /
  REJECTED)로 표현한다 — Execution PASS/FAIL(`ResultStatus`)을 재사용하지 않는다.
- `source_results`는 Low-level 실행 증적이며 Evidence 요구조건을 대신하지 않는다.

## Rationale

- 기존 Skill Contract와 generated validation schema의 급격한 변경을 방지한다.
- Technical Input Error에 공식 Evidence를 강제하는 모순을 방지한다.
- 최종 표준·Mapping·규제 판단의 추적성(AGENTS.md §1.3)을 보장한다.

## Invariants

- APPROVED: human_review_required=false, ERROR Finding 금지, FAIL source_result 금지
- REVIEW_REQUIRED: human_review_required=true, Finding 최소 1개(WARNING/ERROR 허용)
- REJECTED: human_review_required=true, ERROR Finding 최소 1개
- evidence_id 중복 금지, Finding.evidence_refs는 evidence 내 evidence_id만 참조

## Non-goals

- Final Assembler 구현 없음
- Manifest Parser 없음
- 실제 IMO Source Hash 검증 없음
- MCP 또는 LangGraph Routing 없음
