# ADR-0006: Source Manifest SHA-256 검증

- Status: Accepted
- Date: 2026-08-13

## Context

`SourceManifestEntry.verified`는 현재 호출자가 입력하는 State이며, 실제 파일
검증을 기술적으로 증명하지 않는다. 검증되지 않은 verified=true 입력이
`evidence_build`를 통과하면 출처 추적성이 형식적으로만 유지된다.

## Decision

- Manifest 입력의 `verified`·`status` 필드는 사용하지 않으며 존재 자체를
  금지한다 (`MANIFEST_FORBIDDEN_FIELD`). 두 값은 Loader가 결정한다.
- `source_manifest_load` Loader가 실제 파일의 SHA-256을 Chunk 단위로 계산한다.
- 선언된 Hash와 계산된 Hash가 일치할 때만 `verified=true`, `status=approved`의
  `SourceManifestEntry`를 생성한다.
- `source_file`은 명시적 `base_dir`(미지정 시 Manifest 파일의 부모 디렉터리)
  아래 상대경로만 허용한다. 절대경로·`..` Segment·resolve 후 base 이탈·
  base 밖을 가리키는 Symbolic Link는 모두 `SOURCE_PATH_OUTSIDE_BASE`로 거부한다.

## Hash Format

- 알고리즘은 SHA-256으로 고정한다.
- Manifest에는 lowercase hexadecimal 64자를 사용한다
  (`SourceManifestEntry.source_hash` pattern `^[0-9a-f]{64}$`로 강제).
- `sha256:` prefix는 이번 단계에서 허용하지 않는다.

## Status

- Hash 일치 Entry는 approved로 생성한다.
- Hash 불일치 또는 파일 부재 Entry는 생성하지 않고 전체 Loader가 FAIL한다.
- 부분 성공은 이번 단계에서 허용하지 않는다.
- Finding에는 선언·계산 Hash 값, 파일 경로, 입력값을 포함하지 않는다.
- Loader는 Evidence를 만들지 않는다 — Evidence 생성은 `evidence_build`의
  책임이다 (ADR-0003).

## Non-goals

- 실제 IMO 원본 배치 없음
- Remote URL 다운로드 없음
- Excel 분석 없음
- Final Governance Decision 자동 생성 없음
