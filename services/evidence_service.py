"""Read-only view helpers for saved model, episode, spatial, and QC evidence."""
from __future__ import annotations

import pandas as pd

from weather_research.quality import physical_quality_flags


def observation_evidence(timestamp, observations, predictions, stability, episodes,
                         spatial_tables):
    """Assemble available evidence for one timestamp without fabricating a verdict."""
    ts = pd.Timestamp(timestamp)
    model_rows = predictions.loc[predictions.timestamp.eq(ts)].copy()
    stability_rows = stability.loc[stability.timestamp.eq(ts)]
    vote_count = int(model_rows.is_candidate.astype(bool).sum()) if len(model_rows) else None
    episode_rows = episodes.loc[(episodes.start <= ts) & (episodes.end >= ts)]
    row = observations.loc[[ts]] if ts in observations.index else observations.iloc[0:0]
    quality = physical_quality_flags(row) if len(row) else pd.DataFrame()
    spatial_rows = []
    for station, table in spatial_tables.items():
        if table is not None and len(table) and "candidate_time" in table:
            match = table.loc[pd.to_datetime(table.candidate_time, utc=True).dt.tz_convert(str(ts.tz)).eq(ts)]
            if len(match):
                spatial_rows.append(match.assign(station_id=station))
    spatial = pd.concat(spatial_rows, ignore_index=True) if spatial_rows else pd.DataFrame()
    states = {
        "E1": "UNAVAILABLE" if vote_count is None else (
            "NO_DETECTED_EVIDENCE" if vote_count == 0 else
            "SUPPORTING_EVIDENCE" if vote_count >= 8 else "CONFLICTING_EVIDENCE"),
        "E2": "UNAVAILABLE" if vote_count is None else (
            "SUPPORTING_EVIDENCE" if len(episode_rows) else "NO_DETECTED_EVIDENCE"),
        "E3": "UNAVAILABLE" if not len(spatial) else "NO_DETECTED_EVIDENCE",
        "E4": "UNAVAILABLE" if not len(quality) else (
            "SUPPORTING_EVIDENCE" if quality.screening_flag.any() else "NO_DETECTED_EVIDENCE"),
    }
    # The spatial comparisons are exploratory, with no preregistered residual
    # threshold or demonstrated independent provider provenance. Preserve their
    # values for display, but do not use them to assert support or conflict.
    if len(spatial):
        states["E3"] = "UNAVAILABLE"
    return {
        "timestamp": ts,
        "model_rows": model_rows,
        "vote_count": vote_count,
        "stability_row": stability_rows.iloc[0] if len(stability_rows) else None,
        "episodes": episode_rows,
        "quality_flags": quality,
        "spatial_rows": spatial,
        "evidence_states": states,
        "outcome": "UNCERTAIN_INSUFFICIENT_EVIDENCE",
        "outcome_reason": "The integrated E1–E4 decision rule is not yet validated, and neighbor provenance/coverage is incomplete.",
    }
