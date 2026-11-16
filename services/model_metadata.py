"""Data-backed model education metadata for the WeatherGuard UI."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM

from services.model_service import FEATURE_ORDER
from weather_research.models import build_estimator, default_model_configs

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "research_content" / "model_profiles.json"
FEATURE_GROUPS = {
    "Current weather measurements": ["temp", "dwpt", "rhum", "prcp", "wspd", "pres"],
    "Recent temperature behaviour": ["temp_change_1h", "temp_rolling_mean_6h", "temp_deviation_6h"],
    "Seasonal time information": ["month_sin", "month_cos"],
}
FEATURE_LABELS = {
    "temp": ("Air temperature", "°C"), "dwpt": ("Dew point", "°C"),
    "rhum": ("Relative humidity", "%"), "prcp": ("Precipitation", "mm"),
    "wspd": ("Wind speed", "km/h"), "pres": ("Air pressure", "hPa"),
    "temp_change_1h": ("Temperature change between observations", "°C"),
    "temp_rolling_mean_6h": ("Previous six-observation temperature mean", "°C"),
    "temp_deviation_6h": ("Temperature minus previous six-observation mean", "°C"),
    "month_sin": ("Month-of-year sine encoding", "unitless"),
    "month_cos": ("Month-of-year cosine encoding", "unitless"),
}
ESTIMATORS = {
    "IsolationForest": IsolationForest,
    "LocalOutlierFactor": LocalOutlierFactor,
    "OneClassSVM": OneClassSVM,
}


def build_model_education(data):
    """Return profiles, configurations and dataset details from source APIs/data."""
    profiles = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    configs = default_model_configs()
    config_rows = data["configuration_results"].copy()
    config_rows["family"] = config_rows["family"].astype(str)
    config_lookup = config_rows.set_index("configuration").to_dict("index")
    output = {}
    for family, estimator_class in ESTIMATORS.items():
        family_configs = [item for item in configs if item["family"] == family]
        profile = dict(profiles[family])
        profile["family"] = family
        profile["configs"] = []
        profile["defaults"] = estimator_class().get_params(deep=False)
        profile["preprocessing"] = (
            "StandardScaler is fitted on training rows only and applied to train and test rows."
            if family != "IsolationForest" else
            "No scaling: this protocol fits and predicts with the unscaled feature matrix."
        )
        for config in family_configs:
            saved = config_lookup.get(config["name"], {})
            if not saved or "anomalies" not in saved or "anomaly_percentage" not in saved:
                raise ValueError(f"Saved model configuration result is missing: {config['name']}")
            if pd.isna(saved["anomalies"]) or pd.isna(saved["anomaly_percentage"]):
                raise ValueError(f"Saved result metrics are incomplete for configuration: {config['name']}")
            params = build_estimator(config).get_params(deep=False)
            profile["configs"].append({
                **config,
                "anomalies": int(saved.get("anomalies", 0)),
                "anomaly_percentage": float(saved.get("anomaly_percentage", 0.0)),
                "parameters": params,
            })
        output[family] = profile

    train, test = data["train"], data["test"]
    expected_base = list(FEATURE_ORDER[:9])
    if list(train.columns) != expected_base or list(test.columns) != expected_base:
        raise ValueError("Loaded train/test columns do not match the model protocol's nine saved features")
    return {
        "profiles": output,
        "configurations": configs,
        "feature_order": list(FEATURE_ORDER),
        "feature_groups": FEATURE_GROUPS,
        "feature_labels": FEATURE_LABELS,
        "train_rows": len(train), "test_rows": len(test), "input_features": len(FEATURE_ORDER),
        "training_start": train.index.min(), "training_end": train.index.max(),
        "testing_start": test.index.min(), "testing_end": test.index.max(),
        "training_columns": list(train.columns), "test_columns": list(test.columns),
    }
