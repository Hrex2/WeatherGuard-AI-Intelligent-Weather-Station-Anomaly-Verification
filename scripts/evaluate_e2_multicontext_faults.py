"""Evaluate temporal screening on synthetic faults and matched unmodified windows."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from scripts.run_multicontext_fault_matrix import _candidate_context_table
from scripts.run_synthetic_fault_matrix import SCENARIOS
from services.temporal_service import temporal_verification
from weather_research.synthetic_campaign import load_verified_snapshots
from weather_research.faults import inject_fault

VARIABLES = ("temp", "dwpt", "rhum", "prcp", "wspd", "pres")
WINDOWS_HOURS = (3, 6, 12)
ROBUST_THRESHOLDS = (2.5, 3.5, 4.5)
MODES = ("real_time", "retrospective")
MATCH_SEPARATION = pd.Timedelta(days=14)


def select_matched_controls(raw, test, contexts, controls_per_context=2):
    """Choose unmodified windows by same quarter/time and nearest context features."""
    candidates = _candidate_context_table(raw, test)
    selected, used = [], []
    injected_starts = [pd.Timestamp(item["timestamp"]) for item in contexts]
    for context in contexts:
        target = pd.Timestamp(context["timestamp"])
        same_stratum = candidates.loc[
            candidates.calendar_quarter.eq(target.quarter)
            & candidates.hour_of_day.eq(target.hour)
            & candidates.minute_of_hour.eq(target.minute)
        ].copy()
        same_stratum["match_score"] = (
            (same_stratum.temperature_median_24h - context["temperature_median_24h"]).abs()
            + 2.0 * (same_stratum.temperature_sd_6h - context["temperature_sd_6h"]).abs()
            + 5.0 * (same_stratum.missing_fraction_24h - context["missing_fraction_24h"]).abs()
        )
        count = 0
        for _, candidate in same_stratum.sort_values(["match_score", "timestamp"]).iterrows():
            ts = candidate.timestamp
            if any(abs(ts - start) < MATCH_SEPARATION for start in injected_starts):
                continue
            if any(abs(ts - chosen) < MATCH_SEPARATION for chosen in used):
                continue
            row = candidate.to_dict()
            row.update({"matched_context_id": context["context_id"],
                        "matched_context_timestamp": target,
                        "matching_rule": "same calendar quarter and time-of-day; nearest 24h temperature level, 6h variability, and missingness; no detector outputs used"})
            selected.append(row)
            used.append(ts)
            count += 1
            if count >= controls_per_context:
                break
    return pd.DataFrame(selected)


def _evaluate_reading(series, timestamp, variable, condition, context_id,
                      experiment_id=None, synthetic_label=False, pair_id=None):
    output = []
    for window in WINDOWS_HOURS:
        for threshold in ROBUST_THRESHOLDS:
            for mode in MODES:
                result = temporal_verification(series, timestamp, variable,
                    window_hours=window, mode=mode, lookahead_hours=6,
                    min_context=3, robust_z_threshold=threshold)
                output.append({
                    "context_id": context_id, "experiment_id": experiment_id,
                    "timestamp": timestamp, "variable": variable,
                    "condition": condition, "synthetic_label": bool(synthetic_label),
                    "pair_id": pair_id, "mode": mode, "window_hours": window,
                    "robust_z_threshold": threshold,
                    "status": result.get("status", "UNAVAILABLE"),
                    "prior_count": result.get("prior_count", 0),
                    "future_count": result.get("future_count", 0),
                    "robust_deviation": result.get("robust_deviation"),
                    "sudden_change": result.get("sudden_change", False),
                    "stuck_pattern": result.get("stuck_pattern", False),
                    "persistent_unusual_state": result.get("persistent_unusual_state"),
                    "reason": result.get("reason", ""),
                })
    return output


def evaluate_multicontext_e2(campaign_dir, root=ROOT, controls_per_context=2):
    root, campaign_dir = Path(root), Path(campaign_dir)
    campaign_manifest = json.loads((campaign_dir / "campaign_manifest.json").read_text(encoding="utf-8"))
    if campaign_manifest.get("status") != "EXECUTED_LOCAL_SYNTHETIC_MULTICONTEXT":
        raise ValueError("The multi-context synthetic campaign must complete before E2 evaluation")
    snapshots, _, hashes = load_verified_snapshots(root)
    raw, train, test = snapshots["model_df"], snapshots["X_train_multi"], snapshots["X_test_multi"]
    context_rows = pd.read_csv(campaign_dir / "context_selection.csv", parse_dates=["timestamp"])
    metrics_by_id = {row["context_id"]: row for row in context_rows.to_dict("records")}
    contexts = [{**metrics_by_id.get(item["context_id"], {}), **item}
                for item in campaign_manifest["contexts"]]
    controls = select_matched_controls(raw, test, contexts, controls_per_context)
    controls_path = campaign_dir / "e2_matched_controls.csv"
    controls.to_csv(controls_path, index=False)
    rows = []
    for context in contexts:
        context_id = context["context_id"]
        start = pd.Timestamp(context["timestamp"])
        for scenario in SCENARIOS:
            duration_end = raw.index[raw.index.get_loc(start) + scenario["duration"] - 1]
            faulted, labels, _ = inject_fault(raw, scenario["variable"], start, duration_end,
                kind=scenario["kind"], magnitude=scenario["magnitude"],
                random_seed=scenario["seed"], calibration_end=train.index.max())
            for timestamp in labels.index[labels]:
                pair_id = f"{context_id}:{scenario['id']}:{timestamp.isoformat()}:{scenario['variable']}"
                variable = scenario["variable"]
                rows.extend(_evaluate_reading(raw, timestamp, variable, "clean_same_timestamp",
                    context_id, scenario["id"], True, pair_id))
                rows.extend(_evaluate_reading(faulted, timestamp, variable, "synthetic_faulted",
                    context_id, scenario["id"], True, pair_id))
    for control in controls.to_dict("records"):
        timestamp = pd.Timestamp(control["timestamp"])
        for variable in VARIABLES:
            rows.extend(_evaluate_reading(raw, timestamp, variable, "matched_unmodified_control",
                control["matched_context_id"], None, False, None))
    detail = pd.DataFrame(rows)
    paired_rows = detail.loc[detail.condition.isin(["clean_same_timestamp", "synthetic_faulted"])]
    paired = paired_rows.pivot_table(index=["pair_id", "context_id", "experiment_id", "timestamp",
        "variable", "mode", "window_hours", "robust_z_threshold"], columns="condition",
        values="status", aggfunc="first").reset_index()
    paired["status_changed_by_injection"] = paired.synthetic_faulted.ne(paired.clean_same_timestamp)
    summary = detail.groupby(["condition", "experiment_id", "variable", "mode", "window_hours",
        "robust_z_threshold", "status"], dropna=False).size().rename("reading_count").reset_index()
    detail.to_csv(campaign_dir / "e2_multicontext_fault_detail.csv", index=False)
    paired.to_csv(campaign_dir / "e2_multicontext_fault_paired.csv", index=False)
    summary.to_csv(campaign_dir / "e2_multicontext_fault_summary.csv", index=False)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                            capture_output=True, text=True).stdout.strip()
    manifest = {
        "status": "EXECUTED_EXPLORATORY_SYNTHETIC_E2",
        "campaign_id": campaign_manifest["campaign_id"],
        "objective": "Test whether independent temporal screens respond to known synthetic injections and compare with same-time clean series and matched unmodified windows.",
        "code_commit": commit,
        "dataset_hashes": hashes,
        "contexts": contexts,
        "scenarios": SCENARIOS,
        "variables": list(VARIABLES),
        "evaluated_fault_variable": "Only the scenario's directly injected variable is used for its synthetic target-variable test; matched controls are screened on all six available variables.",
        "matched_control_method": "Same calendar quarter and time-of-day; nearest 24-hour temperature median, six-hour temperature variability and missingness; continuous hourly context; controls are unmodified in this campaign, not verified fault-free observations.",
        "controls_per_context_requested": controls_per_context,
        "controls_selected": int(len(controls)),
        "windows_hours": list(WINDOWS_HOURS),
        "robust_deviation_thresholds": list(ROBUST_THRESHOLDS),
        "modes": list(MODES),
        "lookahead_hours": 6,
        "minimum_context_rows": 3,
        "evaluated_rows": int(len(detail)),
        "paired_injection_rows": int(len(paired)),
        "paired_status_changes": int(paired.status_changed_by_injection.sum()),
        "limitations": [
            "E2 SUPPORTING means only a temporal departure or repeated-value screen; it does not identify a regional event or faulty hardware.",
            "The clean same-time comparator and matched controls are not adjudicated fault-free ground truth.",
            "Synthetic fault labels are known by construction; results are not real-world E2 accuracy.",
            "Only temperature and dew point were directly perturbed by the existing scenario set; other variables appear in matched-control summaries only.",
            "E2 thresholds are exploratory and multiple readings within an event are temporally dependent.",
        ],
        "outputs": ["e2_matched_controls.csv", "e2_multicontext_fault_detail.csv",
                    "e2_multicontext_fault_paired.csv", "e2_multicontext_fault_summary.csv"],
    }
    (campaign_dir / "e2_validation_manifest.json").write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")
    return manifest, detail, paired, summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_dir", type=Path)
    args = parser.parse_args()
    manifest, _, _, summary = evaluate_multicontext_e2(args.campaign_dir)
    print(json.dumps({"status": manifest["status"], "evaluated_rows": manifest["evaluated_rows"],
                      "controls_selected": manifest["controls_selected"],
                      "paired_status_changes": manifest["paired_status_changes"],
                      "summary_rows": len(summary)}, indent=2))
