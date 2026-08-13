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

## Amendment (2026-08-13): Local Restricted Manifest 분리와 Inspector Hardening

- Public Placeholder(`data/raw/FAL50/source-manifest.yaml`, pending_source)와
  Local Restricted Manifest(Repository 외부, 실제 filename·SHA-256 포함)를
  분리한다. Local Manifest는 Git에 추적·Stage·Commit·Push하지 않으며 CI에서
  사용하지 않는다. `data/.gitignore`가 raw 하위 Restricted Artifact를 차단한다.
- Inspector에 `--source-base-dir`(Library: `source_base_dir`)를 추가했다.
  미지정 시 manifest parent를 사용하고, 지정 시 Loader의 base_dir로 전달한다.
  Workbook은 resolved source_base_dir 아래에 있어야 하며
  (`WORKBOOK_OUTSIDE_SOURCE_BASE`), base 경로는 Report에 포함하지 않는다.
- Pending 판별을 문자열 포함 방식에서 정확한 Placeholder Contract 검증으로
  강화했다: Strict SafeLoader(중복 Key 거부), Root Extra Field 거부,
  `files == []`, `standard.status`·`ingestion.status`가 정확히
  `pending_source`인 경우에만 pending이다. invalid는 Override로 우회할 수 없다.
- XML Part가 Read Limit를 초과하면 빈 값으로 위장하지 않고
  `WORKBOOK_XML_PART_SCAN_SKIPPED` Finding과 `unsupportedFeatureCount`로
  집계한다 (`--fail-on-unsupported-feature`로 Fatal 전환 가능).
- External Link Metric을 분리했다: `externalLinkDetected`(bool),
  `externalLinkPartCount`, `externalLinkRelationshipCount`. 이 값들은 ZIP
  Container에서 파생된 Detection Count이며 Logical Link 수를 의미하지 않는다.

## Risk Register

- ZIP Bomb Hard Limit는 별도 운영정책으로 결정한다 (현재 Compression Ratio
  Metadata만 기록).
- Workbook 최대 File Size는 별도 운영정책이다.
- 최대 Sheet Count는 별도 운영정책이다.
- openpyxl이 모든 Excel Feature를 완전하게 해석하지 못할 수 있다.
- 실제 Header 의미 검증은 Normalize 단계의 책임이다.
