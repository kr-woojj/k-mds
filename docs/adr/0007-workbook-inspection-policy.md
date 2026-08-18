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

## Empty Sheet Semantics (Amendment 2026-08-13)

- Empty Sheet는 Scan Limit Failure가 아니고 Header Detection Failure도 아니다 —
  명시적인 Structural Inventory 상태다.
- Empty Sheet는 `WORKBOOK_EMPTY_SHEET` Warning으로 표현하며 Reviewable이다.
- Empty Sheet는 자동 Normalize 대상이 아니다.
- Empty 판정은 Full Scan Coverage가 확보된 경우에만 가능하다 —
  Scan Budget이 실제 Declared Dimension보다 작으면 Empty 판정을 내리지 않는다.
- Empty 판정 조건: 비어있지 않은 Cell·Formula·Error Cell·Comment·Hyperlink·
  Data Validation·Table·Drawing·Merged Range가 전부 0.
  Sheet State, Protection, Hidden Dimension, Declared Dimension,
  Document Properties는 Empty 판정을 막지 않으며 별도 Metadata·Finding으로
  유지한다.
- Scan Limit 판정 변경: `WORKBOOK_SCAN_LIMIT_REACHED`는 실제 iterated row 수가
  아니라 **Declared Dimension이 명시적 Scan Budget을 초과한 경우에만** 발생한다.
  실제 iterated row 수는 scannedRowCount Metadata로만 기록한다.
- Empty Sheet에서는 `WORKBOOK_HEADER_NOT_DETECTED`를 발생시키지 않는다.
  Non-empty Sheet의 Header 미탐지는 기존 Blocking Policy를 유지한다.

## Drawing-only Sheet Semantics (Amendment 2026-08-13)

- Drawing-only Sheet는 Empty Sheet가 아니다 — Cell Record 없이 Drawing Content가
  존재하는 구조상 Non-tabular Sheet Candidate다.
- Drawing-only Sheet는 Header Detection Failure가 아니며
  `WORKBOOK_HEADER_NOT_DETECTED`를 발생시키지 않는다.
- `WORKBOOK_DRAWING_ONLY_SHEET` Warning으로 Inventory하며 Reviewable이다.
- 실제 Drawing의 의미는 Inspector가 판단하지 않는다 — Restricted Human Review의
  책임이다.
- Drawing Content, Relationship Target, Image, Text는 Report에 저장하지 않는다.
  Report에는 drawingCount(정수)만 남는다.
- Full Scan Coverage가 확보된 경우에만 Drawing-only 판정이 가능하다.
- 판정 조건: 비어있지 않은 Cell·Formula·Error Cell·Comment·Hyperlink·
  Data Validation·Table·Merged Range가 전부 0이고 drawingCount ≥ 1.
  Hidden·VeryHidden State, Protection, Hidden Row·Column, Declared Dimension,
  Document Properties는 판정을 막지 않고 별도 Metadata·Finding으로 유지한다.
- Drawing과 위 Feature가 함께 있는 Sheet에서 Header를 찾지 못하면 기존
  `WORKBOOK_HEADER_NOT_DETECTED` Policy를 유지한다.
- Drawing-only Sheet는 자동 Normalize 대상이 아니다.
- 판정 순서: Scan Coverage → Empty → Drawing-only → 기존 Header Detection.

## Model Reference Sheet Semantics (Amendment 2026-08-18)

- Drawing-only는 구조적 Inspector Finding이다 — Inspector는 Drawing의 의미를
  판단하지 않는다.
- 실제 Drawing 의미는 Restricted Human Review에서 결정한다.
- Restricted Review에서 Drawing이 IMO Compendium Reference Model의 UML 구조로
  확인된 경우 해당 Sheet는 **Model Reference Asset**으로 취급한다.
- Model Reference Asset은 Empty Sheet, Documentation, Out-of-scope Visual과
  구분되는 별도 자산 유형이다 — 단순 metadata 또는 excluded로 축소하지 않는다.
- Model Reference Asset은 직접 Normalize 대상이 아니다 (Record 추출 금지).
- UML Content(Class·Attribute·Association·Cardinality·Diagram Text·Image·
  Relationship Target)는 Inspector Report에 저장하지 않는다 — Report에는
  drawingCount(정수)만 남는다.
- UML은 Mapping Scope, Entity Relationship, Code List Relationship,
  Business Semantic 및 Dataset Boundary Review에 참조 자산으로 사용할 수 있다.
- UML 참조가 승인되어도 실제 Field Mapping은 별도 Mapping Spec Review를
  요구한다 — UML에서 Target Field·Mapping Spec을 자동 생성하지 않는다.

## Risk Register

- ZIP Bomb Hard Limit는 별도 운영정책으로 결정한다 (현재 Compression Ratio
  Metadata만 기록).
- Workbook 최대 File Size는 별도 운영정책이다.
- 최대 Sheet Count는 별도 운영정책이다.
- openpyxl이 모든 Excel Feature를 완전하게 해석하지 못할 수 있다.
- drawingCount는 Sheet XML의 Drawing Node 수만 집계하며 Chart·Image·Shape·
  SmartArt 등 세부 유형을 구분하지 못한다. Drawing-only Sheet의 실제 내용
  판단은 Restricted Human Review에서 수행해야 한다.
- 실제 Header 의미 검증은 Normalize 단계의 책임이다.
