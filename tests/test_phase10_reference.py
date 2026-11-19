from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest

from weather_research.e3_evidence_policy import INDEPENDENT, SHARED, UNKNOWN
from weather_research.phase09_validation import select_phase03_events
from weather_research.phase10_reference import (
    apply_phase08_policy, classify_raw_value, deterministic_event_registry,
    find_shared_observation_groups, observation_fingerprint,
    report_payload_fingerprint, validate_adjudication_register,
    validate_sufficiency_assessment, verify_phase10_manifest,
)


def test_original_timestamp_and_report_payload_are_retained_in_fingerprints():
    timestamp = "2025-01-01T04:00:00"
    report = "METAR VILD 010400Z ..."
    assert report_payload_fingerprint("INI0000VILD", timestamp, report).startswith("RPF-")
    assert report_payload_fingerprint("INI0000VILD", timestamp, report) == report_payload_fingerprint(
        "INI0000VILD", timestamp, report)
    assert report_payload_fingerprint("INI0000VILD", "2025-01-01T04:00:00Z", report) != report_payload_fingerprint(
        "INI0000VILD", timestamp, report)
    assert observation_fingerprint("INI0000VILD", timestamp, "temperature", "23.4", "degC") != observation_fingerprint(
        "INI0000VILD", timestamp, "temperature", "23.5", "degC")


def test_blank_missing_sentinel_and_nonnumeric_values_remain_distinguishable():
    assert classify_raw_value("") == ("BLANK_MISSING", None)
    assert classify_raw_value("-9999") == ("PROVIDER_MISSING_SENTINEL", None)
    assert classify_raw_value("T") == ("NONNUMERIC_RETAINED", None)
    assert classify_raw_value("0.0") == ("PRESENT", 0.0)


def test_duplicate_provider_records_link_to_one_underlying_observation():
    rows = [
        {"shared_observation_id": "RPF-a", "source_id": "NOAA_GHCNH", "record": "native"},
        {"shared_observation_id": "RPF-a", "source_id": "METEOSTAT_GHCNH", "record": "mirror"},
        {"shared_observation_id": "RPF-b", "source_id": "NOAA_GHCNH", "record": "unique"},
    ]
    groups = find_shared_observation_groups(rows)
    assert len(groups) == 1
    assert groups[0]["source_ids"] == ["METEOSTAT_GHCNH", "NOAA_GHCNH"]
    assert groups[0]["underlying_observation_count"] == 1
    assert groups[0]["independent_vote_count"] == 0


def test_phase08_policy_preserves_shared_and_unknown_lineage_exclusions():
    shared = apply_phase08_policy({"lineage_classification": SHARED})
    unknown = apply_phase08_policy({"lineage_classification": UNKNOWN})
    assert shared["outcome"] == "NOT_COMPARABLE"
    assert unknown["outcome"] == "UNAVAILABLE"
    with pytest.raises(ValueError, match="lineage classes"):
        apply_phase08_policy({"lineage_classification": "INDEPENDENT_BY_ASSUMPTION"})


def test_policy_unit_conversion_is_explicit_and_source_values_are_not_rewritten():
    record = {
        "source_id": "test", "station_id": "PATIALA", "primary_station_id": "VILD",
        "primary_physical_site_id": "A", "physical_site_id": "B",
        "primary_report_id": "P1", "original_report_id": "P2",
        "primary_report_system": "FM15", "report_system": "FM12",
        "lineage_classification": INDEPENDENT, "station_identity_verified": True,
        "primary_station_identity_verified": True, "physical_sites_distinct_verified": True,
        "report_systems_distinct_verified": True, "coordinates_verified": True,
        "distance_km": 76.0, "variable": "temperature", "primary_value": 20,
        "primary_unit": "degC", "reference_value": 68.9, "reference_unit": "degF",
        "candidate_timestamp": "2025-01-01T00:00:00Z",
        "reference_timestamp": "2025-01-01T00:00:00Z", "qc_status": "GOOD",
        "is_imputed": False,
    }
    result = apply_phase08_policy(record, tolerances={"temperature": 1}, tolerance_minutes=0)
    assert result["primary_value_canonical"] == pytest.approx(20.0)
    assert result["reference_value_canonical"] == pytest.approx(20.5)
    assert record["primary_value"] == 20
    assert record["reference_value"] == 68.9


def test_event_selection_reproduces_phase09_signature_without_labels():
    candidates = pd.DataFrame({
        "timestamp": ["2025-01-01 00:00", "2025-01-01 01:00", "2025-01-01 02:00"],
        "temp_change_1h": [0.0, 4.0, -5.0], "temp": [10.0, 15.0, 8.0],
        "rhum": [50.0, 35.0, 60.0], "wspd": [1.0, 3.0, 2.0],
        "pres": [1000.0, 990.0, 995.0], "configuration_votes": [8, 8, 8],
        "episode_id": [1, 1, 1],
    })
    prior = select_phase03_events(candidates).copy()
    prior["event_id"] = [f"P09E{i:02d}" for i in range(1, len(prior) + 1)]
    result = deterministic_event_registry(candidates, prior)
    assert result.event_id.tolist() == [f"P10E{i:02d}" for i in range(1, len(result) + 1)]
    assert set(result.adjudication_status) == {"NOT_ADJUDICATED"}
    assert result.adjudication_label.isna().all()


def test_adjudication_status_rejects_labels_without_review_and_unreviewed_labels():
    base = pd.DataFrame([{"event_id": "e1", "adjudication_status": "NOT_ADJUDICATED",
                          "adjudication_label": None, "reviewer_or_method": "none",
                          "evidence_considered": "records", "rationale": "not reviewed"}])
    assert validate_adjudication_register(base).iloc[0].adjudication_status == "NOT_ADJUDICATED"
    with pytest.raises(ValueError, match="cannot carry a label"):
        validate_adjudication_register(base.assign(adjudication_label="REGIONALLY_SUPPORTED_EVENT"))
    with pytest.raises(ValueError, match="reviewer or documented method"):
        validate_adjudication_register(base.assign(adjudication_status="INCONCLUSIVE",
                                                   adjudication_label="INCONCLUSIVE",
                                                   reviewer_or_method=""))


def test_sufficiency_assessment_requires_all_dimensions_and_allowed_states():
    good = {key: "PARTIAL" for key in ("provenance", "geographic", "temporal",
                                        "measurement", "event", "adjudication")}
    assert validate_sufficiency_assessment(good) == good
    with pytest.raises(ValueError, match="exactly"):
        validate_sufficiency_assessment({"provenance": "PARTIAL"})
    with pytest.raises(ValueError, match="invalid"):
        validate_sufficiency_assessment({**good, "event": "PASS_WITH_NO_EVIDENCE"})


def test_manifest_hash_verification_detects_mutation(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("stable", encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"input_files": {"source.txt": {"sha256": digest}},
                                    "generated_artifacts": {}}), encoding="utf-8")
    assert verify_phase10_manifest(manifest, tmp_path)["valid"]
    source.write_text("changed", encoding="utf-8")
    assert verify_phase10_manifest(manifest, tmp_path)["hash_mismatches"] == ["source.txt"]
