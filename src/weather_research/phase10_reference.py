"""Provenance and event-reference helpers for Phase 10."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from weather_research.e3_evidence_policy import (
    CONTEXT, DERIVED, INDEPENDENT, NOT_COMPARABLE, SHARED, UNKNOWN,
    evaluate_evidence_record,
)
from weather_research.phase09_validation import select_phase03_events


LINEAGE_CLASSES = {INDEPENDENT, SHARED, DERIVED, CONTEXT, UNKNOWN, NOT_COMPARABLE}
ADJUDICATION_STATUS = {
    "REGIONALLY_SUPPORTED_EVENT", "LOCALIZED_EVENT",
    "STATION_SPECIFIC_SUSPICIOUS_OBSERVATION", "INCONCLUSIVE",
    "INSUFFICIENT_REFERENCE_DATA", "NOT_ADJUDICATED",
}
SUFFICIENCY_STATES = {"PASS", "PARTIAL", "FAIL", "NOT_ASSESSED"}
MISSING_SENTINELS = {"-9999", "-9999.0", "-9999.00"}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def report_payload_fingerprint(station_id: str, timestamp_raw: str,
                               report_payload_raw: str | None) -> str:
    """Stable report-payload fingerprint; never a provider-issued report ID."""
    payload = "" if report_payload_raw is None else str(report_payload_raw)
    return "RPF-" + _digest("|".join((str(station_id), str(timestamp_raw), payload)))[:32]


def observation_fingerprint(station_id: str, timestamp_raw: str, variable: str,
                            value_raw: str, unit: str) -> str:
    """Fingerprint for exact product-copy checks, not a scientific tolerance."""
    return "OBSFP-" + _digest("|".join((str(station_id), str(timestamp_raw),
                                         str(variable), str(value_raw), str(unit))))[:32]


def classify_raw_value(value: Any) -> tuple[str, float | None]:
    """Retain blank/sentinel distinctions while exposing a safe numeric parse."""
    raw = "" if value is None else str(value)
    token = raw.strip()
    if not token:
        return "BLANK_MISSING", None
    if token in MISSING_SENTINELS:
        return "PROVIDER_MISSING_SENTINEL", None
    try:
        parsed = float(token)
    except (TypeError, ValueError):
        return "NONNUMERIC_RETAINED", None
    return "PRESENT", parsed


def find_shared_observation_groups(records: Iterable[Mapping[str, Any]], *,
                                   fingerprint_field: str = "shared_observation_id",
                                   source_field: str = "source_id") -> list[dict[str, Any]]:
    """Report fingerprints appearing in multiple products as one underlying record."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in records:
        fingerprint = str(row.get(fingerprint_field) or "")
        if fingerprint:
            groups.setdefault(fingerprint, []).append(dict(row))
    output = []
    for fingerprint, rows in sorted(groups.items()):
        sources = sorted({str(row.get(source_field) or "") for row in rows})
        if len(sources) > 1:
            output.append({"shared_observation_id": fingerprint,
                           "source_ids": sources,
                           "source_record_count": len(rows),
                           "underlying_observation_count": 1,
                           "independent_vote_count": 0,
                           "lineage_classification": SHARED})
    return output


def validate_adjudication_register(events: pd.DataFrame) -> pd.DataFrame:
    """Validate event reference labels without manufacturing adjudication."""
    required = {"event_id", "adjudication_status", "adjudication_label",
                "reviewer_or_method", "evidence_considered", "rationale"}
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"adjudication register missing columns: {sorted(missing)}")
    result = events.copy(deep=True)
    if result.event_id.isna().any() or result.event_id.duplicated().any():
        raise ValueError("event IDs must be present and unique")
    invalid = set(result.adjudication_status.dropna().astype(str)) - ADJUDICATION_STATUS
    if invalid:
        raise ValueError(f"invalid adjudication status: {sorted(invalid)}")
    adjudicated = result.adjudication_status.ne("NOT_ADJUDICATED")
    if (adjudicated & result.adjudication_label.isna()).any():
        raise ValueError("adjudicated events require a reference label")
    if ((~adjudicated) & result.adjudication_label.notna()).any():
        raise ValueError("NOT_ADJUDICATED events cannot carry a label")
    if (adjudicated & result.reviewer_or_method.fillna("").astype(str).str.strip().eq("")).any():
        raise ValueError("adjudicated events require a reviewer or documented method")
    return result


def validate_sufficiency_assessment(assessment: Mapping[str, Any]) -> dict[str, Any]:
    required = {"provenance", "geographic", "temporal", "measurement", "event", "adjudication"}
    if set(assessment) != required:
        raise ValueError(f"sufficiency dimensions must be exactly {sorted(required)}")
    invalid = {key: value for key, value in assessment.items() if value not in SUFFICIENCY_STATES}
    if invalid:
        raise ValueError(f"invalid sufficiency states: {invalid}")
    return dict(assessment)


def deterministic_event_registry(candidates: pd.DataFrame,
                                 prior_phase09_events: pd.DataFrame) -> pd.DataFrame:
    """Recreate the eight Phase 09 extrema selections and verify their signature."""
    selected = select_phase03_events(candidates)
    signature = set(zip(selected.event_type, selected.candidate_timestamp_utc.astype(str)))
    prior = set(zip(prior_phase09_events.event_type,
                    pd.to_datetime(prior_phase09_events.candidate_timestamp_utc,
                                   utc=True).astype(str)))
    if signature != prior:
        raise ValueError("Phase 10 event selection differs from the preserved Phase 09 signature")
    selected.insert(0, "event_id", [f"P10E{i:02d}" for i in range(1, len(selected) + 1)])
    selected["adjudication_status"] = "NOT_ADJUDICATED"
    selected["adjudication_label"] = None
    return selected


def apply_phase08_policy(record: Mapping[str, Any], *,
                         tolerances: Mapping[str, float] | None = None,
                         tolerance_minutes: int = 0) -> dict[str, Any]:
    """Single compatibility entry point that delegates to Phase 08 unchanged."""
    if record.get("lineage_classification") not in LINEAGE_CLASSES:
        raise ValueError("record must use one of the Phase 08 lineage classes")
    return evaluate_evidence_record(record, tolerances=tolerances or {},
                                    tolerance_minutes=tolerance_minutes)


def verify_phase10_manifest(manifest_path: str | Path, root: str | Path) -> dict[str, Any]:
    manifest_path, root = Path(manifest_path), Path(root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checked, missing, mismatched = 0, [], []
    for group in ("input_files", "generated_artifacts"):
        entries = manifest.get(group, {})
        for relative, item in entries.items():
            path = root / relative
            if not path.is_file():
                missing.append(relative)
                continue
            checked += 1
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != item.get("sha256"):
                mismatched.append(relative)
    return {"valid": not missing and not mismatched, "checked_files": checked,
            "missing_files": missing, "hash_mismatches": mismatched}
