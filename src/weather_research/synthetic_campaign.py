"""Reproducible held-out synthetic fault campaign utilities.

The functions in this module operate on supplied verified snapshots. They never
retrieve data, fit preprocessing on test rows, or modify caller-owned frames.
"""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.preprocessing import StandardScaler

from .faults import inject_fault
from .models import build_estimator, default_model_configs

BASE_FEATURES = ("temp", "dwpt", "rhum", "prcp", "wspd", "pres",
                 "temp_change_1h", "temp_rolling_mean_6h", "temp_deviation_6h",
                 "month_sin", "month_cos")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_verified_snapshots(root):
    """Load the four Phase 01 snapshots with their saved index and feature order."""
    root = Path(root)
    folder = root / "verified_phase01"
    files = {name: folder / f"{name}.csv" for name in
             ("model_df", "X_train_multi", "X_test_multi")}
    absent = [str(path) for path in files.values() if not path.is_file()]
    if absent:
        raise FileNotFoundError("required Phase 01 snapshots missing: " + ", ".join(absent))
    loaded = {name: pd.read_csv(path, index_col=0, parse_dates=True)
              for name, path in files.items()}
    for name, frame in loaded.items():
        if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.has_duplicates:
            raise ValueError(f"{name} must have unique timestamp index")
        if not frame.index.is_monotonic_increasing:
            raise ValueError(f"{name} timestamps must be sorted")
    manifest_path = folder / "phase01_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return loaded, manifest, {name: _sha256(path) for name, path in files.items()}


def _seasonal_matrix(frame):
    missing = set(BASE_FEATURES[:-2]) - set(frame.columns)
    if missing:
        raise KeyError(f"feature frame missing columns: {sorted(missing)}")
    out = frame.loc[:, BASE_FEATURES[:-2]].copy(deep=True)
    out["month_sin"] = np.sin(2 * np.pi * out.index.month / 12)
    out["month_cos"] = np.cos(2 * np.pi * out.index.month / 12)
    if not np.isfinite(out.to_numpy(dtype=float)).all():
        raise ValueError("seasonal model matrix contains non-finite values")
    return out.loc[:, BASE_FEATURES]


def _fit_campaign_models(train_matrix, scaled_train, configs, n_estimators):
    """Fit each declared model once; training inputs are identical across dose levels."""
    fitted = []
    for config in configs:
        family = config["family"]
        model = build_estimator(config, n_estimators=n_estimators)
        if family == "IsolationForest":
            model.fit(train_matrix.to_numpy(dtype=float))
        else:
            model.fit(scaled_train)
        fitted.append((config, model))
    return fitted


def _predict_campaign_models(fitted, test_matrix, scaled_test):
    rows = []
    for config, model in fitted:
        family = config["family"]
        values = test_matrix if family == "IsolationForest" else scaled_test
        prediction = model.predict(np.asarray(values, dtype=float))
        rows.append(pd.DataFrame({"configuration": config["name"], "family": family,
                                  "parameter": config["parameter"],
                                  "parameter_value": config["value"],
                                  "prediction": prediction.astype(int),
                                  "is_candidate": prediction == -1}, index=test_matrix.index))
    return pd.concat(rows).rename_axis("timestamp").reset_index()


def run_temperature_spike_campaign(root, output_dir=None,
                                   timestamp="2025-09-02 07:30:00+05:30",
                                   magnitudes=(2.0, 5.0, 10.0, 15.0),
                                   random_seed=42, n_estimators=200):
    """Run a same-time temperature dose series through the verified 12 models.

    Stored Phase 03 predictions are the clean comparator. The training scaler is
    fit only on the supplied training snapshot; model configurations are refit
    for each faulted test matrix using the established protocol.
    """
    root = Path(root)
    snapshots, manifest, hashes = load_verified_snapshots(root)
    raw = snapshots["model_df"]
    x_train = snapshots["X_train_multi"]
    x_test = snapshots["X_test_multi"]
    if tuple(x_train.columns) != tuple(x_test.columns):
        raise ValueError("train/test feature order differs")
    target = pd.Timestamp(timestamp)
    if target not in raw.index or target not in x_test.index:
        raise ValueError("controlled timestamp must exist in raw and test snapshots")
    if not np.isfinite(x_test.loc[target].to_numpy(dtype=float)).all():
        raise ValueError("controlled timestamp does not have valid baseline features")
    calibration_end = x_train.index.max()
    clean_predictions_path = root / "phase03_model_revalidation" / "model_predictions.csv"
    if not clean_predictions_path.is_file():
        raise FileNotFoundError("verified Phase 03 model_predictions.csv is required")
    clean = pd.read_csv(clean_predictions_path, parse_dates=["timestamp"])
    clean["timestamp"] = pd.to_datetime(clean["timestamp"], utc=True).dt.tz_convert(str(x_test.index.tz))
    clean = clean.set_index("timestamp").sort_index()
    expected = len(x_test) * len(default_model_configs(random_seed))
    if len(clean) != expected or clean.reset_index().duplicated(["timestamp", "configuration"]).any():
        raise ValueError("clean prediction table does not reconcile to test/configuration grid")
    train_matrix = _seasonal_matrix(x_train)
    scaler = StandardScaler().fit(train_matrix.to_numpy(dtype=float))
    clean_votes = clean.groupby(level=0)["is_candidate"].sum().astype(int)
    clean_candidates = clean["is_candidate"].astype(bool)
    configs = default_model_configs(random_seed)
    base_train_matrix = _seasonal_matrix(x_train)
    scaled_base_train = scaler.transform(base_train_matrix.to_numpy(dtype=float))
    fitted_models = _fit_campaign_models(base_train_matrix, scaled_base_train, configs, n_estimators)
    clean_matrix = _seasonal_matrix(x_test)
    scaled_clean_test = scaler.transform(clean_matrix.to_numpy(dtype=float))
    computed_clean = _predict_campaign_models(fitted_models, clean_matrix, scaled_clean_test)
    saved_clean = clean.reset_index()[["timestamp", "configuration", "is_candidate"]]
    clean_parity = computed_clean.merge(saved_clean, on=["timestamp", "configuration"],
                                       how="left", validate="one_to_one", suffixes=("_computed", "_saved"))
    if clean_parity["is_candidate_saved"].isna().any():
        raise ValueError("computed clean predictions do not align to saved baseline grid")
    clean_parity["matches_saved_prediction"] = (
        clean_parity["is_candidate_computed"].astype(bool) == clean_parity["is_candidate_saved"].astype(bool))
    registry, summaries, cfg_rows, obs_rows, event_rows, propagation, changes, unaffected = ([] for _ in range(8))
    source_before = raw.copy(deep=True)
    train_before = x_train.copy(deep=True)
    clean_feature_frame = raw.copy(deep=True)

    for magnitude in magnitudes:
        experiment_id = f"TEMP_SPIKE_{magnitude:g}C_20250902T0730_IST"
        faulted, labels, injection_registry = inject_fault(
            raw, "temp", target, kind="spike", magnitude=float(magnitude),
            random_seed=random_seed, calibration_end=calibration_end)
        if not labels.loc[target]:
            raise RuntimeError("injection did not label its target timestamp")
        feature_cols = list(x_train.columns)
        # Historical feature semantics are previous-row diff and previous six
        # observations, calculated within the stored segment ids.
        grouped = faulted.groupby("segment_id", sort=False, dropna=True)["temp"]
        feat = pd.DataFrame(index=faulted.index)
        feat["temp_change_1h"] = grouped.diff()
        feat["temp_rolling_mean_6h"] = grouped.transform(
            lambda series: series.shift(1).rolling(6, min_periods=6).mean())
        feat["temp_deviation_6h"] = faulted["temp"] - feat["temp_rolling_mean_6h"]
        assembled = faulted.loc[:, ["temp", "dwpt", "rhum", "prcp", "wspd", "pres"]].join(feat)
        test_fault = assembled.reindex(x_test.index).loc[:, feature_cols]
        test_fault["prcp"] = test_fault["prcp"].fillna(x_train["prcp"].median())
        fault_matrix = _seasonal_matrix(test_fault)
        scaled_train = pd.DataFrame(scaler.transform(train_matrix.to_numpy(dtype=float)), index=train_matrix.index, columns=BASE_FEATURES)
        scaled_test = pd.DataFrame(scaler.transform(fault_matrix.to_numpy(dtype=float)), index=fault_matrix.index, columns=BASE_FEATURES)
        preds = _predict_campaign_models(fitted_models, fault_matrix, scaled_test)
        preds["experiment_id"] = experiment_id
        preds["fault_type"] = "point_spike"
        preds["variable"] = "temp"
        preds["magnitude"] = float(magnitude)
        preds["start_timestamp"] = str(target)
        preds["end_timestamp"] = str(target)
        preds["segment_id"] = raw.loc[target, "segment_id"]
        preds["random_seed"] = random_seed
        preds["dataset_hash"] = hashes["model_df"]
        preds["feature_configuration"] = json.dumps(BASE_FEATURES)
        baseline = computed_clean[["timestamp", "configuration", "is_candidate"]].rename(
            columns={"is_candidate": "clean_is_candidate"})
        paired = preds.merge(baseline, on=["timestamp", "configuration"], how="left", validate="one_to_one")
        if paired["clean_is_candidate"].isna().any():
            raise ValueError("fault and clean prediction keys differ")
        base = paired["clean_is_candidate"].astype(bool).to_numpy()
        changed = paired["is_candidate"].astype(bool).to_numpy()
        diff = changed != base
        candidate = preds["timestamp"].eq(target)
        votes = int(preds.loc[candidate, "is_candidate"].sum())
        clean_at_target = int(clean_votes.loc[target])
        injected_detected = bool(votes > 0)
        cfg_rows.extend(preds.loc[candidate, ["experiment_id", "fault_type", "variable", "magnitude", "timestamp",
                                                "configuration", "family", "is_candidate"]].to_dict("records"))
        obs_rows.append({"experiment_id": experiment_id, "fault_type": "point_spike", "variable": "temp",
                         "magnitude": float(magnitude), "injected_observations": 1,
                         "detected_injected_observations": int(injected_detected),
                         "synthetic_detection_rate": float(injected_detected),
                         "missed_injected_observations": int(not injected_detected),
                         "newly_flagged_outside_labels": int(np.sum(changed & ~base)),
                         "configuration_votes_clean": clean_at_target, "configuration_votes_faulted": votes,
                         "random_seed": random_seed, "dataset_hash": hashes["model_df"]})
        changes.extend(paired.loc[diff, ["experiment_id", "timestamp", "configuration", "family",
                                         "is_candidate", "clean_is_candidate"]].to_dict("records"))
        pos_target = raw.index.get_loc(target)
        affected_timestamps = [target]
        for pos in range(pos_target + 1, min(len(raw.index), pos_target + 7)):
            if raw.index[pos] - raw.index[pos - 1] != pd.Timedelta(hours=1):
                break
            if raw.iloc[pos]["segment_id"] != raw.iloc[pos - 1]["segment_id"]:
                break
            affected_timestamps.append(raw.index[pos])
        within_affected_window = preds["timestamp"].isin(affected_timestamps).to_numpy()
        outside_features = ~within_affected_window
        event_rows.append({"experiment_id": experiment_id, "event_detected": injected_detected,
                           "event_start": str(target), "event_end": str(target), "duration_observations": 1,
                           "event_detection_delay_hours": 0.0 if injected_detected else np.nan,
                           "fraction_event_duration_detected": float(injected_detected),
                           "unaffected_window_changed_configuration_predictions": int(diff[outside_features].sum()),
                           "changed_configuration_predictions_anywhere": int(diff.sum()),
                           "unaffected_window_false_alarm_timestamps": int(
                               paired.loc[(paired["timestamp"] != target)
                                          & paired["is_candidate"].astype(bool)
                                          & ~paired["clean_is_candidate"].astype(bool), "timestamp"].nunique()),
                           "evaluation_window": "timestamps outside the injected observation's expected feature-propagation window, compared to matching local clean refit"})
        unaffected.append({"experiment_id": experiment_id,
                           "outside_target_changed_configuration_predictions": int(diff[~candidate.to_numpy()].sum()),
                           "changed_timestamps_outside_target": int(preds.loc[~candidate].assign(_changed=diff[~candidate.to_numpy()]).groupby("timestamp")["_changed"].any().sum()),
                           "affected_feature_window_timestamps": json.dumps([str(value) for value in affected_timestamps]),
                           "changed_configuration_predictions_beyond_affected_feature_window": int(diff[outside_features].sum()),
                           "note": "The expected causal feature window ends at the sixth following hourly observation, or earlier at a gap/segment boundary."})
        propagation_features = ("temp", "temp_change_1h", "temp_rolling_mean_6h", "temp_deviation_6h")
        fault_features = pd.DataFrame(index=raw.index)
        fault_features["temp"] = faulted["temp"]
        fault_features[list(propagation_features[1:])] = feat[list(propagation_features[1:])]
        for ts in raw.index[(raw.index >= target) & (raw.index <= target + pd.Timedelta(hours=6))]:
            for feature in propagation_features:
                old = float(clean_feature_frame.loc[ts, feature])
                new = float(fault_features.loc[ts, feature])
                if not (np.isclose(old, new, equal_nan=True)):
                    propagation.append({"experiment_id": experiment_id, "timestamp": str(ts), "feature": feature,
                                        "clean_value": old, "faulted_value": new,
                                        "difference": new-old if np.isfinite(old) and np.isfinite(new) else np.nan})
        registry.append({"experiment_id": experiment_id, "fault_type": "point_spike", "variable": "temp",
                         "magnitude": float(magnitude), "start_timestamp": str(target), "end_timestamp": str(target),
                         "duration_observations": 1, "segment_id": raw.loc[target, "segment_id"],
                         "random_seed": random_seed, "model_configurations": 12,
                         "dataset_hash": hashes["model_df"], "status": "EXECUTED_LOCAL_SYNTHETIC"})
        summaries.append({"experiment_id": experiment_id, "magnitude": float(magnitude),
                          "clean_votes": clean_at_target, "faulted_votes": votes,
                          "changed_configuration_predictions": int(diff.sum()),
                          "newly_flagged_configuration_predictions": int(np.sum(changed & ~base)),
                          "no_longer_flagged_configuration_predictions": int(np.sum(~changed & base))})
    if not raw.equals(source_before) or not x_train.equals(train_before):
        raise RuntimeError("source data or training matrix mutated during campaign")
    outputs = {
        "experiment_registry.csv": pd.DataFrame(registry),
        "experiment_summary.csv": pd.DataFrame(summaries),
        "configuration_detection_results.csv": pd.DataFrame(cfg_rows),
        "observation_level_results.csv": pd.DataFrame(obs_rows),
        "event_level_results.csv": pd.DataFrame(event_rows),
        "feature_propagation.csv": pd.DataFrame(propagation),
        "prediction_changes.csv": pd.DataFrame(changes),
        "unaffected_window_checks.csv": pd.DataFrame(unaffected),
        "clean_baseline_reproduction.csv": pd.DataFrame([{
            "prediction_rows": len(clean_parity),
            "saved_prediction_rows": len(saved_clean),
            "matching_configuration_timestamp_predictions": int(clean_parity["matches_saved_prediction"].sum()),
            "mismatching_configuration_timestamp_predictions": int((~clean_parity["matches_saved_prediction"]).sum()),
            "mismatch_timestamps": int(clean_parity.loc[~clean_parity["matches_saved_prediction"], "timestamp"].nunique()),
            "comparison": "same training snapshot, train-only scaler, seasonal feature order, and 12 model configurations"
        }]),
    }
    output_path = Path(output_dir) if output_dir else root / "outputs" / "synthetic_fault_campaign"
    output_path.mkdir(parents=True, exist_ok=True)
    for name, frame in outputs.items():
        frame.to_csv(output_path / name, index=False)
    manifest_out = {"campaign": "controlled_temperature_point_spikes", "status": "EXECUTED_LOCAL_SYNTHETIC",
                    "dataset_hashes": hashes, "phase01_manifest_audit_passed": manifest.get("audit_passed"),
                    "timestamp": str(target), "magnitudes_celsius": list(map(float, magnitudes)),
                    "model_configurations": [c["name"] for c in configs], "random_seed": random_seed,
                    "n_estimators": n_estimators, "feature_order": list(BASE_FEATURES),
                    "scaler": "StandardScaler fit on X_train_multi only",
                    "python_version": platform.python_version(), "pandas_version": pd.__version__,
                    "numpy_version": np.__version__, "scikit_learn_version": sklearn.__version__,
                    "clean_predictions": "saved phase03_model_revalidation/model_predictions.csv",
                    "clean_baseline_mismatches": int((~clean_parity["matches_saved_prediction"]).sum()),
                    "generated_outputs": list(outputs)}
    (output_path / "synthetic_campaign_manifest.json").write_text(
        json.dumps(manifest_out, indent=2, default=str) + "\n", encoding="utf-8")
    return outputs, manifest_out
