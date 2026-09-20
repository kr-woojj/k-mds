"""EvidenceAgent (A-7) — 실행별 재현 가능 Evidence 패키지.

경로: evidence/{correlation_id}/
- 모든 stage output 은 staging 디렉터리(evidence/.staging/{cid}-{run_id})에 먼저 쓴다.
- manifest 완결 + hash 검증 후에만 staging 을 최종 디렉터리로 atomic rename 한다.
- finalize 실패 시 최종 디렉터리를 만들지 않고(부분 최종 패키지 0), staging 을 정리하며
  evidence/.recovery/ 에 최소 복구 레코드를 남기고 EvidenceCommitError 를 던진다 (F-STEP6-2).
- manifest.json 에 file_hashes 를 기록해 무결성 검증을 지원한다.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class EvidenceError(Exception):
    """중복/덮어쓰기 등 — orchestrator 가 DuplicateRunError 로 매핑."""


class EvidenceCommitError(Exception):
    """Evidence 최종 커밋 실패 — sanitized, retryable. (Stack/Path/Payload 미노출)"""

    def __init__(self, message: str = "evidence commit failed", *, retryable: bool = True) -> None:
        super().__init__(message)
        self.code = "EVIDENCE_COMMIT_FAILED"
        self.retryable = retryable
        self.message = message


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def code_commit(project_root: Path) -> tuple[str | None, bool]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=project_root,
            capture_output=True, text=True, timeout=10,
        )
        if commit.returncode != 0:
            return None, False
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=project_root,
            capture_output=True, text=True, timeout=10,
        )
        return commit.stdout.strip(), bool(dirty.stdout.strip())
    except OSError:
        return None, False


class EvidenceWriter:
    def __init__(self, base_dir: Path, correlation_id: str) -> None:
        self.base_dir = base_dir
        self.correlation_id = correlation_id
        self.run_id = f"run-{uuid.uuid4().hex[:8]}"
        self.final_dir = base_dir / correlation_id
        # 완료된 run(=최종 manifest 존재)만 중복으로 본다.
        if (self.final_dir / "manifest.json").exists():
            raise EvidenceError(
                f"correlation_id {correlation_id} 의 Evidence 가 이미 존재한다 — 덮어쓰기 금지"
            )
        self.staging_dir = base_dir / ".staging" / f"{correlation_id}-{self.run_id}"
        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir, ignore_errors=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.created_at = datetime.now(UTC).isoformat()
        self._files: list[str] = []
        self._committed = False

    # --- staging writes ---

    def _stage_path(self, name: str) -> Path:
        path = self.staging_dir / name
        if path.exists():
            raise EvidenceError(f"stage output 덮어쓰기 금지: {name}")
        return path

    def write_json(self, name: str, payload: Any) -> Path:
        path = self._stage_path(name)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        self._files.append(name)
        return path

    def write_bytes(self, name: str, raw: bytes) -> Path:
        path = self._stage_path(name)
        path.write_bytes(raw)
        self._files.append(name)
        return path

    def write_text(self, name: str, text: str) -> Path:
        path = self._stage_path(name)
        path.write_text(text, encoding="utf-8")
        self._files.append(name)
        return path

    # --- atomic commit ---

    def finalize_manifest(
        self,
        *,
        source_type: str,
        synthetic_data: bool,
        reference_model_version: str | None,
        validator_version: str | None,
        llm_provider: str,
        llm_model: str,
        mcp_real_or_mock: str,
        skill_real_or_mock: str,
        kr_gears_contract_status: str,
        final_status: str,
        project_root: Path,
        governance_flags: dict[str, bool] | None = None,
    ) -> Path:
        try:
            commit, dirty = code_commit(project_root)
            file_hashes: dict[str, str] = {
                name: _sha256(self.staging_dir / name) for name in sorted(self._files)
            }
            manifest = {
                "correlation_id": self.correlation_id,
                "run_id": self.run_id,
                "created_at": self.created_at,
                "completed_at": datetime.now(UTC).isoformat(),
                "source_type": source_type,
                "synthetic_data": synthetic_data,
                "code_commit": commit,
                "dirty_worktree": dirty,
                "reference_model_version": reference_model_version,
                "validator_version": validator_version,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "mcp_real_or_mock": mcp_real_or_mock,
                "skill_real_or_mock": skill_real_or_mock,
                "kr_gears_contract_status": kr_gears_contract_status,
                "final_status": final_status,
                "governance_flags": governance_flags or {},
                "file_hashes": file_hashes,
            }
            # manifest 를 임시 파일에 기록 후 os.replace 로 staging 내 확정.
            tmp = self.staging_dir / "manifest.json.tmp"
            tmp.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(tmp, self.staging_dir / "manifest.json")
            # manifest 와 hash 재검증 (staging 기준).
            for name, expected in file_hashes.items():
                if _sha256(self.staging_dir / name) != expected:
                    raise EvidenceError(f"staging hash mismatch: {name}")
            # 최종 디렉터리 노출은 여기 atomic rename 에서만 발생.
            if self.final_dir.exists():
                raise EvidenceError("final directory already exists (race)")
            os.replace(self.staging_dir, self.final_dir)
            self._committed = True
            return self.final_dir / "manifest.json"
        except Exception as error:  # noqa: BLE001 — 모든 커밋 실패를 controlled 로 변환
            self._quarantine_and_recover(error)
            raise EvidenceCommitError() from None

    def _quarantine_and_recover(self, error: Exception) -> None:
        """부분 최종 패키지 0 보장: staging 정리 + sanitized 복구 레코드."""
        recovery_dir = self.base_dir / ".recovery"
        try:
            recovery_dir.mkdir(parents=True, exist_ok=True)
            record = {
                "correlation_id": self.correlation_id,
                "run_id": self.run_id,
                "created_at": self.created_at,
                "failed_at": datetime.now(UTC).isoformat(),
                "code": "EVIDENCE_COMMIT_FAILED",
                "retryable": True,
                "failure_type": type(error).__name__,  # sanitized: 유형만, 메시지/stack/path 미포함
                "staged_file_count": len(self._files),
                "final_package_created": False,
            }
            (recovery_dir / f"{self.correlation_id}-{self.run_id}.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except OSError:
            pass
        finally:
            # staging 정리 — 부분 최종 패키지가 최종 경로에 남지 않도록.
            shutil.rmtree(self.staging_dir, ignore_errors=True)


def verify_evidence(directory: Path) -> dict[str, Any]:
    """manifest file_hashes 와 실제 파일 해시 대조."""
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    mismatches = {}
    for name, expected in manifest.get("file_hashes", {}).items():
        actual = _sha256(directory / name) if (directory / name).is_file() else None
        if actual != expected:
            mismatches[name] = {"expected": expected, "actual": actual}
    return {"ok": not mismatches, "mismatches": mismatches, "files": len(manifest.get("file_hashes", {}))}
