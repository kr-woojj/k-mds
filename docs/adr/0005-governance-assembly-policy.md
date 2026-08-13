# ADR-0005: Governance Assembly 정책

- Status: Accepted
- Date: 2026-08-13

## Context

`SkillResult.FAIL`만으로는 Technical Failure와 Governance Failure를 구분할 수
없다(ADR-0004). 따라서 Assembler가 source_results의 PASS/FAIL에서 Governance
상태를 자동 도출하는 것은 안전하지 않다 — 입력 타입 오류 같은 Technical
Failure가 REJECTED 규제 판정으로 오인될 수 있다.

## Decision

- Governance status와 decision type은 호출자가 명시적으로 제공한다.
- `governance_assemble`은 상태를 추론하지 않는다.
- 성공적으로 REJECTED 결정을 조립해도 실행 결과는 `SkillResult.PASS`다.
  바깥 SkillResult는 Assembler 실행 성공을, 내부 GovernanceResult는
  Governance Decision을 뜻한다.
- 공식 Evidence는 evidence_build 결과(`evidence_results`)에서만 수집한다.
- `source_results`의 nested Evidence는 자동 승격하지 않는다.

## Evidence Merge

- 같은 evidence_id와 동일 내용은 deduplicate한다.
- 같은 evidence_id와 다른 내용은 FAIL(`EVIDENCE_ID_CONFLICT`)이다.
- Evidence 결과가 성공(PASS·오류 없음·Evidence ≥1)이 아니면 조립 FAIL
  (`EVIDENCE_RESULT_NOT_SUCCESSFUL`)이다.
- 수집된 Evidence가 0개면 조립 FAIL(`GOVERNANCE_EVIDENCE_REQUIRED`)이다.
- 수집 순서는 입력 순서를 유지한다.

## Non-goals

- Governance Decision Engine 없음 (상태 자동 도출 없음)
- Rule Evaluation 없음
- Manifest Parser 없음
- MCP 및 LangGraph 없음
