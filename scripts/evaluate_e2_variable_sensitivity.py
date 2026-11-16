"""Evaluate the exploratory E2 screen across measured variables at saved candidates."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from services.data_service import load_project_data
from services.investigation_service import available_weather_variables
from services.temporal_service import temporal_verification


def evaluate(root=ROOT):
    data, _, hashes = load_project_data(root)
    observations = data["observations"]
    variables = list(available_weather_variables(observations))
    candidates = pd.DatetimeIndex(data["stability"].loc[
        data["stability"].configuration_votes.ge(8), "timestamp"].drop_duplicates()).sort_values()
    rows = []
    for variable in variables:
        for ts in candidates:
            if ts not in observations.index:
                continue
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
    summary = (detail.groupby(["variable", "mode", "window_hours", "robust_z_threshold", "status"],
                              dropna=False).size().rename("candidate_count").reset_index())
    output = Path(root) / "research_results"
    output.mkdir(exist_ok=True)
    detail.to_csv(output / "e2_variable_sensitivity.csv", index=False)
    summary.to_csv(output / "e2_variable_sensitivity_summary.csv", index=False)
    manifest = {"input": "saved 8/12 E1 candidate timestamps and processed observations",
        "candidate_timestamps": int(len(candidates)), "variables_present": variables,
        "evaluated_rows": int(len(detail)), "windows_hours": [1, 3, 6, 12, 24],
        "robust_deviation_thresholds": [2.5, 3.5, 4.5],
        "modes": ["real_time", "retrospective"], "lookahead_hours": 6,
        "data_hashes": hashes,
        "limitation": "All timestamps were selected by E1 8/12 consensus; descriptive variable sensitivity only, not independent event/fault validation or calibration.",
        "outputs": ["research_results/e2_variable_sensitivity.csv",
                    "research_results/e2_variable_sensitivity_summary.csv"]}
    (output / "e2_variable_sensitivity.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return detail, summary, manifest


if __name__ == "__main__":
    _, summary, manifest = evaluate()
    print(json.dumps(manifest, indent=2))
    print(summary.loc[(summary.window_hours == 6) & (summary.robust_z_threshold == 3.5)]
          .pivot_table(index=["variable", "mode"], columns="status", values="candidate_count", fill_value=0)
          .to_string())
