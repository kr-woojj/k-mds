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

## Amendment (2026-08-13)

- YAML Duplicate Key: 동일 Mapping 내 중복 Key는 SafeLoader 기반 Custom
  Loader의 Constructor 단계에서 `MANIFEST_DUPLICATE_KEY`로 거부한다.
  오류에는 중복 Key 이름과 값을 포함하지 않는다.
- 파일 접근 전 검증: Entry의 구조, Hash Format, 금지 필드(verified/status)는
  입력 전용 Private Model(`_ManifestSourceInput`, extra="forbid")로
  파일 I/O 전에 검증한다. 구조적으로 잘못된 Entry에 대해서는 파일을 열거나
  Hash를 계산하지 않는다.
- 오류 분류 분리: Hash Format 오류는 `SOURCE_HASH_FORMAT_INVALID`,
  실제 파일 Hash 불일치는 `SOURCE_HASH_MISMATCH`로 구분한다.
- Safe Type 정책: `yaml.SafeLoader` 수준의 Safe Type 정책을 유지하며
  Unsafe Loader를 사용하지 않는다.
- 실제 원본 배치 정책은 본 ADR의 범위가 아니다.

### 후속 Risk (운영정책 대상)

- Manifest 크기 제한값은 이번 단계에서 도입하지 않았다 — 대용량 Manifest에
  대한 크기·항목 수 제한은 후속 운영정책으로 결정한다.
- YAML Alias Resource Limit(별칭 폭발 방어)도 후속 운영정책 대상으로 기록한다.
