"""imo-compendium-mapping-validator Skill 어댑터 (Python import 방식).

D-3 근거: validator 는 `app.skill.MappingToolkit` (list_tools/invoke) 를
Agent-facing entrypoint 로 제공하며, 자체 테스트(tests/test_skill_interface.py)가
동일한 import 사용법을 보인다. HTTP wrapper 를 새로 만들지 않는다.

제공 기능:
- readiness check / version discovery
- 입력·출력 검증 (invoke envelope {"ok": bool, ...})
- timeout (thread 기반 — validator 는 동기 코드)
- 구조화 오류 변환 (SKILL_EXECUTION_ERROR / SKILL_CONTRACT_ERROR / SKILL_TIMEOUT)
- invocation audit (호출 기록, evidence 용)
- real/mock indicator
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class SkillAdapterError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class SkillCallRecord:
    tool_name: str
    called_at: str
    latency_ms: float
    ok: bool
    error_code: str | None
    real_call: bool
    correlation_id: str | None = None


@dataclass
class ImoMappingSkillAdapter:
    """실제 validator 호출 어댑터. real_call=True."""

    skill_path: Path
    registry_db_path: Path
    timeout_seconds: float = 60.0
    real_call: bool = True
    call_log: list[SkillCallRecord] = field(default_factory=list)
    _toolkit: Any = None
    _executor: ThreadPoolExecutor | None = None

    # --- 준비 ---

    def _ensure_import(self) -> None:
        if self._toolkit is not None:
            return
        if not self.skill_path.is_dir():
            raise SkillAdapterError("SKILL_NOT_FOUND", f"Skill 경로 없음: {self.skill_path}")
        if not self.registry_db_path.is_file():
            raise SkillAdapterError(
                "REGISTRY_DB_NOT_FOUND",
                f"Registry DB 없음: {self.registry_db_path} — tools/prepare_registry.py 를 먼저 실행",
            )
        path_str = str(self.skill_path.resolve())
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
        try:
            from app.registry.database import init_db, make_session_factory
            from app.skill import MappingSkillService, MappingToolkit
        except ImportError as error:  # pragma: no cover - 환경 구성 오류
            raise SkillAdapterError("SKILL_IMPORT_ERROR", f"validator import 실패: {error}") from error
        engine = init_db(self.registry_db_path)
        service = MappingSkillService(session_factory=make_session_factory(engine))
        self._toolkit = MappingToolkit(service=service)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="skill")

    def readiness(self) -> dict[str, Any]:
        try:
            self._ensure_import()
        except SkillAdapterError as error:
            return {"ready": False, "error_code": error.code, "detail": error.message}
        versions = self.registry_versions()
        return {
            "ready": bool(versions),
            "registry_versions": versions,
            "skill_version": self.skill_version(),
            "real_call": self.real_call,
        }

    def skill_version(self) -> str:
        pyproject = self.skill_path / "pyproject.toml"
        if pyproject.is_file():
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("version"):
                    return line.split("=", 1)[1].strip().strip('"')
        return "UNKNOWN"

    def registry_versions(self) -> list[str]:
        self._ensure_import()
        from app.registry.database import create_engine_for
        from sqlalchemy import text

        engine = create_engine_for(self.registry_db_path)
        with engine.connect() as connection:
            rows = connection.execute(
                text("SELECT version FROM compendium_version WHERE loaded = 1")
            ).fetchall()
        return sorted(str(row[0]) for row in rows)

    # --- 호출 ---

    def list_tools(self) -> list[dict[str, Any]]:
        self._ensure_import()
        return self._toolkit.list_tools()

    def invoke(
        self, tool_name: str, arguments: dict[str, Any], correlation_id: str | None = None
    ) -> dict[str, Any]:
        """envelope {"ok": bool, ...} 를 반환. 실패는 SkillAdapterError."""
        self._ensure_import()
        assert self._executor is not None
        started = time.perf_counter()
        called_at = datetime.now(UTC).isoformat()
        error_code: str | None = None
        ok = False
        try:
            future = self._executor.submit(self._toolkit.invoke, tool_name, arguments)
            try:
                result = future.result(timeout=self.timeout_seconds)
            except FutureTimeout as error:
                error_code = "SKILL_TIMEOUT"
                raise SkillAdapterError(
                    "SKILL_TIMEOUT", f"Skill {tool_name} {self.timeout_seconds}s 초과"
                ) from error
            except Exception as error:
                error_code = "SKILL_EXECUTION_ERROR"
                raise SkillAdapterError("SKILL_EXECUTION_ERROR", str(error)) from error
            if not isinstance(result, dict) or "ok" not in result:
                error_code = "SKILL_CONTRACT_ERROR"
                raise SkillAdapterError(
                    "SKILL_CONTRACT_ERROR", "envelope에 ok 필드가 없다"
                )
            ok = bool(result["ok"])
            if not ok:
                error_code = str(result.get("error", {}).get("code", "SKILL_ERROR"))
            return result
        finally:
            self.call_log.append(
                SkillCallRecord(
                    tool_name=tool_name,
                    called_at=called_at,
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                    ok=ok,
                    error_code=error_code,
                    real_call=self.real_call,
                    correlation_id=correlation_id,
                )
            )

    def drain_call_log(self) -> list[dict[str, Any]]:
        drained = [vars(record) for record in self.call_log]
        self.call_log.clear()
        return drained
