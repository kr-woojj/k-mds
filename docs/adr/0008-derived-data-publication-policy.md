# ADR-0008: IMO Derived Data Publication Policy

- Status: Accepted
- Date: 2026-08-13

## Context

- `data/raw`의 실제 원본은 Restricted Local Artifact다 (ADR-0007).
- Normalize 산출물은 원본의 연계·가공·분석으로 생성되는 Derived Data다.
- 원본 Binary가 없어도 실제 IMO 식별자, 정의, Code List, Dataset 관계,
  Header Mapping 및 Record를 대량 포함할 수 있다.
- Public Repository 배포 권한은 현재 확인되지 않았다.
- 기술적 변환이 새로운 자유 이용권리를 자동 생성하는 것은 아니다.
- Source Code와 Generic Schema는 실제 Derived Record와 구분해야 한다.

이 ADR은 법적 위반 여부를 단정하지 않으며, 공개 권한이 확인되지 않은 상태에서
Default Deny 원칙을 적용한다.

## Decision

- `data/normalized`의 실제 산출물은 Internal Restricted Derived Data로 분류한다.
- 기본 공개정책은 Default Deny다.
- Git Stage, Commit, Push, Tag, Release, Git LFS를 금지한다.
- CI Artifact, Test Snapshot, Build Log, Debug Log, Exception Message를 통한
  우발적 공개도 금지한다.
- 실제 파생데이터는 Local Environment 또는 승인된 Internal Artifact Storage에서
  생성·보관·소비한다.
- Public Repository에는 Source Code, Generic Contract 및 Synthetic Fixture만
  포함할 수 있다.
- 실제 파생데이터의 공개는 Publication Exception 절차를 거쳐야 한다.
- `.gitignore`는 실수 방지 장치이며 접근통제나 법적 권한을 대신하지 않는다.
- 실제 Normalize Pipeline은 출력경로가 Restricted Directory인지 향후
  Runtime Boundary에서 강제해야 한다.

## Classification

| Class | Git 허용 | CI Artifact 허용 | Internal Storage 허용 | 승인 필요 |
|---|---|---|---|---|
| restricted-normalized-record | 금지 | 금지 | 허용 | Publication Exception |
| restricted-derived-report | 금지 | 금지 | 허용 | Publication Exception |
| public-candidate-schema | 허용(Review 후) | 허용 | 허용 | 기존 Review·승인 절차 |
| public-candidate-source-code | 허용(Review 후) | 허용 | 허용 | 기존 Review·승인 절차 |
| synthetic-test-fixture | 허용 | 허용 | 허용 | 기존 Test 정책 |
| publication-exception | 별도 승인 시만 | 별도 승인 시만 | 허용 | 필수(하단 절차) |

- Restricted Normalized Record 예: 원본 Row 추출 데이터 요소, 실제 IMO ID 목록,
  실제 Description·Definition·Code List Value, 실제 Dataset 구성, Header·Row·Column
  Mapping, Changes·Readme 기반 변경정보, 실제 Workbook 기반 Validation Finding,
  Normalize Summary, Mapping Evidence, 실제 Record Count와 상세 구조,
  실제 Source Hash·File Name, 실제 Header·Sheet Digest.
- Restricted Derived Report 예: `normalization-report*`, `normalization-findings*`,
  `mapping-evidence*`, `rejected-records*`, `normalization-summary*`,
  실제 Workbook 기반 Inspection Report.
- Public Candidate 예: `normalize_compendium.py` Source Code, Generic JSON Schema,
  Pydantic Model, Synthetic Fixture(TEST/FALTEST/urn:test), 원본 값을 포함하지
  않는 일반화된 Mapping Algorithm, 원본과 무관한 Documentation.
  Public Candidate라는 이유만으로 자동 공개하지 않으며 기존 Repository Review,
  Test, Notice 및 승인절차를 통과해야 한다.

### Publication Exception 절차

Restricted Artifact의 Public 공개는 다음이 모두 완료된 경우에만 별도 승인한다.

- 데이터 이용권리 확인
- 파생데이터 공개범위 확인
- 법무 또는 IP 검토
- Repository Owner 승인
- 연구책임자 승인
- 데이터소유자 또는 권한보유자 승인
- 비식별·요약·재식별 위험 검토
- NOTICE 및 License Scope 검토
- 별도 ADR
- 별도 Commit

본 ADR은 Publication Exception을 승인하지 않는다.

## Storage

허용:

- Local Ignored Directory
- Repository 외부 Secure Directory
- 승인된 Internal Artifact Storage
- 접근통제된 Private Pipeline Workspace

금지:

- Public Git
- Public Release
- Public CI Artifact
- Public Object Storage
- Issue 또는 Pull Request 첨부
- Email·Chat를 통한 무통제 파일 공유

## Retention and Disposal

이번 결정에서 보존기간을 임의로 정하지 않는다. 다음을 후속 운영정책으로
기록한다: 보존기간, Artifact Owner, 접근권한, 백업정책, 암호화정책,
삭제 및 폐기정책, Audit Log, Incident Response.

## Consequences

- 개발자는 실제 Normalize 산출물을 Local 또는 Internal Storage에서 재생성해야 한다.
- Build Cache는 Restricted Storage에서만 허용한다.
- Public CI는 Synthetic Fixture만 사용한다.
- 실제 Normalize 결과를 기반으로 한 Snapshot Test는 금지한다.
- 재현성은 Source Manifest, Version, Algorithm Version 및 Internal Evidence로
  보장한다.
- 공개 가능한 Schema와 Restricted Record를 별도 경로로 관리해야 한다.

## Non-goals

- 법률 의견 확정 없음
- 실제 Normalize 구현 없음
- 실제 Derived Data 생성 없음
- Public Release 승인 없음
- Internal Artifact Storage 구현 없음
