"""Explicit model execution over verified historical train/test snapshots."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import time

import numpy as np
import pandas as pd
import sklearn
from sklearn.preprocessing import StandardScaler

from weather_research.models import default_model_configs, fit_predict_configurations

FEATURE_ORDER = ("temp", "dwpt", "rhum", "prcp", "wspd", "pres",
                 "temp_change_1h", "temp_rolling_mean_6h", "temp_deviation_6h",
                 "month_sin", "month_cos")


def _seasonal(frame):
    base = frame.loc[:, FEATURE_ORDER[:9]].copy(deep=True)
    base["month_sin"] = np.sin(2 * np.pi * base.index.month / 12)
    base["month_cos"] = np.cos(2 * np.pi * base.index.month / 12)
    base = base.loc[:, FEATURE_ORDER]
    if not np.isfinite(base.to_numpy(dtype=float)).all():
        raise ValueError("The eleven-feature model matrix contains non-finite values")
    return base


def run_saved_protocol(train, test, n_estimators=200, random_seed=42):
    """Fit the existing 12 configs on train only and return predictions + provenance."""
    started = time.perf_counter()
    train_matrix, test_matrix = _seasonal(train), _seasonal(test)
    scaler = StandardScaler().fit(train_matrix.to_numpy(dtype=float))
    scaled_train = pd.DataFrame(scaler.transform(train_matrix.to_numpy(dtype=float)),
                                index=train_matrix.index, columns=FEATURE_ORDER)
    scaled_test = pd.DataFrame(scaler.transform(test_matrix.to_numpy(dtype=float)),
                               index=test_matrix.index, columns=FEATURE_ORDER)
    preds = fit_predict_configurations(train_matrix, test_matrix, scaled_train, scaled_test,
                                       default_model_configs(random_seed), n_estimators)
    elapsed = time.perf_counter() - started
    config_json = json.dumps(default_model_configs(random_seed), sort_keys=True)
    return preds, {
        "run_type": "NEW_LOCAL_EXECUTION",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": random_seed,
        "n_estimators": n_estimators,
        "feature_order": list(FEATURE_ORDER),
        "configuration_sha256": hashlib.sha256(config_json.encode()).hexdigest(),
        "training_start": str(train.index.min()),
        "training_end": str(train.index.max()),
        "testing_start": str(test.index.min()),
        "testing_end": str(test.index.max()),
        "train_rows": len(train),
        "test_rows": len(test),
        "scaler": "StandardScaler fitted only to 11-feature training matrix",
        "scikit_learn_version": sklearn.__version__,
        "elapsed_seconds": elapsed,
    }
