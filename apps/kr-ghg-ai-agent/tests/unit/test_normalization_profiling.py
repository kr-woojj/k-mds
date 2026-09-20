"""TS-1: field normalization / profile classification."""

from __future__ import annotations

from ghg_agent.domain.models import SourceProfile
from ghg_agent.domain.normalization import normalize_payload
from ghg_agent.domain.profiling import profile_payload
from ghg_agent.reference.lookup import normalize_name
from tests.conftest import load_fixture_json


def test_normalize_name_basic():
    assert normalize_name("Speed_Through_Water") == "speed through water"
    assert normalize_name("Fuel consumed, by Main Engine") == "fuel consumed by main engine"
    assert normalize_name("  FOC  ") == "foc"


def test_profile_noon_explicit():
    payload = load_fixture_json("noon_report_valid.json")
    result = profile_payload(payload)
    assert result.selected_profile == SourceProfile.NOON_REPORT
    assert result.confidence == 1.0
    assert result.classification_method == "explicit_report_type"


def test_profile_event_explicit():
    result = profile_payload(load_fixture_json("event_departure.json"))
    assert result.selected_profile == SourceProfile.EVENT_REPORT


def test_profile_unknown_when_no_marker():
    result = profile_payload({"random_key": 1, "other": "x"})
    assert result.selected_profile == SourceProfile.UNKNOWN
    assert result.confidence < 0.6


def test_profile_structural_noon_marker():
    result = profile_payload(
        {"report_datetime": "2026-08-01T12:00:00Z", "distance_through_water": 100,
         "speed_through_water": 12}
    )
    assert result.selected_profile in (SourceProfile.NOON_REPORT, SourceProfile.UNKNOWN)
    assert result.classification_method == "structural_marker"


def test_normalize_payload_units_and_context():
    payload = load_fixture_json("noon_report_valid.json")
    fields = normalize_payload(payload, SourceProfile.NOON_REPORT)
    by_name = {f.source_name: f for f in fields}

    stw = by_name["speed_through_water"]
    assert stw.value == 12.0
    assert stw.unit == "knot"
    assert stw.data_type == "numeric"
    assert stw.voyage_context == "SYN-VOY-002"
    assert stw.report_context == "NOON_REPORT"
    assert stw.timestamp == "2026-08-02T12:00:00+00:00"

    # report_type 은 transport 성 marker — canonical field 에서 제외
    assert "report_type" not in by_name


def test_normalize_skips_comment_keys():
    fields = normalize_payload({"_comment": "note", "wind_speed": 10}, SourceProfile.NOON_REPORT)
    assert [f.source_name for f in fields] == ["wind_speed"]
