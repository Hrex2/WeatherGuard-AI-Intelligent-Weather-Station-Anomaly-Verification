"""Run additional held-out synthetic fault scenarios with one shared local fit."""
from __future__ import annotations

import json
import platform
import subprocess
import sys
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from weather_research.faults import evaluate_injection, inject_fault
from weather_research.models import default_model_configs
from weather_research.synthetic_campaign import (_fit_campaign_models,
    _predict_campaign_models, _seasonal_matrix, load_verified_snapshots)

SCENARIOS = [
    {"id": "TEMP_POINT_SPIKE", "variable": "temp", "kind": "spike", "magnitude": 10.0, "duration": 1, "seed": 42},
    {"id": "TEMP_POINT_DROP", "variable": "temp", "kind": "point_negative_offset", "magnitude": 10.0, "duration": 1, "seed": 42},
    {"id": "TEMP_PERSISTENT_OFFSET", "variable": "temp", "kind": "positive_offset", "magnitude": 5.0, "duration": 6, "seed": 42},
    {"id": "TEMP_STUCK_SENSOR", "variable": "temp", "kind": "stuck", "magnitude": 0.0, "duration": 6, "seed": 42},
    {"id": "TEMP_GRADUAL_DRIFT", "variable": "temp", "kind": "drift", "magnitude": 5.0, "duration": 6, "seed": 42},
    {"id": "TEMP_MISSING_BLOCK", "variable": "temp", "kind": "dropout", "magnitude": 0.0, "duration": 3, "seed": 42},
    {"id": "TEMP_INTERMITTENT_NOISE", "variable": "temp", "kind": "noise_burst", "magnitude": 2.0, "duration": 6, "seed": 31415},
    {"id": "DEWPOINT_TEMP_INCONSISTENCY", "variable": "dwpt", "kind": "positive_offset", "magnitude": 20.0, "duration": 3, "seed": 42},
]


def validate_scenarios(raw, train, test, target):
    """Fail on invalid intervals or physical bounds before fitting estimators."""
    calibration_end = train.index.max()
    for scenario in SCENARIOS:
        end_pos = raw.index.get_loc(target) + scenario["duration"] - 1
        if end_pos >= len(raw.index) or raw.index[end_pos] not in test.index:
            raise ValueError(f"Scenario exceeds the held-out test range: {scenario['id']}")
        inject_fault(raw, scenario["variable"], target, raw.index[end_pos],
            kind=scenario["kind"], magnitude=scenario["magnitude"],
            random_seed=scenario["seed"], calibration_end=calibration_end)
    return True


def normalize_metric_table(metrics):
    """Use neutral labels for unmodified rows; they are not verified negatives."""
    rename = {"tp": "injected_and_flagged_count", "fp": "unmodified_observation_flags",
              "fn": "injected_not_flagged_count", "tn": "unmodified_observation_unflagged",
              "synthetic_point_recall": "injected_label_recall",
              "clean_false_positive_rate": "unmodified_observation_flag_rate"}
    out = metrics.rename(columns={old: new for old, new in rename.items() if old in metrics.columns}).copy()
    return out.drop(columns=["sampling_unit", "recall_wilson_95pct_ci",
                             "false_positive_rate_wilson_95pct_ci"], errors="ignore")


def write_scenario_summary(run_dir):
    run_dir = Path(run_dir)
    configuration_metrics = normalize_metric_table(pd.read_csv(run_dir / "configuration_metrics.csv"))
    configuration_metrics.to_csv(run_dir / "configuration_metrics.csv", index=False)
    summary = configuration_metrics.groupby("experiment_id", as_index=False).agg(
        fault_type=("kind", "first"), variable=("variable", "first"),
        magnitude=("magnitude", "first"), duration_observations=("duration_observations", "first"),
        configurations=("name", "nunique"), injected_and_flagged=("injected_and_flagged_count", "sum"),
        unmodified_observation_flags=("unmodified_observation_flags", "sum"),
        injected_not_flagged=("injected_not_flagged_count", "sum"),
        unmodified_observation_unflagged=("unmodified_observation_unflagged", "sum"),
        changed_predictions=("changed_predictions", "sum"),
        newly_flagged_outside_labels=("new_flags_outside_injected_labels", "sum"),
        withdrawn_clean_flags=("withdrawn_clean_flags", "sum"))
    summary["injected_label_recall"] = summary.injected_and_flagged / (summary.injected_and_flagged + summary.injected_not_flagged).replace(0, np.nan)
    summary["unmodified_observation_flag_rate"] = summary.unmodified_observation_flags / (summary.unmodified_observation_flags + summary.unmodified_observation_unflagged).replace(0, np.nan)
    summary.to_csv(run_dir / "scenario_summary.csv", index=False)
    family_summary = configuration_metrics.groupby(["experiment_id", "family"], as_index=False).agg(
        configuration_count=("name", "nunique"), injected_and_flagged=("injected_and_flagged_count", "sum"),
        injected_not_flagged=("injected_not_flagged_count", "sum"),
        changed_predictions=("changed_predictions", "sum"),
        newly_flagged_outside_labels=("new_flags_outside_injected_labels", "sum"))
    family_summary["injected_label_recall"] = family_summary.injected_and_flagged / (
        family_summary.injected_and_flagged + family_summary.injected_not_flagged).replace(0, np.nan)
    family_summary.to_csv(run_dir / "family_scenario_summary.csv", index=False)
    return summary, family_summary


def enrich_injection_registry(run_dir, root=ROOT):
    """Attach exact original/altered values to every injection interval row."""
    root = Path(root)
    run_dir = Path(run_dir)
    snapshots, _, _ = load_verified_snapshots(root)
    raw = snapshots["model_df"]
    seed_registry = pd.read_csv(run_dir / "injection_registry.csv", parse_dates=["timestamp"])
    all_rows = []
    scenario_by_id = {item["id"]: item for item in SCENARIOS}
    for experiment_id, existing in seed_registry.groupby("experiment_id", sort=False):
        scenario = scenario_by_id[experiment_id]
        variable = scenario["variable"]
        row_times = pd.DatetimeIndex(pd.to_datetime(existing.timestamp, utc=True).dt.tz_convert(str(raw.index.tz)))
        end = row_times[-1]
        faulted, _, _ = inject_fault(raw, variable, row_times[0], end,
            kind=scenario["kind"], magnitude=scenario["magnitude"],
            random_seed=scenario["seed"], calibration_end=snapshots["X_train_multi"].index.max())
        existing = existing.copy()
        existing["timestamp"] = row_times
        existing["target_variable"] = variable
        existing["severity"] = scenario["magnitude"]
        existing["original_value"] = raw[variable].reindex(row_times).to_numpy()
        existing["injected_value"] = faulted[variable].reindex(row_times).to_numpy()
        existing["faulted_value_is_missing"] = pd.isna(existing.injected_value)
        all_rows.append(existing)
    result = pd.concat(all_rows, ignore_index=True)
    result.to_csv(run_dir / "injection_registry.csv", index=False)
    return result


def finalize_existing_run(run_dir):
    """Create aggregate scenario summary and reconcile a completed run manifest."""
    run_dir = Path(run_dir)
    summary, family_summary = write_scenario_summary(run_dir)
    metadata_path = run_dir / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["outputs"] = ["configuration_metrics.csv", "scenario_summary.csv", "family_scenario_summary.csv",
                           "changed_and_injected_predictions.csv", "injection_registry.csv"]
    enrich_injection_registry(run_dir)
    metadata["prediction_rows_retained"] = len(pd.read_csv(run_dir / "changed_and_injected_predictions.csv"))
    metadata["prediction_retention_rule"] = "All injected timestamps and all configuration/timestamp labels that changed from the same-run clean comparator."
    metadata["postprocessing_code_commit"] = subprocess.run(["git", "rev-parse", "HEAD"],
        cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    metadata["postprocessing_note"] = "Model predictions and counts are unchanged; aggregate summaries were derived and unmodified timestamps compacted for traceability without storing a duplicate full prediction grid."
    metadata["station_id_dataset_label"] = "VILD0"
    metadata["station_provenance_status"] = "UNVERIFIED; inherited label from processed snapshot, not an independently audited station identity."
    metadata_path.write_text(json.dumps(metadata, indent=2, default=str) + "\n", encoding="utf-8")
    return summary


def compact_completed_run(run_dir):
    """Keep only injected or changed prediction rows in an older full-grid run."""
    run_dir = Path(run_dir)
    full_path = run_dir / "paired_predictions.csv"
    if not full_path.is_file():
        raise FileNotFoundError(f"Full paired prediction file is missing: {full_path}")
    rows = pd.read_csv(full_path)
    injected = rows.synthetic_fault_label.astype(bool)
    changed = rows.is_candidate.astype(bool).ne(rows.clean_is_candidate.astype(bool))
    compact = rows.loc[injected | changed].copy()
    compact["prediction_changed"] = changed.loc[compact.index].to_numpy()
    compact_path = run_dir / "changed_and_injected_predictions.csv"
    compact.to_csv(compact_path, index=False)
    full_path.unlink()
    metadata_path = run_dir / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    write_scenario_summary(run_dir)
    metadata["outputs"] = ["configuration_metrics.csv", "scenario_summary.csv", "family_scenario_summary.csv",
                           "changed_and_injected_predictions.csv", "injection_registry.csv"]
    metadata["prediction_rows_retained"] = int(len(compact))
    metadata["prediction_retention_rule"] = "All injected timestamps and all configuration/timestamp labels that changed from the same-run clean comparator."
    metadata_path.write_text(json.dumps(metadata, indent=2, default=str) + "\n", encoding="utf-8")
    return compact_path, int(len(compact))


def run_fault_matrix(root=ROOT, timestamp="2025-09-02 07:30:00+05:30"):
    root = Path(root)
    snapshots, manifest, hashes = load_verified_snapshots(root)
    raw, train, test = snapshots["model_df"], snapshots["X_train_multi"], snapshots["X_test_multi"]
    target = pd.Timestamp(timestamp)
    if target not in test.index or target not in raw.index:
        raise ValueError("Campaign timestamp must be present in processed and held-out snapshots")
    calibration_end = train.index.max()
    validate_scenarios(raw, train, test, target)
    configs = default_model_configs(random_seed=42)
    train_matrix = _seasonal_matrix(train)
    clean_matrix = _seasonal_matrix(test)
    scaler = StandardScaler().fit(train_matrix.to_numpy(dtype=float))
    scaled_train = scaler.transform(train_matrix.to_numpy(dtype=float))
    scaled_clean = scaler.transform(clean_matrix.to_numpy(dtype=float))
    fitted = _fit_campaign_models(train_matrix, scaled_train, configs, n_estimators=200)
    clean = _predict_campaign_models(fitted, clean_matrix, scaled_clean)

    run_id = "fault_matrix_" + uuid.uuid4().hex[:12]
    run_dir = root / "research_results" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    metadata_rows, prediction_rows, injection_rows = [], [], []
    for scenario in SCENARIOS:
        start = target
        end_pos = raw.index.get_loc(target) + scenario["duration"] - 1
        if end_pos >= len(raw.index):
            raise ValueError(f"Scenario exceeds processed series: {scenario['id']}")
        end = raw.index[end_pos]
        if end not in test.index:
            raise ValueError(f"Scenario extends beyond the held-out test window: {scenario['id']}")
        faulted, labels, registry = inject_fault(raw, scenario["variable"], start, end,
            kind=scenario["kind"], magnitude=scenario["magnitude"], random_seed=scenario["seed"],
            calibration_end=calibration_end)
        if not registry.value_modified.any():
            raise ValueError(f"Scenario did not modify any values: {scenario['id']}")
        fault_matrix = clean_matrix.copy(deep=True)
        for column in ("temp", "dwpt", "rhum", "prcp", "wspd", "pres"):
            fault_matrix[column] = faulted[column].reindex(test.index)
        grouped = faulted.groupby("segment_id", sort=False, dropna=True)["temp"]
        change = grouped.diff().reindex(test.index)
        rolling = grouped.transform(lambda values: values.shift(1).rolling(6, min_periods=6).mean()).reindex(test.index)
        fault_matrix["temp_change_1h"] = change
        fault_matrix["temp_rolling_mean_6h"] = rolling
        fault_matrix["temp_deviation_6h"] = fault_matrix.temp - rolling
        medians = train.median(numeric_only=True)
        fault_matrix = fault_matrix.replace([np.inf, -np.inf], np.nan).fillna(medians)
        fault_matrix = _seasonal_matrix(fault_matrix)
        scaled_fault = scaler.transform(fault_matrix.to_numpy(dtype=float))
        fault_predictions = _predict_campaign_models(fitted, fault_matrix, scaled_fault)
        clean_key = clean[["timestamp", "configuration", "is_candidate"]].rename(columns={"is_candidate": "clean_is_candidate"})
        paired = fault_predictions.merge(clean_key, on=["timestamp", "configuration"], validate="one_to_one")
        labels_test = labels.reindex(test.index).fillna(False).astype(bool)
        labeled = paired.set_index("timestamp")
        scenario_rows = []
        for config in configs:
            cfg = labeled.loc[labeled.configuration.eq(config["name"])]
            metric = evaluate_injection(cfg.is_candidate.astype(bool), labels_test.reindex(cfg.index).fillna(False))
            metric = {"injected_and_flagged_count": metric["tp"],
                      "unmodified_observation_flags": metric["fp"],
                      "injected_not_flagged_count": metric["fn"],
                      "unmodified_observation_unflagged": metric["tn"],
                      "injected_label_recall": metric["synthetic_point_recall"],
                      "unmodified_observation_flag_rate": metric["clean_false_positive_rate"]}
            changed = cfg.is_candidate.astype(bool).ne(cfg.clean_is_candidate.astype(bool))
            outside = ~labels_test.reindex(cfg.index).fillna(False).astype(bool)
            counts = {"changed_predictions": int(changed.sum()),
                      "new_flags_outside_injected_labels": int((cfg.is_candidate.astype(bool) & ~cfg.clean_is_candidate.astype(bool) & outside).sum()),
                      "withdrawn_clean_flags": int((~cfg.is_candidate.astype(bool) & cfg.clean_is_candidate.astype(bool)).sum())}
            row = {**scenario, **config, **metric, **counts,
                   "experiment_id": scenario["id"], "start_timestamp": str(start),
                   "end_timestamp": str(end), "duration_observations": int(registry.value_modified.sum()),
                   "faulted_configuration_votes": int(cfg.loc[cfg.index.isin(labels_test.index[labels_test]), "is_candidate"].sum())}
            scenario_rows.append(row)
            config_predictions = paired.loc[paired.configuration.eq(config["name"])].copy()
            config_predictions["synthetic_fault_label"] = labels_test.reindex(config_predictions.timestamp).to_numpy()
            config_predictions["prediction_changed"] = config_predictions.is_candidate.astype(bool).ne(
                config_predictions.clean_is_candidate.astype(bool)).to_numpy()
            # Retain all injected timestamps and changed labels; avoid a
            # redundant full 8,415×12 grid for every scenario.
            audit_rows = config_predictions.loc[
                config_predictions.synthetic_fault_label | config_predictions.prediction_changed].copy()
            prediction_rows.append(audit_rows.assign(
                experiment_id=scenario["id"], fault_type=scenario["kind"], variable=scenario["variable"]))
        registry = registry.copy()
        registry["experiment_id"] = scenario["id"]
        injection_rows.append(registry)
        metadata_rows.extend(scenario_rows)

    pd.DataFrame(metadata_rows).to_csv(run_dir / "configuration_metrics.csv", index=False)
    pd.concat(prediction_rows, ignore_index=True).to_csv(run_dir / "changed_and_injected_predictions.csv", index=False)
    pd.concat(injection_rows, ignore_index=True).to_csv(run_dir / "injection_registry.csv", index=False)
    write_scenario_summary(run_dir)
    enrich_injection_registry(run_dir, root)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                            capture_output=True, text=True).stdout.strip()
    metadata = {"run_id": run_id, "status": "EXECUTED_LOCAL_SYNTHETIC",
        "objective": "Explore detector response across additional controlled held-out fault patterns.",
        "hypothesis": "Different synthetic fault patterns and variables may alter saved-protocol model flags differently.",
        "dataset_hashes": hashes, "phase01_audit_passed": manifest.get("audit_passed") is True,
        "code_commit": commit, "model_version": "local refit of existing 12-config protocol; synthetic results only",
        "feature_order": list(train_matrix.columns), "random_seeds": sorted({s["seed"] for s in SCENARIOS}),
        "n_estimators": 200, "scaler": "StandardScaler fit on train only for LOF/SVM; Isolation Forest unscaled",
        "python_version": platform.python_version(), "numpy_version": np.__version__,
        "pandas_version": pd.__version__, "scikit_learn_version": sklearn.__version__,
        "training_rows": len(train), "test_rows": len(test), "training_end": str(train.index.max()),
        "test_start": str(test.index.min()), "scenarios": SCENARIOS,
        "clean_comparator": "same local fitted models and clean held-out predictions for every scenario",
        "saved_grid_mismatches": "Historical parity differs at 42 labels, all Isolation Forest; comparison here is within this run's clean baseline.",
        "limitations": ["Synthetic injections are not real-world fault validation.",
            "Scenario timestamp is one selected held-out interval; results do not estimate population performance.",
            "Ground-truth labels mark modified observations only; causal feature propagation can alter neighboring predictions.",
            "No fitted estimator objects are persisted.", "E3 spatial evidence is not part of these experiments."],
        "outputs": ["configuration_metrics.csv", "scenario_summary.csv", "family_scenario_summary.csv", "changed_and_injected_predictions.csv", "injection_registry.csv"]}
    (run_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2, default=str) + "\n", encoding="utf-8")
    return run_dir, metadata


if __name__ == "__main__":
    directory, result = run_fault_matrix()
    print(json.dumps({"run_id": result["run_id"], "output_dir": str(directory),
                      "scenarios": len(result["scenarios"]), "code_commit": result["code_commit"]}, indent=2))
