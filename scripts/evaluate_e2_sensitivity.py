"""Descriptive sensitivity of E2 screening on saved 8/12 candidate timestamps."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from services.data_service import load_project_data
from services.temporal_service import temporal_verification


def evaluate(root=ROOT, variable="temp"):
    data, _, hashes = load_project_data(root)
    candidates = pd.DatetimeIndex(data["stability"].loc[
        data["stability"].configuration_votes.ge(8), "timestamp"].drop_duplicates()).sort_values()
    observations = data["observations"]
    rows = []
    for ts in candidates:
        if ts not in observations.index:
            continue
        # Bound work to the largest requested temporal context plus retrospective
        # lookahead while preserving actual timestamp gaps and segment boundaries.
        local = observations.loc[ts - pd.Timedelta(hours=24):ts + pd.Timedelta(hours=6)]
        for window in (1, 3, 6, 12, 24):
            for threshold in (2.5, 3.5, 4.5):
                for mode in ("real_time", "retrospective"):
                    result = temporal_verification(local, ts, variable, window_hours=window,
                        mode=mode, lookahead_hours=6, min_context=3,
                        robust_z_threshold=threshold)
                    rows.append({"timestamp": ts, "variable": variable, "mode": mode,
                        "window_hours": window, "robust_z_threshold": threshold,
                        "status": result["status"], "prior_count": result.get("prior_count", 0),
                        "future_count": result.get("future_count", 0),
                        "robust_deviation": result.get("robust_deviation"),
                        "sudden_change": result.get("sudden_change", False),
                        "stuck_pattern": result.get("stuck_pattern", False),
                        "persistent_unusual_state": result.get("persistent_unusual_state"),
                        "reason": result.get("reason", "")})
    detail = pd.DataFrame(rows)
    summary = (detail.groupby(["mode", "window_hours", "robust_z_threshold", "status"],
                              dropna=False).size().rename("candidate_count").reset_index())
    out = root / "research_results"
    out.mkdir(exist_ok=True)
    detail.to_csv(out / "e2_candidate_sensitivity.csv", index=False)
    summary.to_csv(out / "e2_candidate_sensitivity_summary.csv", index=False)
    report = {"input": "saved 8/12 candidate timestamps and processed observations",
        "candidate_timestamps": int(len(candidates)), "evaluated_rows": int(len(detail)),
        "variable": variable, "windows_hours": [1, 3, 6, 12, 24],
        "robust_deviation_thresholds": [2.5, 3.5, 4.5],
        "modes": ["real_time", "retrospective"], "lookahead_hours": 6,
        "data_hashes": hashes,
        "interpretation_limit": "Descriptive sensitivity on model-selected timestamps; not independent event/fault validation and not threshold calibration.",
        "files": ["research_results/e2_candidate_sensitivity.csv",
                  "research_results/e2_candidate_sensitivity_summary.csv"]}
    (out / "e2_candidate_sensitivity.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return detail, summary, report


if __name__ == "__main__":
    detail, summary, report = evaluate()
    print(json.dumps(report, indent=2))
    print(summary.pivot_table(index=["mode", "window_hours", "robust_z_threshold"],
        columns="status", values="candidate_count", fill_value=0).to_string())
