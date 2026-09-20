# kr-ghg-ai-agent

- 테스트: `uv run pytest tests/unit tests/contract -q` (47건). integration 은 `tools/prepare_registry.py` 로 `var/registry.sqlite3` 를 만든 뒤.
- 기본 경로: validator = `../imo-compendium-mapping-validator`, FAL50 xlsx = `../../data/raw/FAL50/IMO Compendium.xlsx` (k-mds 루트). 환경변수 `IMO_MAPPING_SKILL_PATH`, `K_MDS_REFERENCE_PATH` 로 덮어쓴다.
- `.env` 는 원본 폴더(C:\kr-dev\kr-ghg-ai-agent)에 남아 있다. 필요하면 사람이 복사한다. `var/`, `evidence/` 는 재생성 산출물(git 제외).
- LLM 은 매핑 후보 생성만. 최종 판정·수치는 결정론 코드가 한다.
