"""Reproduce the saved-versus-local prediction comparison and export mismatches."""
from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from services.data_service import load_project_data
from services.model_service import FEATURE_ORDER, run_saved_protocol
from weather_research.models import default_model_configs


def investigate(root: Path):
    data, manifest, hashes = load_project_data(root)
    local, protocol = run_saved_protocol(data["train"], data["test"])
    saved = data["predictions"].set_index(["timestamp", "configuration"]).sort_index()
    reproduced = local.reset_index().set_index(["timestamp", "configuration"]).sort_index()
    if not saved.index.equals(reproduced.index):
        raise ValueError("Saved and reproduced prediction grids do not align exactly")
    mismatch = saved.loc[saved.is_candidate.astype(bool).ne(reproduced.is_candidate.astype(bool))].copy()
    rows = mismatch.reset_index()
    test_matrix = data["test"].copy()
    test_matrix["month_sin"] = np.sin(2 * np.pi * test_matrix.index.month / 12)
    test_matrix["month_cos"] = np.cos(2 * np.pi * test_matrix.index.month / 12)
    test_matrix = test_matrix.loc[:, FEATURE_ORDER]
    rows["saved_label"] = rows.pop("is_candidate").astype(bool)
    rows["recomputed_label"] = [bool(reproduced.loc[(r.timestamp, r.configuration), "is_candidate"])
                                for r in rows.itertuples()]
    rows["prediction_changed"] = True
    rows["feature_vector_json"] = [json.dumps(test_matrix.loc[r.timestamp].to_dict(), sort_keys=True)
                                   for r in rows.itertuples()]
    rows["feature_order_json"] = json.dumps(list(FEATURE_ORDER))
    config_map = {c["name"]: c for c in default_model_configs()}
    rows["model_parameters_json"] = [json.dumps(config_map[name], sort_keys=True)
                                     for name in rows.configuration]
    rows["dataset_identity_json"] = json.dumps({"observations_sha256": hashes["observations"],
        "train_sha256": hashes["train"], "test_sha256": hashes["test"],
        "phase01_manifest_audit_passed": manifest.get("audit_passed") is True}, sort_keys=True)
    rows["training_rows"] = len(data["train"])
    rows["training_start"] = str(data["train"].index.min())
    rows["training_end"] = str(data["train"].index.max())
    rows["scaler_information"] = protocol["scaler"]
    rows["scaler_fit_scope"] = "training matrix only; local scaler refitted for this reproduction"
    rows["python_version"] = platform.python_version()
    rows["numpy_version"] = np.__version__
    rows["pandas_version"] = pd.__version__
    rows["scikit_learn_version"] = sklearn.__version__
    rows["interpretation"] = "Saved artifact differs from a current-environment refit; cause not identified by available saved estimator/scaler provenance."
    output = root / "research_results"
    output.mkdir(exist_ok=True)
    path = output / "prediction_mismatch_investigation.csv"
    rows.to_csv(path, index=False)
    summary = {**protocol, "saved_prediction_rows": int(len(saved)),
               "matching_rows": int(len(saved) - len(rows)), "mismatching_rows": int(len(rows)),
               "mismatch_timestamps": int(rows.timestamp.nunique()),
               "mismatch_by_family": rows.groupby("family").size().to_dict(),
               "mismatch_by_configuration": rows.groupby("configuration").size().to_dict(),
               "finding": "The discrepancy is reproduced, but cannot be causally attributed because historical estimator/scaler objects, exact fit provenance, and original package versions are absent.",
               "row_level_csv": str(path.relative_to(root).as_posix())}
    (output / "prediction_mismatch_investigation.json").write_text(
        json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    return rows, summary


if __name__ == "__main__":
    project_root = PROJECT_ROOT
    mismatch_rows, report = investigate(project_root)
    print(json.dumps({k: report[k] for k in ("saved_prediction_rows", "matching_rows", "mismatching_rows", "mismatch_timestamps", "mismatch_by_family", "mismatch_by_configuration", "finding", "row_level_csv")}, indent=2))
