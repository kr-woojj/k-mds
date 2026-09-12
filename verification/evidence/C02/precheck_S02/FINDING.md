# precheck_S02 Finding (2026-09-12) — 검증 run 아님

F-1 (도구 오라클 약점): tools/run_mock_e2e.py 는 최종 상태(REVIEW_REQUIRED)만 기대값과 비교한다.
검증기·registry 부재로 candidate_mapping_eligible=false 인 상태에서 8건 전부
error=GOVERNANCE_CANDIDATE_MAPPING_BLOCKED, profile='-' 로 매핑 단계에 진입하지 못했는데도
"overall=PASS" 를 출력했다(mock_e2e.txt, agent-evidence/*/summary.md).
→ C02 판정에서는 최종 상태 외에 error 코드(None 이어야 함)와 mapping-result.json 존재를 반드시 확인한다.
   baseline reports/mock-e2e-results.json 은 git checkout 으로 원복했고, 생성된 agent evidence 8건은
   correlation_id 중복 차단을 피하기 위해 본 폴더(agent-evidence/)로 이관했다(삭제 아님).

F-2 (전제 부재): imo-compendium-mapping-validator(형제 저장소) 및 k-mds/data/raw/FAL50/IMO Compendium.xlsx 부재.
   pytest 1 failed(test_governance: candidate inventory FILE_NOT_FOUND) / 90 skipped 의 단일 원인. 코드 결함 아님.

F-3 (표준 범위): PoC 코드·문서에 ISO 19848 참조 없음(grep 0건). PoC 매핑 기준은 IMO Compendium(FAL50)만.
   ISO 19848 매핑은 랩오투원 코드북(IMO Compendium↔ISO 19848 1:1/1:N) 측 산출물로, 본 에이전트 범위 밖.
