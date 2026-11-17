"""Portable path and integrity checks for saved research artifacts."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PureWindowsPath

import pandas as pd


E2_COLUMNS = {
    "e2_matched_controls.csv": ["timestamp", "matched_context_id", "matched_context_timestamp", "matching_rule"],
    "e2_multicontext_fault_detail.csv": ["context_id", "experiment_id", "timestamp", "variable", "condition", "synthetic_label", "pair_id", "mode", "window_hours", "robust_z_threshold", "status"],
    "e2_multicontext_fault_paired.csv": ["pair_id", "context_id", "experiment_id", "timestamp", "variable", "mode", "window_hours", "robust_z_threshold", "clean_same_timestamp", "synthetic_faulted", "status_changed_by_injection"],
    "e2_multicontext_fault_summary.csv": ["condition", "experiment_id", "variable", "mode", "window_hours", "robust_z_threshold", "status", "reading_count"],
}
BASELINE_COLUMNS = {
    "synthetic_baseline_response_detail.csv": ["context_id", "experiment_id", "timestamp_utc", "injected_timestamp_units", "configuration_count", "configuration_flag_count", "baseline", "setting", "flagged", "denominator", "response_fraction"],
    "synthetic_baseline_context_summary.csv": ["baseline", "setting", "experiment_id", "context_id", "timestamp_unit_count", "expected_timestamp_units", "mean_timestamp_response_fraction", "context_response_fraction"],
    "synthetic_baseline_response_summary.csv": ["baseline", "setting", "experiment_id", "context_count", "timestamp_unit_count", "mean_context_response_fraction", "minimum_context_response_fraction", "maximum_context_response_fraction"],
    "synthetic_e2_setting_sensitivity.csv": ["experiment_id", "mode", "window_hours", "robust_z_threshold", "screen_rows", "supporting", "conflicting", "unavailable", "supporting_fraction_available"],
    "evidence_coverage_ablation.csv": ["context_id", "experiment_id", "timestamp_utc", "mode", "window_hours", "robust_z_threshold", "combination", "evidence_complete", "evidence_groups", "coverage_limit"],
    "evidence_coverage_ablation_summary.csv": ["combination", "mode", "window_hours", "robust_z_threshold", "units", "complete_units", "coverage_fraction"],
}
BASELINE_INPUT_COLUMNS = {
    "context_selection.csv": ["context_id"],
    "context_scenario_summary.csv": ["context_id", "experiment_id"],
    "context_family_summary.csv": ["context_id", "experiment_id", "family"],
    "changed_and_injected_predictions.csv": ["timestamp", "configuration", "family", "is_candidate", "synthetic_fault_label", "experiment_id"],
    "physical_screening_results.csv": ["timestamp", "variable", "experiment_id", "screening_flag_faulted"],
    "injection_registry.csv": ["experiment_id", "target_variable", "injected_timestamps_json"],
}


def _absolute(path: str | Path) -> Path:
    """Return an absolute lexical path; do not rewrite Windows sandbox aliases."""
    return Path(os.path.abspath(Path(path)))


def _resolved_is_relative(path: str | Path, root: str | Path) -> bool:
    child = str(Path(path).resolve(strict=False))
    parent = str(Path(root).resolve(strict=True))
    # pathlib adds the Windows extended-length prefix only to some resolved paths.
    if child.startswith("\\\\?\\"):
        child = child[4:]
    if parent.startswith("\\\\?\\"):
        parent = parent[4:]
    child, parent = os.path.normcase(os.path.normpath(child)), os.path.normcase(os.path.normpath(parent))
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:
        return False


def resolve_repo_path(repo_root: str | Path, relative_path: str | Path, *,
                      expected: str | None = None, must_exist: bool = True) -> Path:
    """Resolve POSIX or Windows relative paths safely beneath the repository root."""
    root = _absolute(repo_root)
    if not root.is_dir():
        raise FileNotFoundError(f"Repository root does not exist: {root}")
    resolved_root = root.resolve(strict=True)
    raw = str(relative_path)
    windows = PureWindowsPath(raw)
    if not raw or windows.is_absolute() or windows.drive or raw.startswith(("/", "\\")):
        raise ValueError(f"Expected a repository-relative path, got absolute/empty path: {raw!r}")
    parts = raw.replace("\\", "/").split("/")
    if any(part == ".." for part in parts):
        raise ValueError(f"Repository-relative path may not traverse parent directories: {raw!r}")
    target = _absolute(root.joinpath(*[part for part in parts if part not in ("", ".")]))
    if not _resolved_is_relative(target, resolved_root):
        raise ValueError(f"Path resolves outside repository root: {raw!r}")
    if must_exist and not target.exists():
        raise FileNotFoundError(f"Research artifact path does not exist: {raw!r} (resolved to {target})")
    if expected == "file" and target.exists() and not target.is_file():
        raise ValueError(f"Expected a file at {raw!r}, found a non-file path")
    if expected == "directory" and target.exists() and not target.is_dir():
        raise ValueError(f"Expected a directory at {raw!r}, found a non-directory path")
    return target


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_record(repo_root: str | Path, path: str | Path, *, experiment_id: str | None = None,
                    source_artifact_references: list[str] | None = None) -> dict:
    root = _absolute(repo_root)
    target = _absolute(path)
    if not target.is_file() or not _resolved_is_relative(target, root):
        raise ValueError(f"Artifact is outside repository root: {target}")
    record = {"path": target.relative_to(root).as_posix(), "sha256": sha256_file(target),
              "size_bytes": target.stat().st_size}
    if target.suffix.lower() == ".csv":
        frame = pd.read_csv(target)
        record.update({"rows": int(len(frame)), "columns": frame.columns.tolist()})
    if experiment_id is not None:
        record["experiment_id"] = experiment_id
    if source_artifact_references is not None:
        record["source_artifact_references"] = list(source_artifact_references)
    return record


def verify_artifact_record(repo_root: str | Path, record: dict, *,
                           required_columns: list[str] | None = None) -> pd.DataFrame | None:
    target = resolve_repo_path(repo_root, record["path"], expected="file")
    if target.stat().st_size != record.get("size_bytes"):
        raise ValueError(f"Artifact size mismatch: {record['path']}")
    if sha256_file(target) != record.get("sha256"):
        raise ValueError(f"Artifact SHA-256 mismatch: {record['path']}")
    if target.suffix.lower() != ".csv":
        return None
    frame = pd.read_csv(target)
    columns = record.get("columns")
    if columns is not None and frame.columns.tolist() != columns:
        raise ValueError(f"Artifact ordered columns mismatch: {record['path']}")
    if record.get("rows") is not None and len(frame) != record["rows"]:
        raise ValueError(f"Artifact row count mismatch: {record['path']}")
    if required_columns and not set(required_columns).issubset(frame.columns):
        missing = sorted(set(required_columns) - set(frame.columns))
        raise ValueError(f"Artifact required columns missing in {record['path']}: {missing}")
    return frame


def verify_e2_manifest(repo_root: str | Path, campaign_dir: str | Path,
                       evaluation_dir: str | Path, expected_dataset_hashes: dict) -> tuple[dict, dict[str, pd.DataFrame]]:
    root = _absolute(repo_root)
    campaign = _absolute(campaign_dir)
    evaluation = _absolute(evaluation_dir)
    manifest_path = evaluation / "e2_validation_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Required reviewed E2 manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared_dir = manifest.get("output_directory")
    if not declared_dir or declared_dir != evaluation.name or evaluation.parent != campaign:
        raise ValueError("E2 manifest evaluation directory does not match the directory being loaded")
    if manifest.get("campaign_id") != json.loads((campaign / "campaign_manifest.json").read_text(encoding="utf-8")).get("campaign_id"):
        raise ValueError("E2 manifest campaign identity does not match the verified campaign")
    if manifest.get("dataset_hashes") != expected_dataset_hashes:
        raise ValueError("E2 manifest dataset hashes do not match the verified campaign")
    integrity = manifest.get("output_integrity")
    declared_outputs = manifest.get("outputs")
    if (manifest.get("status") != "EXECUTED_EXPLORATORY_SYNTHETIC_E2"
            or not isinstance(integrity, dict) or not isinstance(declared_outputs, list)
            or len(declared_outputs) != len(set(declared_outputs))
            or set(declared_outputs) != set(integrity) or set(declared_outputs) != set(E2_COLUMNS)):
        raise ValueError("E2 manifest has an incomplete output artifact set")
    tables = {}
    for name in declared_outputs:
        if name not in E2_COLUMNS:
            raise ValueError(f"E2 manifest declares an unexpected output: {name}")
        target = resolve_repo_path(root, (evaluation / name).relative_to(root).as_posix(), expected="file")
        record = integrity[name]
        if sha256_file(target) != record.get("sha256"):
            raise ValueError(f"E2 output SHA-256 mismatch: {name}")
        if record.get("size_bytes") is not None and target.stat().st_size != record["size_bytes"]:
            raise ValueError(f"E2 output size mismatch: {name}")
        frame = pd.read_csv(target)
        if len(frame) != record.get("rows"):
            raise ValueError(f"E2 output row count mismatch: {name}")
        if record.get("columns") is not None and frame.columns.tolist() != record["columns"]:
            raise ValueError(f"E2 output ordered columns mismatch: {name}")
        missing = set(E2_COLUMNS[name]) - set(frame.columns)
        if missing:
            raise ValueError(f"E2 output required columns missing in {name}: {sorted(missing)}")
        tables[name] = frame
    return manifest, tables


def verify_baseline_manifest(repo_root: str | Path, campaign_dir: str | Path,
                             output_dir: str | Path, expected_dataset_hashes: dict) -> tuple[dict, dict[str, pd.DataFrame]]:
    root = _absolute(repo_root)
    campaign = _absolute(campaign_dir)
    output = _absolute(output_dir)
    path = output / "synthetic_baseline_comparison_manifest.json"
    sidecar = output / "synthetic_baseline_comparison_manifest.integrity.json"
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError("Baseline review manifest or its integrity sidecar is missing")
    sidecar_data = json.loads(sidecar.read_text(encoding="utf-8"))
    if sidecar_data.get("manifest_path") != path.relative_to(root).as_posix():
        raise ValueError("Baseline manifest sidecar points at a different manifest")
    if sidecar_data.get("sha256") != sha256_file(path):
        raise ValueError("Baseline manifest SHA-256 does not match its integrity sidecar")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("campaign_id") != json.loads((campaign / "campaign_manifest.json").read_text(encoding="utf-8")).get("campaign_id"):
        raise ValueError("Baseline manifest experiment identity does not match the campaign")
    if manifest.get("dataset_hashes") != expected_dataset_hashes:
        raise ValueError("Baseline manifest dataset hashes do not match the verified campaign")
    if manifest.get("output_directory") != output.name or output.parent != campaign:
        raise ValueError("Baseline manifest output directory does not match the directory being loaded")
    if manifest.get("schema_version") != 2 or manifest.get("experiment_id") != manifest.get("campaign_id"):
        raise ValueError("Baseline manifest schema or experiment identity is invalid")
    inputs = manifest.get("inputs")
    outputs = manifest.get("outputs")
    if not isinstance(inputs, list) or not inputs or not isinstance(outputs, list) or not outputs:
        raise ValueError("Baseline manifest has an incomplete input or output artifact set")
    input_paths = {record.get("path") for record in inputs}
    if any(record.get("experiment_id") != manifest.get("experiment_id") for record in inputs + outputs):
        raise ValueError("Baseline artifact experiment identity is inconsistent")
    required_inputs = {
        (campaign / "campaign_manifest.json").relative_to(root).as_posix(),
        (campaign / "context_selection.csv").relative_to(root).as_posix(),
        (campaign / "context_scenario_summary.csv").relative_to(root).as_posix(),
        (campaign / "context_family_summary.csv").relative_to(root).as_posix(),
        (campaign / "e2_validation_review_1" / "e2_validation_manifest.json").relative_to(root).as_posix(),
        *{(campaign / "e2_validation_review_1" / name).relative_to(root).as_posix() for name in E2_COLUMNS},
    }
    expected_context_count = manifest.get("context_count")
    required_run_files = {"changed_and_injected_predictions.csv", "physical_screening_results.csv",
                          "injection_registry.csv", "run_metadata.json"}
    campaign_manifest = json.loads((campaign / "campaign_manifest.json").read_text(encoding="utf-8"))
    contexts = campaign_manifest.get("contexts", [])
    if len(contexts) != expected_context_count:
        raise ValueError("Baseline context count does not match its campaign manifest")
    for context in contexts:
        run_dir = resolve_repo_path(root, context["run_directory"], expected="directory")
        run_prefix = run_dir.relative_to(root).as_posix()
        for filename in required_run_files:
            if f"{run_prefix}/{filename}" not in input_paths:
                raise ValueError(f"Baseline manifest omits context input: {run_prefix}/{filename}")
    if not required_inputs.issubset(input_paths):
        raise ValueError("Baseline manifest omits required campaign or reviewed E2 inputs")
    for record in inputs:
        required = BASELINE_INPUT_COLUMNS.get(Path(record["path"]).name)
        verify_artifact_record(root, record, required_columns=required)
    tables = {}
    for record in outputs:
        if record.get("code_revision") != manifest.get("code_revision"):
            raise ValueError(f"Baseline output code revision mismatch: {record.get('path')}")
        if set(record.get("source_artifact_references", [])) != input_paths:
            raise ValueError(f"Baseline output has invalid source references: {record.get('path')}")
        name = Path(record["path"]).name
        frame = verify_artifact_record(root, record, required_columns=BASELINE_COLUMNS.get(name))
        tables[Path(record["path"]).name] = frame
    if set(manifest.get("output_files", [])) != set(tables):
        raise ValueError("Baseline manifest output file list does not match its integrity records")
    required_outputs = set(BASELINE_COLUMNS)
    if set(tables) != required_outputs:
        raise ValueError("Baseline manifest output set is incomplete or unexpected")
    return manifest, tables


def load_verified_multicontext_results(repo_root: str | Path, phase01_hashes: dict) -> dict:
    """Load PR #2 tables only when campaign, source, E2 and baseline artifacts verify."""
    root = _absolute(repo_root)
    campaign_dir = root / "research_results" / "fault_matrix_multicontext_46ae5d119d"
    campaign_path = campaign_dir / "campaign_manifest.json"
    campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
    campaign_hashes = campaign.get("dataset_hashes", {})
    expected = {"model_df": phase01_hashes.get("observations"),
                "X_train_multi": phase01_hashes.get("train"),
                "X_test_multi": phase01_hashes.get("test")}
    if campaign_hashes != expected:
        raise ValueError("Campaign dataset hashes do not match the verified Phase 01 snapshots")
    baseline_manifest, baseline_outputs = verify_baseline_manifest(
        root, campaign_dir, campaign_dir / "baseline_review_1", campaign_hashes)
    e2_manifest, e2_outputs = verify_e2_manifest(
        root, campaign_dir, campaign_dir / "e2_validation_review_1", campaign_hashes)
    # These campaign summaries are source inputs in the verified baseline manifest.
    return {"campaign": campaign, "baseline_manifest": baseline_manifest,
            "baseline_outputs": baseline_outputs, "e2_manifest": e2_manifest,
            "e2_outputs": e2_outputs,
            "context_summary": pd.read_csv(campaign_dir / "context_scenario_summary.csv"),
            "family_context_summary": pd.read_csv(campaign_dir / "context_family_summary.csv")}


def multicontext_artifact_state(repo_root: str | Path, phase01_hashes: dict) -> dict:
    try:
        return {"verified": True,
                "bundle": load_verified_multicontext_results(repo_root, phase01_hashes),
                "warning": None}
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return {"verified": False, "bundle": None,
                "warning": f"Research results are hidden because artifact integrity verification failed: {exc}"}
