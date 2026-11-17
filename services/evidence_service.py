"""Read-only view helpers for saved model, episode, spatial, and QC evidence."""
from __future__ import annotations

import pandas as pd

from weather_research.quality import physical_quality_flags
from services.temporal_service import temporal_verification


def observation_evidence(timestamp, observations, predictions, stability, episodes,
                         spatial_tables, primary_variable=None):
    """Assemble available evidence for one timestamp without fabricating a verdict."""
    ts = pd.Timestamp(timestamp)
    model_rows = predictions.loc[predictions.timestamp.eq(ts)].copy()
    stability_rows = stability.loc[stability.timestamp.eq(ts)]
    vote_count = int(model_rows.is_candidate.astype(bool).sum()) if len(model_rows) else None
    episode_rows = episodes.loc[(episodes.start <= ts) & (episodes.end >= ts)]
    row = observations.loc[[ts]] if ts in observations.index else observations.iloc[0:0]
    quality = physical_quality_flags(row) if len(row) else pd.DataFrame()
    if primary_variable not in observations.columns:
        primary_variable = "temp" if "temp" in observations.columns else next(
            (name for name in ("dwpt", "rhum", "prcp", "wspd", "pres") if name in observations.columns), None)
    temporal = (temporal_verification(observations, ts, primary_variable, mode="real_time")
                if primary_variable else {"status": "UNAVAILABLE", "reason": "No supported weather variable is available."})
    spatial_rows = []
    for station, table in spatial_tables.items():
        if table is not None and len(table) and "candidate_time" in table:
            match = table.loc[pd.to_datetime(table.candidate_time, utc=True).dt.tz_convert(str(ts.tz)).eq(ts)]
            if len(match):
                spatial_rows.append(match.assign(station_id=station))
    spatial = pd.concat(spatial_rows, ignore_index=True) if spatial_rows else pd.DataFrame()
    physical_violations = quality.loc[
        quality.screening_flag & ~quality.missing
    ] if len(quality) else quality
    has_missing_only = bool(len(quality) and quality.missing.any() and not len(physical_violations))
    states = {
        "E1": "UNAVAILABLE" if vote_count is None else (
            "SUPPORTING_EVIDENCE" if vote_count >= 8 else "NO_DETECTED_EVIDENCE"),
        # Independently calculated from measured series; episodes are ignored.
        "E2": temporal["status"],
        "E3": "UNAVAILABLE" if not len(spatial) else "NO_DETECTED_EVIDENCE",
        "E4": "UNAVAILABLE" if not len(quality) or has_missing_only else (
            "SUPPORTING_EVIDENCE" if len(physical_violations) else "NO_DETECTED_EVIDENCE"),
    }
    # The spatial comparisons are exploratory, with no preregistered residual
    # threshold or demonstrated independent provider provenance. Preserve their
    # values for display, but do not use them to assert support or conflict.
    if len(spatial):
        states["E3"] = "UNAVAILABLE"
    evidence_available_count = sum(state != "UNAVAILABLE" for state in states.values())
    return {
        "timestamp": ts,
        "model_rows": model_rows,
        "vote_count": vote_count,
        "stability_row": stability_rows.iloc[0] if len(stability_rows) else None,
        "episodes": episode_rows,
        "quality_flags": quality,
        "temporal_result": temporal,
        "missing_quality_values": int(quality.missing.sum()) if len(quality) else None,
        "physical_screening_violations": physical_violations,
        "spatial_rows": spatial,
        "evidence_states": states,
        "evidence_available_count": evidence_available_count,
        "evidence_complete": evidence_available_count == len(states),
        "outcome": "UNCERTAIN_INSUFFICIENT_EVIDENCE",
        "outcome_reason": "The integrated E1–E4 decision rule is not yet validated, and neighbor provenance/coverage is incomplete.",
        "evidence_meanings": {
            "E1": "Model-configuration stability indicates detector agreement only; it is not event truth or probability.",
            "E2": "SUPPORTING indicates a temporal departure or repeated-value screen; it does not identify a regional weather event or diagnose hardware.",
            "E3": "Spatial support requires verified, time-aligned neighboring station observations and provenance.",
            "E4": "A physical-quality flag indicates a broad rule violation only; it is not a sensor diagnosis.",
        },
    }
