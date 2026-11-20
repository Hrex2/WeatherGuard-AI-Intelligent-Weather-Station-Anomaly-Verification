from __future__ import annotations

import json

import pandas as pd
import pytest

from weather_research.e3_evidence_policy import (
    DERIVED, INDEPENDENT, SHARED, UNKNOWN, evaluate_evidence_record,
)
from weather_research.e3_spatial import nearest_timestamp_pairs
from weather_research.phase09_validation import (
    compute_descriptive_metrics, select_candidate_events, select_phase03_events,
    summarize_tolerance_sensitivity, verify_phase09_manifest,
)


def policy_row(**overrides):
    row = {
        "source_id": "NOAA_NATIVE", "station_id": "WMO-42101",
        "primary_station_id": "ICAO-VILD", "primary_physical_site_id": "VILD",
        "physical_site_id": "PATIALA", "primary_report_id": "P1",
        "original_report_id": "R1", "primary_report_system": "FM15",
        "report_system": "FM12", "lineage_classification": INDEPENDENT,
        "station_identity_verified": True, "primary_station_identity_verified": True,
        "physical_sites_distinct_verified": True, "report_systems_distinct_verified": True,
        "coordinates_verified": True, "distance_km": 76.0,
        "variable": "temperature", "primary_value": 20, "primary_unit": "degC",
        "reference_value": 20.5, "reference_unit": "degC",
        "candidate_timestamp": "2025-04-01T00:00:00Z",
        "reference_timestamp": "2025-04-01T00:00:00Z",
        "qc_status": "GOOD", "is_imputed": False,
    }
    row.update(overrides)
    return row


def test_phase03_extrema_selection_is_deterministic_and_deduplicated():
    candidates = pd.DataFrame({
        "timestamp": ["2025-01-01 00:00", "2025-01-01 01:00", "2025-01-01 02:00"],
        "temp_change_1h": [0, 4, -5], "temp": [10, 15, 8], "rhum": [50, 35, 60],
        "wspd": [1, 3, 2], "pres": [1000, 990, 995],
        "configuration_votes": [8, 8, 8], "episode_id": [1, 1, 1],
    })
    a, b = select_phase03_events(candidates), select_phase03_events(candidates.copy())
    assert a.event_type.tolist() == b.event_type.tolist()
    assert a.candidate_timestamp_utc.astype(str).tolist() == b.candidate_timestamp_utc.astype(str).tolist()
    assert len(a) <= len({"2025-01-01 00:00", "2025-01-01 01:00", "2025-01-01 02:00"})


def test_event_selection_rejects_duplicate_ids_and_naive_or_invalid_times():
    base = pd.DataFrame({"event_id": ["e1"], "candidate_timestamp_utc": ["2025-01-01T00:00Z"],
                         "event_type": ["x"], "comparison_variable": ["temperature"]})
    assert select_candidate_events(base).event_id.tolist() == ["e1"]
    with pytest.raises(ValueError, match="unique"):
        select_candidate_events(pd.concat([base, base], ignore_index=True))
    with pytest.raises(ValueError, match="timezone-aware"):
        select_candidate_events(base.assign(candidate_timestamp_utc="not a timestamp"))


def test_timestamp_matching_exact_and_tolerance_are_separate_and_one_to_one():
    p = pd.Series([10.0, 11.0], index=pd.to_datetime(["2025-01-01T00:00Z", "2025-01-01T01:00Z"]))
    r = pd.Series([10.2, 11.2], index=pd.to_datetime(["2025-01-01T00:10Z", "2025-01-01T01:05Z"]))
    exact = nearest_timestamp_pairs(p, r, 0)
    within = nearest_timestamp_pairs(p, r, 15)
    assert exact.neighbor_time.isna().all()
    assert within.neighbor_time.notna().sum() == 2
    assert within.neighbor_time.dropna().is_unique


def test_phase08_policy_excludes_shared_unknown_duplicate_and_imputed_records():
    for lineage in (SHARED, DERIVED):
        result = evaluate_evidence_record(policy_row(lineage_classification=lineage),
                                          tolerances={"temperature": 1}, tolerance_minutes=0)
        assert result["outcome"] == "NOT_COMPARABLE"
    unknown = evaluate_evidence_record(policy_row(lineage_classification=UNKNOWN),
                                      tolerances={"temperature": 1}, tolerance_minutes=0)
    assert unknown["outcome"] == "UNAVAILABLE"
    duplicate = evaluate_evidence_record(policy_row(duplicate_or_reused_observation=True),
                                         tolerances={"temperature": 1}, tolerance_minutes=0)
    assert duplicate["lineage_classification"] == DERIVED
    imputed = evaluate_evidence_record(policy_row(is_imputed=True),
                                       tolerances={"temperature": 1}, tolerance_minutes=0)
    assert imputed["outcome"] == "NOT_COMPARABLE"


def test_policy_unit_qc_tolerance_and_temporal_gates():
    converted = evaluate_evidence_record(policy_row(primary_unit="C", reference_unit="F",
                                                     primary_value=20, reference_value=68.9),
                                         tolerances={"temperature": 1}, tolerance_minutes=0)
    assert converted["comparison_eligibility"] == "ELIGIBLE_REPORT_LEVEL"
    bad_qc = evaluate_evidence_record(policy_row(qc_status="SUSPECT"),
                                      tolerances={"temperature": 1}, tolerance_minutes=0)
    assert bad_qc["outcome"] == "NOT_COMPARABLE"
    no_threshold = evaluate_evidence_record(policy_row(), tolerances={}, tolerance_minutes=0)
    assert no_threshold["outcome"] == "NOT_COMPARABLE"
    shifted = evaluate_evidence_record(policy_row(reference_timestamp="2025-04-01T01:00:00Z"),
                                       tolerances={"temperature": 1}, tolerance_minutes=15)
    assert shifted["outcome"] == "TEMPORALLY_MISMATCHED"


def test_policy_reports_missing_values_and_classifies_configured_report_level_outcomes():
    missing = evaluate_evidence_record(policy_row(primary_value=None),
                                       tolerances={"temperature": 1}, tolerance_minutes=0)
    assert missing["outcome"] == "UNAVAILABLE"
    assert missing["comparison_reason"] == "MISSING_OBSERVATION_VALUE"
    supported = evaluate_evidence_record(policy_row(distance_km=5.0, reference_value=20.5),
                                         tolerances={"temperature": 1}, tolerance_minutes=0)
    conflict = evaluate_evidence_record(policy_row(distance_km=5.0, reference_value=24),
                                        tolerances={"temperature": 1}, tolerance_minutes=0)
    assert supported["outcome"] == "SUPPORTS_LOCAL_EVENT"
    assert conflict["outcome"] == "CONFLICTS_WITH_LOCAL_EVENT"


def test_descriptive_metrics_sample_safeguard_and_circular_direction():
    small = pd.DataFrame({"primary_time": pd.date_range("2025-01-01", periods=2, tz="UTC"),
                          "primary_value": [1, 2], "reference_value": [2, 4]})
    result = compute_descriptive_metrics("temperature", small, minimum_pairs=3, minimum_distinct_dates=2)
    assert result["n_valid_pairs"] == 2
    assert result["bias_reference_minus_primary"] is None
    direction = pd.DataFrame({"primary_time": pd.date_range("2025-01-01", periods=30, tz="UTC"),
                              "primary_value": [359.0] * 30, "reference_value": [1.0] * 30})
    circular = compute_descriptive_metrics("wind_direction", direction)
    assert circular["metrics_status"] == "METRICS_REPORTED"
    assert circular["mae"] == pytest.approx(2.0)
    assert circular["correlation"] is None


def test_tolerance_sensitivity_counts_do_not_claim_agreement():
    rows = [{"source_pair": "a", "variable": "temperature", "tolerance_minutes": 0, "n_value_pairs": 4},
            {"source_pair": "a", "variable": "temperature", "tolerance_minutes": 15, "n_value_pairs": 6}]
    result = summarize_tolerance_sensitivity(rows)
    assert result[1]["pair_count_change_vs_exact"] == 2
    assert "Availability sensitivity only" in result[1]["interpretation"]


def test_manifest_verification_detects_hash_mismatch(tmp_path):
    data = tmp_path / "input.txt"
    data.write_text("original", encoding="utf-8")
    import hashlib
    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"input_files": {"input.txt": {"sha256": digest}},
                                   "generated_artifacts": {}}), encoding="utf-8")
    assert verify_phase09_manifest(manifest, tmp_path)["valid"]
    data.write_text("changed", encoding="utf-8")
    assert verify_phase09_manifest(manifest, tmp_path)["hash_mismatches"] == ["input.txt"]
