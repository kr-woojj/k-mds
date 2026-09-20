"""TS-3: FastAPI contract — IDS webhook + Mock LLM + Real Skill + Mock delivery."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ghg_agent.api.app import create_app
from tests.conftest import load_fixture, load_fixture_json, requires_registry, requires_skill


@pytest.fixture()
def client(settings):
    app = create_app(settings)
    return TestClient(app)


@requires_registry
@requires_skill
class TestApi:
    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_ready(self, client):
        response = client.get("/ready")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "READY"
        assert body["components"]["reference_model"]["elements"] == 1205
        assert body["components"]["skill"]["status"] == "READY"
        assert body["components"]["kr_gears_contract"]["status"] == "PARTIAL"
        assert body["components"]["llm"]["provider"] == "mock"

    def test_ids_events_full_run_and_get_run(self, client):
        raw = load_fixture("noon_report_valid.json")
        response = client.post(
            "/api/v1/ids/events", content=raw,
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["correlation_id"] == "SYN-NOON-0001"
        assert body["final_status"] == "REVIEW_REQUIRED"  # PROVISIONAL 계약
        assert body["error"] == "KR_GEARS_CONTRACT_PROVISIONAL"

        run = client.get(f"/api/v1/runs/{body['correlation_id']}")
        assert run.status_code == 200
        run_body = run.json()
        assert run_body["final_status"] == "REVIEW_REQUIRED"
        assert "manifest.json" in run_body["evidence_files"]
        assert "mapping-result.json" in run_body["evidence_files"]
        assert run_body["manifest"]["file_hashes"]

    def test_ids_events_duplicate_409(self, client):
        raw = load_fixture("event_departure.json")
        first = client.post(
            "/api/v1/ids/events", content=raw,
            headers={"content-type": "application/json"},
        )
        assert first.status_code == 200
        second = client.post(
            "/api/v1/ids/events", content=raw,
            headers={"content-type": "application/json"},
        )
        assert second.status_code == 409
        assert second.json()["detail"]["error"] == "DUPLICATE_CORRELATION_ID"

    def test_ids_events_non_json_422(self, client):
        response = client.post(
            "/api/v1/ids/events", content=b"\x00 not json",
            headers={"content-type": "application/octet-stream"},
        )
        assert response.status_code == 422
        body = response.json()
        assert "BODY_NOT_JSON" in body["validation_errors"]
        assert body["raw_sha256"]
        assert body["final_status"] == "REVIEW_REQUIRED"

    def test_map_validate_transform_chain(self, client):
        payload = load_fixture_json("noon_report_valid.json")
        mapped = client.post(
            "/api/v1/map",
            json={"profile": "NOON_REPORT", "payload": payload,
                  "correlation_id": "api-chain-001"},
        )
        assert mapped.status_code == 200
        mapping_result = mapped.json()["mapping_result"]
        fields = mapped.json()["fields"]
        assert mapping_result["metrics"]["unmapped"] == 0

        validated = client.post(
            "/api/v1/validate",
            json={"mapping_result": mapping_result, "fields": fields},
        )
        assert validated.status_code == 200
        validation = validated.json()
        assert validation["overall"] in ("PASS", "WARNING")

        transformed = client.post(
            "/api/v1/transform/kr-gears",
            json={"mapping_result": mapping_result, "fields": fields,
                  "validation_result": validation},
        )
        assert transformed.status_code == 200
        body = transformed.json()
        assert body["contract_status"] == "PROVISIONAL"
        assert body["verdict_report"]["validation_status"] in ("PASS", "REVIEW_REQUIRED", "FAIL")

    def test_transform_rejects_failed_validation(self, client):
        payload = load_fixture_json("noon_report_valid.json")
        mapped = client.post(
            "/api/v1/map",
            json={"profile": "NOON_REPORT", "payload": payload,
                  "correlation_id": "api-chain-002"},
        ).json()
        validation = client.post(
            "/api/v1/validate",
            json={"mapping_result": mapped["mapping_result"], "fields": mapped["fields"]},
        ).json()
        validation["overall"] = "FAIL"
        response = client.post(
            "/api/v1/transform/kr-gears",
            json={"mapping_result": mapped["mapping_result"], "fields": mapped["fields"],
                  "validation_result": validation},
        )
        assert response.status_code == 409

    def test_run_not_found(self, client):
        assert client.get("/api/v1/runs/no-such-run").status_code == 404
