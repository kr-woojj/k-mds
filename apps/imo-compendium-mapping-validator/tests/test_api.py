"""FastAPI 계층 테스트.

정책 (REQ-028): IMO 값은 tests/fixtures/에서만 유도한다.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.api.report import canonical_hash
from app.registry.database import make_session_factory
from app.registry.loader import run_import

FIXTURES = Path(__file__).parent / "fixtures"
MAPPING_FIXTURE = "mapping_registry.csv"
API_KEY = "TEST-API-KEY-001"

NUMBER_COLUMN = "IMO Data Number"
NAME_COLUMN = "Data Element"
DATASET_COLUMN = "Dataset"
VERSION_COLUMN = "Version"

REPORT_KEYS = {
    "mapping_job_id",
    "source_dataset_id",
    "compendium_version",
    "validation_status",
    "selected_mappings",
    "errors",
    "error_code",
    "error_detail",
    "timestamp",
    "payload_hash",
}


def read_rows(name: str) -> list[dict[str, str]]:
    with (FIXTURES / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def number_of(rows, name: str, dataset: str | None = None) -> str:
    matches = [
        row[NUMBER_COLUMN]
        for row in rows
        if row[NAME_COLUMN].lower() == name.lower()
        and (dataset is None or row[DATASET_COLUMN] == dataset)
    ]
    assert len(matches) == 1
    return matches[0]


def nonexistent_number(rows) -> str:
    highest = max(int(row[NUMBER_COLUMN][3:]) for row in rows)
    return f"IMO{highest + 1:04d}"


@pytest.fixture(scope="module")
def mapping_rows():
    return read_rows(MAPPING_FIXTURE)


@pytest.fixture(scope="module")
def client(tmp_path_factory, mapping_rows) -> TestClient:
    db_path = tmp_path_factory.mktemp("api") / "registry.sqlite3"
    app = create_app(db_path, api_key=API_KEY)
    session_factory = make_session_factory(
        app.state.service.session_factory.kw["bind"]
    )
    for name in ("registry_v1.csv", "registry_v2.csv", MAPPING_FIXTURE):
        rows = read_rows(name)
        result = run_import(session_factory, FIXTURES / name, rows[0][VERSION_COLUMN])
        assert result.ok, result.issue_codes
    return TestClient(app, headers={"X-API-Key": API_KEY})


def create_job(client, mapping_rows, **overrides) -> dict:
    body = {
        "source_dataset_id": "NOON-REPORT-FEED-01",
        "dataset": {"ship_name": "TEST SHIP", "fuel_oil_consumption": 123.4},
        "input_format": "json",
        "compendium_version": mapping_rows[0][VERSION_COLUMN],
    }
    body.update(overrides)
    response = client.post("/api/v1/mapping/jobs", json=body)
    assert response.status_code == 201, response.text
    return response.json()


# --- SEC-001 / SEC-002 ---


def test_missing_api_key_rejected(client) -> None:
    bare = TestClient(client.app)
    response = bare.get("/api/v1/registry/versions")
    assert response.status_code == 401
    assert response.json()["error_code"] == "SEC-001"


def test_payload_integrity_check(client, mapping_rows) -> None:
    body = {
        "source_dataset_id": "INTEGRITY-CHECK-01",
        "dataset": {"ship_name": "TEST SHIP"},
        "input_format": "json",
    }
    raw = json.dumps(body).encode("utf-8")
    good = hashlib.sha256(raw).hexdigest()

    bad = client.post(
        "/api/v1/mapping/jobs",
        content=raw,
        headers={"Content-Type": "application/json", "X-Payload-SHA256": "0" * 64},
    )
    assert bad.status_code == 400
    assert bad.json()["error_code"] == "SEC-002"

    ok = client.post(
        "/api/v1/mapping/jobs",
        content=raw,
        headers={"Content-Type": "application/json", "X-Payload-SHA256": good},
    )
    assert ok.status_code == 201


# --- Mapping Jobs ---


def test_create_and_get_job(client, mapping_rows) -> None:
    created = create_job(client, mapping_rows)
    assert re.fullmatch(r"MAPJOB-\d{8}", created["mapping_job_id"])
    assert created["summary"]["matched"] == 1
    assert created["summary"]["reviewRequired"] == 1
    assert created["status"] == "REVIEW_PENDING"

    response = client.get(f"/api/v1/mapping/jobs/{created['mapping_job_id']}")
    assert response.status_code == 200
    job = response.json()
    assert job["status"] == "REVIEW_PENDING"
    assert len(job["review_queue"]) == 1


def test_unknown_job_returns_404(client) -> None:
    response = client.get("/api/v1/mapping/jobs/MAPJOB-99999999")
    assert response.status_code == 404


def test_unsupported_version_returns_ver_001(client, mapping_rows) -> None:
    response = client.post(
        "/api/v1/mapping/jobs",
        json={
            "source_dataset_id": "BAD-VERSION-01",
            "dataset": {"ship_name": "TEST SHIP"},
            "input_format": "json",
            "compendium_version": mapping_rows[0][VERSION_COLUMN] + "-GHOST",
        },
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "VER-001"


# --- Report + Review 흐름 ---


def test_report_review_flow(client, mapping_rows) -> None:
    noon = number_of(mapping_rows, "Fuel oil consumption", "TEST-DS-NOON")
    ship = number_of(mapping_rows, "Ship name")
    created = create_job(client, mapping_rows)
    job_id = created["mapping_job_id"]

    # Review 전 Report: REVIEW_REQUIRED + MAP-002
    response = client.get(f"/api/v1/mapping/jobs/{job_id}/report")
    assert response.status_code == 200
    report = response.json()
    assert set(report.keys()) == REPORT_KEYS
    assert report["validation_status"] == "REVIEW_REQUIRED"
    assert report["error_code"] == "MAP-002"
    assert report["compendium_version"] == mapping_rows[0][VERSION_COLUMN]
    assert canonical_hash(report) == report["payload_hash"]
    assert report["timestamp"]
    selected_numbers = [
        item["imo_data_number"] for item in report["selected_mappings"]
    ]
    assert ship in selected_numbers

    # 후보 목록에 없는 코드 승인 -> MAP-003
    job = client.get(f"/api/v1/mapping/jobs/{job_id}").json()
    review_field = job["review_queue"][0]["fieldId"]
    ghost = nonexistent_number(mapping_rows)
    bad = client.post(
        f"/api/v1/mapping/jobs/{job_id}/review",
        json={
            "decisions": [
                {"field_id": review_field, "action": "accept", "imo_data_number": ghost}
            ]
        },
    )
    assert bad.status_code == 422
    assert bad.json()["error_code"] == "MAP-003"

    # 정상 승인 -> COMPLETED, Report PASS
    accepted = client.post(
        f"/api/v1/mapping/jobs/{job_id}/review",
        json={
            "decisions": [
                {"field_id": review_field, "action": "accept", "imo_data_number": noon}
            ]
        },
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "COMPLETED"
    assert accepted.json()["remaining_review_count"] == 0

    report = client.get(f"/api/v1/mapping/jobs/{job_id}/report").json()
    assert report["validation_status"] == "PASS"
    assert report["error_code"] is None and report["errors"] == []
    origins = {
        item["imo_data_number"]: item["origin"]
        for item in report["selected_mappings"]
    }
    assert origins[ship] == "auto"
    assert origins[noon] == "review_accepted"
    assert canonical_hash(report) == report["payload_hash"]


def test_missing_context_reported_as_val_005(client, mapping_rows) -> None:
    created = create_job(
        client,
        mapping_rows,
        source_dataset_id="MISSING-CONTEXT-01",
        dataset=[{"name": "value"}],
        input_format="csv-columns",
    )
    report = client.get(
        f"/api/v1/mapping/jobs/{created['mapping_job_id']}/report"
    ).json()
    assert report["validation_status"] == "FAIL"
    assert any(entry["error_code"] == "VAL-005" for entry in report["errors"])


# --- Validation ---


def test_validation_namespace_codes(client, mapping_rows) -> None:
    ship = number_of(mapping_rows, "Ship name")
    distance = number_of(mapping_rows, "Distance travelled")
    ghost = nonexistent_number(mapping_rows)
    response = client.post(
        "/api/v1/validation",
        json={
            "mappings": [
                {
                    "field": {"name": "ship_name", "declared_type": "string"},
                    "imo_data_number": ship,
                },
                {
                    "field": {
                        "name": "distance travelled",
                        "declared_type": "string",
                        "sample_values": ["around ten miles"],
                    },
                    "imo_data_number": distance,
                },
                {"field": {"name": "anything"}, "imo_data_number": ghost},
            ]
        },
    )
    assert response.status_code == 200
    outcome = response.json()
    assert outcome["overallStatus"] == "FAIL"
    by_number = {entry["imoDataNumber"]: entry for entry in outcome["results"]}
    assert by_number[ship]["status"] == "PASS"
    assert any(
        issue["error_code"] == "VAL-001" for issue in by_number[distance]["issues"]
    )
    assert any(
        issue["error_code"] == "MAP-003" for issue in by_number[ghost]["issues"]
    )


# --- Registry ---


def test_registry_versions(client, mapping_rows) -> None:
    response = client.get("/api/v1/registry/versions")
    assert response.status_code == 200
    versions = {entry["version"] for entry in response.json()["versions"]}
    assert mapping_rows[0][VERSION_COLUMN] in versions
    assert len(versions) == 3


def test_registry_element_lookup(client, mapping_rows) -> None:
    ship = number_of(mapping_rows, "Ship name")
    version = mapping_rows[0][VERSION_COLUMN]
    response = client.get(
        f"/api/v1/registry/elements/{ship}", params={"version": version}
    )
    assert response.status_code == 200
    element = response.json()
    assert element["imo_data_number"] == ship
    assert element["compendium_version"] == version
    assert element["occurrences"]

    ghost = nonexistent_number(mapping_rows)
    missing = client.get(
        f"/api/v1/registry/elements/{ghost}", params={"version": version}
    )
    assert missing.status_code == 404
    assert missing.json()["error_code"] == "MAP-003"


# --- OpenAPI ---


def test_openapi_document_and_examples(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    document = response.json()
    assert document["openapi"].startswith("3.1")
    expected_paths = {
        "/api/v1/mapping/jobs",
        "/api/v1/mapping/jobs/{job_id}",
        "/api/v1/mapping/jobs/{job_id}/report",
        "/api/v1/mapping/jobs/{job_id}/review",
        "/api/v1/validation",
        "/api/v1/registry/versions",
        "/api/v1/registry/elements/{imo_data_number}",
    }
    assert expected_paths <= set(document["paths"])

    schemas = document["components"]["schemas"]
    assert "examples" in schemas["CreateMappingJobRequest"]
    assert "examples" in schemas["KrGearsReport"]
    # REQ-028: 문서 예시에 실제 IMO 값을 넣지 않는다 (자리표시 IMOnnnn 사용).
    assert not re.search(r"IMO\d{4}", json.dumps(schemas, ensure_ascii=False))
