# data/ Local AGENTS.md

Root `AGENTS.md`가 Master Contract이다. 이 문서는 `data/` 폴더의 추가 제약만 정의한다.

## 책임

- `raw/`: FAL 버전별 공식 원본 Snapshot과 `source-manifest.yaml`
- `normalized/`: 스크립트가 생성하는 Git Diff 가능 JSON (직접 수정 금지, `DO_NOT_EDIT.md` 참조)
- `samples/`: 매핑 및 검증 테스트 Payload (`valid/`, `invalid/`)

## 추가 금지사항

- `raw/` 내 파일의 내용 수정, 이름 변경, 삭제 (신규 FAL 버전은 새 폴더로 추가)
- 공식 출처 없이 원본처럼 보이는 Excel, HTML, PDF 또는 표준 데이터 배치
- `source-manifest.yaml`에 실제 계산하지 않은 SHA-256 값(Placeholder 포함) 기재
- 원본 미확보 상태에서 `pending_source` 이외의 ingestion status 기재
- `samples/`에 실제 선박·운항 데이터 또는 개인정보·기밀정보 저장 (테스트용 가공 Payload만 허용)
- 하나의 FAL 버전 폴더에 다른 버전의 파일 혼합
