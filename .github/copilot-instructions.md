# GitHub Copilot 연결 지침

이 파일은 연결 지침만 제공한다. 규칙 본문을 이 파일에 복사하지 않는다.

작업 전에 다음 순서로 지침을 읽고 적용한다 (AGENTS.md §2.6 지침 계층).

1. Repository Root의 [`AGENTS.md`](../AGENTS.md) — Master Contract, 항상 먼저 읽는다.
2. 변경 대상 파일에서 가장 가까운 상위 폴더의 Local `AGENTS.md` — 현재 경계 폴더: [`data/`](../data/AGENTS.md), [`ontology/`](../ontology/AGENTS.md), [`schemas/`](../schemas/AGENTS.md), [`src/`](../src/AGENTS.md), [`tests/`](../tests/AGENTS.md)
3. 승인된 작업 Prompt 및 현재 사용자 요청

Local `AGENTS.md`는 Root 규칙을 완화하거나 무효화할 수 없다. 지침 간 충돌 시 더 엄격한 데이터 무결성, 보안, Evidence 및 검증 규칙을 적용하고 충돌 사실을 작업 결과에 기록한다.
