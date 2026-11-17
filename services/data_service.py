"""Read-only loaders for verified research snapshots and saved outputs."""
from __future__ import annotations

import hashlib
import json
import csv
from pathlib import Path

import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _csv_identity_counts(path: Path, timestamp_column: str | None, config_column: str | None):
    row_count = 0
    timestamps = set()
    configurations = set()
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        for row in reader:
            row_count += 1
            if timestamp_column:
                timestamps.add(row.get(timestamp_column, ""))
            if config_column:
                configurations.add(row.get(config_column, ""))
    return columns, row_count, (len(timestamps) if timestamp_column else None), (len(configurations) if config_column else None)


def write_phase03_integrity_manifest(phase03: Path, dataset_hashes: dict,
                                    manifest_created_revision: str | None = None) -> dict:
    """Hash saved Phase 03 CSV artifacts without asserting their historical origin."""
    phase03 = Path(phase03)
    artifacts = []
    for path in sorted(phase03.glob("*.csv")):
        columns, row_count, _, _ = _csv_identity_counts(path, None, None)
        timestamp_column = next((name for name in ("timestamp", "start", "candidate_time") if name in columns), None)
        config_column = next((name for name in ("configuration", "name") if name in columns), None)
        _, _, timestamp_count, configuration_count = _csv_identity_counts(path, timestamp_column, config_column)
        artifacts.append({
            "filename": path.name, "sha256": sha256_file(path), "rows": row_count,
            "columns": columns,
            "unique_timestamp_count": timestamp_count,
            "timestamp_column": timestamp_column,
            "configuration_count": configuration_count,
            "configuration_column": config_column,
        })
    payload = {
        "manifest_version": 1,
        "dataset_reference_hashes": dict(dataset_hashes),
        "manifest_created_revision": manifest_created_revision,
        "artifact_generation_revision": None,
        "audit_status": "HASHED_INTEGRITY_ONLY_HISTORICAL_PROVENANCE_UNKNOWN",
        "audit_scope": "File identity, row counts, ordered columns, available timestamp/configuration counts and Phase 01 snapshot linkage.",
        "artifacts": artifacts,
    }
    manifest_path = phase03 / "phase03_integrity_manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def verify_phase03_integrity(phase03: Path, dataset_hashes: dict | None = None) -> dict:
    """Verify saved Phase 03 artifacts against their identity manifest."""
    phase03 = Path(phase03)
    manifest_path = phase03 / "phase03_integrity_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Required Phase 03 integrity manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("audit_status") != "HASHED_INTEGRITY_ONLY_HISTORICAL_PROVENANCE_UNKNOWN":
        raise ValueError("Phase 03 manifest must preserve the historical provenance limitation")
    if dataset_hashes is not None and manifest.get("dataset_reference_hashes") != dataset_hashes:
        raise ValueError("Phase 03 manifest references different Phase 01 snapshot hashes")
    recorded = {entry["filename"]: entry for entry in manifest.get("artifacts", [])}
    current_files = {path.name for path in phase03.glob("*.csv")}
    if current_files != set(recorded):
        missing = sorted(set(recorded) - current_files)
        unmanifested = sorted(current_files - set(recorded))
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unmanifested:
            details.append("unmanifested: " + ", ".join(unmanifested))
        raise ValueError("Phase 03 artifact file list does not match its integrity manifest (" + "; ".join(details) + ")")
    for filename, entry in recorded.items():
        path = phase03 / filename
        if sha256_file(path) != entry.get("sha256"):
            raise ValueError(f"Phase 03 SHA-256 verification failed for {filename}")
        columns, row_count, timestamp_count, configuration_count = _csv_identity_counts(
            path, entry.get("timestamp_column"), entry.get("configuration_column"))
        if row_count != entry.get("rows") or columns != entry.get("columns"):
            raise ValueError(f"Phase 03 row count or ordered columns mismatch for {filename}")
        if entry.get("timestamp_column") and timestamp_count != entry.get("unique_timestamp_count"):
            raise ValueError(f"Phase 03 timestamp count mismatch for {filename}")
        if entry.get("configuration_column") and configuration_count != entry.get("configuration_count"):
            raise ValueError(f"Phase 03 configuration count mismatch for {filename}")
    return manifest


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
    phase03_manifest = verify_phase03_integrity(phase03, hashes)
    hashes.update({"phase03:" + item["filename"]: item["sha256"]
                   for item in phase03_manifest["artifacts"]})
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
