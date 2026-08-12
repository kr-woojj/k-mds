# ontology/ Local AGENTS.md

Root `AGENTS.md`가 Master Contract이다. 이 문서는 `ontology/` 폴더의 추가 제약만 정의한다.

## 책임

- `core/`: 공통 Ontology Class, Relation, Context, SHACL Shape
- `domains/`: 국제표준 기반 데이터 유형별 Dataset 및 Component (예: `environment-ghg`)
- `profiles/`: 업무 목적별 선택집합과 추가 제약 (예: `kr-ghg`)
- `mappings/source-to-imo/`, `mappings/imo-to-target/`: 방향별 Mapping YAML
- `generated/`: 자동 생성 JSON-LD와 Turtle (직접 수정 금지, `DO_NOT_EDIT.md` 참조)

## 추가 금지사항

- IMO Core Ontology(`core/`, `domains/`)에 KR 업무 해석 또는 KR GHG Profile 내용 기재 — Profile 확장은 `profiles/kr-ghg/`에만 기재
- Source-to-IMO Mapping과 IMO-to-Target Mapping을 하나의 파일 또는 폴더에 혼합
- 공식 출처에서 확인되지 않은 IMO ID, 정의, Technical Position, Format, Code Value 기재 — 미확인 항목은 `unresolved` 또는 `review_required`로 기록
- 하나의 IMO ID에 단일 Technical Position만 저장 (DataElement와 ElementOccurrence를 분리)
- 근거(Evidence) 없는 매핑에 `approved` 상태 부여
- Canonical Path와 Target System Path 혼합
