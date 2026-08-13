# ADR-0007: Workbook Inspection 정책

- Status: Accepted
- Date: 2026-08-13

## Context

- 실제 FAL50 Workbook이 Local Restricted Artifact로 배치되었다.
- Normalize 전에 Workbook Structure Inventory가 필요하다.
- 실제 원본과 Derived Metadata의 외부 공개를 금지해야 한다.
- Manifest가 pending 상태일 수 있어 Local Development Override가 필요하다.

## Decision

- Inspection은 read-only, deterministic, fail-closed로 동작한다.
- `source_manifest_load` PASS가 기본 선행조건이다.
- pending Manifest는 명시적 Local Override(`--allow-pending-manifest`)에서만
  허용하며, CI·Normalize·evidence_build·Governance Evidence에 사용할 수 없다.
- invalid Manifest는 Override로 무시할 수 없다.
- ZIP Container Preflight를 openpyxl Load보다 먼저 수행한다.
- 실제 Cell 값, Header 원문, Formula 원문, Sheet 이름을 Report에 저장하지 않는다.
- Sheet 이름과 Header 값은 SHA-256 Digest로만 표현한다.
- Formula 계산, Macro 실행, External Link Follow, Workbook Save를 금지한다.
- 실제 Report는 Internal Restricted Derived Metadata다.
- Synthetic Fixture Report만 Test/Public으로 분류할 수 있다.
- Normalize는 provenanceVerified=true Report만 사용할 수 있다.
- Scan Limit(row·column)는 CLI에서 명시적으로 전달한다 (기본값 없음).

## Report Classification

- Actual FAL50 Report: internal-restricted
- Synthetic Fixture Result: test-public
- Actual Workbook: internal-restricted

## Non-goals

- 의미적 IMO ID 검증 없음
- Normalize 없음
- PDF 또는 HTML Parsing 없음
- 원본 공개 없음
- Derived Report 공개 없음
- Formula Evaluation 없음
- Macro Analysis 또는 실행 없음
- External Link Content Retrieval 없음

## Risk Register

- ZIP Bomb Hard Limit는 별도 운영정책으로 결정한다 (현재 Compression Ratio
  Metadata만 기록).
- Workbook 최대 File Size는 별도 운영정책이다.
- 최대 Sheet Count는 별도 운영정책이다.
- openpyxl이 모든 Excel Feature를 완전하게 해석하지 못할 수 있다.
- 실제 Header 의미 검증은 Normalize 단계의 책임이다.
