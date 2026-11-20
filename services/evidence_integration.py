"""Conservative orchestration for WeatherGuard's saved E1–E4 evidence.

This module reports evidence without creating a validated combined classifier.
The baseline remains the saved Phase 03 prediction grid; no model is refit here.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from services.temporal_service import temporal_verification
from weather_research.quality import physical_quality_flags

COMPONENT_IDS = ("E1", "E2", "E3", "E4")
EXECUTION_STATUSES = {
    "AVAILABLE", "UNAVAILABLE", "DESCRIPTIVE_ONLY", "INSUFFICIENT_DATA",
    "ERROR", "NOT_APPLICABLE",
}
EVIDENCE_RESULTS = {
    "SUPPORTING_EVIDENCE", "NO_DETECTED_EVIDENCE", "CONFLICTING_EVIDENCE",
    "DESCRIPTIVE_ONLY", "UNAVAILABLE", "NOT_APPLICABLE",
}
ASSESSMENTS = {"NORMAL", "SUSPICIOUS", "ANOMALOUS", "INSUFFICIENT_EVIDENCE"}

COMPONENT_NAMES = {
    "E1": "Model stability",
    "E2": "Temporal consistency",
    "E3": "Spatial corroboration",
    "E4": "Physical plausibility",
}


def _iso(timestamp) -> str:
    return pd.Timestamp(timestamp).isoformat()


def component_record(component_id: str, execution_status: str, evidence_result: str,
                     evidence_label: str, explanation: str, timestamp,
                     source: dict[str, Any], limitations: list[str],
                     decision_eligible: bool = False,
                     details: Any = None) -> dict[str, Any]:
    """Create the common component contract; reliability is deliberately null."""
    record = {
        "component_id": component_id,
        "component_name": COMPONENT_NAMES[component_id],
        "execution_status": execution_status,
        "evidence_result": evidence_result,
        "evidence_label": evidence_label,
        "explanation": explanation,
        "timestamp": _iso(timestamp),
        "source": source,
        "reliability": None,
        "limitations": list(limitations),
        "decision_eligible": bool(decision_eligible),
    }
    if details is not None:
        record["details"] = details
    return record


def validate_component_record(record: Any, expected_id: str | None = None) -> None:
    required = {
        "component_id", "component_name", "execution_status", "evidence_result",
        "evidence_label", "explanation", "timestamp", "source", "reliability",
        "limitations", "decision_eligible",
    }
    if not isinstance(record, dict) or not required.issubset(record):
        raise ValueError("component output is not a complete evidence record")
    if record["component_id"] not in COMPONENT_IDS or (expected_id and record["component_id"] != expected_id):
        raise ValueError("component output has an invalid component ID")
    if record["execution_status"] not in EXECUTION_STATUSES:
        raise ValueError("component output has an invalid execution status")
    if record["evidence_result"] not in EVIDENCE_RESULTS:
        raise ValueError("component output has an invalid evidence result")
    compatible_results = {
        "AVAILABLE": {"SUPPORTING_EVIDENCE", "NO_DETECTED_EVIDENCE", "CONFLICTING_EVIDENCE"},
        "DESCRIPTIVE_ONLY": {"DESCRIPTIVE_ONLY"},
        "UNAVAILABLE": {"UNAVAILABLE"}, "INSUFFICIENT_DATA": {"UNAVAILABLE"},
        "ERROR": {"UNAVAILABLE"}, "NOT_APPLICABLE": {"NOT_APPLICABLE"},
    }
    if record["evidence_result"] not in compatible_results[record["execution_status"]]:
        raise ValueError("component execution status and evidence result are inconsistent")
    if not isinstance(record["source"], dict) or not isinstance(record["limitations"], list):
        raise ValueError("component source and limitations must use the common schema")
    if not isinstance(record["decision_eligible"], bool):
        raise ValueError("decision_eligible must be boolean")
    if record["component_id"] == "E3" and record["decision_eligible"]:
        raise ValueError("E3 is decision-ineligible until independent validation requirements are met")


def load_spatial_tables(root: str | Path) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Load existing exploratory comparisons without asserting provenance."""
    tables: dict[str, pd.DataFrame] = {}
    sources: list[str] = []
    folder = Path(root) / "phase03_model_revalidation"
    for station in ("42099", "42101"):
        path = folder / f"spatial_comparison_{station}.csv"
        if not path.is_file():
            continue
        try:
            table = pd.read_csv(path, parse_dates=["candidate_time", "station_time"])
        except (OSError, ValueError, KeyError, pd.errors.ParserError):
            continue
        tables[station] = table
        sources.append(path.relative_to(Path(root)).as_posix())
    return tables, sources


def _normalize_time(timestamp, index: pd.DatetimeIndex) -> pd.Timestamp:
    ts = pd.Timestamp(timestamp)
    if index.tz is not None:
        return ts.tz_localize(index.tz) if ts.tzinfo is None else ts.tz_convert(index.tz)
    return ts.tz_localize(None) if ts.tzinfo is not None else ts


def _e1(timestamp, station_id, observations, predictions, stability, **_):
    ts = _normalize_time(timestamp, observations.index)
    if station_id != "VILD0":
        return component_record("E1", "NOT_APPLICABLE", "NOT_APPLICABLE", "Primary station only",
            "The saved baseline prediction grid covers VILD0; no baseline output is available for this neighboring station record.", ts,
            {"artifact": "phase03_model_revalidation/model_predictions.csv", "station_id": station_id},
            ["Neighbor records are contextual and are not baseline-model outputs."])
    rows = predictions.loc[predictions.timestamp.eq(ts)].copy()
    if rows.empty or "is_candidate" not in rows:
        return component_record("E1", "INSUFFICIENT_DATA", "UNAVAILABLE", "Saved prediction unavailable",
            "No saved model predictions exist for this timestamp.", ts,
            {"artifact": "phase03_model_revalidation/model_predictions.csv"},
            ["No model is refit by the evidence integration view."])
    votes = int(rows.is_candidate.astype(bool).sum())
    available = int(len(rows))
    stability_rows = stability.loc[stability.timestamp.eq(ts)] if "timestamp" in stability else pd.DataFrame()
    consistency_note = ""
    if len(stability_rows) and "configuration_votes" in stability_rows:
        saved_votes = int(stability_rows.iloc[0].configuration_votes)
        consistency_note = f" Saved stability artifact reports {saved_votes} votes."
    if available != 12:
        return component_record("E1", "INSUFFICIENT_DATA", "UNAVAILABLE", f"{votes}/{available} configurations available",
            "The existing 8/12 screen requires the complete saved 12-configuration result grid." + consistency_note, ts,
            {"artifact": "phase03_model_revalidation/model_predictions.csv", "configurations": available, "votes": votes},
            ["Configuration agreement is not probability, event truth, or a sensor-fault diagnosis."],
            details=rows[[c for c in ("configuration", "family", "is_candidate", "anomaly_score") if c in rows]].to_dict("records"))
    result = "SUPPORTING_EVIDENCE" if votes >= 8 else "NO_DETECTED_EVIDENCE"
    label = f"E1 candidate · {votes}/12" if votes >= 8 else f"Below existing 8/12 screen · {votes}/12"
    return component_record("E1", "AVAILABLE", result, label,
        (f"{votes} of 12 saved configurations flagged this reading; the established 8/12 screen "
         + ("is met." if votes >= 8 else "is not met.")) + consistency_note,
        ts, {"artifact": "phase03_model_revalidation/model_predictions.csv", "configurations": 12, "votes": votes},
        ["This is saved historical output, not a new model fit.",
         "Agreement is not a probability and does not confirm an anomalous weather event or faulty sensor."],
        decision_eligible=True,
        details=rows[[c for c in ("configuration", "family", "is_candidate", "anomaly_score") if c in rows]].to_dict("records"))


def _e2(timestamp, station_id, observations, primary_variable="temp", **_):
    ts = _normalize_time(timestamp, observations.index)
    if station_id != "VILD0":
        return component_record("E2", "NOT_APPLICABLE", "NOT_APPLICABLE", "Primary station only",
            "The temporal screen uses the verified processed VILD0 series; it is not run on neighbor source exports.", ts,
            {"implementation": "services/temporal_service.py", "station_id": station_id},
            ["Neighbor source series have separate and unresolved lineage constraints."])
    if primary_variable not in observations.columns:
        return component_record("E2", "INSUFFICIENT_DATA", "UNAVAILABLE", "Variable unavailable",
            f"The selected variable {primary_variable!r} is not present in the observation series.", ts,
            {"implementation": "services/temporal_service.py"},
            ["Screening thresholds are exploratory and are not calibrated fault rules."])
    result = temporal_verification(observations, ts, primary_variable, mode="real_time")
    raw_status = result["status"]
    if raw_status == "UNAVAILABLE":
        status, evidence = "INSUFFICIENT_DATA", "UNAVAILABLE"
    else:
        status = "AVAILABLE"
        evidence = {"SUPPORTING": "SUPPORTING_EVIDENCE", "NO_DETECTED_EVIDENCE": "NO_DETECTED_EVIDENCE",
                    "CONFLICTING": "CONFLICTING_EVIDENCE"}.get(raw_status, "UNAVAILABLE")
    return component_record("E2", status, evidence, raw_status.replace("_", " ").title(), result["reason"], ts,
        {"implementation": "services/temporal_service.py", "mode": result.get("mode"), "variable": primary_variable},
        ["Real-time mode uses prior observations only.", "Temporal flags do not establish regional weather or diagnose hardware.",
         "The screening defaults are not validated fault thresholds."], details=result)


def _e3(timestamp, station_id, observations, spatial_tables=None, spatial_sources=None, **_):
    ts = _normalize_time(timestamp, observations.index)
    if station_id != "VILD0":
        return component_record("E3", "NOT_APPLICABLE", "NOT_APPLICABLE", "Primary station comparison only",
            "Available spatial comparison artifacts describe neighboring records relative to primary VILD0 candidates.", ts,
            {"artifacts": spatial_sources or []}, ["The selected neighbor record is not an independently adjudicated event reference."])
    matches = []
    for neighbor, table in (spatial_tables or {}).items():
        if table is None or not len(table) or "candidate_time" not in table:
            continue
        candidate_times = pd.to_datetime(table.candidate_time, utc=True, errors="coerce")
        ts_utc = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        found = table.loc[candidate_times.eq(ts_utc)].copy()
        if len(found):
            found["neighbor_station_id"] = str(neighbor)
            matches.append(found)
    if not matches:
        return component_record("E3", "INSUFFICIENT_DATA", "UNAVAILABLE", "Independent spatial evidence unavailable",
            "No spatial comparison record indexed to this selected candidate timestamp is available; the project has not established independent station provenance or event adjudication.", ts,
            {"artifacts": spatial_sources or [], "independent_observations_verified": False,
             "exact_neighbor_timestamp_alignment_verified": False},
            ["Phase 09 evidence was descriptive only.", "Phases 10–11 found insufficient independent data for validation.",
             "Missing spatial evidence is not evidence of normal regional conditions."],
            details=[])
    frame = pd.concat(matches, ignore_index=True)
    rows = frame.where(pd.notna(frame), None).to_dict("records")
    return component_record("E3", "DESCRIPTIVE_ONLY", "DESCRIPTIVE_ONLY", "Exploratory comparison · decision-ineligible",
        f"{len(frame)} saved comparison row(s) indexed to this candidate timestamp are shown descriptively. Recorded neighbor time offsets may be nonzero; these rows cannot establish corroboration, contradiction, or independent event truth.", ts,
        {"artifacts": spatial_sources or [], "independent_observations_verified": False,
         "exact_neighbor_timestamp_alignment_verified": False},
        ["Phase 09 status: DESCRIPTIVE_ONLY.", "Phases 10 and 11: INSUFFICIENT_INDEPENDENT_DATA.",
         "Sensor/operator provenance and independent event adjudication are unresolved."],
        decision_eligible=False, details=rows)


def _e4(timestamp, station_id, observations, **_):
    ts = _normalize_time(timestamp, observations.index)
    if station_id != "VILD0":
        return component_record("E4", "NOT_APPLICABLE", "NOT_APPLICABLE", "Primary station only",
            "The processed physical screen is defined for the VILD0 observation series, not for separate neighbor exports.", ts,
            {"implementation": "weather_research.quality.physical_quality_flags", "station_id": station_id},
            ["Broad screening ranges are not sensor calibration limits or fault labels."])
    if ts not in observations.index:
        return component_record("E4", "INSUFFICIENT_DATA", "UNAVAILABLE", "Observation unavailable",
            "No processed primary-station observation is available at this timestamp.", ts,
            {"implementation": "weather_research.quality.physical_quality_flags"},
            ["Missing data are not treated as normal evidence or a fault diagnosis."])
    row = observations.loc[[ts]]
    flags = physical_quality_flags(row)
    missing_only = bool(len(flags) and flags.missing.any() and not flags.loc[flags.screening_flag & ~flags.missing].shape[0])
    if missing_only or flags.empty:
        status, evidence, label = "INSUFFICIENT_DATA", "UNAVAILABLE", "Physical screen unavailable for missing inputs"
        explanation = "Required measured values are missing or no supported variables are available for broad physical screening."
    else:
        violations = flags.loc[flags.screening_flag & ~flags.missing]
        status = "AVAILABLE"
        evidence = "SUPPORTING_EVIDENCE" if len(violations) else "NO_DETECTED_EVIDENCE"
        label = f"{len(violations)} broad screening flag(s)" if len(violations) else "No broad screening flag detected"
        explanation = (f"{len(violations)} non-missing value(s) triggered broad range or consistency screening."
                       if len(violations) else "No broad range or cross-variable screening violation was detected for available values.")
    return component_record("E4", status, evidence, label, explanation, ts,
        {"implementation": "weather_research.quality.physical_quality_flags", "rule_set": "DEFAULT_SCREENING_BOUNDS"},
        ["A broad screening flag is not a sensor-fault diagnosis.", "Missing values are reported separately and never interpreted as normal."],
        details=flags.where(pd.notna(flags), None).to_dict("records"))


def _error_record(component_id: str, timestamp, error: Exception | str) -> dict[str, Any]:
    error_text = f"{type(error).__name__}: {error}"
    return component_record(component_id, "ERROR", "UNAVAILABLE", "Component execution error",
        error_text, timestamp, {"implementation": "component adapter"},
        ["This component failed; its absence is not normal evidence."])


def integrate_evidence(baseline_prediction: dict[str, Any],
                       component_outputs: dict[str, Any], timestamp) -> dict[str, Any]:
    """Validate component records and produce an explicitly non-classifier summary."""
    components: dict[str, dict[str, Any]] = {}
    for component_id in COMPONENT_IDS:
        output = component_outputs.get(component_id)
        try:
            validate_component_record(output, component_id)
            components[component_id] = deepcopy(output)
        except (ValueError, TypeError, KeyError) as exc:
            components[component_id] = _error_record(component_id, timestamp, exc)

    baseline = deepcopy(baseline_prediction)
    baseline_votes = baseline.get("configuration_votes")
    baseline_available = baseline.get("execution_status") == "AVAILABLE"
    candidate = bool(baseline_available and baseline.get("candidate_8_of_12") is True)
    if candidate:
        category = "SUSPICIOUS"
        reason = ("The unchanged saved baseline meets its existing 8/12 E1 candidate screen. "
                  "This is a review signal only; no validated integrated classifier confirms an anomalous event or sensor fault.")
    else:
        category = "INSUFFICIENT_EVIDENCE"
        if baseline_available:
            reason = ("The saved baseline does not meet the existing 8/12 E1 candidate screen. "
                      "Because independent E3 validation and an integrated decision rule are unavailable, the reading is not labeled normal.")
        else:
            reason = "No saved baseline prediction is available for this station and timestamp; the system cannot make an integrated assessment."

    supporting = [cid for cid, item in components.items() if item["evidence_result"] == "SUPPORTING_EVIDENCE"]
    conflicting = [cid for cid, item in components.items() if item["evidence_result"] == "CONFLICTING_EVIDENCE"]
    restricted = [cid for cid, item in components.items() if item["execution_status"] == "DESCRIPTIVE_ONLY"]
    unavailable = [cid for cid, item in components.items()
                   if item["execution_status"] in {"UNAVAILABLE", "INSUFFICIENT_DATA", "ERROR", "NOT_APPLICABLE"}]
    return {
        "timestamp": _iso(timestamp),
        "station_id": baseline.get("station_id", "VILD0"),
        "baseline_prediction": baseline,
        "components": components,
        "integrated_assessment": {
            "category": category,
            "is_validated_combined_classifier": False,
            "reason": reason,
            "supporting_evidence": supporting,
            "contradictory_evidence": conflicting,
            "restricted_descriptive_evidence": restricted,
            "unavailable_evidence": unavailable,
        },
        "research_boundary": "ANOMALY ≠ FAULT. E3 is never decision-eligible; missing evidence is not normal evidence.",
    }


def run_integrated_assessment(timestamp, station_id: str, observations: pd.DataFrame,
                              predictions: pd.DataFrame, stability: pd.DataFrame,
                              episodes: pd.DataFrame, spatial_tables: dict[str, pd.DataFrame] | None = None,
                              spatial_sources: list[str] | None = None, primary_variable: str = "temp",
                              component_adapters: dict[str, Callable] | None = None) -> dict[str, Any]:
    """Run the four evidence adapters against an exact saved observation."""
    ts = _normalize_time(timestamp, observations.index)
    adapters = component_adapters or {"E1": _e1, "E2": _e2, "E3": _e3, "E4": _e4}
    context = {
        "timestamp": ts, "station_id": station_id, "observations": observations,
        "predictions": predictions, "stability": stability, "episodes": episodes,
        "spatial_tables": spatial_tables or {}, "spatial_sources": spatial_sources or [],
        "primary_variable": primary_variable,
    }
    component_outputs = {}
    for component_id in COMPONENT_IDS:
        try:
            adapter = adapters[component_id]
            component_outputs[component_id] = adapter(**context)
        except Exception as exc:  # component failures remain visible and isolated
            component_outputs[component_id] = _error_record(component_id, ts, exc)

    baseline_rows = (predictions.loc[predictions.timestamp.eq(ts)].copy()
                     if station_id == "VILD0" and "timestamp" in predictions else pd.DataFrame())
    votes = int(baseline_rows.is_candidate.astype(bool).sum()) if len(baseline_rows) and "is_candidate" in baseline_rows else None
    available = int(len(baseline_rows))
    baseline = {
        "execution_status": "AVAILABLE" if available == 12 else "INSUFFICIENT_DATA" if available else "NOT_APPLICABLE" if station_id != "VILD0" else "UNAVAILABLE",
        "station_id": station_id,
        "source": "saved Phase 03 predictions; no new model fit",
        "configuration_votes": votes,
        "configuration_count": available,
        "candidate_8_of_12": bool(votes is not None and available == 12 and votes >= 8),
        "model_rows": baseline_rows[[c for c in ("configuration", "family", "is_candidate", "anomaly_score") if c in baseline_rows]].to_dict("records"),
    }
    return integrate_evidence(baseline, component_outputs, ts)
