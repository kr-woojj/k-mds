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

## Amendment (2026-08-13): Reviewed Input Binding

- **Report Identity Binding**: `inspection_report_id`는 Inspection Report 원
  Byte의 SHA-256 lowercase hex 64자다(`sha256:` Prefix 금지, Model Pattern 강제).
  Validator는 `compute_inspection_report_id(report_bytes)`로 계산해 상수시간
  비교하며(`INSPECTION_REPORT_ID_MISMATCH`), Dict 재직렬화 Digest를 사용하지
  않는다. 실제 Digest는 Restricted이며 결과·Console에 복사하지 않는다.
- **전체 Sheet Coverage**: Report Sheet Ordinal 집합과 Authorization Sheet
  Ordinal 집합이 정확히 일치해야 한다(`SHEET_AUTHORIZATION_MISSING`/`_EXTRA`,
  `REPORT_SHEET_ORDINAL_DUPLICATE`). 모든 Sheet(제외 Sheet 포함)가 반드시
  분류된다.
- **Finding 집합의 정확한 일치**: (code, sheetOrdinal) Key 기준으로 Report와
  acknowledgedFindings가 정확히 일치해야 한다(`FINDING_AUTHORIZATION_MISSING`/
  `_STALE`, `REPORT_FINDING_DUPLICATE`).
- **Current Blocking Finding 정책 변경**: 현재 Report에 Blocking Finding이
  존재하면 처분과 무관하게 실패한다(`CURRENT_REPORT_BLOCKING_FINDING`).
  해소 절차는 Inspector 재실행 → 새 Report → 새 Identity → 새 Authorization이다.
  `resolved` disposition은 Historical/외부 Workflow 기록용으로만 유지한다.
- **Reviewable Finding**: 현재 Report에서는 `accepted_for_reviewed_scope`만
  허용한다 (Stale Approval 방지).
- **Controlled Reason Code**: reason_code·exclusion_reason_code는
  `^[A-Z][A-Z0-9_]{2,63}$`, Logical Root ID는 `^[A-Z][A-Z0-9_-]{2,63}$` Pattern을
  강제한다 (자유서술 Text·Path Separator 금지).
- **OutputRootBinding**: Logical Root ID를 실제 Restricted Absolute Path에
  결합하는 Local Binding Model(Public에는 Model·Synthetic Fixture만). Validator는
  rootId 일치, resolve 후 Root 포함(Symlink 포함), Repository 내부는
  data/normalized+Ignored만 허용, Tracked/Staged 출력 거부를 검증하며 실제
  Path를 결과에 포함하지 않는다.

### Normalizer Integration 요구사항 (후속 작업)

향후 `normalize_compendium.py`는 Actual Normalize 전에 다음을 요구해야 한다.

- Authorization File과 Output Root Binding File
- Validator `valid=true`, `reportIdentityMatched=true`,
  `sheetCoverageComplete=true`, `findingCoverageComplete=true`,
  `outputRootAuthorized=true`
- `authorizedSheetOrdinals`에 Mapping Spec의 Sheet가 포함됨

Actual Normalize는 Integration 완료 전 실행할 수 없다.

### Integration Amendment (2026-08-13)

- Validator 단독 `valid=true`만으로는 Actual Normalize 승인에 불충분하다 —
  `outputRootAuthorized=true`를 포함한 필수 Flag 전체(valid,
  reportIdentityMatched, sheetCoverageComplete, findingCoverageComplete,
  outputRootAuthorized, humanReviewCompleted)가 모두 true여야 한다.
- Normalizer CLI와 Library API 어느 경로로도 이 Gate를 우회할 수 없다
  (우회 Option 미제공, medium Boolean Override 폐기).
- Authorization·OutputRootBinding·Inspection Report(원 Byte)는 하나의
  **Runtime Authorization Bundle**로 취급한다.
- Binding 없이 실행한 Validator 결과(`outputRootAuthorized=false`)는 Analysis
  용도로만 사용할 수 있으며 실행 승인용이 아니다.

### Readiness Amendment (2026-08-13)

- `valid=true`와 필수 Flag 전체 true는 **authorizedNormalizationReady**를
  의미한다 — Inspector의 기존 `normalizationReady`를 대체하는 Runtime
  Execution Decision이다.
- Inspector Report Byte는 수정하지 않는다. Reviewable Finding 승인 후에도
  `normalizationReady` Field를 수동 변경하지 않는다 — 수동 변경 시 Report
  Identity가 변경되므로 해당 Authorization은 무효가 된다.
- Current Blocking Finding은 계속 새 Inspection Report로만 해소한다.

### Empty Sheet Amendment (2026-08-13)

- `WORKBOOK_EMPTY_SHEET`를 REVIEWABLE_CODES에 추가한다. Current Report에서
  `accepted_for_reviewed_scope` 처분을 허용한다.
- Empty Sheet의 Authorization Classification은 `metadata_or_readme` 또는
  `excluded_non_data`만 허용한다. `data_table`·`code_list`·`normalize=true`로
  승인하면 `EMPTY_SHEET_CLASSIFICATION_INVALID`로 실패한다.
- 권고 reasonCode: `NO_NORMALIZABLE_RECORD_STRUCTURE`,
  `EMPTY_SHEET_EXCLUDED_FROM_SCOPE`.
- Empty Sheet가 존재해도 다른 data_table Sheet가 하나 이상 있으면
  Actual Normalize Authorization은 가능하다.

### Drawing-only Sheet Amendment (2026-08-13)

- `WORKBOOK_DRAWING_ONLY_SHEET`를 REVIEWABLE_CODES에 추가한다.
  `accepted_for_reviewed_scope` 처분만 허용하며 resolved·remains_blocking은
  실패한다.
- Drawing-only Sheet의 Classification은 `metadata_or_readme` 또는
  `excluded_non_data`만 허용하고 `normalize=false`와 exclusionReasonCode가
  필수다. `data_table`·`code_list`로 승인하면
  `DRAWING_ONLY_SHEET_CLASSIFICATION_INVALID`로 실패한다.
- 권고 reasonCode: `DRAWING_ONLY_DOCUMENTATION`,
  `DRAWING_ONLY_EXCLUDED_FROM_SCOPE`, `NON_TABULAR_VISUAL_CONTENT`.
- Drawing-only Sheet 외에 data_table Sheet가 하나 이상 있으면 Authorization이
  가능하다.
- Drawing의 실제 의미 확인은 Restricted Human Review의 책임이며 Validator는
  구조 정합성만 강제한다.

## Model Reference Authorization (Amendment 2026-08-18)

Restricted Review에서 Drawing-only Sheet의 Drawing이 IMO Compendium Reference
Model의 UML 구조로 확인되었다. 기존 Classification(metadata_or_readme,
excluded_non_data)은 이 자산을 잘못 축소할 위험이 있어 신규 Classification을
추가한다.

- 신규 Classification: **model_reference** — Mapping·Semantic Review의 참조
  자산이며 직접 Record Mapping 대상이 아니다.
- Model 불변조건: `normalize=false`, `headerRow=null`, `headerConfidence=none`,
  `mediumConfidenceApproved=false`, `exclusionReasonCode=null` 필수.
- model_reference Sheet는 data_table 또는 code_list Mapping 대상이 아니며
  Validator 결과의 `authorizedSheetOrdinals`에서 제외된다.
- WORKBOOK_DRAWING_ONLY_SHEET Finding Exact Match는 유지된다 — 해당 Finding이
  있는 Sheet만 model_reference로 분류할 수 있다.
- Authorization은 `modelReferenceReviews`(sheetOrdinal 결합)로 Restricted
  Drawing Review 결과를 선언한다. model_reference 승인 조건:
  - `drawingReviewCategory=imo_compendium_model_reference` (documentation·
    out_of_scope_visual·separate_visual_review_required·undecided로는 승인 불가)
  - `completed=true`, `referenceModelAlignmentApproved=true`,
    `modelReferenceScopeApproved=true`, `modelReferenceReviewerRecorded=true`
  - Evidence Reference(Logical ID)와 외부 검증 Assertion 필요
- Model Reference Review 미완료 시 Final Authorization(Validator `valid=true`)은
  실패한다.
- Drawing-only Sheet를 metadata_or_readme 또는 excluded_non_data로 닫으려면
  완료된 비-Model 해소 선언(documentation→metadata_or_readme,
  out_of_scope_visual→excluded_non_data)이 필요하다. 해소 선언이 없거나
  Category가 imo_compendium_model_reference인데 다른 Classification이면
  `MODEL_REFERENCE_AUTHORIZATION_CLASSIFICATION_UNRESOLVED`로 실패한다
  (자동 model_reference 승인 금지, 자동 강등 금지 — fail-closed).
- Mapping Reference Sheet가 있어도 승인된 data_table Sheet가 하나 이상 있으면
  Final Authorization이 가능하다. model_reference만 있고 data_table이 없으면
  Normalize Authorization은 실패한다(`NO_NORMALIZE_TARGET_SHEET`).
- UML Content·Sheet 이름·Drawing Target·Image 이름은 Authorization·Validator
  결과·Finding Message에 복사하지 않는다. 모든 신규 실패 Finding은
  `actualValue=null`이다.
- 실패 Code: `MODEL_REFERENCE_CLASSIFICATION_INVALID`,
  `MODEL_REFERENCE_REVIEW_REQUIRED`, `REFERENCE_MODEL_ALIGNMENT_NOT_APPROVED`,
  `MODEL_REFERENCE_SCOPE_NOT_APPROVED`, `MODEL_REFERENCE_REVIEWER_NOT_RECORDED`,
  `MODEL_REFERENCE_REVIEW_EVIDENCE_NOT_VERIFIED`,
  `MODEL_REFERENCE_AUTHORIZATION_CLASSIFICATION_UNRESOLVED`.

### External Evidence 경계

- Public Authorization Validator는 외부 Audit System을 조회하지 않는다.
  따라서 `externallyVerified=true`를 실제 기술 검증으로 표현하지 않는다.
- Evidence 상태를 세 가지로 분리한다: Evidence Reference 유효성
  (`evidenceReferenceId` Logical ID), 외부 검증 Assertion
  (`externalVerificationAsserted` — 승인 주체의 선언), 기술적 확인
  (`externalVerificationTechnicallyConfirmed` — 외부 Connector의 실제 확인).
- 외부 Connector가 없는 현재 Contract에서는
  `externalVerificationTechnicallyConfirmed=false`만 유효하다 — true로
  선언하면 Validator가 거부하며, 어떤 경로로도 자동으로 true를 만들지 않는다.
- 기관 정책상 Human Assertion(`externalVerificationAsserted=true` + Logical
  Evidence ID)을 Gate 통과 조건으로 허용한다. Assertion의 실재 확인은 내부
  Audit Workflow의 책임이며, 기술적 확인은 외부 Connector 도입 시 별도
  Amendment로 전환한다.

### Non-goals (Model Reference Amendment)

- 실제 Mapping Spec 작성 없음 — UML Class→target_field, Attribute→Column,
  Association→Foreign Key, Cardinality→required 자동 변환 금지
- Actual Normalize 실행 없음
- UML Content 접근·Export·OCR 없음
