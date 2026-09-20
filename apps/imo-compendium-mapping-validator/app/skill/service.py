"""Tool 작업 구현 (5종).

버전 규칙:
- compendium_version 미지정 -> 서버 active version(가장 최근 적재본)을 사용하고
  응답 provenance에 실제 사용 버전을 명시한다.
- 존재하지 않는 버전 -> fallback 없이 VERSION_NOT_LOADED 오류.

노출 규칙:
- Agent에게 Registry 전체 원문을 넘기지 않는다. top-k 후보와 단일 record 근거
  요약(정의 발췌 최대 길이 제한)만 반환한다.
- 모든 결과는 compendiumVersion + registry 근거 + audit_id를 포함한다.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.mapping import MappingEngine
from app.mapping.decision import (
    STATUS_MATCHED,
    STATUS_MISSING_CONTEXT,
    STATUS_NO_MATCH,
    STATUS_REVIEW_REQUIRED,
    DecisionThresholds,
    FieldDecision,
)
from app.mapping.normalizer import normalize_field
from app.mapping.ranker import ScoredCandidate, rank_candidates
from app.mapping.retriever import RetrievedCandidate, retrieve_candidates
from app.mapping.validator import validate_candidate, validate_candidates
from app.registry.diff import DiffError, diff_versions
from app.registry.models import AuditEvent, CompendiumVersion
from app.registry.validator import IMO_DATA_NUMBER_PATTERN
from app.skill.extractor import ExtractionError, extract_fields
from app.skill.schemas import (
    ExplainMappingRequest,
    FieldSpec,
    ListCandidatesRequest,
    MapDatasetRequest,
    ValidateMappingRequest,
)

_DEFINITION_EXCERPT_LIMIT = 280


class SkillError(Exception):
    """도구 실행 오류 — 오류 코드와 함께 Agent에게 반환된다 (fallback 없음)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _input_hash(payload: Any) -> str:
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, default=str
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _definition_excerpt(definition: str | None) -> str | None:
    if definition is None:
        return None
    if len(definition) <= _DEFINITION_EXCERPT_LIMIT:
        return definition
    return definition[: _DEFINITION_EXCERPT_LIMIT - 1] + "…"


def _candidate_view(candidate_dict: dict[str, Any], element) -> dict[str, Any]:
    """Agent에게 전달되는 후보 뷰 — 근거 요약만 포함한다."""
    view = dict(candidate_dict)
    view["registryEvidence"] = {
        "name": element.name,
        "definitionExcerpt": _definition_excerpt(element.definition),
        "format": element.format_spec,
        "status": element.status,
        "datasets": sorted(
            {occ.dataset_key or "-" for occ in element.occurrences}
        ),
    }
    return view


@dataclass
class MappingSkillService:
    session_factory: sessionmaker[Session]
    #: 서버 설정으로 고정할 수 있다. None이면 가장 최근 적재 버전을 사용한다.
    active_version: str | None = None
    _engines: dict[str, MappingEngine] = field(default_factory=dict)

    # --- 버전 해석 ---

    def resolve_version(self, requested: str | None) -> tuple[str, bool]:
        """(사용 버전, active 사용 여부). 미존재 버전은 오류 — fallback 금지."""
        with self.session_factory() as session:
            if requested is not None:
                row = session.execute(
                    select(CompendiumVersion).where(
                        CompendiumVersion.version == requested,
                        CompendiumVersion.loaded.is_(True),
                    )
                ).scalar_one_or_none()
                if row is None:
                    raise SkillError(
                        "VERSION_NOT_LOADED",
                        "요청한 Compendium version이 적재되어 있지 않다 (fallback 없음)",
                    )
                return requested, False
            if self.active_version is not None:
                candidate = self.active_version
            else:
                row = session.execute(
                    text(
                        "SELECT version FROM compendium_version "
                        "WHERE loaded = 1 ORDER BY rowid DESC LIMIT 1"
                    )
                ).first()
                if row is None:
                    raise SkillError(
                        "NO_ACTIVE_VERSION", "적재된 Compendium version이 없다"
                    )
                candidate = str(row[0])
        return candidate, True

    def _engine(self, version: str) -> MappingEngine:
        engine = self._engines.get(version)
        if engine is None:
            engine = MappingEngine(
                session_factory=self.session_factory, version=version
            )
            self._engines[version] = engine
        return engine

    def _source_hash(self, version: str) -> str:
        with self.session_factory() as session:
            row = session.get(CompendiumVersion, version)
        return row.source_hash if row is not None else ""

    def _audit(self, event_type: str, version: str, input_hash: str, detail: dict) -> str:
        with self.session_factory() as session:
            event = AuditEvent(
                event_type=event_type,
                version=version,
                source_hash=input_hash,
                detail=json.dumps(detail, ensure_ascii=False, sort_keys=True),
            )
            session.add(event)
            session.commit()
            sequence = event.seq
        return f"{event_type.replace('_', '-')}-{sequence:08d}"

    # --- 공통 파이프라인 ---

    def _decide_field(
        self,
        engine: MappingEngine,
        field_id: str,
        kwargs: dict[str, Any],
        thresholds: DecisionThresholds,
    ) -> FieldDecision:
        normalized = normalize_field(
            field_id,
            kwargs["name"],
            description=kwargs.get("description"),
            declared_type=kwargs.get("declared_type"),
            declared_unit=kwargs.get("declared_unit"),
            declared_format=kwargs.get("declared_format"),
            path=kwargs.get("path"),
            sample_values=kwargs.get("sample_values"),
        )
        retrieved = retrieve_candidates(engine.index, normalized, engine.alias_dictionary)
        scored = rank_candidates(normalized, retrieved)
        validate_candidates(normalized, scored)
        from app.mapping.decision import decide

        return decide(normalized, scored, engine.version, thresholds=thresholds)

    def _decision_views(
        self, engine: MappingEngine, decision: FieldDecision, top_k: int
    ) -> list[dict[str, Any]]:
        views: list[dict[str, Any]] = []
        for candidate_dict in decision.candidates[:top_k]:
            element = engine.index.elements[str(candidate_dict["imoDataNumber"])]
            views.append(_candidate_view(candidate_dict, element))
        return views

    # --- 1) map_dataset ---

    def map_dataset(self, request: MapDatasetRequest) -> dict[str, Any]:
        version, used_active = self.resolve_version(request.compendium_version)
        try:
            field_kwargs = extract_fields(
                request.dataset, request.input_format, request.service_context
            )
        except ExtractionError as error:
            raise SkillError(error.code, str(error)) from error

        thresholds = DecisionThresholds(
            matched=(
                request.auto_accept_threshold
                if request.auto_accept_threshold is not None
                else DecisionThresholds().matched
            )
        )
        engine = self._engine(version)

        mappings: list[dict[str, Any]] = []
        review_queue: list[dict[str, Any]] = []
        unmapped: list[dict[str, Any]] = []
        validation_errors: list[dict[str, Any]] = []
        counts = {
            STATUS_MATCHED: 0,
            STATUS_REVIEW_REQUIRED: 0,
            STATUS_NO_MATCH: 0,
            STATUS_MISSING_CONTEXT: 0,
        }

        for index, kwargs in enumerate(field_kwargs, start=1):
            field_id = f"f{index:04d}"
            decision = self._decide_field(engine, field_id, kwargs, thresholds)
            counts[decision.status] += 1

            for candidate_dict in decision.candidates:
                for issue in candidate_dict["issues"]:
                    if issue["severity"] == "ERROR":
                        validation_errors.append(
                            {
                                "fieldId": field_id,
                                "fieldName": kwargs["name"],
                                "imoDataNumber": candidate_dict["imoDataNumber"],
                                "code": issue["code"],
                            }
                        )

            base = {
                "fieldId": field_id,
                "fieldName": kwargs["name"],
                "path": kwargs.get("path"),
            }
            if decision.status == STATUS_MATCHED:
                top = decision.candidates[0]
                element = engine.index.elements[str(top["imoDataNumber"])]
                mappings.append(
                    {
                        **base,
                        "imoDataNumber": top["imoDataNumber"],
                        "candidate": _candidate_view(top, element),
                        "reasons": decision.reasons,
                    }
                )
            elif decision.status == STATUS_REVIEW_REQUIRED:
                review_queue.append(
                    {
                        **base,
                        "candidates": self._decision_views(
                            engine, decision, request.top_k
                        ),
                        "comparisons": decision.comparisons,
                        "reasons": decision.reasons,
                    }
                )
            else:
                unmapped.append(
                    {
                        **base,
                        "status": decision.status,
                        "missing_context": decision.missing_context,
                        "reasons": decision.reasons,
                        "rejectedCandidates": self._decision_views(
                            engine, decision, request.top_k
                        ),
                    }
                )

        request_hash = _input_hash(request.model_dump(mode="json"))
        audit_id = self._audit(
            "MAP_DATASET",
            version,
            request_hash,
            {
                "fieldCount": len(field_kwargs),
                "counts": counts,
                "usedActiveVersion": used_active,
            },
        )
        matched_targets = [str(item["imoDataNumber"]) for item in mappings]
        duplicate_targets = sorted(
            {
                number
                for number in matched_targets
                if matched_targets.count(number) > 1
            }
        )
        return {
            "summary": {
                "fieldCount": len(field_kwargs),
                "matched": counts[STATUS_MATCHED],
                "reviewRequired": counts[STATUS_REVIEW_REQUIRED],
                "noMatch": counts[STATUS_NO_MATCH],
                "missingContext": counts[STATUS_MISSING_CONTEXT],
                "autoAcceptThreshold": thresholds.matched,
                "topGapRuleApplied": True,
                "duplicateTargetCount": len(duplicate_targets),
                "duplicateTargets": duplicate_targets,
            },
            "mappings": mappings,
            "unmapped_fields": unmapped,
            "review_queue": review_queue,
            "validation_errors": validation_errors,
            "provenance": {
                "compendiumVersion": version,
                "requestedVersion": request.compendium_version,
                "usedActiveVersion": used_active,
                "registrySourceHash": self._source_hash(version),
                "inputHash": request_hash,
                "deterministicPipeline": True,
                "llmUsed": False,
            },
            "audit_id": audit_id,
        }

    # --- 2) validate_mapping ---

    def validate_mapping(self, request: ValidateMappingRequest) -> dict[str, Any]:
        version, used_active = self.resolve_version(request.compendium_version)
        engine = self._engine(version)
        results: list[dict[str, Any]] = []
        overall_pass = True

        for index, item in enumerate(request.mappings, start=1):
            number = item.imo_data_number.strip().upper()
            entry: dict[str, Any] = {
                "fieldName": item.field.name,
                "imoDataNumber": number,
            }
            element = engine.index.elements.get(number)
            if not IMO_DATA_NUMBER_PATTERN.match(number) or element is None:
                entry["status"] = "FAIL"
                entry["issues"] = [
                    {
                        "code": "MAPPING_TARGET_NOT_IN_REGISTRY",
                        "severity": "ERROR",
                        "message": "대상 코드가 해당 버전 Registry에 존재하지 않는다",
                    }
                ]
                overall_pass = False
                results.append(entry)
                continue

            normalized = normalize_field(
                f"v{index:04d}",
                item.field.name,
                description=item.field.description,
                declared_type=item.field.declared_type,
                declared_unit=item.field.declared_unit,
                declared_format=item.field.declared_format,
                path=item.field.path,
                sample_values=list(item.field.sample_values),
            )
            scored = rank_candidates(
                normalized, [RetrievedCandidate(element=element, channels={"direct"})]
            )
            candidate = scored[0]
            validate_candidate(normalized, candidate)
            has_error = any(issue["severity"] == "ERROR" for issue in candidate.issues)
            entry["status"] = (
                "FAIL" if has_error else ("WARNING" if candidate.issues else "PASS")
            )
            entry["issues"] = candidate.issues
            entry["components"] = candidate.components
            entry["final_score"] = candidate.final_score
            if has_error:
                overall_pass = False
            results.append(entry)

        request_hash = _input_hash(request.model_dump(mode="json"))
        audit_id = self._audit(
            "VALIDATE_MAPPING",
            version,
            request_hash,
            {"mappingCount": len(results), "overallPass": overall_pass},
        )
        return {
            "compendiumVersion": version,
            "usedActiveVersion": used_active,
            "overallStatus": "PASS" if overall_pass else "FAIL",
            "results": results,
            "audit_id": audit_id,
        }

    # --- 3) explain_mapping ---

    def explain_mapping(self, request: ExplainMappingRequest) -> dict[str, Any]:
        version, used_active = self.resolve_version(request.compendium_version)
        engine = self._engine(version)
        number = request.imo_data_number.strip().upper()
        element = engine.index.elements.get(number)
        if element is None:
            raise SkillError(
                "MAPPING_TARGET_NOT_IN_REGISTRY",
                "대상 코드가 해당 버전 Registry에 존재하지 않는다",
            )

        decision = self._decide_field(
            engine,
            "explain",
            _fieldspec_kwargs(request.field),
            DecisionThresholds(),
        )
        rank_position = None
        target_view: dict[str, Any] | None = None
        for position, candidate_dict in enumerate(decision.candidates, start=1):
            if candidate_dict["imoDataNumber"] == number:
                rank_position = position
                target_view = _candidate_view(candidate_dict, element)
                break
        if target_view is None:
            # 검색 후보에 없으면 직접 점수화해 근거를 제공한다 (생성이 아니라 조회).
            normalized = normalize_field("explain", request.field.name)
            scored = rank_candidates(
                normalized, [RetrievedCandidate(element=element, channels={"direct"})]
            )
            validate_candidate(normalized, scored[0])
            target_view = _candidate_view(scored[0].to_dict(), element)

        request_hash = _input_hash(request.model_dump(mode="json"))
        audit_id = self._audit(
            "EXPLAIN_MAPPING", version, request_hash, {"target": number}
        )
        return {
            "compendiumVersion": version,
            "usedActiveVersion": used_active,
            "fieldName": request.field.name,
            "target": target_view,
            "rankAmongCandidates": rank_position,
            "decisionStatus": decision.status,
            "comparisons": decision.comparisons,
            "reasons": decision.reasons,
            "audit_id": audit_id,
        }

    # --- 4) list_candidates ---

    def list_candidates(self, request: ListCandidatesRequest) -> dict[str, Any]:
        version, used_active = self.resolve_version(request.compendium_version)
        engine = self._engine(version)
        decision = self._decide_field(
            engine, "list", _fieldspec_kwargs(request.field), DecisionThresholds()
        )
        request_hash = _input_hash(request.model_dump(mode="json"))
        audit_id = self._audit(
            "LIST_CANDIDATES",
            version,
            request_hash,
            {"candidateCount": min(len(decision.candidates), request.top_k)},
        )
        return {
            "compendiumVersion": version,
            "usedActiveVersion": used_active,
            "fieldName": request.field.name,
            "status": decision.status,
            "missing_context": decision.missing_context,
            "candidates": self._decision_views(engine, decision, request.top_k),
            "comparisons": decision.comparisons,
            "reasons": decision.reasons,
            "audit_id": audit_id,
        }

    # --- 5) compare_compendium_versions ---

    def compare_compendium_versions(self, request) -> dict[str, Any]:
        try:
            diff = diff_versions(
                self.session_factory, request.from_version, request.to_version
            )
        except DiffError as error:
            raise SkillError("VERSION_NOT_LOADED", str(error)) from error
        request_hash = _input_hash(request.model_dump(mode="json"))
        audit_id = self._audit(
            "COMPARE_VERSIONS",
            request.to_version,
            request_hash,
            {
                "added": len(diff.added),
                "modified": len(diff.modified),
                "deprecated": len(diff.deprecated),
            },
        )
        payload = diff.to_dict()
        payload["audit_id"] = audit_id
        return payload


def _fieldspec_kwargs(spec: FieldSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "description": spec.description,
        "declared_type": spec.declared_type,
        "declared_unit": spec.declared_unit,
        "declared_format": spec.declared_format,
        "path": spec.path,
        "sample_values": list(spec.sample_values),
    }
