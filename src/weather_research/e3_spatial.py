"""Configurable, provenance-gated utilities for the exploratory E3 study.

These functions do not assign an E3 verdict. A source is eligible as
independent corroboration only when provenance explicitly identifies it as a
verified direct observation; unknown and model-filled records are excluded.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DistanceZone:
    name: str
    lower_km: float
    upper_km: float | None


DEFAULT_ZONES = (
    DistanceZone("A", 0.0, 10.0),
    DistanceZone("B", 10.0, 50.0),
    DistanceZone("C", 50.0, 100.0),
    DistanceZone("D", 100.0, 250.0),
    DistanceZone("E", 250.0, None),
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km for finite decimal-degree coordinates."""
    values = (lat1, lon1, lat2, lon2)
    if any(pd.isna(value) for value in values):
        raise ValueError("coordinates must be finite numbers")
    if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90):
        raise ValueError("latitude must be between -90 and 90 degrees")
    if not (-180 <= lon1 <= 180 and -180 <= lon2 <= 180):
        raise ValueError("longitude must be between -180 and 180 degrees")
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 6371.0088 * 2 * asin(sqrt(a))


def assign_distance_zone(distance_km: float, zones=DEFAULT_ZONES) -> str:
    """Assign a provisional configurable zone; bounds are [lower, upper)."""
    if pd.isna(distance_km) or distance_km < 0:
        raise ValueError("distance_km must be a non-negative number")
    ordered = sorted(zones, key=lambda zone: zone.lower_km)
    for zone in ordered:
        if distance_km >= zone.lower_km and (
            zone.upper_km is None or distance_km < zone.upper_km
        ):
            return zone.name
    raise ValueError("distance is not covered by configured zones")


def nearest_timestamp_pairs(primary: pd.Series, neighbor: pd.Series,
                            tolerance_minutes: int) -> pd.DataFrame:
    """Maximum-cardinality chronological 1:1 pairs within tolerance.

    Values are retained as raw measurements, but this utility makes no
    provenance claim and does not itself establish independent corroboration.
    If several neighbor times qualify, the earliest compatible pair is matched
    first. This deterministic interval-matching rule avoids row reuse and
    maximizes pair count; it is not a minimum-total-time-offset optimizer.
    """
    if tolerance_minutes < 0:
        raise ValueError("tolerance_minutes must be non-negative")
    if not isinstance(primary.index, pd.DatetimeIndex) or not isinstance(neighbor.index, pd.DatetimeIndex):
        raise TypeError("both inputs require DatetimeIndex")
    # Normalize the pandas datetime resolution as well as the timezone. CSV
    # readers can produce seconds/microseconds while in-memory indexes use ns.
    primary = primary.copy()
    neighbor = neighbor.copy()
    if primary.index.tz is not None:
        primary.index = primary.index.tz_convert("UTC").as_unit("ns")
    else:
        primary.index = primary.index.as_unit("ns")
    if neighbor.index.tz is not None:
        neighbor.index = neighbor.index.tz_convert("UTC").as_unit("ns")
    else:
        neighbor.index = neighbor.index.as_unit("ns")
    if (primary.index.tz is None) != (neighbor.index.tz is None):
        raise ValueError("cannot align timezone-aware and timezone-naive indexes")
    if primary.index.tz != neighbor.index.tz:
        neighbor.index = neighbor.index.tz_convert(primary.index.tz)
    p = pd.DataFrame({"primary_time": primary.index, "primary_value": primary.to_numpy()}).dropna(subset=["primary_value"])
    n = pd.DataFrame({"neighbor_time": neighbor.index, "neighbor_value": neighbor.to_numpy()}).dropna(subset=["neighbor_value"])
    p, n = p.sort_values("primary_time").reset_index(drop=True), n.sort_values("neighbor_time").reset_index(drop=True)
    if p.primary_time.duplicated().any() or n.neighbor_time.duplicated().any():
        raise ValueError("timestamp indexes must be unique for one-to-one matching")

    p_ns = pd.DatetimeIndex(p.primary_time).asi8
    n_ns = pd.DatetimeIndex(n.neighbor_time).asi8
    tol_ns = int(pd.Timedelta(minutes=tolerance_minutes).value)
    selected = {}
    p_idx = n_idx = 0
    while p_idx < len(p_ns) and n_idx < len(n_ns):
        offset = int(n_ns[n_idx]) - int(p_ns[p_idx])
        if abs(offset) <= tol_ns:
            selected[p_idx] = n_idx
            p_idx += 1
            n_idx += 1
        elif offset < -tol_ns:
            n_idx += 1
        else:
            p_idx += 1

    out = p.copy()
    out["neighbor_time"] = pd.Series(pd.NaT, index=out.index, dtype=p.primary_time.dtype)
    out["neighbor_value"] = np.nan
    for p_idx, n_idx in selected.items():
        out.loc[p_idx, "neighbor_time"] = n.loc[n_idx, "neighbor_time"]
        out.loc[p_idx, "neighbor_value"] = n.loc[n_idx, "neighbor_value"]
    out["offset_minutes"] = (out.neighbor_time - out.primary_time).dt.total_seconds() / 60
    out["match_type"] = "NO_MATCH"
    matched = out.neighbor_time.notna()
    out.loc[matched & out.offset_minutes.eq(0), "match_type"] = "EXACT"
    out.loc[matched & out.offset_minutes.ne(0), "match_type"] = "TOLERANCE_MATCH"
    out["difference_neighbor_minus_primary"] = out.neighbor_value - out.primary_value
    return out


def provenance_eligible(provenance: pd.Series) -> pd.Series:
    """Only an explicit verified direct-observation label is eligible."""
    return provenance.fillna("").astype(str).str.strip().str.lower().eq("verified_direct_observation")


def evaluate_spatial_evidence(stations: list[dict], tolerance: float | None,
                              min_independent_support: int = 2) -> dict:
    """Summarize auditable, variable-specific station evidence without weights.

    Each record requires station_id, zone, matched, primary_value,
    neighbor_value, offset_minutes, provenance_status, independence_status,
    and quality_status. Independent evidence requires explicit direct-observation
    provenance and verified independent source lineage. A missing tolerance
    prevents agreement classification; no tolerance is inferred from the data.
    """
    if min_independent_support < 1:
        raise ValueError("min_independent_support must be positive")
    station_results = []
    for record in stations:
        item = dict(record)
        zone = str(item.get("zone", ""))
        if zone not in {"A", "B", "C", "D", "E"}:
            item.update(status="UNAVAILABLE", reason="UNVERIFIED_OR_UNASSIGNED_ZONE")
        elif not item.get("matched", False):
            status = "TEMPORALLY_MISMATCHED" if item.get("candidate_available", False) else "UNAVAILABLE"
            item.update(status=status, reason="NO_VALID_TIME_MATCH")
        elif item.get("quality_status") != "VALID":
            item.update(status="UNAVAILABLE", reason="OBSERVATION_QUALITY_NOT_VERIFIED")
        elif (str(item.get("provenance_status", "")).upper() != "VERIFIED_DIRECT_OBSERVATION"
              or str(item.get("independence_status", "")).upper() != "VERIFIED_INDEPENDENT"):
            item.update(status="UNAVAILABLE", reason="SOURCE_LINEAGE_OR_INDEPENDENCE_UNVERIFIED")
        elif tolerance is None:
            item.update(status="UNAVAILABLE", reason="VARIABLE_TOLERANCE_NOT_PREREGISTERED")
        else:
            difference = float(item["neighbor_value"]) - float(item["primary_value"])
            item["difference_neighbor_minus_primary"] = difference
            support = abs(difference) <= tolerance
            if zone in {"A", "B"}:
                item.update(status="SUPPORTS_LOCAL_EVENT" if support else "CONFLICTS_WITH_LOCAL_EVENT",
                            reason="WITHIN_PREREGISTERED_TOLERANCE" if support else "OUTSIDE_PREREGISTERED_TOLERANCE")
            elif zone in {"C", "D"}:
                item.update(status="REGIONAL_SUPPORT" if support else "CONFLICTS_WITH_LOCAL_EVENT",
                            reason="WITHIN_PREREGISTERED_TOLERANCE" if support else "OUTSIDE_PREREGISTERED_TOLERANCE")
            else:
                item.update(status="WIDER_CONTEXT_SUPPORT" if support else "CONFLICTS_WITH_LOCAL_EVENT",
                            reason="WITHIN_PREREGISTERED_TOLERANCE" if support else "OUTSIDE_PREREGISTERED_TOLERANCE")
        station_results.append(item)

    available = [row for row in station_results if row["status"] in {
        "SUPPORTS_LOCAL_EVENT", "REGIONAL_SUPPORT", "WIDER_CONTEXT_SUPPORT", "CONFLICTS_WITH_LOCAL_EVENT"
    }]
    supports = [row for row in available if row["status"] in {
        "SUPPORTS_LOCAL_EVENT", "REGIONAL_SUPPORT", "WIDER_CONTEXT_SUPPORT"
    }]
    conflicts = [row for row in available if row["status"] == "CONFLICTS_WITH_LOCAL_EVENT"]
    local_conflicts = [row for row in conflicts if row.get("zone") in {"A", "B"}]
    if not available:
        if any(row["status"] == "TEMPORALLY_MISMATCHED" for row in station_results):
            overall_status = "TEMPORALLY_MISMATCHED"
        elif any(row["status"] == "UNAVAILABLE" for row in station_results):
            overall_status = "UNAVAILABLE"
        else:
            overall_status = "INSUFFICIENT_COVERAGE"
        outcome = "INSUFFICIENT_OR_UNCERTAIN_EVIDENCE"
    elif supports and conflicts:
        overall_status = "MIXED_SPATIAL_EVIDENCE"
        outcome = "INSUFFICIENT_OR_UNCERTAIN_EVIDENCE"
    elif conflicts:
        overall_status = "CONFLICTS_WITH_LOCAL_EVENT"
        outcome = ("STATION_SPECIFIC_SUSPICIOUS_OBSERVATION" if local_conflicts
                   else "INSUFFICIENT_OR_UNCERTAIN_EVIDENCE")
    elif len(supports) >= min_independent_support:
        overall_status = "SUPPORTS_LOCAL_EVENT" if any(x["status"] == "SUPPORTS_LOCAL_EVENT" for x in supports) else "REGIONAL_SUPPORT"
        outcome = "REGIONALLY_SUPPORTED_EVENT"
    else:
        overall_status = next((x["status"] for x in supports), "INSUFFICIENT_COVERAGE")
        outcome = "INSUFFICIENT_OR_UNCERTAIN_EVIDENCE"
    return {"status": overall_status, "research_outcome": outcome,
            "supporting_station_count": len(supports), "conflicting_station_count": len(conflicts),
            "station_results": station_results,
            "interpretation":"Unweighted station evidence; requires explicit direct provenance, independent lineage, valid quality and a preregistered variable tolerance. These outcomes are not ground truth or sensor-fault diagnoses."}
