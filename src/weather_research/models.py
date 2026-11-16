"""Explicit definitions and timestamp-aligned evaluation for historical models."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM


def default_model_configs(random_seed=42):
    return ([{"family": "IsolationForest", "name": f"IF_{c}", "parameter": "contamination",
              "value": c, "random_seed": random_seed} for c in (0.01, 0.02, 0.03, 0.05)]
            + [{"family": "LocalOutlierFactor", "name": f"LOF_{n}", "parameter": "n_neighbors",
                "value": n, "random_seed": random_seed} for n in (10, 20, 30, 50)]
            + [{"family": "OneClassSVM", "name": f"SVM_{nu}", "parameter": "nu",
                "value": nu, "random_seed": random_seed} for nu in (0.01, 0.02, 0.03, 0.05)])


def fit_predict_configurations(x_train_unscaled, x_test_unscaled,
                               x_train_scaled, x_test_scaled,
                               configs=None, n_estimators=200):
    """Fit all configured models and return long prediction table indexed by time.

    Call explicitly; this function does not run during notebook import/setup.
    Scaling must already be fitted on training data only.
    """
    configs = configs or default_model_configs()
    frames = [x_train_unscaled, x_test_unscaled, x_train_scaled, x_test_scaled]
    if any(not isinstance(x, pd.DataFrame) for x in frames):
        raise TypeError("model inputs must be pandas DataFrames")
    if any(frame.index.has_duplicates or not frame.index.is_monotonic_increasing for frame in frames):
        raise ValueError("all model indexes must be unique and chronologically sorted")
    if not x_train_unscaled.columns.equals(x_train_scaled.columns) or not x_test_unscaled.columns.equals(x_test_scaled.columns):
        raise ValueError("scaled and unscaled feature columns must match exactly")
    if not x_train_unscaled.index.equals(x_train_scaled.index):
        raise ValueError("scaled and unscaled train indexes differ")
    if not x_test_unscaled.index.equals(x_test_scaled.index):
        raise ValueError("scaled and unscaled test indexes differ")
    if len(x_train_unscaled) == 0 or len(x_test_unscaled) == 0:
        raise ValueError("train and test inputs must be non-empty")
    if not x_train_unscaled.index.intersection(x_test_unscaled.index).empty:
        raise ValueError("training and test timestamps overlap")
    if x_train_unscaled.index.max() >= x_test_unscaled.index.min():
        raise ValueError("training timestamps must precede test timestamps")
    for name, frame in (("train",x_train_unscaled),("test",x_test_unscaled),
                        ("scaled train",x_train_scaled),("scaled test",x_test_scaled)):
        if not np.isfinite(frame.to_numpy(dtype=float)).all():
            raise ValueError(f"{name} contains non-finite model inputs")
    results = []
    names=[cfg.get("name") for cfg in configs]
    if any(not name for name in names) or len(set(names))!=len(names):
        raise ValueError("configuration names must be present and unique")
    for cfg in configs:
        family, value = cfg["family"], cfg["value"]
        if family == "IsolationForest":
            model = IsolationForest(n_estimators=n_estimators, contamination=value,
                                    random_state=cfg.get("random_seed", 42), n_jobs=-1)
            model.fit(x_train_unscaled)
            pred = model.predict(x_test_unscaled)
        elif family == "LocalOutlierFactor":
            if value >= len(x_train_scaled):
                raise ValueError("LOF n_neighbors must be less than train size")
            model = LocalOutlierFactor(n_neighbors=value, contamination=0.02, novelty=True)
            model.fit(x_train_scaled.to_numpy())
            pred = model.predict(x_test_scaled.to_numpy())
        elif family == "OneClassSVM":
            model = OneClassSVM(kernel="rbf", gamma="scale", nu=value)
            model.fit(x_train_scaled)
            pred = model.predict(x_test_scaled)
        else:
            raise ValueError(f"unsupported model family: {family}")
        results.append(pd.DataFrame({"configuration": cfg["name"], "family": family,
                                     "parameter": cfg["parameter"], "parameter_value": value,
                                     "prediction": pred.astype(int), "is_candidate": pred == -1},
                                    index=x_test_unscaled.index))
    out = pd.concat(results).rename_axis("timestamp").reset_index()
    if out.duplicated(["timestamp", "configuration"]).any():
        raise AssertionError("duplicate timestamp/configuration predictions")
    return out.set_index("timestamp").sort_index()


def stability_summary(predictions: pd.DataFrame):
    required = {"configuration", "family", "is_candidate"}
    if not required.issubset(predictions.columns):
        raise KeyError(f"predictions need columns: {sorted(required)}")
    long = predictions.rename_axis("timestamp").reset_index()
    if long.duplicated(["timestamp", "configuration"]).any():
        raise ValueError("duplicate timestamp/configuration predictions")
    if long["is_candidate"].isna().any():
        raise ValueError("missing predictions cannot be treated as normal votes")
    if long[["configuration","family"]].isna().any().any():
        raise ValueError("configuration and family metadata cannot be missing")
    if not long["is_candidate"].isin([True,False,0,1]).all():
        raise ValueError("is_candidate must contain boolean/0-1 values")
    per_config=long.groupby("configuration")["timestamp"].agg(lambda x:frozenset(x))
    reference=per_config.iloc[0]
    if any(times!=reference for times in per_config.iloc[1:]):
        raise ValueError("every configuration must predict the exact same test timestamps")
    if set(long["family"].unique())!={"IsolationForest","LocalOutlierFactor","OneClassSVM"}:
        raise ValueError("family-balanced stability requires all three model families")
    config_family=long.groupby("configuration")["family"].nunique()
    if config_family.gt(1).any():
        raise ValueError("a configuration maps to more than one model family")
    wide = long.pivot(index="timestamp", columns="configuration", values="is_candidate")
    metadata = long.drop_duplicates("configuration").set_index("configuration")
    votes = wide.astype(bool).astype(int)
    family_votes = pd.DataFrame(index=votes.index)
    for family, names in metadata.groupby("family").groups.items():
        family_votes[f"{family}_votes"] = votes[list(names)].sum(axis=1)
        family_votes[f"{family}_fraction"] = votes[list(names)].mean(axis=1)
    result = pd.concat([votes.add_prefix("vote_"), family_votes], axis=1)
    result["configuration_votes"] = votes.sum(axis=1)
    result["family_balanced_agreement"] = family_votes.filter(like="_fraction").mean(axis=1)
    result["candidate_any"] = votes.any(axis=1)
    configs = list(votes.columns)
    jac = pd.DataFrame(index=configs, columns=configs, dtype=float)
    sets = {
    c: set(votes.index[votes[c].eq(1)])
    for c in configs
}
    for a in configs:
        for b in configs:
            union = sets[a] | sets[b]
            jac.loc[a, b] = len(sets[a] & sets[b]) / len(union) if union else np.nan
    return result, jac
