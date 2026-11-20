import pandas as pd
import pytest

from weather_research.e3_spatial import (
    DEFAULT_ZONES,
    assign_distance_zone,
    evaluate_spatial_evidence,
    haversine_km,
    nearest_timestamp_pairs,
    provenance_eligible,
)


def test_provisional_zone_boundaries_are_half_open():
    assert [assign_distance_zone(x) for x in (0, 9.999, 10, 49.999, 50, 100, 250, 250.001)] == [
        "A", "A", "B", "B", "C", "D", "E", "E"
    ]
    assert DEFAULT_ZONES[-1].upper_km is None


def test_haversine_returns_zero_and_known_equatorial_distance():
    assert haversine_km(0, 0, 0, 0) == 0
    assert haversine_km(0, 0, 0, 1) == pytest.approx(111.195, rel=1e-4)
    with pytest.raises(ValueError):
        haversine_km(91, 0, 0, 0)


def test_nearest_pairing_keeps_exact_and_tolerance_matches_separate():
    primary = pd.Series([10.0, 20.0], index=pd.DatetimeIndex([
        "2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z"
    ]))
    neighbor = pd.Series([11.0, 19.0], index=pd.DatetimeIndex([
        "2025-01-01T00:00:00Z", "2025-01-01T01:15:00Z"
    ]))
    pairs = nearest_timestamp_pairs(primary, neighbor, 15)
    assert pairs.match_type.tolist() == ["EXACT", "TOLERANCE_MATCH"]
    assert pairs.offset_minutes.tolist() == [0.0, 15.0]
    assert pairs.difference_neighbor_minus_primary.tolist() == [1.0, -1.0]
    assert nearest_timestamp_pairs(primary, neighbor, 0).match_type.tolist() == ["EXACT", "NO_MATCH"]


def test_provenance_gate_excludes_unknown_and_model_filled_values():
    labels = pd.Series(["verified_direct_observation", "unknown", "model", None])
    assert provenance_eligible(labels).tolist() == [True, False, False, False]


def test_tolerance_matching_never_reuses_a_neighbor_timestamp():
    primary = pd.Series([10.0, 11.0], index=pd.DatetimeIndex([
        "2025-01-01T00:00:00Z", "2025-01-01T01:00:00Z"
    ]))
    neighbor = pd.Series([10.5], index=pd.DatetimeIndex(["2025-01-01T00:30:00Z"]))
    pairs = nearest_timestamp_pairs(primary, neighbor, 30)
    assert pairs.neighbor_time.notna().sum() == 1
    assert pairs.neighbor_time.dropna().is_unique


def test_unknown_lineage_and_missing_tolerance_cannot_support_event():
    result = evaluate_spatial_evidence([{
        "station_id":"n1", "zone":"A", "matched":True,
        "primary_value":20.0, "neighbor_value":20.1, "offset_minutes":0,
        "provenance_status":"SOURCE_ID_ONLY", "independence_status":"UNKNOWN",
        "quality_status":"VALID",
    }], tolerance=None)
    assert result["status"] == "UNAVAILABLE"
    assert result["research_outcome"] == "INSUFFICIENT_OR_UNCERTAIN_EVIDENCE"
    assert result["supporting_station_count"] == 0


def test_spatial_evidence_requires_independent_sources_and_keeps_mixed_results_uncertain():
    base = {"matched":True, "primary_value":20.0, "offset_minutes":0,
            "provenance_status":"VERIFIED_DIRECT_OBSERVATION",
            "independence_status":"VERIFIED_INDEPENDENT", "quality_status":"VALID"}
    result = evaluate_spatial_evidence([
        {**base, "station_id":"near", "zone":"A", "neighbor_value":20.2},
        {**base, "station_id":"regional", "zone":"C", "neighbor_value":24.0},
    ], tolerance=1.0)
    assert result["status"] == "MIXED_SPATIAL_EVIDENCE"
    assert result["research_outcome"] == "INSUFFICIENT_OR_UNCERTAIN_EVIDENCE"
    assert result["supporting_station_count"] == 1
    assert result["conflicting_station_count"] == 1


def test_synthetic_positive_and_negative_controls_are_unweighted():
    base = {"matched":True, "primary_value":20.0, "offset_minutes":0,
            "provenance_status":"VERIFIED_DIRECT_OBSERVATION",
            "independence_status":"VERIFIED_INDEPENDENT", "quality_status":"VALID"}
    positive = evaluate_spatial_evidence([
        {**base, "station_id":"near", "zone":"A", "neighbor_value":20.2},
        {**base, "station_id":"regional", "zone":"C", "neighbor_value":20.6},
    ], tolerance=1.0)
    assert positive["research_outcome"] == "REGIONALLY_SUPPORTED_EVENT"
    assert positive["supporting_station_count"] == 2

    negative = evaluate_spatial_evidence([
        {**base, "station_id":"near", "zone":"A", "neighbor_value":24.0},
    ], tolerance=1.0)
    assert negative["research_outcome"] == "STATION_SPECIFIC_SUSPICIOUS_OBSERVATION"
    assert "not ground truth or sensor-fault diagnoses" in negative["interpretation"].lower()

