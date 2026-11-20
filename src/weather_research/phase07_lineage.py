"""Conservative lineage and event-reference utilities for Phase 07."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd


LINEAGE_CLASSES = {
    "INDEPENDENT_OBSERVING_SYSTEM",
    "POSSIBLY_SHARED_SOURCE",
    "DERIVED_FROM_SAME_REPORT",
    "UNKNOWN_LINEAGE",
    "NOT_COMPARABLE",
}


def _present(value: Any) -> bool:
    return value is not None and not pd.isna(value) and str(value).strip() != ""


def classify_lineage_pair(left: Mapping[str, Any], right: Mapping[str, Any]) -> str:
    """Classify a source pair from explicit provenance evidence only.

    Different provider labels, station IDs, or value agreement alone never
    establish independence. Callers must supply verified report/site evidence.
    """
    if left.get("context_only") or right.get("context_only"):
        return "NOT_COMPARABLE"

    left_report = left.get("verified_original_report_id")
    right_report = right.get("verified_original_report_id")
    if (_present(left_report) and _present(right_report)
            and str(left_report) == str(right_report)
            and left.get("report_identity_verified") is True
            and right.get("report_identity_verified") is True):
        return "DERIVED_FROM_SAME_REPORT"

    if left.get("shared_source_evidence") is True or right.get("shared_source_evidence") is True:
        return "POSSIBLY_SHARED_SOURCE"

    left_site, right_site = left.get("verified_physical_site_id"), right.get("verified_physical_site_id")
    left_source, right_source = left.get("verified_original_station_id"), right.get("verified_original_station_id")
    left_type, right_type = left.get("verified_report_type"), right.get("verified_report_type")
    complete = all(_present(v) for v in (left_site, right_site, left_source, right_source, left_type, right_type))
    independent_reports = (left.get("distinct_original_reports_verified") is True
                           and right.get("distinct_original_reports_verified") is True)
    if (complete and independent_reports and str(left_site) != str(right_site)
            and str(left_source) != str(right_source)
            and str(left_type) != str(right_type)):
        return "INDEPENDENT_OBSERVING_SYSTEM"

    if (left.get("same_verified_physical_site") is True
            and _present(left_source) and str(left_source) == str(right_source)
            and _present(left_type) and str(left_type) == str(right_type)):
        return "POSSIBLY_SHARED_SOURCE"

    return "UNKNOWN_LINEAGE"


def match_event_observation(event_time: Any, observations: pd.DataFrame,
                            tolerance_minutes: int, *,
                            time_column: str = "timestamp",
                            value_column: str = "value") -> dict[str, Any]:
    """Find one nearest source row without converting a missing value to conflict."""
    if tolerance_minutes < 0:
        raise ValueError("tolerance_minutes must be non-negative")
    event = pd.Timestamp(event_time)
    if event.tzinfo is None:
        raise ValueError("event_time must be timezone-aware")
    event = event.tz_convert("UTC")
    if time_column not in observations.columns:
        raise KeyError(time_column)
    if observations.empty:
        return {"match_status": "NO_REFERENCE_ROWS", "matched_time": None,
                "offset_minutes": None, "value": None}
    frame = observations.copy()
    frame[time_column] = pd.to_datetime(frame[time_column], utc=True, errors="coerce")
    frame = frame.dropna(subset=[time_column])
    if frame.empty:
        return {"match_status": "NO_REFERENCE_ROWS", "matched_time": None,
                "offset_minutes": None, "value": None}
    frame["_offset_minutes"] = (frame[time_column] - event).dt.total_seconds().abs() / 60
    row = frame.sort_values(["_offset_minutes", time_column], kind="stable").iloc[0]
    offset = float((row[time_column] - event).total_seconds() / 60)
    if abs(offset) > tolerance_minutes:
        return {"match_status": "NO_MATCH_WITHIN_TOLERANCE", "matched_time": None,
                "offset_minutes": None, "value": None}
    value = row.get(value_column)
    if not _present(value):
        status = "MISSING_REFERENCE_VALUE"
        value = None
    else:
        status = "EXACT_MATCH" if offset == 0 else "TOLERANCE_MATCH"
    return {"match_status": status, "matched_time": row[time_column].isoformat(),
            "offset_minutes": offset, "value": value,
            "source_row": row.drop(labels=["_offset_minutes"]).to_dict()}


def compare_event_value(candidate_value: Any, reference_value: Any, *,
                        units_comparable: bool, lineage_class: str,
                        match_status: str) -> dict[str, Any]:
    """Return a descriptive difference, never a support/conflict verdict."""
    if lineage_class not in LINEAGE_CLASSES:
        raise ValueError(f"unknown lineage class: {lineage_class}")
    if match_status in {"NO_REFERENCE_ROWS", "NO_MATCH_WITHIN_TOLERANCE"}:
        return {"comparison_status": "REFERENCE_UNAVAILABLE", "difference": None,
                "evidence_role": "MISSING_NOT_DISAGREEMENT"}
    if match_status == "MISSING_REFERENCE_VALUE" or not _present(reference_value):
        return {"comparison_status": "REFERENCE_VALUE_MISSING", "difference": None,
                "evidence_role": "MISSING_NOT_DISAGREEMENT"}
    if not _present(candidate_value):
        return {"comparison_status": "CANDIDATE_VALUE_MISSING", "difference": None,
                "evidence_role": "REFERENCE_ONLY_CONTEXT"}
    if not units_comparable or lineage_class == "NOT_COMPARABLE":
        return {"comparison_status": "NOT_COMPARABLE", "difference": None,
                "evidence_role": "CONTEXT_ONLY"}
    return {"comparison_status": "DESCRIPTIVE_DIFFERENCE_NO_PREREGISTERED_TOLERANCE",
            "difference": float(reference_value) - float(candidate_value),
            "evidence_role": ("INDEPENDENT_REPORT_LEVEL_REFERENCE" if lineage_class == "INDEPENDENT_OBSERVING_SYSTEM"
                              else "SHARED_OR_UNKNOWN_LINEAGE_CONTEXT")}
