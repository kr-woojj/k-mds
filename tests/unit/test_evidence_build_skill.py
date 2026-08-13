"""evidence_build Skill Contract Test (ADR-0003).

검증된 SourceManifestEntry에서만 Evidence를 생성하는지 검증한다.
모든 Fixture는 TEST/FALTEST/urn:test 표기의 가상 값만 사용한다.
"""

from k_mds.models import ResultStatus, SkillResult, SourceManifestEntry
from k_mds.skills import evidence_build

SOURCE_HASH = "TEST-SHA256-NOT-A-REAL-HASH"
SOURCE_FILE = "data/raw/FALTEST/test-source.xlsx"


def make_entry_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "source_id": "TEST-SOURCE-001",
        "fal_version": "FALTEST",
        "ontology_version": "0.0.0-test",
        "profile_version": "kr-profile-0.0.0-test",
        "source_file": SOURCE_FILE,
        "source_hash": SOURCE_HASH,
        "resource_uri": "urn:test:source:001",
        "verified": True,
        "status": "approved",
    }
    base.update(overrides)
    return base


def make_entry(**overrides: object) -> SourceManifestEntry:
    return SourceManifestEntry.model_validate(make_entry_dict(**overrides))


# --- PASS 경로 (지시 Test 1~5) ---


def test_valid_entry_object_passes() -> None:
    assert evidence_build(make_entry()).status is ResultStatus.PASS


def test_valid_dict_passes() -> None:
    assert evidence_build(make_entry_dict()).status is ResultStatus.PASS


def test_generated_evidence_versions_match_entry() -> None:
    entry = make_entry()
    evidence = evidence_build(entry).evidence[0]
    assert evidence.fal_version == entry.fal_version
    assert evidence.ontology_version == entry.ontology_version
    assert evidence.profile_version == entry.profile_version
    assert evidence.source_file == entry.source_file
    assert evidence.source_hash == entry.source_hash
    assert evidence.resource_uri == entry.resource_uri


def test_evidence_id_is_deterministic_from_source_id() -> None:
    result = evidence_build(make_entry())
    assert result.evidence[0].evidence_id == "evidence:TEST-SOURCE-001"
    assert result.data["evidenceId"] == "evidence:TEST-SOURCE-001"


def test_same_entry_produces_identical_result() -> None:
    entry = make_entry()
    first = evidence_build(entry).model_dump(by_alias=True)
    second = evidence_build(entry).model_dump(by_alias=True)
    assert first == second


# --- FAIL 경로 (지시 Test 6~8) ---


def test_unverified_entry_fails() -> None:
    result = evidence_build(make_entry(verified=False, status="draft"))
    assert result.status is ResultStatus.FAIL


def test_non_approved_entry_fails() -> None:
    result = evidence_build(make_entry(status="review_required"))
    assert result.status is ResultStatus.FAIL


def test_invalid_dict_fails() -> None:
    assert evidence_build({"source_id": "TEST-SOURCE-001"}).status is ResultStatus.FAIL


# --- 불변조건 (지시 Test 9~10) ---


def _fail_results() -> list[SkillResult]:
    return [
        evidence_build(make_entry(verified=False, status="draft")),
        evidence_build(make_entry(status="review_required")),
        evidence_build({}),
    ]


def test_all_fail_results_have_review_errors_and_no_evidence() -> None:
    for result in _fail_results():
        assert result.status is ResultStatus.FAIL
        assert result.human_review_required is True
        assert len(result.errors) >= 1
        assert result.evidence == []


def test_pass_results_have_single_evidence_and_no_findings() -> None:
    for result in (evidence_build(make_entry()), evidence_build(make_entry_dict())):
        assert result.status is ResultStatus.PASS
        assert result.human_review_required is False
        assert result.errors == [] and result.warnings == []
        assert len(result.evidence) == 1
        assert result.data["verified"] is True
        assert result.data["sourceId"] == "TEST-SOURCE-001"


# --- 원본 값 비노출 (지시 Test 11~13) ---


def test_findings_do_not_expose_source_hash() -> None:
    for result in _fail_results():
        for finding in result.errors:
            dumped = finding.model_dump_json(by_alias=True)
            assert SOURCE_HASH not in dumped


def test_findings_do_not_expose_source_file() -> None:
    for result in _fail_results():
        for finding in result.errors:
            dumped = finding.model_dump_json(by_alias=True)
            assert SOURCE_FILE not in dumped


def test_finding_actual_value_is_none() -> None:
    for result in _fail_results():
        for finding in result.errors:
            assert finding.actual_value is None


# --- Skill 실행 Contract (지시 Test 14~15) ---


def test_returns_skill_result_instance() -> None:
    assert isinstance(evidence_build(make_entry()), SkillResult)


def test_serialization_contains_evidence_and_source_ids() -> None:
    dumped = evidence_build(make_entry()).model_dump_json(by_alias=True)
    assert "evidenceId" in dumped
    assert "sourceId" in dumped
    assert "humanReviewRequired" in dumped
