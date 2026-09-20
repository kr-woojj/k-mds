# 환경규제 보고 데이터 표준 모델 (단일 원본)

앱 3종이 참조하는 스키마·명세는 여기 한 벌만 둔다. 앱 안에 사본을 커밋하지 않는다.

| 파일 | 내용 | 출처 |
| --- | --- | --- |
| `data-model.md` | ER 다이어그램(mermaid). 엔티티 12개, 필드마다 IMO Compendium 데이터 요소 번호(IMO0140 등) 주석 | data-space `imo_compendium.md` (2026-09-20 이동) |
| `openapi.yaml` | Ship-ODMS API OpenAPI 3.0.1 명세. `components/schemas`는 `data-model.md`와 1:1 | data-space `openapi.yaml` (동일 사본 3벌 중 1벌) |
| `gaps.md` | 7개 데이터 그룹·규제 항목 중 대응 요소가 없거나 미확정인 것 | |

IMO Compendium 원본(FAL50 xlsx, sha256은 manifest)은 `data/raw/FAL50/`에 있고 git에 올리지 않는다.
매핑 검증 API 계약(JSON Schema)은 `apps/imo-compendium-mapping-validator/schemas/`에 있다(표준 모델이 아니라 API 계약).

규칙: 스키마를 바꾸면 같은 커밋에서 `openapi.yaml`, 예제 페이로드, 검증 기대값을 함께 고친다(`.claude/rules/standard-model.md`).
