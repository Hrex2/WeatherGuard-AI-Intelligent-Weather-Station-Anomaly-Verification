"""Pure descriptive calculations for Phase 12 evidence contribution analysis.

These helpers do not alter the integration policy or infer event/fault truth.
"""
from __future__ import annotations

from collections.abc import Iterable
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


PHASE12_CONFIGURATIONS = {
    "P0": ("Baseline only", ()),
    "P1": ("Baseline + E1", ("E1",)),
    "P2": ("Baseline + E2", ("E2",)),
    "P3": ("Baseline + E4", ("E4",)),
    "P4": ("Baseline + E1 + E2 + E4", ("E1", "E2", "E4")),
    "P5": ("Full architecture + descriptive E3", ("E1", "E2", "E3", "E4")),
    "P6": ("E1 + E2 + E4 without E3", ("E1", "E2", "E4")),
}


def binary_contingency(left: Iterable[bool], right: Iterable[bool]) -> dict:
    """Return descriptive binary agreement; undefined indices stay null."""
    a = np.asarray(list(left), dtype=bool)
    b = np.asarray(list(right), dtype=bool)
    if a.size != b.size:
        raise ValueError("paired indicators must have equal length")
    n11 = int(np.sum(a & b))
    n10 = int(np.sum(a & ~b))
    n01 = int(np.sum(~a & b))
    n00 = int(np.sum(~a & ~b))
    union = n11 + n10 + n01
    agreement = (n11 + n00) / a.size if a.size else None
    phi_denominator = np.sqrt((n11+n10)*(n01+n00)*(n11+n01)*(n10+n00))
    phi = ((n11*n00 - n10*n01) / phi_denominator) if phi_denominator else None
    return {
        "n": int(a.size), "both_positive": n11, "left_only": n10,
        "right_only": n01, "both_negative": n00,
        "agreement_pct": 100 * agreement if agreement is not None else None,
        "jaccard_positive": n11 / union if union else None,
        "phi": phi,
        "interpretation_limit": "Descriptive association only; not causal, calibrated, or predictive validation.",
    }


def evidence_profile(statuses: dict[str, str], results: dict[str, str], included: Iterable[str]) -> dict:
    """Summarize status-separated evidence without treating absence as negative."""
    included = tuple(included)
    available = [cid for cid in included if statuses.get(cid) == "AVAILABLE"]
    supporting = [cid for cid in available if results.get(cid) == "SUPPORTING_EVIDENCE"]
    conflicting = [cid for cid in available if results.get(cid) == "CONFLICTING_EVIDENCE"]
    missing = [cid for cid in included if statuses.get(cid) in {
        "UNAVAILABLE", "INSUFFICIENT_DATA", "ERROR", "NOT_APPLICABLE"
    }]
    descriptive = [cid for cid in included if statuses.get(cid) == "DESCRIPTIVE_ONLY"]
    return {
        "included_components": "+".join(included) if included else "none",
        "available_component_count": len(available),
        "supporting_evidence_count": len(supporting),
        "contradictory_evidence_count": len(conflicting),
        "missing_evidence_count": len(missing),
        "descriptive_only_count": len(descriptive),
        "supporting_components": "+".join(supporting),
        "contradictory_components": "+".join(conflicting),
        "missing_components": "+".join(missing),
        "descriptive_components": "+".join(descriptive),
    }


def timestamp_offset_minutes(candidate_time, station_time) -> float | None:
    """Signed neighbor-minus-candidate offset, preserving exact-match distinction."""
    if pd.isna(candidate_time) or pd.isna(station_time):
        return None
    candidate = pd.Timestamp(candidate_time)
    station = pd.Timestamp(station_time)
    if candidate.tzinfo is None and station.tzinfo is not None:
        candidate = candidate.tz_localize(station.tzinfo)
    elif station.tzinfo is None and candidate.tzinfo is not None:
        station = station.tz_localize(candidate.tzinfo)
    else:
        station = station.tz_convert(candidate.tzinfo) if candidate.tzinfo is not None else station
    return (station - candidate).total_seconds() / 60


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
