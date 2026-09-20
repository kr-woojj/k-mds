"""TS-2: Skill 입출력 계약 (실제 validator 호출)."""

from __future__ import annotations

from tests.conftest import requires_registry, requires_skill

EXPECTED_TOOLS = {
    "map_dataset",
    "validate_mapping",
    "explain_mapping",
    "list_candidates",
    "compare_compendium_versions",
}


@requires_registry
@requires_skill
class TestSkillContract:
    def test_list_tools_discovery(self, skill):
        tools = skill.list_tools()
        names = {tool["name"] for tool in tools}
        assert EXPECTED_TOOLS <= names
        for tool in tools:
            assert "inputSchema" in tool and "description" in tool

    def test_readiness_and_versions(self, skill):
        readiness = skill.readiness()
        assert readiness["ready"] is True
        assert "FAL50" in readiness["registry_versions"]
        assert readiness["skill_version"] == "0.1.0"
        assert readiness["real_call"] is True

    def test_invalid_arguments_fail_closed(self, skill):
        envelope = skill.invoke("validate_mapping", {"unexpected": 1})
        assert envelope["ok"] is False
        assert envelope["error"]["code"] == "INVALID_ARGUMENTS"

    def test_unknown_tool(self, skill):
        envelope = skill.invoke("no_such_tool", {})
        assert envelope["ok"] is False
        assert envelope["error"]["code"] == "UNKNOWN_TOOL"

    def test_validate_mapping_output_contract(self, skill):
        envelope = skill.invoke(
            "validate_mapping",
            {
                "mappings": [
                    {
                        "field": {"name": "speed_through_water", "declared_type": "numeric"},
                        "imo_data_number": "IMO0616",
                    }
                ]
            },
        )
        assert envelope["ok"] is True
        result = envelope["result"]
        assert result["compendiumVersion"] == "FAL50"
        assert result["overallStatus"] in ("PASS", "FAIL")
        entry = result["results"][0]
        assert set(entry) >= {"fieldName", "imoDataNumber", "status", "issues"}

    def test_map_dataset_provenance_no_llm(self, skill):
        envelope = skill.invoke(
            "map_dataset",
            {
                "dataset": {"speed_through_water": 12.5},
                "input_format": "json",
            },
        )
        assert envelope["ok"] is True
        provenance = envelope["result"]["provenance"]
        assert provenance["compendiumVersion"] == "FAL50"
        assert provenance["deterministicPipeline"] is True
        assert provenance["llmUsed"] is False
        assert envelope["result"]["audit_id"]

    def test_nonexistent_version_fails_closed(self, skill):
        envelope = skill.invoke(
            "list_candidates",
            {"field": {"name": "speed"}, "compendium_version": "FAL99"},
        )
        assert envelope["ok"] is False
        assert envelope["error"]["code"] == "VERSION_NOT_LOADED"

    def test_timeout_conversion(self, settings):
        import pytest

        from ghg_agent.adapters.skill_adapter import (
            ImoMappingSkillAdapter,
            SkillAdapterError,
        )

        adapter = ImoMappingSkillAdapter(
            skill_path=settings.imo_mapping_skill_path,
            registry_db_path=settings.registry_db_path,
            timeout_seconds=0.000001,
        )
        with pytest.raises(SkillAdapterError) as exc_info:
            adapter.invoke(
                "map_dataset",
                {"dataset": {"a": 1, "b": 2, "c": 3}, "input_format": "json"},
            )
        assert exc_info.value.code == "SKILL_TIMEOUT"
        assert adapter.call_log[-1].error_code == "SKILL_TIMEOUT"
