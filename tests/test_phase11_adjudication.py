from __future__ import annotations

import pandas as pd
import pytest

from weather_research.e3_evidence_policy import NOT_COMPARABLE, SHARED, UNKNOWN
from weather_research.phase11_adjudication import (
    apply_phase08_policy, classify_record_origin, exact_candidate_link,
    find_duplicate_reports, record_fingerprint, validate_adjudication_register,
    verify_sha256_manifest,
)
from scripts.build_phase11_evidence_registers import metar_variable_check


def _candidate(timestamp="2025-12-02T05:00:00Z"):
    return {"event_id": "P10E05", "primary_station": "VILD0 / ICAO-VILD station record",
            "timestamp_utc_reproduction": timestamp}


def test_source_provenance_keeps_archive_copy_distinct_from_provider_original():
    assert classify_record_origin(raw_message="VILD 020500Z ...", provider="IEM") == "ARCHIVED_RAW_MESSAGE_NO_PROVIDER_ID"
    assert classify_record_origin(raw_message="VILD ...", provider_record_id="provider-1", provider="IMD") == "ORIGINAL_MESSAGE_WITH_PROVIDER_ID"
    assert classify_record_origin() == "DERIVED_OR_HARMONIZED_RECORD"


def test_report_fingerprint_is_deterministic_but_explicitly_local():
    one = record_fingerprint("VILD", "2025-12-02 05:00", "VILD 020500Z 19/10")
    assert one == record_fingerprint("VILD", "2025-12-02 05:00", "VILD 020500Z 19/10")
    assert one.startswith("P11FP-")


def test_exact_link_requires_station_archive_time_and_raw_message_time():
    frame = pd.DataFrame([{"station": "VILD", "valid": "2025-12-02 05:00",
                           "metar": "VILD 020500Z 12001KT 2000 HZ NSC 19/10 Q1018"}])
    result = exact_candidate_link(_candidate(), frame)
    assert result["linkage_status"] == "PROVISIONAL"
    assert result["temporal_offset_seconds"] == 0
    assert result["source_record_id"] == "NOT_PROVIDED"
    assert result["record_origin"] == "ARCHIVED_RAW_MESSAGE_NO_PROVIDER_ID"
    assert result["lineage_classification"] == UNKNOWN


def test_exact_timestamp_alone_does_not_link_if_raw_message_identity_disagrees():
    frame = pd.DataFrame([{"station": "VILD", "valid": "2025-12-02 05:00",
                           "metar": "VILD 020600Z 12001KT 19/10 Q1018"}])
    result = exact_candidate_link(_candidate(), frame)
    assert result["linkage_status"] == "UNAVAILABLE"
    assert result["matching_report_count"] == 0


def test_nearby_timestamp_is_not_used_as_identity():
    frame = pd.DataFrame([{"station": "VILD", "valid": "2025-12-02 05:08",
                           "metar": "VILD 020508Z 12001KT 19/10 Q1018"}])
    result = exact_candidate_link(_candidate(), frame)
    assert result["linkage_status"] == "UNAVAILABLE"
    assert "no tolerance" in result["link_rule"]


def test_naive_candidate_timezone_is_rejected():
    frame = pd.DataFrame([{"station": "VILD", "valid": "2025-12-02 05:00",
                           "metar": "VILD 020500Z 12001KT 19/10 Q1018"}])
    with pytest.raises(ValueError, match="timezone-aware"):
        exact_candidate_link(_candidate("2025-12-02 05:00:00"), frame)


def test_duplicate_reports_are_local_fingerprint_groups_without_provider_ids():
    rows = [{"station": "VILD", "valid": "2025-12-02 05:00", "metar": "VILD 020500Z"}] * 2
    duplicates = find_duplicate_reports(rows)
    assert len(duplicates) == 1
    assert duplicates[0]["provider_report_id"] == "NOT_PROVIDED"


def test_missing_event_evidence_is_unavailable_through_phase08_policy():
    result = apply_phase08_policy({"lineage_classification": UNKNOWN, "is_imputed": None,
                                   "variable": "temperature"})
    assert result["outcome"] == "UNAVAILABLE"
    assert result["comparison_eligibility"] == "INELIGIBLE"


def test_phase08_shared_and_noncomparable_evidence_never_become_independent_votes():
    shared = apply_phase08_policy({"lineage_classification": SHARED,
                                   "variable": "temperature", "is_imputed": False})
    incomparable = apply_phase08_policy({"lineage_classification": NOT_COMPARABLE,
                                         "variable": "relative_humidity", "is_imputed": False})
    assert shared["outcome"] == "NOT_COMPARABLE"
    assert shared["comparison_eligibility"] == "SHARED_CONTEXT_ONLY"
    assert incomparable["outcome"] == "NOT_COMPARABLE"
    assert incomparable["comparison_eligibility"] == "INELIGIBLE"


def test_metar_humidity_is_derived_and_pressure_definition_is_not_pooled():
    rh_result = metar_variable_check("rhum", 100,
                                     "VILD 220400Z 00000KT 0200 FG VV/// 08/08 Q1020")
    pressure_result = metar_variable_check("pres", 993.8,
                                           "VILD 280900Z 09005KT 3000 BR 29/27 Q0997")
    assert rh_result[0] == "DERIVED_VALUE_COMPATIBLE_NOT_DIRECT_RH"
    assert "not direct RH" in rh_result[1]
    assert pressure_result[0] == "NOT_COMPARABLE_PRESSURE_DEFINITION"


def test_event_adjudication_status_and_label_pairing():
    valid = pd.DataFrame([{"event_id": "P10E01", "adjudication_status": "NOT_ADJUDICATED",
                           "adjudication_label": None, "rationale": "No independent evidence."}])
    assert validate_adjudication_register(valid).iloc[0].adjudication_status == "NOT_ADJUDICATED"
    bad = valid.copy()
    bad.loc[0, "adjudication_label"] = "NORMAL"
    with pytest.raises(ValueError):
        validate_adjudication_register(bad)


def test_manifest_hash_integrity(tmp_path):
    artifact = tmp_path / "raw.txt"
    artifact.write_bytes(b"original bytes\n")
    import hashlib
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    manifest = tmp_path / "SHA256SUMS.txt"
    manifest.write_text(f"{digest}  raw.txt\n", encoding="utf-8")
    assert verify_sha256_manifest(manifest, tmp_path)["valid"]
    artifact.write_bytes(b"changed\n")
    assert not verify_sha256_manifest(manifest, tmp_path)["valid"]

