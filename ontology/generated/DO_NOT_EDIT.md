# 직접 수정 금지

이 폴더(`ontology/generated/`)의 JSON-LD와 Turtle 파일은 `scripts/build_ontology.py`가 Source Model에서 생성한다 (AGENTS.md §2.5).

- 이 폴더의 파일을 직접 수정하지 않는다.
- 수정이 필요하면 `ontology/core/`, `ontology/domains/`, `ontology/profiles/`의 Source YAML 또는 생성 스크립트를 수정한 후 `make build`를 실행한다.
- 현재는 Bootstrap 단계로 생성 파이프라인이 아직 구현되지 않았다.
