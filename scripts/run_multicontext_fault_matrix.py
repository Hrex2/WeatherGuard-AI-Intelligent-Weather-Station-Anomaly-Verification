"""Run the existing eight synthetic fault scenarios across selected contexts.

Contexts are selected from pre-injection data only. One declared local model fit
and clean held-out prediction grid are shared across every selected context.
"""
from __future__ import annotations

import json
import platform
import subprocess
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from scripts.run_synthetic_fault_matrix import (SCENARIOS, fit_shared_protocol,
    run_fault_matrix, validate_scenarios)
from weather_research.synthetic_campaign import load_verified_snapshots

MIN_CONTEXT_SEPARATION = pd.Timedelta(days=14)
EXPECTED_INTERVAL = pd.Timedelta(hours=1)
CORE_VARIABLES = ("temp", "dwpt", "rhum", "wspd", "pres")


def _candidate_context_table(raw: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    """Find held-out starts with 24h prior context and a continuous six-row interval."""
    test_positions = raw.index.get_indexer(test.index)
    test_positions = test_positions[test_positions >= 24]
    values = raw.loc[:, list(CORE_VARIABLES)].to_numpy(dtype=float)
    precipitation = pd.to_numeric(raw["prcp"], errors="coerce").to_numpy(dtype=float)
    segment_ids = raw["segment_id"].to_numpy() if "segment_id" in raw else None
    rows = []
    for position in test_positions:
        end = int(position) + 6
        if end > len(raw):
            continue
        # Require one regular hourly span from the start of the 24h history
        # through the end of the longest existing six-reading injection.
        adjacent_intervals = raw.index[position - 23:end] - raw.index[position - 24:end - 1]
        if not np.all(adjacent_intervals == EXPECTED_INTERVAL):
            continue
        if segment_ids is not None and pd.Series(segment_ids[position - 24:end]).nunique(dropna=False) != 1:
            continue
        if not np.isfinite(values[position - 24:end]).all():
            continue
        prior_temp = values[position - 24:position, 0]
        prior_values = raw.loc[:, list(CORE_VARIABLES) + ["prcp"]].iloc[position - 24:position].to_numpy(dtype=float)
        rows.append({
            "timestamp": raw.index[position],
            "calendar_quarter": int(raw.index[position].quarter),
            "calendar_month": int(raw.index[position].month),
            "hour_of_day": int(raw.index[position].hour),
            "minute_of_hour": int(raw.index[position].minute),
            "temperature_median_24h": float(np.median(prior_temp)),
            "temperature_sd_6h": float(np.std(prior_temp[-6:], ddof=0)),
            "missing_fraction_24h": float(np.isnan(prior_values).mean()),
            "precipitation_missing_24h": int(np.isnan(precipitation[position - 24:position]).sum()),
        })
    return pd.DataFrame(rows)


def select_heldout_contexts(root=ROOT, max_contexts=5,
                            min_separation=MIN_CONTEXT_SEPARATION):
    """Select temperature/variability strata without inspecting detector results."""
    if not 1 <= int(max_contexts) <= 5:
        raise ValueError("max_contexts must be between one and five")
    snapshots, _, _ = load_verified_snapshots(root)
    raw, train, test = snapshots["model_df"], snapshots["X_train_multi"], snapshots["X_test_multi"]
    candidates = _candidate_context_table(raw, test)
    if candidates.empty:
        raise ValueError("No held-out intervals meet the continuous context and measured-variable requirements")
    tq25, tq75 = candidates.temperature_median_24h.quantile([0.25, 0.75])
    vq25, vq75 = candidates.temperature_sd_6h.quantile([0.25, 0.75])
    specifications = [
        ("TEMP_LOW_VAR_LOW", candidates.temperature_median_24h.le(tq25) & candidates.temperature_sd_6h.le(vq25)),
        ("TEMP_LOW_VAR_HIGH", candidates.temperature_median_24h.le(tq25) & candidates.temperature_sd_6h.ge(vq75)),
        ("TEMP_HIGH_VAR_LOW", candidates.temperature_median_24h.ge(tq75) & candidates.temperature_sd_6h.le(vq25)),
        ("TEMP_HIGH_VAR_HIGH", candidates.temperature_median_24h.ge(tq75) & candidates.temperature_sd_6h.ge(vq75)),
    ]
    selected = []
    targets = []

    def try_candidates(frame, context_id, score_columns):
        for _, candidate in frame.sort_values(score_columns + ["timestamp"]).iterrows():
            timestamp = candidate.timestamp
            if any(abs(timestamp - chosen) < min_separation for chosen in targets):
                continue
            try:
                validate_scenarios(raw, train, test, timestamp)
            except (ValueError, KeyError, IndexError):
                continue
            record = candidate.to_dict()
            record["context_id"] = context_id
            record["selection_rule"] = "pre-injection 24h temperature level and 6h variability strata; no detector outputs used"
            selected.append(record)
            targets.append(timestamp)
            return

    for context_id, mask in specifications:
        if len(selected) >= max_contexts:
            break
        frame = candidates.loc[mask].copy()
        if frame.empty:
            continue
        frame["level_score"] = (frame.temperature_median_24h - frame.temperature_median_24h.median()).abs()
        frame["variability_score"] = (frame.temperature_sd_6h - frame.temperature_sd_6h.median()).abs()
        try_candidates(frame, context_id, ["level_score", "variability_score"])

    if len(selected) < max_contexts:
        middle = candidates.loc[
            candidates.temperature_median_24h.between(tq25, tq75)
            & candidates.temperature_sd_6h.between(vq25, vq75)].copy()
        if not middle.empty:
            quarter_counts = {quarter: sum(pd.Timestamp(x["timestamp"]).quarter == quarter for x in selected)
                              for quarter in range(1, 5)}
            middle["quarter_count"] = middle.calendar_quarter.map(quarter_counts)
            middle["center_score"] = (
                (middle.temperature_median_24h - candidates.temperature_median_24h.median()).abs()
                + (middle.temperature_sd_6h - candidates.temperature_sd_6h.median()).abs()
            )
            try_candidates(middle.sort_values(["quarter_count", "center_score", "timestamp"]),
                           "TEMP_MIDLEVEL_MIDVAR", ["quarter_count", "center_score"])
    result = pd.DataFrame(selected)
    if result.empty:
        raise ValueError("No context passed the eight-scenario pre-fit validation")
    if not (result.timestamp > train.index.max()).all() or not result.timestamp.isin(test.index).all():
        raise AssertionError("Selected context escaped the original chronological held-out test set")
    report_columns = ["context_id", "timestamp", "calendar_quarter", "temperature_median_24h",
                      "temperature_sd_6h", "missing_fraction_24h", "precipitation_missing_24h",
                      "selection_rule"]
    result = result.loc[:, report_columns].sort_values("timestamp").reset_index(drop=True)
    result.attrs["selection_thresholds"] = {
        "temperature_median_24h_q25": float(tq25), "temperature_median_24h_q75": float(tq75),
        "temperature_sd_6h_q25": float(vq25), "temperature_sd_6h_q75": float(vq75),
    }
    return result


def run_multicontext_fault_matrix(root=ROOT, max_contexts=5):
    root = Path(root)
    snapshots, _, hashes = load_verified_snapshots(root)
    contexts = select_heldout_contexts(root, max_contexts=max_contexts)
    campaign_id = "fault_matrix_multicontext_" + uuid.uuid4().hex[:10]
    campaign_dir = root / "research_results" / campaign_id
    campaign_dir.mkdir(parents=True, exist_ok=False)
    contexts.to_csv(campaign_dir / "context_selection.csv", index=False)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                            capture_output=True, text=True).stdout.strip()
    manifest = {
        "campaign_id": campaign_id,
        "status": "PREFLIGHT_VALIDATED_MODEL_FIT_PENDING",
        "objective": "Assess context dependence of the existing eight synthetic fault scenarios.",
        "hypothesis": "Detector responses to the same declared fault may differ with background temperature level and recent variability.",
        "selection_method": "Select up to five well-separated test windows by pre-injection 24-hour temperature quartile and six-hour variability quartile; one middle context is added when available. Detector outputs are not consulted.",
        "selection_thresholds": contexts.attrs.get("selection_thresholds", {}),
        "minimum_context_separation_days": int(MIN_CONTEXT_SEPARATION.days),
        "context_count": int(len(contexts)),
        "contexts": [{"context_id": row.context_id, "timestamp": str(row.timestamp),
                      "calendar_quarter": int(row.calendar_quarter)} for row in contexts.itertuples()],
        "scenarios": SCENARIOS,
        "dataset_hashes": hashes,
        "phase01_audit_passed": True,
        "code_commit": commit,
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "scikit_learn_version": sklearn.__version__,
        "model_random_state": 42,
        "isolation_forest_estimators": 200,
        "scaling": "StandardScaler fit on train only for LOF/SVM; Isolation Forest unscaled.",
        "model_protocol": "One train-only fit of the existing 12 configurations and one clean holdout prediction grid shared across all contexts and scenarios; no historical saved predictions overwritten.",
        "feature_order": list(snapshots["X_train_multi"].columns),
        "limitations": [
            "Synthetic injections are not real-world fault validation.",
            "Unmodified held-out observations are controlled comparators, not verified fault-free labels.",
            "Context selection spans measured temperature and variability only; station identity/provenance remains unverified.",
            "The same local fit is reused across contexts; results measure context sensitivity under this declared protocol, not model-fit uncertainty.",
            "Historical saved-label refit parity still differs at 42 Isolation Forest cells; this experiment uses its own same-fit clean comparator.",
        ],
        "outputs": ["context_selection.csv", "context_scenario_summary.csv", "context_family_summary.csv"],
    }
    manifest_path = campaign_dir / "campaign_manifest.json"

    def save_manifest():
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str) + "\n", encoding="utf-8")

    save_manifest()
    try:
        # All scenarios at every selected context were validated before this
        # single shared model/scaler fit is started.
        shared_fit = fit_shared_protocol(snapshots["X_train_multi"], snapshots["X_test_multi"])
        scenario_tables, family_tables, run_records = [], [], []
        for row in contexts.to_dict("records"):
            run_dir, metadata = run_fault_matrix(root, timestamp=str(row["timestamp"]),
                shared_fit=shared_fit, context_id=row["context_id"])
            scenario = pd.read_csv(run_dir / "scenario_summary.csv")
            family = pd.read_csv(run_dir / "family_scenario_summary.csv")
            scenario.insert(0, "context_id", row["context_id"])
            scenario.insert(1, "context_timestamp", str(row["timestamp"]))
            family.insert(0, "context_id", row["context_id"])
            family.insert(1, "context_timestamp", str(row["timestamp"]))
            scenario_tables.append(scenario)
            family_tables.append(family)
            run_records.append({"context_id": row["context_id"], "timestamp": str(row["timestamp"]),
                                "calendar_quarter": int(row["calendar_quarter"]),
                                "temperature_median_24h": float(row["temperature_median_24h"]),
                                "temperature_sd_6h": float(row["temperature_sd_6h"]),
                                "missing_fraction_24h": float(row["missing_fraction_24h"]),
                                "precipitation_missing_24h": int(row["precipitation_missing_24h"]),
                                "run_directory": str(run_dir.relative_to(root)), "run_id": metadata["run_id"]})
            manifest["completed_context_runs"] = list(run_records)
            save_manifest()
        pd.concat(scenario_tables, ignore_index=True).to_csv(campaign_dir / "context_scenario_summary.csv", index=False)
        pd.concat(family_tables, ignore_index=True).to_csv(campaign_dir / "context_family_summary.csv", index=False)
        manifest["contexts"] = run_records
        manifest["status"] = "EXECUTED_LOCAL_SYNTHETIC_MULTICONTEXT"
        manifest["training_rows"] = int(len(snapshots["X_train_multi"]))
        manifest["test_rows"] = int(len(snapshots["X_test_multi"]))
        manifest["feature_order"] = list(shared_fit["train_matrix"].columns)
        save_manifest()
    except Exception as exc:
        manifest["status"] = "FAILED_AFTER_PREFLIGHT"
        manifest["failure"] = {"exception_type": type(exc).__name__, "message": str(exc)}
        save_manifest()
        raise
    return campaign_dir, manifest


if __name__ == "__main__":
    directory, manifest = run_multicontext_fault_matrix()
    print(json.dumps({"campaign_id": manifest["campaign_id"], "contexts": manifest["contexts"],
                      "output_dir": str(directory), "status": manifest["status"]}, indent=2))
