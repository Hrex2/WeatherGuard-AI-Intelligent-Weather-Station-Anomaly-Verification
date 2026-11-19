import pandas as pd

from weather_research.phase07_lineage import (
    classify_lineage_pair,
    compare_event_value,
    match_event_observation,
)


def test_shared_report_identity_classifies_derived_product():
    left = {"verified_original_report_id": "VILD|2025-12-02T05:00Z",
            "report_identity_verified": True}
    right = {"verified_original_report_id": "VILD|2025-12-02T05:00Z",
             "report_identity_verified": True}
    assert classify_lineage_pair(left, right) == "DERIVED_FROM_SAME_REPORT"


def test_different_provider_ids_alone_do_not_prove_independence():
    assert classify_lineage_pair({"provider_id": "metar"}, {"provider_id": "ghcnh"}) == "UNKNOWN_LINEAGE"


def test_distinct_verified_sites_and_original_report_classes_are_independent():
    left = {"verified_physical_site_id": "ICAO-VILD", "verified_original_station_id": "ICAO-VILD",
            "verified_report_type": "FM15", "distinct_original_reports_verified": True}
    right = {"verified_physical_site_id": "WMO-42101", "verified_original_station_id": "WMO-42101",
             "verified_report_type": "FM12", "distinct_original_reports_verified": True}
    assert classify_lineage_pair(left, right) == "INDEPENDENT_OBSERVING_SYSTEM"


def test_same_verified_site_and_report_class_is_only_possible_shared_source():
    left = {"verified_physical_site_id": "VILD", "verified_original_station_id": "ICAO-VILD",
            "verified_report_type": "FM15", "same_verified_physical_site": True}
    right = {"verified_physical_site_id": "VILD", "verified_original_station_id": "ICAO-VILD",
             "verified_report_type": "FM15", "same_verified_physical_site": True}
    assert classify_lineage_pair(left, right) == "POSSIBLY_SHARED_SOURCE"


def test_context_grid_is_not_comparable_as_station_observation():
    assert classify_lineage_pair({}, {"context_only": True}) == "NOT_COMPARABLE"


def test_event_matching_distinguishes_exact_tolerance_and_missing_value():
    event = pd.Timestamp("2025-01-01T00:00:00Z")
    records = pd.DataFrame({"timestamp": [event, event + pd.Timedelta(minutes=30)],
                            "value": [10.0, 12.0]})
    assert match_event_observation(event, records.iloc[[0]], 0)["match_status"] == "EXACT_MATCH"
    assert match_event_observation(event, records.iloc[[1]], 30)["match_status"] == "TOLERANCE_MATCH"
    missing = pd.DataFrame({"timestamp": [event], "value": [None]})
    assert match_event_observation(event, missing, 0)["match_status"] == "MISSING_REFERENCE_VALUE"


def test_missing_external_reference_is_not_counted_as_disagreement():
    result = compare_event_value(10.0, None, units_comparable=True,
                                lineage_class="INDEPENDENT_OBSERVING_SYSTEM",
                                match_status="NO_MATCH_WITHIN_TOLERANCE")
    assert result == {"comparison_status": "REFERENCE_UNAVAILABLE", "difference": None,
                      "evidence_role": "MISSING_NOT_DISAGREEMENT"}


def test_event_comparison_separates_independent_and_context_sources():
    independent = compare_event_value(10.0, 10.5, units_comparable=True,
                                      lineage_class="INDEPENDENT_OBSERVING_SYSTEM",
                                      match_status="TOLERANCE_MATCH")
    context = compare_event_value(10.0, 10.5, units_comparable=True,
                                  lineage_class="POSSIBLY_SHARED_SOURCE",
                                  match_status="TOLERANCE_MATCH")
    assert independent["difference"] == 0.5
    assert independent["evidence_role"] == "INDEPENDENT_REPORT_LEVEL_REFERENCE"
    assert context["evidence_role"] == "SHARED_OR_UNKNOWN_LINEAGE_CONTEXT"
    assert "DESCRIPTIVE" in independent["comparison_status"]
