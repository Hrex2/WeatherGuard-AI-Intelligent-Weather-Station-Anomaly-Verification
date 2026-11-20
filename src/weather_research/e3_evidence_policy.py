"""Conservative research policy for E3 spatial evidence.

This module is deliberately isolated from ``classify_evidence``. It classifies
the eligibility and descriptive role of individual records; it does not infer
sensor faults, assign confidence scores, or establish empirical E3 validity.
"""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

import pandas as pd

from .e3_spatial import assign_distance_zone


INDEPENDENT = "INDEPENDENT_REPORT_EVIDENCE"
SHARED = "POSSIBLY_SHARED_EVIDENCE"
DERIVED = "DERIVED_SAME_OBSERVATION"
CONTEXT = "CONTEXT_ONLY"
UNKNOWN = "UNKNOWN_LINEAGE"
NOT_COMPARABLE = "NOT_COMPARABLE"

LINEAGE_CLASSES = {INDEPENDENT, SHARED, DERIVED, CONTEXT, UNKNOWN, NOT_COMPARABLE}
OUTCOMES = {
    "SUPPORTS_LOCAL_EVENT", "CONFLICTS_WITH_LOCAL_EVENT", "REGIONAL_SUPPORT",
    "REGIONAL_DISAGREEMENT_CONTEXT", "WIDER_CONTEXT_SUPPORT",
    "WIDER_CONTEXT_CONTRADICTION", "MIXED_SPATIAL_EVIDENCE",
    "INSUFFICIENT_COVERAGE", "TEMPORALLY_MISMATCHED", "UNAVAILABLE",
    "NOT_COMPARABLE",
}
TIME_TOLERANCES_MIN = {0, 15, 30, 60}

# Canonical units for policy comparisons. Conversion is explicit and does not
# supply an agreement tolerance; tolerances must be provided by the experiment.
CANONICAL_UNITS = {
    "temperature": "degC", "dewpoint": "degC", "relative_humidity": "%",
    "precipitation": "mm", "wind_speed": "m/s", "wind_direction": "degree",
    "pressure": "hPa",
}


def classify_lineage(record: Mapping[str, Any]) -> str:
    """Derive a conservative record class from documented evidence fields."""
    if record.get("context_only") is True:
        return CONTEXT
    if record.get("same_observation_verified") is True:
        return DERIVED
    if record.get("shared_source_evidence") is True:
        return SHARED
    site_ids = (record.get("primary_physical_site_id"), record.get("physical_site_id"))
    report_ids = (record.get("primary_report_id"), record.get("original_report_id"))
    systems = (record.get("primary_report_system"), record.get("report_system"))
    if (record.get("physical_sites_distinct_verified") is True
            and record.get("report_systems_distinct_verified") is True
            and all(_present(x) for x in (*site_ids, *report_ids, *systems))
            and str(site_ids[0]) != str(site_ids[1])
            and str(report_ids[0]) != str(report_ids[1])
            and str(systems[0]) != str(systems[1])):
        return INDEPENDENT
    if record.get("lineage_classification") == NOT_COMPARABLE:
        return NOT_COMPARABLE
    return UNKNOWN


def _present(value: Any) -> bool:
    if value is None:
        return False
    try:
        return bool(pd.notna(value)) and str(value).strip() != ""
    except (TypeError, ValueError):
        return False


def _convert_value(variable: str, value: Any, unit: Any) -> tuple[float | None, str | None]:
    if variable not in CANONICAL_UNITS or not _present(value) or not _present(unit):
        return None, None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None, None
    if not isfinite(number):
        return None, None
    raw = str(unit).strip().lower().replace("°", "deg").replace(" ", "")
    if variable in {"temperature", "dewpoint"}:
        if raw in {"c", "degc", "celsius"}:
            return number, "degC"
        if raw in {"f", "degf", "fahrenheit"}:
            return (number - 32.0) * 5.0 / 9.0, "degC"
    elif variable == "relative_humidity":
        if raw in {"%", "percent", "%rh", "percentrh"}:
            return number, "%"
        if raw in {"fraction", "1"}:
            return number * 100.0, "%"
    elif variable == "precipitation":
        if raw in {"mm", "millimeter", "millimeters"}:
            return number, "mm"
        if raw in {"cm", "centimeter", "centimeters"}:
            return number * 10.0, "mm"
        if raw in {"in", "inch", "inches"}:
            return number * 25.4, "mm"
    elif variable == "wind_speed":
        if raw in {"m/s", "ms-1", "mps"}:
            return number, "m/s"
        if raw in {"km/h", "kmh", "kph"}:
            return number / 3.6, "m/s"
        if raw in {"kt", "kts", "knot", "knots"}:
            return number * 0.5144444444444445, "m/s"
    elif variable == "wind_direction":
        if raw in {"degree", "degrees", "deg"}:
            return number % 360.0, "degree"
    elif variable == "pressure":
        if raw in {"hpa", "mbar", "millibar"}:
            return number, "hPa"
        if raw in {"pa", "pascal", "pascals"}:
            return number / 100.0, "hPa"
    return None, None


def _circular_difference(a: float, b: float) -> float:
    """Smallest absolute angular distance in degrees."""
    delta = abs((a - b) % 360.0)
    return min(delta, 360.0 - delta)


def _result(record: Mapping[str, Any], *, lineage: str, eligibility: str,
            outcome: str, reason: str, offset: float | None = None,
            distance: float | None = None, difference: float | None = None,
            primary_value: float | None = None, reference_value: float | None = None,
            match_type: str | None = None) -> dict[str, Any]:
    return {
        "source_id": record.get("source_id"), "station_id": record.get("station_id"),
        "original_report_id": record.get("original_report_id"),
        "variable": record.get("variable"), "lineage_classification": lineage,
        "comparison_eligibility": eligibility, "comparison_reason": reason,
        "evidence_role": ("INDEPENDENT_REPORT" if lineage == INDEPENDENT else
                          "SHARED_OR_DERIVED" if lineage in {SHARED, DERIVED} else
                          "CONTEXT" if lineage == CONTEXT else "UNKNOWN_OR_EXCLUDED"),
        "outcome": outcome, "timestamp_offset_minutes_reference_minus_candidate": offset,
        "time_match_type": match_type, "distance_km": distance,
        "distance_zone": assign_distance_zone(distance) if distance is not None else None,
        "qc_status": record.get("qc_status"),
        "is_imputed": record.get("is_imputed"),
        "primary_value_canonical": primary_value,
        "reference_value_canonical": reference_value,
        "difference_reference_minus_primary": difference,
        "unit": CANONICAL_UNITS.get(str(record.get("variable"))),
    }


def evaluate_evidence_record(record: Mapping[str, Any], *,
                             tolerances: Mapping[str, float] | None = None,
                             tolerance_minutes: int = 0) -> dict[str, Any]:
    """Evaluate one candidate/reference record without assigning fault.

    ``tolerances`` are experiment-supplied, provisional absolute differences in
    canonical units. No default numerical agreement threshold is provided.
    Precipitation mismatches remain non-comparable by default because nearby
    rainfall is spatially intermittent; a preregistered event-window protocol
    is required before interpreting occurrence differences.
    """
    tolerances = tolerances or {}
    lineage = str(record.get("lineage_classification", UNKNOWN)).upper()
    if record.get("lineage_evidence_supplied") is True:
        lineage = classify_lineage(record)
    if lineage not in LINEAGE_CLASSES:
        lineage = UNKNOWN
    dist = record.get("distance_km")
    try:
        distance = float(dist) if _present(dist) else None
    except (TypeError, ValueError):
        distance = None
    if distance is not None and not isfinite(distance):
        distance = None

    if lineage in {SHARED, DERIVED}:
        return _result(record, lineage=lineage, eligibility="SHARED_CONTEXT_ONLY",
                       outcome=NOT_COMPARABLE,
                       reason="SHARED_OR_DERIVED_OBSERVATION_CANNOT_ADD_AN_INDEPENDENT_VOTE",
                       distance=distance)
    if bool(record.get("duplicate_or_reused_observation", False)):
        return _result(record, lineage=DERIVED, eligibility="SHARED_CONTEXT_ONLY",
                       outcome=NOT_COMPARABLE,
                       reason="DUPLICATE_OR_REUSED_OBSERVATION_CANNOT_ADD_AN_INDEPENDENT_VOTE",
                       distance=distance)
    if lineage == UNKNOWN:
        return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                       outcome="UNAVAILABLE", reason="ORIGINAL_LINEAGE_UNKNOWN",
                       distance=distance)
    if lineage == NOT_COMPARABLE:
        return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                       outcome=NOT_COMPARABLE, reason="SOURCE_PAIR_DECLARED_NOT_COMPARABLE",
                       distance=distance)
    if record.get("is_imputed") is not False:
        return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                       outcome=NOT_COMPARABLE, reason="IMPUTED_OR_IMPUTATION_STATUS_UNVERIFIED",
                       distance=distance)

    variable = str(record.get("variable", ""))
    if variable not in CANONICAL_UNITS:
        return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                       outcome=NOT_COMPARABLE, reason="VARIABLE_NOT_SUPPORTED",
                       distance=distance)
    primary, p_unit = _convert_value(variable, record.get("primary_value"), record.get("primary_unit"))
    reference, r_unit = _convert_value(variable, record.get("reference_value"), record.get("reference_unit"))
    if primary is None or reference is None or p_unit != r_unit:
        return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                       outcome=("UNAVAILABLE" if not _present(record.get("primary_value"))
                                or not _present(record.get("reference_value")) else NOT_COMPARABLE),
                       reason=("MISSING_OBSERVATION_VALUE" if not _present(record.get("primary_value"))
                               or not _present(record.get("reference_value")) else "UNITS_INCOMPATIBLE"),
                       distance=distance)

    if str(record.get("qc_status", "")).upper() not in {"GOOD", "VALID", "PASS"}:
        return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                       outcome=NOT_COMPARABLE, reason="QC_NOT_PASSING_OR_NOT_DOCUMENTED",
                       distance=distance, primary_value=primary, reference_value=reference)

    try:
        candidate_time = pd.Timestamp(record.get("candidate_timestamp"))
        reference_time = pd.Timestamp(record.get("reference_timestamp"))
        if candidate_time.tzinfo is None or reference_time.tzinfo is None:
            raise ValueError
        offset = (reference_time.tz_convert("UTC") - candidate_time.tz_convert("UTC")).total_seconds() / 60
    except (TypeError, ValueError):
        return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                       outcome="UNAVAILABLE", reason="TIMESTAMP_MISSING_OR_TIMEZONE_NAIVE",
                       distance=distance, primary_value=primary, reference_value=reference)
    if tolerance_minutes not in TIME_TOLERANCES_MIN:
        return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                       outcome=NOT_COMPARABLE, reason="TIME_TOLERANCE_NOT_IN_PREREGISTERED_SET",
                       offset=offset, distance=distance, primary_value=primary,
                       reference_value=reference)
    if abs(offset) > tolerance_minutes:
        return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                       outcome="TEMPORALLY_MISMATCHED", reason="OUTSIDE_CONFIGURED_TIME_TOLERANCE",
                       offset=offset, distance=distance, primary_value=primary,
                       reference_value=reference)
    match_type = "EXACT" if offset == 0 else "TOLERANCE_MATCH"

    if lineage == INDEPENDENT:
        required = ("primary_station_id", "station_id", "primary_physical_site_id",
                    "physical_site_id", "primary_report_id",
                    "original_report_id", "primary_report_system", "report_system",
                    "station_identity_verified", "primary_station_identity_verified",
                    "coordinates_verified", "physical_sites_distinct_verified",
                    "report_systems_distinct_verified")
        if any(not _present(record.get(field)) for field in required):
            return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                           outcome="UNAVAILABLE", reason="REPORT_OR_STATION_METADATA_INCOMPLETE",
                           offset=offset, distance=distance, primary_value=primary,
                           reference_value=reference, match_type=match_type)
        if (str(record["primary_station_id"]) == str(record["station_id"])
                or str(record["primary_physical_site_id"]) == str(record["physical_site_id"])
                or str(record["primary_report_id"]) == str(record["original_report_id"])
                or str(record["primary_report_system"]) == str(record["report_system"])):
            return _result(record, lineage=SHARED, eligibility="SHARED_CONTEXT_ONLY",
                           outcome=NOT_COMPARABLE,
                           reason="DISTINCT_REPORT_SYSTEM_NOT_ESTABLISHED",
                           offset=offset, distance=distance, primary_value=primary,
                           reference_value=reference, match_type=match_type)
        if (record.get("station_identity_verified") is not True
                or record.get("primary_station_identity_verified") is not True
                or record.get("coordinates_verified") is not True
                or record.get("physical_sites_distinct_verified") is not True
                or record.get("report_systems_distinct_verified") is not True):
            return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                           outcome="UNAVAILABLE", reason="STATION_IDENTITY_OR_COORDINATES_UNVERIFIED",
                           offset=offset, distance=distance, primary_value=primary,
                           reference_value=reference, match_type=match_type)
        if distance is None:
            return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                           outcome="UNAVAILABLE", reason="VERIFIED_GEOGRAPHIC_REFERENCE_MISSING",
                           offset=offset, primary_value=primary, reference_value=reference,
                           match_type=match_type)
    elif lineage == CONTEXT:
        if variable == "precipitation":
            return _result(record, lineage=lineage, eligibility="CONTEXT_ONLY",
                           outcome=NOT_COMPARABLE,
                           reason="PRECIPITATION_CONTEXT_REQUIRES_PREREGISTERED_INTERVAL_PROTOCOL",
                           offset=offset, distance=distance, primary_value=primary,
                           reference_value=reference, match_type=match_type)
        try:
            context_tolerance = float(tolerances[variable])
            valid_context_tolerance = isfinite(context_tolerance) and context_tolerance >= 0
        except (KeyError, TypeError, ValueError):
            context_tolerance, valid_context_tolerance = float("nan"), False
        if not valid_context_tolerance:
            return _result(record, lineage=lineage, eligibility="CONTEXT_ONLY",
                           outcome="NOT_COMPARABLE", reason="VARIABLE_TOLERANCE_NOT_CONFIGURED",
                           offset=offset, distance=distance, primary_value=primary,
                           reference_value=reference, match_type=match_type)
        diff = (abs((reference - primary + 180) % 360 - 180) if variable == "wind_direction"
                else abs(reference - primary))
        result_outcome = "WIDER_CONTEXT_SUPPORT" if diff <= context_tolerance else "WIDER_CONTEXT_CONTRADICTION"
        return _result(record, lineage=lineage, eligibility="CONTEXT_ONLY",
                       outcome=result_outcome, reason="CONTEXT_IS_NOT_STATION_CORROBORATION",
                       offset=offset, distance=distance, primary_value=primary,
                       reference_value=reference,
                       difference=(reference - primary), match_type=match_type)

    if variable == "precipitation":
        interval_fields = ("primary_interval_start", "primary_interval_end",
                           "reference_interval_start", "reference_interval_end")
        if (not _present(record.get("precipitation_protocol_id"))
                or any(not _present(record.get(field)) for field in interval_fields)
                or record.get("primary_interval_start") != record.get("reference_interval_start")
                or record.get("primary_interval_end") != record.get("reference_interval_end")):
            return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                           outcome=NOT_COMPARABLE,
                           reason="PRECIPITATION_REQUIRES_PREREGISTERED_MATCHED_ACCUMULATION_PROTOCOL",
                           offset=offset, distance=distance, primary_value=primary,
                           reference_value=reference, match_type=match_type)
        wet_threshold = record.get("precipitation_occurrence_threshold_mm")
        try:
            valid_wet_threshold = _present(wet_threshold) and isfinite(float(wet_threshold)) and float(wet_threshold) >= 0
        except (TypeError, ValueError):
            valid_wet_threshold = False
        if not valid_wet_threshold or primary < 0 or reference < 0:
            return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                           outcome=NOT_COMPARABLE, reason="PRECIPITATION_VALUE_OR_OCCURRENCE_THRESHOLD_INVALID",
                           offset=offset, distance=distance, primary_value=primary,
                           reference_value=reference, match_type=match_type)
        p_wet, r_wet = primary >= float(wet_threshold), reference >= float(wet_threshold)
        if p_wet != r_wet:
            return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                           outcome=NOT_COMPARABLE,
                           reason="SPATIALLY_INTERMITTENT_PRECIPITATION_DIFFERENCE_NOT_A_STATION_CONFLICT",
                           offset=offset, distance=distance, primary_value=primary,
                           reference_value=reference, match_type=match_type)
        diff = reference - primary
        zone = assign_distance_zone(distance)
        outcome = ("SUPPORTS_LOCAL_EVENT" if p_wet and zone in {"A", "B"} else
                   "REGIONAL_SUPPORT" if p_wet and zone in {"C", "D"} else
                   "WIDER_CONTEXT_SUPPORT" if p_wet else "INSUFFICIENT_COVERAGE")
        return _result(record, lineage=lineage, eligibility="ELIGIBLE_REPORT_LEVEL",
                       outcome=outcome, reason="MATCHED_INTERVAL_OCCURRENCE_ONLY_AMOUNT_IS_NOT_EVENT_TRUTH",
                       offset=offset, distance=distance, primary_value=primary,
                       reference_value=reference, difference=diff, match_type=match_type)

    try:
        tolerance = float(tolerances[variable])
        valid_tolerance = isfinite(tolerance) and tolerance >= 0
    except (KeyError, TypeError, ValueError):
        tolerance, valid_tolerance = float("nan"), False
    if not valid_tolerance:
        return _result(record, lineage=lineage, eligibility="INELIGIBLE",
                       outcome=NOT_COMPARABLE, reason="VARIABLE_TOLERANCE_NOT_CONFIGURED_OR_INVALID",
                       offset=offset, distance=distance, primary_value=primary,
                       reference_value=reference, match_type=match_type)
    difference = (reference - primary if variable != "wind_direction"
                  else _circular_difference(reference, primary))
    magnitude = abs(difference)
    zone = assign_distance_zone(distance)
    agrees = magnitude <= tolerance
    if zone in {"A", "B"}:
        outcome = "SUPPORTS_LOCAL_EVENT" if agrees else "CONFLICTS_WITH_LOCAL_EVENT"
    elif zone in {"C", "D"}:
        outcome = "REGIONAL_SUPPORT" if agrees else "REGIONAL_DISAGREEMENT_CONTEXT"
    else:
        outcome = "WIDER_CONTEXT_SUPPORT" if agrees else "WIDER_CONTEXT_CONTRADICTION"
    return _result(record, lineage=lineage, eligibility="ELIGIBLE_REPORT_LEVEL",
                   outcome=outcome,
                   reason="PROVISIONAL_CONFIGURED_TOLERANCE_COMPARISON_NOT_A_FAULT_LABEL",
                   offset=offset, distance=distance, difference=difference,
                   primary_value=primary, reference_value=reference, match_type=match_type)


def aggregate_variable_outcomes(results: list[Mapping[str, Any]], *,
                                variable: str | None = None) -> dict[str, Any]:
    """Aggregate eligible report/context outcomes without weights or votes."""
    rows = [dict(row) for row in results if variable is None or row.get("variable") == variable]
    if not rows:
        return {"outcome": "INSUFFICIENT_COVERAGE", "eligible_independent_rows": 0,
                "reason": "NO_REFERENCE_RECORDS"}
    eligible = [row for row in rows if row.get("comparison_eligibility") == "ELIGIBLE_REPORT_LEVEL"]
    support = any(row.get("outcome") in {"SUPPORTS_LOCAL_EVENT", "REGIONAL_SUPPORT"}
                  for row in eligible)
    conflict = any(row.get("outcome") in {
        "CONFLICTS_WITH_LOCAL_EVENT", "REGIONAL_DISAGREEMENT_CONTEXT"} for row in eligible)
    if support and conflict:
        outcome = "MIXED_SPATIAL_EVIDENCE"
    elif support:
        outcome = "SUPPORTS_LOCAL_EVENT"
    elif conflict:
        outcome = "CONFLICTS_WITH_LOCAL_EVENT"
    elif any(row.get("outcome") == "REGIONAL_SUPPORT" for row in eligible):
        outcome = "REGIONAL_SUPPORT"
    elif any(row.get("outcome") == "REGIONAL_DISAGREEMENT_CONTEXT" for row in eligible):
        outcome = "REGIONAL_DISAGREEMENT_CONTEXT"
    elif any(row.get("outcome") == "WIDER_CONTEXT_SUPPORT" for row in rows):
        outcome = "WIDER_CONTEXT_SUPPORT"
    elif any(row.get("outcome") == "WIDER_CONTEXT_CONTRADICTION" for row in rows):
        outcome = "WIDER_CONTEXT_CONTRADICTION"
    elif any(row.get("outcome") == "TEMPORALLY_MISMATCHED" for row in rows):
        outcome = "TEMPORALLY_MISMATCHED"
    elif any(row.get("outcome") == "UNAVAILABLE" for row in rows):
        outcome = "UNAVAILABLE"
    else:
        outcome = "NOT_COMPARABLE"
    return {"outcome": outcome, "eligible_independent_rows": len(eligible),
            "reason": "PER_VARIABLE_UNWEIGHTED_SUMMARY; NO_SENSOR_FAULT_INFERENCE"}


def evaluate_readiness_gates(gates: Mapping[str, str]) -> dict[str, Any]:
    """Validate required readiness gate states and derive a conservative decision."""
    required = {"provenance", "geographic", "temporal", "measurement",
                "event_validation", "reproducibility"}
    if set(gates) != required:
        raise ValueError(f"readiness gates must be exactly {sorted(required)}")
    allowed = {"PASS", "PARTIAL", "FAIL", "NOT_ASSESSED"}
    if any(value not in allowed for value in gates.values()):
        raise ValueError("readiness values must be PASS, PARTIAL, FAIL, or NOT_ASSESSED")
    if gates["provenance"] == "FAIL":
        decision = "BLOCKED_BY_DATA_PROVENANCE"
    elif gates["geographic"] == "FAIL":
        decision = "BLOCKED_BY_METADATA"
    elif gates["event_validation"] == "FAIL" and gates["measurement"] == "FAIL":
        decision = "BLOCKED_BY_VALIDATION_DESIGN"
    elif all(value == "PASS" for value in gates.values()):
        decision = "READY_FOR_CONTROLLED_VALIDATION"
    else:
        decision = "PARTIALLY_READY"
    return {"gates": dict(gates), "decision": decision,
            "software_tests_are_not_readiness_evidence": True}
