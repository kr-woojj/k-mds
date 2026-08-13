# ADR-0003: Evidence Provenance 정책

- Status: Accepted
- Date: 2026-08-13

## Context

`SkillResult.evidence`는 선택값이다. Schema Contract 검사나 Payload 검증 같은
Low-level validation failure에는 공식 FAL source가 존재하지 않을 수 있으므로
모든 결과에 Evidence를 강제할 수 없다. 반면 임의 문자열을 Evidence로 포장하면
출처 추적성(AGENTS.md §1.3)이 무의미해진다.

## Decision

- Evidence는 검증된 `SourceManifestEntry`(`src/k_mds/models/provenance.py`)에서만
  생성한다 (`evidence_build` Skill).
- Low-level Skill은 Evidence 없이 결과를 반환할 수 있다.
- 공식 Source Provenance가 필요한 Final governance result는 별도 Assembler
  단계에서 Evidence 존재를 강제한다 (Assembler는 후속 작업).
- raw payload 값, source_hash, source_file 경로는 Finding message에 포함하지
  않는다.
- `source_hash`는 호출자가 임의 입력하는 일반 문자열이 아니라
  SourceManifestEntry의 검증된 필드에서만 전달한다.

## Evidence ID

`"evidence:" + source_id`의 결정론적 조합을 사용한다. 임의 hash, uuid,
random, timestamp를 생성하지 않는다. 동일 Entry는 항상 동일한 Evidence를
생성한다.

## Invariants (Pydantic model_validator)

- `verified=true`가 아니면 `status=approved` 불가
- `source_file`은 Repository 상대경로만 허용 (절대경로·`..` Segment 금지)
- `source_hash`·`source_file`은 비어 있을 수 없다
- Hash 알고리즘은 이번 단계에서 강제하지 않으며 실제 파일 존재 여부도
  검사하지 않는다

## Non-goals

- 실제 파일 Hash 계산 미구현
- IMO 원본 배치 없음
- source-manifest.yaml Parser 미구현
- Final Assembler 미구현
