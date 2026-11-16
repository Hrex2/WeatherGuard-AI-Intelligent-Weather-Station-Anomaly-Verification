"""Read-only loaders for verified research snapshots and saved outputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_project_data(root):
    """Read bundled processed observations, verified predictions, and summaries."""
    root = Path(root)
    verified = root / "verified_phase01"
    phase03 = root / "phase03_model_revalidation"
    required = {
        "observations": verified / "model_df.csv",
        "train": verified / "X_train_multi.csv",
        "test": verified / "X_test_multi.csv",
        "predictions": phase03 / "model_predictions.csv",
        "stability": phase03 / "stability_results_verified.csv",
        "episodes": phase03 / "episode_profiles_1h.csv",
        "configuration_results": phase03 / "configuration_results.csv",
    }
    absent = [str(path) for path in required.values() if not path.is_file()]
    if absent:
        raise FileNotFoundError("Required saved research artifacts are missing: " + ", ".join(absent))
    data = {
        "observations": pd.read_csv(required["observations"], index_col=0, parse_dates=True),
        "train": pd.read_csv(required["train"], index_col=0, parse_dates=True),
        "test": pd.read_csv(required["test"], index_col=0, parse_dates=True),
        "predictions": pd.read_csv(required["predictions"], parse_dates=["timestamp"]),
        "stability": pd.read_csv(required["stability"], parse_dates=["timestamp"]),
        "episodes": pd.read_csv(required["episodes"], parse_dates=["start", "end"]),
        "configuration_results": pd.read_csv(required["configuration_results"]),
    }
    tz = str(data["observations"].index.tz)
    for name in ("predictions", "stability"):
        data[name]["timestamp"] = pd.to_datetime(data[name]["timestamp"], utc=True).dt.tz_convert(tz)
    for name, frame in data.items():
        if name in {"observations", "train", "test"}:
            if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.has_duplicates:
                raise ValueError(f"{name} must use a unique timestamp index")
    manifest_path = verified / "phase01_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Required Phase 01 manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("audit_passed") is not True:
        raise ValueError(f"Phase 01 manifest does not record a passed integrity audit: {manifest_path}")
    manifest_files = {
        "observations": ("model_df", data["observations"]),
        "train": ("X_train_multi", data["train"]),
        "test": ("X_test_multi", data["test"]),
    }
    hashes = {}
    for label, (dataset_name, frame) in manifest_files.items():
        path = required[label]
        entry = manifest.get("datasets", {}).get(dataset_name)
        if not isinstance(entry, dict) or not entry.get("sha256"):
            raise ValueError(f"Manifest entry or expected SHA-256 is missing for {path.name}")
        actual_hash = sha256_file(path)
        if actual_hash.lower() != str(entry["sha256"]).lower():
            raise ValueError(f"SHA-256 verification failed for {path.name}: expected {entry['sha256']}, got {actual_hash}")
        if len(frame) != entry.get("rows"):
            raise ValueError(f"Manifest row count mismatch for {path.name}: expected {entry.get('rows')}, got {len(frame)}")
        if list(frame.columns) != entry.get("columns"):
            raise ValueError(f"Manifest column order mismatch for {path.name}")
        hashes[label] = actual_hash
    return data, manifest, hashes


def prediction_wide(predictions: pd.DataFrame) -> pd.DataFrame:
    """Return timestamp-indexed candidate votes after checking exact pairs."""
    required = {"timestamp", "configuration", "is_candidate"}
    if not required.issubset(predictions.columns):
        raise KeyError(f"prediction table requires {sorted(required)}")
    if predictions.duplicated(["timestamp", "configuration"]).any():
        raise ValueError("saved predictions contain duplicate timestamp/configuration pairs")
    if predictions["is_candidate"].isna().any():
        raise ValueError("saved predictions contain missing anomaly labels")
    return predictions.pivot(index="timestamp", columns="configuration", values="is_candidate").sort_index()
