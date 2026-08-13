"""Pydantic 모델과 committed generated Schema 간 Drift를 검사한다 (AGENTS.md §2.5).

generate_schemas.py의 동일한 생성 규칙으로 임시 Directory에 Schema를 생성한 뒤
committed 파일과 byte 단위로 비교한다. Drift가 있으면 변경된 파일명만 출력하고
exit 1을 반환한다. 절대경로, 파일 본문, 민감정보를 출력하지 않는다.

환경변수 K_MDS_GENERATED_DIR은 Test에서 비교 대상 Directory를 주입하기 위한
Seam이며 미설정 시 schemas/generated를 사용한다.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from generate_schemas import OUTPUT_DIR, generate_to


def check_drift(generated_dir: Path) -> list[str]:
    """Drift 또는 누락이 발견된 파일명 목록을 반환한다. committed 파일은 수정하지 않는다."""
    drifted: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for filename in generate_to(tmp_dir):
            committed = generated_dir / filename
            if not committed.is_file():
                drifted.append(filename)
                continue
            if committed.read_bytes() != (tmp_dir / filename).read_bytes():
                drifted.append(filename)
    return drifted


def main() -> int:
    generated_dir = Path(os.environ.get("K_MDS_GENERATED_DIR", str(OUTPUT_DIR)))
    drifted = check_drift(generated_dir)
    if drifted:
        for filename in drifted:
            print(f"[schema-drift] 불일치 또는 누락: {filename}")
        print(
            "[schema-drift] src/k_mds/models 변경 후 재생성이 필요하다: "
            "uv run python scripts/generate_schemas.py"
        )
        return 1
    print("[schema-drift] OK: generated Schema가 Pydantic 모델과 일치한다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
