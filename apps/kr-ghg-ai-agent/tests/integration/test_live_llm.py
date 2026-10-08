"""TS-4: live commercial LLM invocation (marker: live_llm).

실행 조건 (모두 충족 시에만):
- ALLOW_LIVE_LLM=true
- provider credential 존재 (env 또는 LIVE_LLM_ENV_FILE 로 지정한 .env)

credential 이 없으면 skip 되며, skip 은 성공으로 보고하지 않는다.
전송 데이터: controlled synthetic fixture 의 필드명/설명/타입/단위와
registry 후보 요약만 (S-2 데이터 최소화). 비밀 값은 로그/Evidence 에
기록하지 않는다.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ghg_agent.config import PROJECT_ROOT
from ghg_agent.llm.client import LangChainLLMClient, LLMCandidateBatch
from tests.conftest import requires_registry, requires_skill

pytestmark = pytest.mark.live_llm


def _load_env_file() -> None:
    # 기본은 저장소 루트 k-mds/.env (템플릿 .env.example). LIVE_LLM_ENV_FILE 로 바꿀 수 있다.
    env_file = os.environ.get("LIVE_LLM_ENV_FILE") or str(PROJECT_ROOT.parents[1] / ".env")
    if Path(env_file).is_file():
        from dotenv import load_dotenv

        load_dotenv(env_file, override=False)  # 기존 env 우선


def _live_client() -> LangChainLLMClient | None:
    _load_env_file()
    if os.environ.get("ALLOW_LIVE_LLM", "").lower() != "true":
        return None
    if os.environ.get("AZURE_OPENAI_API_KEY") and os.environ.get("AZURE_OPENAI_ENDPOINT"):
        return LangChainLLMClient(
            provider="azure_openai",
            deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT", ""),
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            timeout_seconds=60.0,
        )
    if os.environ.get("OPENAI_API_KEY"):
        return LangChainLLMClient(
            provider="openai",
            model=os.environ.get("LLM_MODEL")
            or os.environ.get("OPENAI_DEPLOYMENT", "gpt-4o-mini"),
            timeout_seconds=60.0,
        )
    return None


@requires_registry
@requires_skill
def test_live_llm_candidate_generation_and_validation(reference, skill):
    client = _live_client()
    if client is None:
        pytest.skip("SKIPPED_CREDENTIAL_NOT_AVAILABLE (또는 ALLOW_LIVE_LLM!=true)")

    # controlled synthetic fixture: 모호한 단일 필드 + registry 근거 후보
    envelope = skill.invoke(
        "list_candidates",
        {"field": {"name": "distance", "declared_type": "numeric"}, "top_k": 5},
    )
    assert envelope["ok"] is True
    reference_candidates = [
        {
            "imo_data_number": str(c["imoDataNumber"]),
            "name": str(c["registryEvidence"]["name"]),
        }
        for c in envelope["result"]["candidates"]
    ]
    assert reference_candidates, "registry 후보가 필요하다"

    batch = client.generate_candidates(
        field_name="distance",
        description="distance figure reported daily by the crew",
        declared_type="numeric",
        declared_unit="nautical mile",
        report_context="NOON_REPORT",
        reference_candidates=reference_candidates,
        correlation_id="live-llm-001",
    )
    # 구조화 응답 계약
    assert isinstance(batch, LLMCandidateBatch)
    assert 1 <= len(batch.candidates) <= 5

    # 후보를 실제 Skill 로 검증 (accepted/rejected 기록)
    allowed = {c["imo_data_number"] for c in reference_candidates}
    verdicts = []
    for candidate in batch.candidates:
        number = candidate.imo_data_number.strip().upper()
        if number not in allowed or not reference.exists(number):
            verdicts.append({"imo_data_number": number, "verdict": "REJECTED_NOT_IN_REGISTRY"})
            continue
        check = skill.invoke(
            "validate_mapping",
            {"mappings": [{"field": {"name": "distance", "declared_type": "numeric"},
                           "imo_data_number": number}]},
        )
        status = check["result"]["results"][0]["status"] if check.get("ok") else "SKILL_ERROR"
        verdicts.append({"imo_data_number": number, "verdict": status})

    # Evidence (redacted — 비밀/원본 미포함)
    log = client.drain_call_log()
    evidence_dir = PROJECT_ROOT / "evidence" / "live-llm"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence = {
        "correlation_id": "live-llm-001",
        "provider": log[0]["provider"],
        "model": log[0]["model"],
        "invocation_timestamp": log[0]["called_at"],
        "latency_ms": log[0]["latency_ms"],
        "token_usage": log[0]["token_usage"],
        "redacted_input": log[0]["redacted_input"],
        "candidate_count": len(batch.candidates),
        "structured_output": [c.model_dump() for c in batch.candidates],
        "validator_verdicts": verdicts,
        "real_call": True,
    }
    (evidence_dir / f"live-llm-{stamp}.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    assert log[0]["ok"] is True
    assert any(v["verdict"] in ("PASS", "WARNING", "FAIL",
                                "REJECTED_NOT_IN_REGISTRY") for v in verdicts)
