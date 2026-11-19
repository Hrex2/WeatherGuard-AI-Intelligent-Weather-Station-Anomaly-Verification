"""Phase 11 source-record and event-linkage helpers.

This module classifies provenance and exact linkability; it does not create
weather observations, independent labels, or a second E3 evidence policy.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from weather_research.e3_evidence_policy import (
    CONTEXT, DERIVED, INDEPENDENT, NOT_COMPARABLE, SHARED, UNKNOWN,
    evaluate_evidence_record,
)


ADJUDICATION_STATUSES = {
    "ADJUDICATED_REGIONALLY_SUPPORTED",
    "ADJUDICATED_STATION_SPECIFIC_SUSPICIOUS",
    "NOT_ADJUDICATED", "INSUFFICIENT_EVIDENCE", "SOURCE_UNAVAILABLE",
}
LINEAGE_CLASSES = {INDEPENDENT, SHARED, DERIVED, CONTEXT, UNKNOWN, NOT_COMPARABLE}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record_fingerprint(source_station: str, valid_utc: str, raw_message: str) -> str:
    """Local duplicate fingerprint; never presented as an upstream record ID."""
    payload = "|".join((source_station.strip(), valid_utc.strip(), raw_message.strip()))
    return "P11FP-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def classify_record_origin(*, raw_message: str = "", provider_record_id: str = "",
                           provider: str = "") -> str:
    if raw_message.strip() and provider_record_id.strip():
        return "ORIGINAL_MESSAGE_WITH_PROVIDER_ID"
    if raw_message.strip() and provider.strip():
        return "ARCHIVED_RAW_MESSAGE_NO_PROVIDER_ID"
    if raw_message.strip():
        return "RAW_MESSAGE_UNKNOWN_LINEAGE"
    return "DERIVED_OR_HARMONIZED_RECORD"


def exact_candidate_link(candidate: Mapping[str, Any], reports: pd.DataFrame) -> dict[str, Any]:
    """Link only exact station+UTC timestamps; never use proximity as identity."""
    event_id = str(candidate["event_id"])
    station_label = str(candidate["primary_station"]).strip().upper()
    station = "VILD" if "ICAO-VILD" in station_label or station_label == "VILD0" else station_label.split("/")[0].strip()
    event_time = pd.Timestamp(candidate["timestamp_utc_reproduction"])
    if event_time.tzinfo is None:
        raise ValueError("candidate timestamp must be timezone-aware")
    if reports.empty:
        return {"event_id": event_id, "linkage_status": "UNAVAILABLE",
                "reason": "No report rows were returned for the requested source/time coverage.",
                "matching_report_count": 0, "temporal_offset_seconds": None,
                "link_rule": "EXACT_STATION_AND_UTC_TIMESTAMP_ONLY; no tolerance applied"}
    normalized = reports.copy()
    normalized["valid_utc_parsed"] = pd.to_datetime(normalized["valid"], utc=True, errors="coerce")
    normalized["station_upper"] = normalized["station"].astype(str).str.strip().str.upper()
    station_key = station
    matches = normalized[(normalized.station_upper == station_key) &
                         (normalized.valid_utc_parsed == event_time.tz_convert("UTC"))]
    if matches.empty:
        return {"event_id": event_id, "linkage_status": "UNAVAILABLE",
                "reason": "No exact station and UTC timestamp match; proximity is not used as report identity.",
                "matching_report_count": 0, "temporal_offset_seconds": None,
                "link_rule": "EXACT_STATION_AND_UTC_TIMESTAMP_ONLY; no tolerance applied"}
    row = matches.iloc[0]
    raw = str(row.get("metar", ""))
    report_station = raw.strip().split(maxsplit=1)[0].upper() if raw.strip() else ""
    report_time = re.search(r"\b(\d{2})(\d{2})(\d{2})Z\b", raw)
    valid_time = pd.Timestamp(row.valid_utc_parsed).tz_convert("UTC")
    if (report_station != station_key or report_time is None or
            (int(report_time.group(1)), int(report_time.group(2)), int(report_time.group(3))) !=
            (valid_time.day, valid_time.hour, valid_time.minute)):
        return {"event_id": event_id, "linkage_status": "UNAVAILABLE",
                "reason": "Archive valid time did not agree with the station/time group in the raw report message.",
                "matching_report_count": 0, "temporal_offset_seconds": None,
                "link_rule": "EXACT_STATION_AND_UTC_TIMESTAMP_PLUS_RAW_MESSAGE_TIME; no tolerance applied"}
    fp = record_fingerprint(station_key, str(row.valid), raw)
    return {"event_id": event_id, "linkage_status": "PROVISIONAL",
            "reason": "Exact archive station/time and raw report message match; archive copy has no provider-issued unique ID.",
            "matching_report_count": int(len(matches)), "source_station_id": station_key,
            "source_valid_timestamp": str(row.valid), "source_record_id": "NOT_PROVIDED",
            "report_fingerprint": fp, "raw_message": raw,
            "temporal_offset_seconds": 0, "link_rule": "EXACT_STATION_AND_UTC_TIMESTAMP_PLUS_RAW_MESSAGE_TIME; no tolerance applied",
            "record_origin": classify_record_origin(raw_message=raw, provider="Iowa State IEM archive"),
            "lineage_classification": UNKNOWN}


def find_duplicate_reports(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for row in records:
        fp = record_fingerprint(str(row.get("station", "")), str(row.get("valid", "")),
                                str(row.get("metar", "")))
        groups.setdefault(fp, []).append(row)
    return [{"report_fingerprint": fp, "duplicate_row_count": len(rows),
             "provider_report_id": "NOT_PROVIDED", "duplicate_status": "LOCAL_FINGERPRINT_ONLY"}
            for fp, rows in sorted(groups.items()) if len(rows) > 1]


def validate_adjudication_register(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"event_id", "adjudication_status", "adjudication_label", "rationale"}
    if required - set(frame.columns):
        raise ValueError(f"missing adjudication fields: {sorted(required - set(frame.columns))}")
    result = frame.copy(deep=True)
    if result.event_id.isna().any() or result.event_id.duplicated().any():
        raise ValueError("event IDs must be present and unique")
    invalid = set(result.adjudication_status.dropna().astype(str)) - ADJUDICATION_STATUSES
    if invalid:
        raise ValueError(f"invalid adjudication status: {sorted(invalid)}")
    adjudicated = result.adjudication_status.isin({
        "ADJUDICATED_REGIONALLY_SUPPORTED", "ADJUDICATED_STATION_SPECIFIC_SUSPICIOUS"})
    if (adjudicated & result.adjudication_label.isna()).any():
        raise ValueError("adjudicated labels require an explicit label")
    if ((~adjudicated) & result.adjudication_label.notna()).any():
        raise ValueError("non-adjudicated statuses cannot carry a truth label")
    return result


def apply_phase08_policy(record: Mapping[str, Any]) -> dict[str, Any]:
    """Delegate evidence eligibility to the unchanged Phase 08 implementation."""
    lineage = record.get("lineage_classification")
    if lineage not in LINEAGE_CLASSES:
        raise ValueError("unknown lineage must be explicit in the Phase 08 policy categories")
    return evaluate_evidence_record(record, tolerances={})


def verify_sha256_manifest(manifest_path: str | Path, root: str | Path) -> dict[str, Any]:
    manifest_path, root = Path(manifest_path), Path(root)
    missing, mismatched, checked = [], [], 0
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split("  ", 1)
        path = root / relative
        if not path.is_file():
            missing.append(relative)
            continue
        checked += 1
        if sha256_bytes(path.read_bytes()) != expected:
            mismatched.append(relative)
    return {"valid": not missing and not mismatched, "checked_files": checked,
            "missing_files": missing, "hash_mismatches": mismatched}
