"""Step 6R 회귀 — Resource Limit(F-STEP6-1) 및 Evidence Atomicity(F-STEP6-2).

한계값(config 기본): node 3000 / field 2000 / array 1000 / scalar 8192.
정상 fixture 는 node≈31, field≈15 로 여유. 경계 ±1 을 격리 검증한다.
"""

from __future__ import annotations

import json

import pytest

from ghg_agent.adapters.ids_adapter import ResourceLimits, ingest, measure_payload
from ghg_agent.agents.orchestrator import build_pipeline
from ghg_agent.evidence import EvidenceCommitError, verify_evidence
from tests.conftest import load_fixture, requires_registry, requires_skill

LIM = ResourceLimits()  # 기본 한계값


def _run(pipeline, raw: bytes):
    return pipeline.run(raw, "application/json")


def _errors(raw: bytes):
    result, _ = ingest(raw, "application/json", limits=LIM)
    return result.validation_errors


# --- A. Resource limit (ingress 단독, pipeline 무관) ---

class TestResourceLimits:
    def test_node_limit_minus_1_accepted(self):
        n = (LIM.max_node_count - 1) // 2   # {"kN":{"a":1}} → node=2N+1
        body = {"correlation_id": "c", **{f"k{i}": {"a": 1} for i in range(n)}}
        node, *_ = measure_payload(body)
        assert node <= LIM.max_node_count
        assert not _errors(json.dumps(body).encode())

    def test_node_limit_plus_1_rejected(self):
        n = LIM.max_node_count // 2 + 1     # node=2N+1 > limit, field=N < 2000
        body = {"correlation_id": "c", **{f"k{i}": {"a": 1} for i in range(n)}}
        node, leaves, *_ = measure_payload(body)
        assert node > LIM.max_node_count and leaves <= LIM.max_field_count
        assert "PAYLOAD_TOO_COMPLEX" in _errors(json.dumps(body).encode())

    def test_field_limit_accepted_and_plus_1_rejected(self):
        ok = {"correlation_id": "c", **{f"k{i}": i for i in range(LIM.max_field_count - 1)}}
        assert not _errors(json.dumps(ok).encode())
        over = {"correlation_id": "c", **{f"k{i}": i for i in range(LIM.max_field_count + 1)}}
        assert "PAYLOAD_TOO_COMPLEX" in _errors(json.dumps(over).encode())

    def test_array_limit_plus_1_rejected(self):
        over = {"correlation_id": "c", "arr": list(range(LIM.max_array_length + 1))}
        assert "ARRAY_TOO_LARGE" in _errors(json.dumps(over).encode())
        ok = {"correlation_id": "c", "arr": list(range(LIM.max_array_length))}
        assert "ARRAY_TOO_LARGE" not in _errors(json.dumps(ok).encode())

    def test_scalar_limit_plus_1_rejected(self):
        over = {"correlation_id": "c", "blob": "A" * (LIM.max_scalar_text_length + 1)}
        assert "FIELD_VALUE_TOO_LARGE" in _errors(json.dumps(over).encode())

    def test_non_finite_rejected(self):
        raw = b'{"correlation_id":"c","x":NaN}'
        assert "NON_FINITE_NUMBER_NOT_ALLOWED" in _errors(raw)

    def test_non_dict_body_rejected(self):
        for raw in (b'[1,2,3]', b'"scalar"', b'null'):
            assert "UNSUPPORTED_BODY_TYPE" in _errors(raw)


@requires_registry
@requires_skill
class TestWidePayloadPipeline:
    def test_rejected_wide_payload_no_external_calls(self, settings):
        pipe = build_pipeline(settings)
        big = {"correlation_id": "STEP6R-WIDE-0001", "report_type": "noon",
               "arr": list(range(20000))}
        state = _run(pipe, json.dumps(big).encode())
        assert state.status.value == "REVIEW_REQUIRED"
        assert "ARRAY_TOO_LARGE" in (state.error or "") or "PAYLOAD_TOO_COMPLEX" in (state.error or "")
        d = settings.audit_log_dir / "STEP6R-WIDE-0001"
        assert not (d / "mapping-result.json").exists()  # mapping 미실행
        skill = json.loads((d / "skill-calls.json").read_text(encoding="utf-8"))
        llm = json.loads((d / "llm-calls.json").read_text(encoding="utf-8"))
        assert skill == [] and llm == []

    def test_20000_array_returns_fast_without_hang(self, settings):
        import time
        pipe = build_pipeline(settings)
        big = {"correlation_id": "STEP6R-WIDE-FAST-0001", "report_type": "noon",
               "arr": list(range(20000))}
        t0 = time.perf_counter()
        state = _run(pipe, json.dumps(big).encode())
        elapsed = time.perf_counter() - t0
        assert state.status.value == "REVIEW_REQUIRED"
        assert elapsed < 5.0  # hang 없음 (이전엔 필드당 skill 호출로 수백초)


# --- B. Evidence atomicity ---

@requires_registry
@requires_skill
class TestEvidenceAtomicity:
    def _noon(self, cid):
        d = json.loads(load_fixture("noon_report_valid.json"))
        d["correlation_id"] = cid
        return json.dumps(d).encode()

    def test_finalize_failure_no_partial_and_sanitized_and_recovery(self, settings, monkeypatch):
        import os as _os

        import ghg_agent.evidence as ev
        orig = _os.replace

        def flaky_replace(src, dst):
            # 최종 published rename(디렉터리)만 실패시킨다.
            if str(dst).endswith("STEP6R-EVFAIL-0001"):
                raise OSError("injected commit failure")
            return orig(src, dst)

        monkeypatch.setattr(ev.os, "replace", flaky_replace)
        pipe = build_pipeline(settings)
        with pytest.raises(EvidenceCommitError) as ei:
            _run(pipe, self._noon("STEP6R-EVFAIL-0001"))
        assert ei.value.code == "EVIDENCE_COMMIT_FAILED" and ei.value.retryable is True
        # 부분 최종 패키지 0
        assert not (settings.audit_log_dir / "STEP6R-EVFAIL-0001").exists()
        # 복구 레코드 생성 (sanitized)
        recs = list((settings.audit_log_dir / ".recovery").glob("STEP6R-EVFAIL-0001-*.json"))
        assert recs
        rec = json.loads(recs[0].read_text(encoding="utf-8"))
        assert rec["code"] == "EVIDENCE_COMMIT_FAILED" and rec["final_package_created"] is False
        assert "traceback" not in rec and "message" not in rec  # stack/message 미노출

    def test_request_after_evidence_failure_succeeds(self, settings, monkeypatch):
        import os as _os

        import ghg_agent.evidence as ev
        orig = _os.replace
        state = {"fail": True}

        def flaky_replace(src, dst):
            if state["fail"] and str(dst).endswith("STEP6R-RECOVER-0001"):
                raise OSError("injected once")
            return orig(src, dst)

        monkeypatch.setattr(ev.os, "replace", flaky_replace)
        pipe = build_pipeline(settings)
        with pytest.raises(EvidenceCommitError):
            _run(pipe, self._noon("STEP6R-RECOVER-0001"))
        # 복구 후 동일 cid 재요청 성공 (final 미생성이었으므로 중복 아님)
        state["fail"] = False
        ok = _run(build_pipeline(settings), self._noon("STEP6R-RECOVER-0001"))
        assert ok.status.value == "REVIEW_REQUIRED"
        assert verify_evidence(settings.audit_log_dir / "STEP6R-RECOVER-0001")["ok"]

    def test_existing_evidence_unchanged_on_new_failure(self, settings, monkeypatch):
        # 정상 run 1건 생성
        pipe = build_pipeline(settings)
        good = _run(pipe, self._noon("STEP6R-KEEP-0001"))
        assert good.status.value == "REVIEW_REQUIRED"
        man_before = (settings.audit_log_dir / "STEP6R-KEEP-0001" / "manifest.json").read_bytes()
        # 다른 cid 의 evidence 실패가 기존 것을 건드리지 않음
        import os as _os

        import ghg_agent.evidence as ev
        orig = _os.replace

        def flaky(src, dst):
            if str(dst).endswith("STEP6R-OTHER-0001"):
                raise OSError("injected")
            return orig(src, dst)

        monkeypatch.setattr(ev.os, "replace", flaky)
        with pytest.raises(EvidenceCommitError):
            _run(build_pipeline(settings), self._noon("STEP6R-OTHER-0001"))
        man_after = (settings.audit_log_dir / "STEP6R-KEEP-0001" / "manifest.json").read_bytes()
        assert man_before == man_after


# --- C. 정상 pipeline 회귀 ---

@requires_registry
@requires_skill
class TestNormalRegression:
    def test_noon_regression(self, settings):
        state = build_pipeline(settings).run(load_fixture("noon_report_valid.json"), "application/json")
        assert state.status.value == "REVIEW_REQUIRED"
        assert verify_evidence(settings.audit_log_dir / state.correlation_id)["ok"]

    def test_event_regression(self, settings):
        state = build_pipeline(settings).run(load_fixture("event_departure.json"), "application/json")
        assert state.status.value == "REVIEW_REQUIRED"
        assert verify_evidence(settings.audit_log_dir / state.correlation_id)["ok"]
