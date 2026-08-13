# ADR-0010: Normalization Authorization

- Status: Accepted
- Date: 2026-08-13

## Context

- Verified Inspection과 Normalize 가능 상태는 다르다.
- 모든 Warning이 같은 의미를 갖지 않는다.
- 단순 Boolean Override는 승인 대상과 근거를 추적할 수 없다.
- 실제 Header Mapping과 Sheet Classification은 Restricted Review가 필요하다.
- Actual Normalize 전에 Scan Coverage와 Output Storage 승인이 필요하다.

## Decision

- Normalization Authorization은 별도 Restricted Artifact다.
- Actual Authorization은 Public Git에 Commit하지 않는다.
- Public Repository에는 Contract(`NormalizationAuthorization` Pydantic Model,
  `validate_normalization_authorization.py`)와 Synthetic Fixture만 포함한다.
- Authorization은 sourceId 및 Inspection Report Identity(`inspection_report_id`)에
  결합한다. Actual Local 실행에서는 Report Byte Digest를 Local에서만 계산하며
  실제 Digest를 Public Commit이나 Validator 결과에 복사하지 않는다.
- 승인 Sheet는 sheetOrdinal로 식별하고 Sheet 이름은 저장하지 않는다.
- Sheet별 Classification을 명시한다: data_table Sheet만 Normalize 대상이 될 수
  있고, excluded_non_data와 metadata_or_readme는 제외 이유 Code가 필요하며,
  code_list는 별도 Code-list Mapping ADR 전에는 일반 Record Normalize 대상이
  아니다.
- Header Row와 Header Confidence 승인상태를 명시한다. Medium Confidence는
  Sheet별 승인(`medium_confidence_approved`) 근거가 있어야 하고, low·none
  Confidence는 data_table로 승인할 수 없다.
- Scan Limit Finding은 Coverage 승인(resolved 처분) 없이 해제할 수 없다.
- Output Storage Root는 Logical ID(`approved_output_root_id`)로만 기록하며
  실제 Path는 Repository 외부 Local Runtime Binding(`rootId`+`path`)으로
  주입한다. Normalizer는 향후 Binding rootId 일치, resolve 후 Binding Path 포함,
  Public Repository Path 배제, data/normalized 사용 시 Git Ignore를 강제해야 한다.
- Authorization은 Timestamp, 개인명, 이메일을 사용하지 않고 결정론적이어야 한다.
- 승인 주체의 신원 Workflow는 후속 운영정책으로 분리한다.
- Authorization 변조 검증은 실제 실행 시 Local Digest로 확인한다.

## Finding Classification

blocking (resolved 처분 없이는 승인 불가):

- WORKBOOK_SCAN_LIMIT_REACHED
- WORKBOOK_HEADER_NOT_DETECTED
- WORKBOOK_XML_PART_SCAN_SKIPPED
- Fatal ERROR Finding (Authorization으로 승인 불가)

reviewable (accepted_for_reviewed_scope 허용):

- WORKBOOK_DECLARED_DIMENSION_EXCESSIVE
- WORKBOOK_PROTECTION_ENABLED
- WORKBOOK_CUSTOM_XML_PRESENT
- WORKBOOK_DIGITAL_SIGNATURE_PRESENT

informational:

- 별도 ADR에서 확정되지 않은 항목은 자동 informational로 내리지 않는다.

Unknown Finding:

- 기본 blocking이다.
- 명시적 Policy 추가 전에는 승인할 수 없다.

## Non-goals

- 실제 Sheet 의미 추출 없음
- 법적 승인 Workflow 없음
- 실제 Mapping 작성 없음
- 실제 Normalize 실행 없음
