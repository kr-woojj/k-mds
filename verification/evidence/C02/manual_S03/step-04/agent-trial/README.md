# step-04 agent-trial (정식 run 아님, 2026-09-12)
실 Provider payload(step-04/payloads/)를 GHG AI Agent 파이프라인(LLM mock, Skill real)에 6개 변형으로 투입한 시험 결과.
변형: wrapper(원본 {code,message,data}), data(래퍼 제거), data.events[0] / data.items[0](단일 레코드).
결과: 6건 전부 REVIEW_REQUIRED / PROFILE_UNKNOWN ("no deterministic marker") — 매핑 단계 미진입.
원인: 프로파일러(domain/profiling.py)는 report_type 마커 또는 fixture 계열 필드명(_NOON/_EVENT/_PERFORMANCE_MARKERS)만 인식.
      랩오투원 payload 는 코드북 externalKey(camelCase: eventKey, dateEventUtc, consumptionMeHfo …)를 키로 사용.
