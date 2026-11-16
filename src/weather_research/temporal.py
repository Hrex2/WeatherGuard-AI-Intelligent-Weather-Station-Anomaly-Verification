"""Segment- and gap-aware point-to-event construction."""
from __future__ import annotations

import pandas as pd


def build_episodes(candidate_times, segment_ids: pd.Series | None = None,
                   gap_threshold="1h") -> pd.DataFrame:
    idx = pd.DatetimeIndex(candidate_times)
    if idx.has_duplicates:
        idx = idx.drop_duplicates()
    idx = idx.sort_values()
    if len(idx) == 0:
        return pd.DataFrame(columns=["episode_id", "start", "end", "observations",
                                     "elapsed_hours", "singleton"])
    frame = pd.DataFrame(index=idx)
    if segment_ids is None:
        frame["segment_id"] = 0
    else:
        if not isinstance(segment_ids, pd.Series):
            segment_ids = pd.Series(segment_ids, index=idx)
        frame["segment_id"] = segment_ids.reindex(idx)
    gaps = frame.index.to_series().diff()
    new = gaps.isna() | gaps.gt(pd.Timedelta(gap_threshold))
    new |= frame["segment_id"].ne(frame["segment_id"].shift())
    frame["episode_id"] = new.cumsum().astype(int)
    rows = []
    for eid, part in frame.groupby("episode_id", sort=True):
        start, end = part.index[0], part.index[-1]
        rows.append({"episode_id": int(eid), "start": start, "end": end,
                     "observations": len(part),
                     "elapsed_hours": (end-start).total_seconds()/3600,
                     "singleton": len(part) == 1,
                     "segment_id": part["segment_id"].iloc[0]})
    return pd.DataFrame(rows)


def episode_gap_sensitivity(candidate_times, segment_ids=None, thresholds=("1h", "2h", "3h")):
    parts=[]
    for threshold in thresholds:
        out=build_episodes(candidate_times, segment_ids, threshold)
        out["gap_threshold"] = str(threshold)
        parts.append(out)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
