"""Interpretable three-outcome evidence logic with explicit abstention."""
from __future__ import annotations

import pandas as pd


def classify_evidence(evidence: pd.DataFrame, min_supporting_stations=2):
    """Classify rows using explicit boolean evidence; unavailable is never disagreement.

    Expected columns: model_stable, temporal_coherent, spatial_status,
    supporting_stations, conflicting_stations, hard_physical_violation.
    This is rule-based scaffolding, not calibrated probability estimation.
    """
    if not isinstance(min_supporting_stations,int) or min_supporting_stations<1:
        raise ValueError("min_supporting_stations must be a positive integer")
    out=evidence.copy(deep=True)
    required_evidence=("model_stable","temporal_coherent","spatial_status",
                       "supporting_stations","conflicting_stations","hard_physical_violation")
    for col in required_evidence:
        if col not in out: out[col]=pd.NA
    out["spatial_evidence_available"] = out["spatial_status"].isin(["SUPPORTED","CONFLICTING"])
    out["evidence_complete"] = out[list(required_evidence)].notna().all(axis=1)
    out["evidence_available_count"] = (
        out["model_stable"].notna().astype(int)
        + out["temporal_coherent"].notna().astype(int)
        + out["spatial_evidence_available"].astype(int)
        + out["hard_physical_violation"].notna().astype(int)
    )
    model_candidate=out.get("model_stable",pd.Series(False,index=out.index)).fillna(False).astype(bool)
    temporal_candidate=out.get("temporal_coherent",pd.Series(False,index=out.index)).fillna(False).astype(bool)
    supporting=pd.to_numeric(out["supporting_stations"],errors="coerce")
    conflicting=pd.to_numeric(out["conflicting_stations"],errors="coerce")
    hard_violation=out["hard_physical_violation"].fillna(False).astype(bool)
    region = (out["evidence_complete"] & model_candidate & temporal_candidate
              & out["spatial_status"].eq("SUPPORTED")
              & supporting.ge(min_supporting_stations).fillna(False)
              & ~hard_violation
              & conflicting.eq(0).fillna(False))
    suspicious = (out["evidence_complete"] & model_candidate & hard_violation
                  & out["spatial_status"].eq("CONFLICTING")
                  & conflicting.gt(0).fillna(False))
    out["outcome"]="UNCERTAIN_INSUFFICIENT_EVIDENCE"
    out.loc[region,"outcome"]="REGIONALLY_SUPPORTED_UNUSUAL_EVENT"
    out.loc[suspicious,"outcome"]="STATION_SPECIFIC_SUSPICIOUS_OBSERVATION"
    out["reason"]="Evidence is missing, conflicting, or below the declared rule threshold."
    out.loc[region,"reason"]="Stable model evidence and a coherent event are supported by multiple observed neighbors; no hard physical violation flagged."
    out.loc[suspicious,"reason"]="A hard physical screening violation conflicts with observed neighbor evidence."
    out["supporting_evidence"]=""
    out["evidence_against"]=""
    out["missing_evidence"]=""
    out["conflicting_evidence"]=""
    out.loc[region,"supporting_evidence"]="model stability; temporal coherence; spatial support"
    out.loc[region,"evidence_against"]="none under the supplied rules"
    out.loc[suspicious,"supporting_evidence"]="model stability; physical screening violation"
    out.loc[suspicious,"conflicting_evidence"]="observed neighboring-station disagreement"
    for idx, row in out.iterrows():
        missing = [name for name in required_evidence if pd.isna(row[name])]
        if missing:
            out.at[idx,"missing_evidence"] = "; ".join(missing)
        conflicts = []
        if pd.notna(row["spatial_status"]) and row["spatial_status"] == "CONFLICTING":
            conflicts.append("spatial_status")
        if pd.notna(row["supporting_stations"]) and pd.notna(row["conflicting_stations"]):
            support_count = pd.to_numeric(pd.Series([row["supporting_stations"]]), errors="coerce").iloc[0]
            conflict_count = pd.to_numeric(pd.Series([row["conflicting_stations"]]), errors="coerce").iloc[0]
            if pd.notna(support_count) and pd.notna(conflict_count) and support_count > 0 and conflict_count > 0:
                conflicts.append("neighboring stations disagree")
        if conflicts and pd.isna(row["conflicting_evidence"]):
            out.at[idx,"conflicting_evidence"] = "; ".join(conflicts)
    out["uncertainty_description"]="Rule-based outcome; no calibrated probability or confidence score."
    return out
