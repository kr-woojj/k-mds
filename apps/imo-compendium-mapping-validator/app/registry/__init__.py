"""IMO Compendium Registry 적재·조회 모듈.

- Registry는 IMO Data Number의 유일한 원천이다 (REQ-006).
- 버전은 immutable snapshot으로 보관하며 삭제·덮어쓰기하지 않는다 (REQ-008).
- 적재는 전체 성공 또는 전체 실패다 — 부분 commit 금지 (REQ-033).
"""

from app.registry.diff import diff_versions
from app.registry.loader import ImportResult, run_import

__all__ = ["ImportResult", "diff_versions", "run_import"]
