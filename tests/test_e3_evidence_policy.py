from datetime import datetime, timezone

import pytest

from weather_research.e3_evidence_policy import (
    CONTEXT, DERIVED, INDEPENDENT, NOT_COMPARABLE, SHARED, UNKNOWN,
    aggregate_variable_outcomes, classify_lineage, evaluate_evidence_record,
    evaluate_readiness_gates,
)


def eligible_record(**overrides):
    record = {
        "source_id": "NOAA_GHCNH_42101", "station_id": "WMO-42101",
        "primary_station_id": "ICAO-VILD", "original_report_id": "42101|2025-04-26T09:00Z",
        "primary_physical_site_id": "Ludhiana-airport", "physical_site_id": "Patiala-WMO-site",
        "primary_report_id": "VILD|2025-04-26T08:00Z", "primary_report_system": "FM15",
        "report_system": "FM12", "lineage_classification": INDEPENDENT,
        "station_identity_verified": True, "primary_station_identity_verified": True,
        "coordinates_verified": True, "physical_sites_distinct_verified": True,
        "report_systems_distinct_verified": True, "distance_km": 76.04,
        "variable": "temperature", "primary_value": 40.0, "primary_unit": "degC",
        "reference_value": 40.5, "reference_unit": "degC",
        "candidate_timestamp": datetime(2025, 4, 26, 8, tzinfo=timezone.utc),
        "reference_timestamp": datetime(2025, 4, 26, 9, tzinfo=timezone.utc),
        "qc_status": "GOOD", "is_imputed": False,
    }
    record.update(overrides)
    return record


def test_lineage_classification_requires_distinct_verified_reports_and_sites():
    evidence = {
        "lineage_evidence_supplied": True,
        "physical_sites_distinct_verified": True,
        "report_systems_distinct_verified": True,
        "primary_physical_site_id": "ICAO-VILD", "physical_site_id": "WMO-42101",
        "primary_report_id": "VILD-1", "original_report_id": "PAT-1",
        "primary_report_system": "FM15", "report_system": "FM12",
    }
    assert classify_lineage(evidence) == INDEPENDENT
    assert classify_lineage({**evidence, "shared_source_evidence": True}) == SHARED
    assert classify_lineage({**evidence, "same_observation_verified": True}) == DERIVED
    assert classify_lineage({"context_only": True}) == CONTEXT
    assert classify_lineage({}) == UNKNOWN
    assert classify_lineage({"lineage_classification": NOT_COMPARABLE}) == NOT_COMPARABLE


def test_independent_report_support_is_report_level_and_not_fault_diagnosis():
    result = evaluate_evidence_record(eligible_record(), tolerances={"temperature": 1.0},
                                      tolerance_minutes=60)
    assert result["comparison_eligibility"] == "ELIGIBLE_REPORT_LEVEL"
    assert result["outcome"] == "REGIONAL_SUPPORT"
    assert result["time_match_type"] == "TOLERANCE_MATCH"
    assert result["timestamp_offset_minutes_reference_minus_candidate"] == 60
    assert result["distance_zone"] == "C"


def test_independent_report_conflict_is_local_only_in_provisional_local_zones():
    record = eligible_record(distance_km=5.0, reference_value=45.0)
    result = evaluate_evidence_record(record, tolerances={"temperature": 1.0},
                                      tolerance_minutes=60)
    assert result["outcome"] == "CONFLICTS_WITH_LOCAL_EVENT"


def test_shared_and_derived_observations_never_add_independent_votes():
    for lineage in (SHARED, DERIVED):
        result = evaluate_evidence_record(eligible_record(lineage_classification=lineage),
                                          tolerances={"temperature": 1.0}, tolerance_minutes=60)
        assert result["comparison_eligibility"] == "SHARED_CONTEXT_ONLY"
        assert result["outcome"] == "NOT_COMPARABLE"
        assert result["evidence_role"] == "SHARED_OR_DERIVED"


def test_duplicate_observation_is_not_counted_twice():
    result = evaluate_evidence_record(eligible_record(duplicate_or_reused_observation=True),
                                      tolerances={"temperature": 1.0}, tolerance_minutes=60)
    assert result["comparison_eligibility"] == "SHARED_CONTEXT_ONLY"
    assert result["lineage_classification"] == DERIVED


def test_unknown_lineage_is_excluded():
    result = evaluate_evidence_record(eligible_record(lineage_classification=UNKNOWN),
                                      tolerances={"temperature": 1.0}, tolerance_minutes=60)
    assert result["comparison_eligibility"] == "INELIGIBLE"
    assert result["outcome"] == "UNAVAILABLE"


def test_context_support_remains_context_not_station_corroboration():
    record = eligible_record(lineage_classification=CONTEXT, distance_km=None)
    result = evaluate_evidence_record(record, tolerances={"temperature": 1.0},
                                      tolerance_minutes=60)
    assert result["comparison_eligibility"] == "CONTEXT_ONLY"
    assert result["outcome"] == "WIDER_CONTEXT_SUPPORT"
    assert result["evidence_role"] == "CONTEXT"


@pytest.mark.parametrize("minutes,expected", [(0, "EXACT"), (15, "TOLERANCE_MATCH"),
                                               (30, "TOLERANCE_MATCH"), (60, "TOLERANCE_MATCH")])
def test_exact_and_preregistered_tolerance_windows(minutes, expected):
    base = eligible_record(reference_timestamp=datetime(2025, 4, 26, 8, tzinfo=timezone.utc)
                           if minutes == 0 else
                           datetime.fromtimestamp(datetime(2025, 4, 26, 8, tzinfo=timezone.utc).timestamp()
                                                  + minutes * 60, tz=timezone.utc))
    result = evaluate_evidence_record(base, tolerances={"temperature": 1.0},
                                      tolerance_minutes=minutes)
    assert result["time_match_type"] == expected
    assert result["timestamp_offset_minutes_reference_minus_candidate"] == minutes


def test_temporal_mismatch_is_not_conflict():
    result = evaluate_evidence_record(eligible_record(), tolerances={"temperature": 1.0},
                                      tolerance_minutes=15)
    assert result["outcome"] == "TEMPORALLY_MISMATCHED"
    assert result["comparison_eligibility"] == "INELIGIBLE"


def test_missing_and_imputed_observations_are_not_conflicts_or_independent_evidence():
    missing = evaluate_evidence_record(eligible_record(reference_value=None),
                                       tolerances={"temperature": 1.0}, tolerance_minutes=60)
    imputed = evaluate_evidence_record(eligible_record(is_imputed=True),
                                       tolerances={"temperature": 1.0}, tolerance_minutes=60)
    assert missing["outcome"] == "UNAVAILABLE"
    assert imputed["outcome"] == "NOT_COMPARABLE"
    assert imputed["comparison_eligibility"] == "INELIGIBLE"
    unverified_imputation = evaluate_evidence_record(eligible_record(is_imputed=None),
                                                     tolerances={"temperature": 1.0},
                                                     tolerance_minutes=60)
    assert unverified_imputation["comparison_reason"] == "IMPUTED_OR_IMPUTATION_STATUS_UNVERIFIED"


def test_qc_failure_and_unverified_station_metadata_exclude_support():
    failed_qc = evaluate_evidence_record(eligible_record(qc_status="FAILED"),
                                         tolerances={"temperature": 1.0}, tolerance_minutes=60)
    unverified = evaluate_evidence_record(eligible_record(station_identity_verified=False),
                                          tolerances={"temperature": 1.0}, tolerance_minutes=60)
    no_geography = evaluate_evidence_record(eligible_record(coordinates_verified=False),
                                            tolerances={"temperature": 1.0}, tolerance_minutes=60)
    assert failed_qc["outcome"] == "NOT_COMPARABLE"
    assert unverified["outcome"] == "UNAVAILABLE"
    assert no_geography["outcome"] == "UNAVAILABLE"


def test_unit_conversion_is_explicit_and_incompatible_dimensions_are_rejected():
    converted = evaluate_evidence_record(eligible_record(primary_value=104, primary_unit="degF",
                                                          reference_value=40, reference_unit="degC"),
                                         tolerances={"temperature": 0.2}, tolerance_minutes=60)
    incompatible = evaluate_evidence_record(eligible_record(reference_unit="hPa"),
                                            tolerances={"temperature": 1.0}, tolerance_minutes=60)
    assert converted["outcome"] == "REGIONAL_SUPPORT"
    assert converted["primary_value_canonical"] == pytest.approx(40)
    assert incompatible["outcome"] == "NOT_COMPARABLE"


def test_no_default_or_invalid_tolerance_cannot_create_agreement_or_conflict():
    missing = evaluate_evidence_record(eligible_record(), tolerance_minutes=60)
    invalid = evaluate_evidence_record(eligible_record(), tolerances={"temperature": float("nan")},
                                       tolerance_minutes=60)
    assert missing["outcome"] == "NOT_COMPARABLE"
    assert invalid["outcome"] == "NOT_COMPARABLE"


def test_wind_direction_uses_circular_difference():
    record = eligible_record(variable="wind_direction", primary_value=359, reference_value=1,
                             primary_unit="degree", reference_unit="degree")
    result = evaluate_evidence_record(record, tolerances={"wind_direction": 3}, tolerance_minutes=60)
    assert result["difference_reference_minus_primary"] == pytest.approx(2)
    assert result["outcome"] == "REGIONAL_SUPPORT"


def test_precipitation_occurrence_mismatch_is_not_spatial_conflict_by_default():
    interval = "2025-04-26T08:00:00Z"
    record = eligible_record(variable="precipitation", primary_value=5, reference_value=0,
                             primary_unit="mm", reference_unit="mm",
                             primary_interval_start=interval, reference_interval_start=interval,
                             primary_interval_end="2025-04-26T09:00:00Z",
                             reference_interval_end="2025-04-26T09:00:00Z",
                             precipitation_protocol_id="pre-registered-test",
                             precipitation_occurrence_threshold_mm=0.1)
    result = evaluate_evidence_record(record, tolerances={"precipitation": 1}, tolerance_minutes=60)
    assert result["outcome"] == "NOT_COMPARABLE"
    assert "SPATIALLY_INTERMITTENT" in result["comparison_reason"]


def test_variable_outcomes_are_separate_and_mixed_evidence_abstains():
    support = evaluate_evidence_record(eligible_record(distance_km=5),
                                       tolerances={"temperature": 1}, tolerance_minutes=60)
    conflict = evaluate_evidence_record(eligible_record(distance_km=5, reference_value=50),
                                        tolerances={"temperature": 1}, tolerance_minutes=60)
    mixed = aggregate_variable_outcomes([support, conflict], variable="temperature")
    other_variable = aggregate_variable_outcomes([support], variable="pressure")
    assert mixed["outcome"] == "MIXED_SPATIAL_EVIDENCE"
    assert other_variable["outcome"] == "INSUFFICIENT_COVERAGE"


def test_readiness_gate_evaluation_is_conservative_and_separate_from_tests():
    gates = {"provenance": "PARTIAL", "geographic": "PARTIAL", "temporal": "PARTIAL",
             "measurement": "PARTIAL", "event_validation": "FAIL", "reproducibility": "PARTIAL"}
    result = evaluate_readiness_gates(gates)
    assert result["decision"] == "PARTIALLY_READY"
    assert result["software_tests_are_not_readiness_evidence"] is True
    assert evaluate_readiness_gates({**gates, "provenance": "FAIL"})["decision"] == "BLOCKED_BY_DATA_PROVENANCE"
    assert evaluate_readiness_gates({k: "PASS" for k in gates})["decision"] == "READY_FOR_CONTROLLED_VALIDATION"
    with pytest.raises(ValueError):
        evaluate_readiness_gates({"provenance": "PASS"})
