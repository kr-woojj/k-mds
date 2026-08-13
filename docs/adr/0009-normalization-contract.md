# ADR-0009: Normalization Contract

- Status: Accepted
- Date: 2026-08-13

## Context

- ADR-0008에 따라 실제 Normalize 산출물은 Internal Restricted다.
- 실제 Workbook Inspection은 verified지만 normalizationReady=false다.
- Normalize는 Workbook 구조를 임의 추론하면 안 된다.
- Header Mapping과 Sheet Classification은 명시적 입력이어야 한다.
- Public Unit Test는 Synthetic Workbook만 사용해야 한다.

## Decision

- Normalizer는 verified Manifest와 verified Inspection Report를 요구한다.
- inspectionMode는 verified-source여야 한다.
- provenanceVerified=true, manifestStatus=verified여야 한다.
- normalizationReady=false 입력은 기본 거부한다.
- 명시적 Human Review 승인 없이 Warning을 무시하는 Option은 제공하지 않는다.
  (Header Confidence medium 허용은 `allow_medium_header_confidence`라는
  명시적 승인 Option으로만 가능하다.)
- Sheet와 Header Mapping은 별도 Mapping Specification으로 받는다.
- 실제 Sheet 이름 대신 sheetOrdinal을 사용한다.
- Row·Column 위치는 1-based Ordinal로 표현한다.
- 실제 Header 문자열은 Normalization 결과 Metadata에 복사하지 않는다.
- 실제 Header Mapping Specification은 Restricted Artifact다.
- 출력은 Internal Restricted Directory에만 허용한다
  (Repository 내부는 data/normalized 아래의 Git-ignored 경로만,
  그 외에는 Repository 외부 Directory만).
- 출력은 Atomic Write한다 (전체 직렬화 성공 후 Rename).
- 실패 시 Partial Output을 남기지 않는다.
- 기존 Output을 자동 덮어쓰지 않는다 (--overwrite Option 없음).
- 동일 입력은 동일 Byte Output을 생성한다.
- Console에 실제 Record, ID, Header, Hash, Path를 출력하지 않는다.
- sourceRecordCount는 완전 Blank Row를 제외한 Data Row 수
  (normalized + rejected)로 정의한다.

## Output Classes

- normalized-records
- normalization-findings
- mapping-evidence
- normalization-summary

모두 internal-restricted다.

## Non-goals

- 실제 FAL50 변환 없음
- 자동 Header 의미 추론 없음
- IMO Semantic Validation 없음
- Public Derived Data 생성 없음

## Amendment (2026-08-13): Reviewed Authorization Gate

- Authorization과 OutputRootBinding은 Normalizer의 **필수 Runtime 입력**이다
  (`authorization_path`, `output_root_binding_path`).
- Normalizer는 ADR-0010 Validator Result의 필수 Flag(valid,
  reportIdentityMatched, sheetCoverageComplete, findingCoverageComplete,
  outputRootAuthorized, humanReviewCompleted)가 모두 승인된 경우에만 실행한다.
- Mapping Spec의 Sheet는 `authorizedSheetOrdinals`에 포함되어야 하며
  (`MAPPING_SHEET_NOT_AUTHORIZED`), 해당 Authorization Sheet는 data_table이고
  headerRow가 Mapping Spec과 일치해야 한다(`AUTHORIZATION_HEADER_MISMATCH`).
- `allow_medium_header_confidence` Option은 폐기한다. 실제 Header Confidence
  승인 책임은 ADR-0010 Authorization(Sheet별 `medium_confidence_approved`)에
  있다. Normalizer는 medium 여부를 자체 추론하지 않는다.
- Validator 실패 시 source_manifest_load, Workbook File I/O, Output Write를
  수행하지 않는다.
- Repository Root는 호출자 입력이 아니라 Script 위치에서 결정론적으로 탐지하며
  `.git`·`pyproject.toml` 존재를 확인한다(`REPOSITORY_ROOT_NOT_FOUND`).
- 기존 Normalizer 자체 Output Boundary는 Validator Binding 검증과 함께
  Defense-in-Depth로 유지된다 — 둘 다 통과해야 실행된다.
- Authorization 및 Binding은 Restricted Artifact다.
