"""TS-1: state transition / reference lookup / confidence 정책."""

from __future__ import annotations

import pytest

from ghg_agent.domain.models import InvalidTransition, RunStatus, assert_transition
from tests.conftest import nonexistent_imo_number, requires_registry


def test_allowed_transition():
    assert_transition(RunStatus.RECEIVED, RunStatus.PROFILED)
    assert_transition(RunStatus.MAPPED, RunStatus.VALIDATED)


def test_invalid_transition_rejected():
    with pytest.raises(InvalidTransition):
        assert_transition(RunStatus.RECEIVED, RunStatus.DELIVERED)
    with pytest.raises(InvalidTransition):
        assert_transition(RunStatus.DELIVERED, RunStatus.RECEIVED)
    with pytest.raises(InvalidTransition):
        assert_transition(RunStatus.FAILED, RunStatus.PROFILED)


@requires_registry
class TestReferenceLookup:
    def test_exact_element(self, reference):
        element = reference.element("IMO0616")
        assert element is not None
        assert element.name == "Speed through water"
        assert "Noon Data Report" in element.datasets

    def test_nonexistent_number(self, reference):
        fake = nonexistent_imo_number(reference)
        assert not reference.exists(fake)

    def test_normalized_name_lookup(self, reference):
        hits = reference.by_normalized_name("speed_through_water")
        assert [e.imo_data_number for e in hits] == ["IMO0616"]

    def test_alias_lookup(self, reference):
        hits = reference.by_alias("foc")
        assert [e.imo_data_number for e in hits] == ["IMO0669"]

    def test_alias_to_missing_target_is_ignored(self, reference, tmp_path):
        from ghg_agent.reference.lookup import ReferenceLookup

        alias_file = tmp_path / "aliases.json"
        alias_file.write_text(
            '{"aliases": {"ghost": "Nonexistent Element Name XYZ"}}', encoding="utf-8"
        )
        lookup = ReferenceLookup(
            registry_db_path=reference.registry_db_path,
            version="FAL50",
            alias_config_path=alias_file,
        )
        assert lookup.by_alias("ghost") == []

    def test_code_list_values(self, reference):
        values = reference.code_list_values("Event type")
        assert values is not None
        assert "EV01" in values and "EV02" in values and "EV12" in values
        assert "BUNKERING" not in values

    def test_element_count_matches_import(self, reference):
        assert reference.element_count() == 1205
