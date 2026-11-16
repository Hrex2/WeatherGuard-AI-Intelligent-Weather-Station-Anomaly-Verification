"""Chronological splitting and train-only numeric imputation/scaling."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def chronological_split(frame: pd.DataFrame, cutoff, timezone=None):
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("frame index must be a DatetimeIndex")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("frame timestamps must be unique and sorted")
    boundary = pd.Timestamp(cutoff)
    if frame.index.tz is not None and boundary.tzinfo is None:
        boundary = boundary.tz_localize(timezone or str(frame.index.tz))
    elif frame.index.tz is None and boundary.tzinfo is not None:
        boundary = boundary.tz_localize(None)
    train = frame.loc[frame.index < boundary].copy()
    test = frame.loc[frame.index >= boundary].copy()
    if train.empty or test.empty:
        raise ValueError("cutoff must produce non-empty train and test frames")
    if not train.index.intersection(test.index).empty:
        raise AssertionError("train/test overlap")
    return train, test


def prepare_train_test(train: pd.DataFrame, test: pd.DataFrame, columns, scale=False):
    """Fit medians (and optional scaler) on train only; return matrices and metadata."""
    if not train.index.intersection(test.index).empty:
        raise ValueError("train and test timestamps overlap")
    if train.index.max() >= test.index.min():
        raise ValueError("train must be strictly earlier than test")
    columns = list(columns)
    for name, frame in (("train", train), ("test", test)):
        missing = set(columns) - set(frame.columns)
        if missing:
            raise KeyError(f"{name} is missing columns: {sorted(missing)}")
    train_numeric = train[columns].replace([np.inf, -np.inf], np.nan)
    test_numeric = test[columns].replace([np.inf, -np.inf], np.nan)
    medians = train_numeric.median(numeric_only=True)
    all_missing = medians[medians.isna()].index.tolist()
    if all_missing:
        raise ValueError(f"cannot impute all-missing training columns: {all_missing}")
    x_train = train_numeric.fillna(medians)
    x_test = test_numeric.fillna(medians)
    if x_train.isna().any().any() or x_test.isna().any().any():
        raise ValueError("non-finite or un-imputed values remain")
    scaler = StandardScaler().fit(x_train) if scale else None
    if scaler is not None:
        x_train = pd.DataFrame(scaler.transform(x_train), index=train.index, columns=columns)
        x_test = pd.DataFrame(scaler.transform(x_test), index=test.index, columns=columns)
    return x_train, x_test, {"medians": medians.to_dict(), "scaler": scaler,
                             "train_missing": train[columns].isna().sum().to_dict(),
                             "test_missing": test[columns].isna().sum().to_dict()}
