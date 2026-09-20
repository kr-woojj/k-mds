"""DataProfilerAgent 핵심 로직 (A-3) — 결정론 marker 기반.

근거 프로파일:
- FAL50 'Performance report type' code list: 1=Noon data report,
  2=Fuel consumption report, 3=CII report (var/reference/code_lists.json)
- FAL50 'Event type, coded' (IMO0597) / 'Operation type, coded' (IMO0598)
- data-space/openapi.yaml PerformanceReport 필드 구성
"""

from __future__ import annotations

from typing import Any

from ghg_agent.domain.models import ProfileResult, SourceProfile

_MIN_CONFIDENCE = 0.6

_NOON_MARKERS = {"report_datetime", "distance_through_water", "speed_through_water"}
_EVENT_MARKERS = {"event_type", "event_timestamp", "event"}
_PERFORMANCE_MARKERS = {"speed", "fuel_consumption", "power", "rpm", "foc", "shaft_power"}


def profile_payload(business: dict[str, Any]) -> ProfileResult:
    keys = {str(k).lower() for k in business.keys()}
    evidence: list[str] = []
    competing: list[str] = []

    report_type = str(business.get("report_type", "")).strip().lower()

    # 1) 명시적 report_type marker
    if report_type in {"noon", "noon data report", "noon_report", "1"}:
        return ProfileResult(
            selected_profile=SourceProfile.NOON_REPORT,
            confidence=1.0,
            deterministic_evidence=[f"report_type={report_type!r} (Performance report type code 1)"],
            classification_method="explicit_report_type",
        )
    if report_type in {"event", "event report", "event_report"}:
        return ProfileResult(
            selected_profile=SourceProfile.EVENT_REPORT,
            confidence=1.0,
            deterministic_evidence=[f"report_type={report_type!r}"],
            classification_method="explicit_report_type",
        )
    if report_type in {"vessel_performance", "performance", "performance_report"}:
        return ProfileResult(
            selected_profile=SourceProfile.VESSEL_PERFORMANCE,
            confidence=1.0,
            deterministic_evidence=[f"report_type={report_type!r}"],
            classification_method="explicit_report_type",
        )

    # 2) 구조적 marker
    scores: dict[SourceProfile, float] = {}
    event_hits = keys & _EVENT_MARKERS
    if event_hits:
        scores[SourceProfile.EVENT_REPORT] = 0.7 + 0.1 * min(len(event_hits), 2)
        evidence.append(f"event markers: {sorted(event_hits)}")
    noon_hits = keys & _NOON_MARKERS
    if noon_hits and not event_hits:
        scores[SourceProfile.NOON_REPORT] = 0.6 + 0.1 * min(len(noon_hits), 3)
        evidence.append(f"noon markers: {sorted(noon_hits)}")
    perf_hits = keys & _PERFORMANCE_MARKERS
    if perf_hits:
        scores[SourceProfile.VESSEL_PERFORMANCE] = 0.5 + 0.1 * min(len(perf_hits), 3)
        evidence.append(f"performance markers: {sorted(perf_hits)}")

    if not scores:
        return ProfileResult(
            selected_profile=SourceProfile.UNKNOWN,
            confidence=0.0,
            deterministic_evidence=["no deterministic marker"],
            classification_method="structural_marker",
        )

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    selected, confidence = ranked[0]
    competing = [p.value for p, s in ranked[1:] if ranked[0][1] - s < 0.2]
    if confidence < _MIN_CONFIDENCE or competing:
        return ProfileResult(
            selected_profile=SourceProfile.UNKNOWN,
            confidence=round(confidence, 3),
            deterministic_evidence=evidence,
            competing_profiles=[selected.value, *competing] if competing else [],
            classification_method="structural_marker",
        )
    return ProfileResult(
        selected_profile=selected,
        confidence=round(min(confidence, 0.99), 3),
        deterministic_evidence=evidence,
        competing_profiles=competing,
        classification_method="structural_marker",
    )
