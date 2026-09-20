"""FastAPI integration service (지시서 FASTAPI CONTRACT).

- POST /api/v1/ids/events        IDS Consumer payload 수신 → 전체 파이프라인
- POST /api/v1/map               canonical payload 매핑
- POST /api/v1/validate          매핑 결과 결정론 검증
- POST /api/v1/transform/kr-gears  검증된 매핑 변환 (PROVISIONAL 명시)
- GET  /api/v1/runs/{correlation_id}
- GET  /health                   liveness only
- GET  /ready                    구성요소 readiness (READY/DEGRADED/NOT_READY)
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from ghg_agent.adapters.kr_gears import transform
from ghg_agent.agents.orchestrator import DuplicateRunError, Pipeline, build_pipeline
from ghg_agent.config import Settings, load_settings
from ghg_agent.domain.mapping import MapperConfig, map_fields
from ghg_agent.domain.models import (
    CanonicalField,
    MappingResult,
    SourceProfile,
    ValidationResult,
)
from ghg_agent.domain.normalization import NormalizationError, normalize_payload
from ghg_agent.domain.validation import ValidationConfig, validate_mapping_result
from ghg_agent.evidence import EvidenceCommitError
from ghg_agent.llm.client import LLMClient


class MapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: SourceProfile
    payload: dict[str, Any]
    correlation_id: str = "adhoc-map"


class ValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mapping_result: MappingResult
    fields: list[CanonicalField] = Field(default_factory=list)


class TransformRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mapping_result: MappingResult
    fields: list[CanonicalField] = Field(default_factory=list)
    validation_result: ValidationResult


def create_app(
    settings: Settings | None = None, llm_client: LLMClient | None = None
) -> FastAPI:
    settings = settings or load_settings()
    pipeline: Pipeline = build_pipeline(settings, llm_client)

    app = FastAPI(
        title="kr-ghg-ai-agent",
        version="0.1.0",
        description=(
            "GHG AI Agent PoC — deterministic-first IMO Compendium mapping, "
            "validation, KR GEARs(PROVISIONAL) transformation"
        ),
    )
    app.state.pipeline = pipeline
    app.state.settings = settings

    @app.post("/api/v1/ids/events")
    async def ids_events(request: Request) -> JSONResponse:
        raw = await request.body()
        content_type = request.headers.get("content-type")
        try:
            state = pipeline.run(raw, content_type)
        except DuplicateRunError as error:
            raise HTTPException(
                status_code=409,
                detail={"error": "DUPLICATE_CORRELATION_ID",
                        "correlation_id": error.correlation_id},
            ) from error
        except EvidenceCommitError as error:
            # F-STEP6-2: evidence 커밋 실패는 sanitized 5xx + retryable (부분 최종 패키지 없음).
            return JSONResponse(
                status_code=503,
                content={"error": error.code, "retryable": error.retryable,
                         "message": "evidence commit failed"},
            )
        body = {
            "correlation_id": state.correlation_id,
            "final_status": state.status.value,
            "error": state.error,
            "evidence_dir": str(
                (settings.audit_log_dir / state.correlation_id).resolve()
            ),
        }
        if state.ingress is not None and state.ingress.validation_errors:
            return JSONResponse(
                status_code=422,
                content={
                    **body,
                    "validation_errors": state.ingress.validation_errors,
                    "raw_sha256": state.ingress.raw_sha256,
                },
            )
        return JSONResponse(status_code=200, content=body)

    @app.post("/api/v1/map")
    def map_endpoint(request: MapRequest) -> dict[str, Any]:
        # Governance: CandidateSet/Reference Authority 미승인 시 매핑 차단(fail-closed)
        if not pipeline.governance.candidate_mapping_eligible:
            raise HTTPException(
                status_code=409,
                detail={"error": "GOVERNANCE_CANDIDATE_MAPPING_BLOCKED",
                        "flags": pipeline.governance.flags()},
            )
        try:
            fields = normalize_payload(request.payload, request.profile)
        except NormalizationError as error:
            raise HTTPException(
                status_code=422, detail={"error": error.code, "message": error.message}
            ) from error
        result = map_fields(
            fields, request.profile, pipeline.reference, pipeline.skill,
            pipeline.llm_client,
            MapperConfig(confidence_threshold=settings.mapping_confidence_threshold,
                         candidate_scope=pipeline.candidate_scope),
            request.correlation_id,
        )
        return {
            "mapping_result": result.model_dump(mode="json"),
            "fields": [f.model_dump(mode="json") for f in fields],
        }

    @app.post("/api/v1/validate")
    def validate_endpoint(request: ValidateRequest) -> dict[str, Any]:
        result = validate_mapping_result(
            request.mapping_result, request.fields, pipeline.reference,
            pipeline.skill,
            ValidationConfig(confidence_threshold=settings.mapping_confidence_threshold),
        )
        return result.model_dump(mode="json")

    @app.post("/api/v1/transform/kr-gears")
    def transform_endpoint(request: TransformRequest) -> dict[str, Any]:
        try:
            result = transform(
                request.mapping_result, request.fields, request.validation_result,
                request.mapping_result.correlation_id,
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return result.model_dump(mode="json")

    @app.get("/api/v1/runs/{correlation_id}")
    def get_run(correlation_id: str) -> dict[str, Any]:
        directory = settings.audit_log_dir / correlation_id
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            raise HTTPException(status_code=404, detail="run not found")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        summary_path = directory / "summary.md"
        return {
            "correlation_id": correlation_id,
            "final_status": manifest.get("final_status"),
            "summary": summary_path.read_text(encoding="utf-8")
            if summary_path.is_file()
            else None,
            "manifest": manifest,
            "evidence_files": sorted(p.name for p in directory.iterdir() if p.is_file()),
        }

    @app.get("/api/v1/governance")
    def governance_context() -> dict[str, Any]:
        return pipeline.governance.snapshot()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> JSONResponse:
        components: dict[str, Any] = {}
        # reference model
        try:
            pipeline.reference.load()
            components["reference_model"] = {
                "status": "READY",
                "version": pipeline.reference.version,
                "elements": pipeline.reference.element_count(),
            }
        except Exception as error:
            components["reference_model"] = {"status": "NOT_READY", "detail": type(error).__name__}
        # skill
        skill_ready = pipeline.skill.readiness()
        components["skill"] = {
            "status": "READY" if skill_ready.get("ready") else "NOT_READY",
            **{k: v for k, v in skill_ready.items() if k != "ready"},
        }
        # MCP (optional)
        components["mcp"] = {
            "status": "OFF" if pipeline.mcp_mode == "off" else "CONFIGURED",
            "mode": pipeline.mcp_mode,
        }
        # LLM
        components["llm"] = {
            "status": "READY",
            "provider": pipeline.llm_client.provider,
            "real": pipeline.llm_client.real_call,
        }
        # KR GEARs contract / delivery
        components["kr_gears_contract"] = {
            "status": "PARTIAL",
            "detail": "verdict envelope(KrGearsReport)만 실계약 확인 — 제출 스키마 PROVISIONAL",
        }
        components["delivery_adapter"] = {
            "status": "READY", "mode": settings.kr_gears_delivery_mode,
        }
        # Governance Runtime Binding — 강제 플래그 + 승인 후보 집합 요약
        components["governance"] = {
            "status": "BOUND",
            "enforced_flags": pipeline.governance.flags(),
            "candidate_scope_enforcement": pipeline.governance.candidate_scope_enforcement,
            "candidate_inventory": pipeline.governance.candidate_inventory,
        }

        if (
            components["reference_model"]["status"] != "READY"
            or components["skill"]["status"] != "READY"
        ):
            overall = "NOT_READY"
        elif not pipeline.llm_client.real_call and settings.llm_provider != "mock":
            overall = "DEGRADED"
        else:
            overall = "READY"
        return JSONResponse(
            status_code=200 if overall != "NOT_READY" else 503,
            content={"status": overall, "components": components},
        )

    return app
