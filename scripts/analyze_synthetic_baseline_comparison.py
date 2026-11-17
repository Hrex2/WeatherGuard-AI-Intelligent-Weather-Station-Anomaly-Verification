"""Audit saved synthetic responses without fitting or rerunning the campaign."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.research_artifact_integrity import (artifact_record, resolve_repo_path,
    sha256_file, verify_e2_manifest)

CAMPAIGN = ROOT / "research_results" / "fault_matrix_multicontext_46ae5d119d"
BASELINES = (4, 6, 8, 10, 12)
EXPECTED_FAMILIES = {"IsolationForest", "LocalOutlierFactor", "OneClassSVM"}
REQUIRED_RUN_INPUTS = ("changed_and_injected_predictions.csv", "physical_screening_results.csv",
                       "injection_registry.csv", "run_metadata.json")
E2_STATUS = {"SUPPORTING", "CONFLICTING", "NO_DETECTED_EVIDENCE", "UNAVAILABLE"}


def _bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series
    normalized = series.astype(str).str.strip().str.casefold()
    if not normalized.isin({"true", "false", "1", "0"}).all():
        raise ValueError("Boolean artifact column contains invalid values")
    return normalized.isin({"true", "1"})


def _read_csv(root: Path, relpath: str) -> tuple[Path, pd.DataFrame]:
    path = resolve_repo_path(root, relpath, expected="file")
    return path, pd.read_csv(path)


def _expected_injected_timestamps(registry: pd.DataFrame, context_id: str) -> dict[str, set[str]]:
    required = {"experiment_id", "target_variable", "injected_timestamps_json"}
    if not required.issubset(registry.columns):
        raise ValueError(f"Injection registry missing columns: {sorted(required - set(registry.columns))}")
    expected: dict[str, set[str]] = {}
    for experiment_id, group in registry.groupby("experiment_id", sort=False):
        if group.target_variable.nunique(dropna=False) != 1:
            raise ValueError(f"Registry target variable is inconsistent for {context_id}/{experiment_id}")
        event_times: set[str] = set()
        for payload in group.injected_timestamps_json:
            import json as _json
            for raw in _json.loads(payload):
                event_times.add(pd.Timestamp(raw).tz_convert("UTC").isoformat())
        if not event_times:
            raise ValueError(f"Registry has no injected timestamps for {context_id}/{experiment_id}")
        expected[str(experiment_id)] = event_times
    return expected


def _context_response_summary(detail: pd.DataFrame) -> pd.DataFrame:
    if "response_fraction" not in detail:
        detail = detail.copy()
        detail["response_fraction"] = detail.flagged / detail.denominator.replace(0, pd.NA)
    context = (detail.groupby(["baseline", "setting", "experiment_id", "context_id"], dropna=False)
               .agg(timestamp_unit_count=("timestamp_utc", "nunique"),
                    expected_timestamp_units=("timestamp_utc", "nunique"),
                    mean_timestamp_response_fraction=("response_fraction", "mean"))
               .reset_index())
    context["context_response_fraction"] = context.mean_timestamp_response_fraction
    return context


def _across_context_summary(context_summary: pd.DataFrame) -> pd.DataFrame:
    return (context_summary.groupby(["baseline", "setting", "experiment_id"], dropna=False)
            .agg(context_count=("context_id", "nunique"),
                 timestamp_unit_count=("timestamp_unit_count", "sum"),
                 mean_context_response_fraction=("context_response_fraction", "mean"),
                 minimum_context_response_fraction=("context_response_fraction", "min"),
                 maximum_context_response_fraction=("context_response_fraction", "max"))
            .reset_index())


def _validate_e2_outputs(detail: pd.DataFrame, paired: pd.DataFrame, manifest: dict,
                         expected_events: set[tuple[str, str, str, str]] | None = None) -> None:
    if not detail.status.isin(E2_STATUS).all() or not paired.clean_same_timestamp.isin(E2_STATUS).all() or not paired.synthetic_faulted.isin(E2_STATUS).all():
        raise ValueError("E2 outputs contain an invalid status")
    if detail.loc[detail.condition.eq("synthetic_faulted"), "synthetic_label"].astype(bool).eq(False).any():
        raise ValueError("E2 faulted rows contain unlabeled synthetic conditions")
    if detail.loc[detail.condition.eq("clean_same_timestamp"), "synthetic_label"].astype(bool).any():
        raise ValueError("E2 clean same-time rows carry synthetic fault labels")
    pair_keys = ["context_id", "experiment_id", "timestamp", "variable", "mode", "window_hours", "robust_z_threshold"]
    if paired.duplicated(pair_keys).any():
        raise ValueError("E2 paired output contains duplicate paired setting rows")
    if not paired.status_changed_by_injection.eq(
            paired.synthetic_faulted.ne(paired.clean_same_timestamp)).all():
        raise ValueError("E2 status-change counts do not match paired statuses")
    if int(manifest.get("paired_injection_rows", -1)) != len(paired):
        raise ValueError("E2 paired row denominator disagrees with its manifest")
    condition_rows = detail.loc[detail.condition.isin(["clean_same_timestamp", "synthetic_faulted"])]
    detail_keys = pair_keys + ["condition"]
    if condition_rows.duplicated(detail_keys).any():
        raise ValueError("E2 detail contains duplicate clean/faulted paired rows")
    detail_pairs = condition_rows.pivot(index=pair_keys, columns="condition", values="status").sort_index()
    if not {"clean_same_timestamp", "synthetic_faulted"}.issubset(detail_pairs.columns) or detail_pairs.isna().any().any():
        raise ValueError("E2 detail contains a missing clean/faulted pair")
    paired_values = paired.set_index(pair_keys)[["clean_same_timestamp", "synthetic_faulted"]].sort_index()
    if not detail_pairs.index.equals(paired_values.index):
        raise ValueError("E2 detail and paired output have different pair sets")
    if not detail_pairs[["clean_same_timestamp", "synthetic_faulted"]].equals(paired_values):
        raise ValueError("E2 paired statuses do not match their detail rows")
    if expected_events is not None:
        normalized = set()
        for row in paired.itertuples(index=False):
            normalized.add((row.context_id, row.experiment_id,
                            pd.Timestamp(row.timestamp).tz_convert("UTC").isoformat(), row.variable,
                            row.mode, int(row.window_hours), float(row.robust_z_threshold)))
        expected_keys = {
            (context_id, experiment_id, timestamp, variable, mode, window, threshold)
            for context_id, experiment_id, timestamp, variable in expected_events
            for mode in manifest["modes"] for window in manifest["windows_hours"]
            for threshold in manifest["robust_deviation_thresholds"]
        }
        if normalized != expected_keys:
            raise ValueError("E2 paired setting grid does not exactly cover the registered injected timestamps")
        counts = detail.groupby("condition").size().to_dict()
        if counts.get("synthetic_faulted") != len(expected_events) * 18:
            raise ValueError("E2 faulted-row denominator does not match 18 settings per registered injected timestamp")
        if counts.get("clean_same_timestamp") != len(expected_events) * 18:
            raise ValueError("E2 clean-comparator denominator does not match 18 settings per registered injected timestamp")
        if counts.get("matched_unmodified_control", 0) != int(manifest.get("controls_selected", 0)) * 6 * 18:
            raise ValueError("E2 matched-control denominator does not match six variables and 18 settings per control")


def analyze(campaign_dir: str | Path = CAMPAIGN, *, repo_root: str | Path = ROOT,
            output_dir: str | Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    root = Path(os.path.abspath(Path(repo_root)))
    if not root.is_dir():
        raise FileNotFoundError(f"Repository root does not exist: {root}")
    campaign_dir = Path(campaign_dir)
    if not campaign_dir.is_absolute():
        campaign_dir = resolve_repo_path(root, campaign_dir, expected="directory")
    else:
        campaign_dir = Path(os.path.abspath(campaign_dir))
        if not campaign_dir.is_dir():
            raise FileNotFoundError(f"Campaign directory does not exist: {campaign_dir}")
        if not campaign_dir.resolve(strict=True).is_relative_to(root.resolve(strict=True)):
            raise ValueError("Campaign directory must be within the repository root")
    manifest_path = campaign_dir / "campaign_manifest.json"
    campaign = json.loads(manifest_path.read_text(encoding="utf-8"))
    if campaign.get("status") != "EXECUTED_LOCAL_SYNTHETIC_MULTICONTEXT":
        raise ValueError("Campaign manifest does not identify a completed synthetic multi-context campaign")
    if campaign.get("campaign_id") != campaign_dir.name:
        raise ValueError("Campaign directory name does not match its declared campaign identity")
    contexts = campaign.get("contexts", [])
    scenarios = campaign.get("scenarios", [])
    if len(contexts) != campaign.get("context_count") or len(scenarios) != 8:
        raise ValueError("Campaign must declare its complete context/eight-scenario design")
    if len({item["id"] for item in scenarios}) != 8:
        raise ValueError("Campaign scenario identifiers are duplicated")
    if len({item["context_id"] for item in contexts}) != len(contexts):
        raise ValueError("Campaign context identifiers are duplicated")
    if len({item["run_directory"] for item in contexts}) != len(contexts):
        raise ValueError("Campaign context run directories are duplicated")

    e2_dir = campaign_dir / "e2_validation_review_1"
    e2_manifest, e2_tables = verify_e2_manifest(root, campaign_dir, e2_dir, campaign["dataset_hashes"])
    e2_detail = e2_tables["e2_multicontext_fault_detail.csv"]
    e2_paired = e2_tables["e2_multicontext_fault_paired.csv"]
    _validate_e2_outputs(e2_detail, e2_paired, e2_manifest)

    input_records: list[dict] = [artifact_record(root, manifest_path, experiment_id=campaign["campaign_id"])]
    for display_input in ("context_selection.csv", "context_scenario_summary.csv", "context_family_summary.csv"):
        input_records.append(artifact_record(root, campaign_dir / display_input,
                                             experiment_id=campaign["campaign_id"]))
    all_detail: list[pd.DataFrame] = []
    expected_e2_events: set[tuple[str, str, str, str]] = set()
    for context in contexts:
        run_path = resolve_repo_path(root, context["run_directory"], expected="directory")
        run_relative = run_path.relative_to(root).as_posix()
        run_records = {}
        frames = {}
        for filename in REQUIRED_RUN_INPUTS:
            path, frame = _read_csv(root, f"{run_relative}/{filename}") if filename.endswith(".csv") else (
                resolve_repo_path(root, f"{run_relative}/{filename}", expected="file"), None)
            run_records[filename] = artifact_record(root, path, experiment_id=campaign["campaign_id"])
            if frame is not None:
                frames[filename] = frame
        metadata = json.loads((run_path / "run_metadata.json").read_text(encoding="utf-8"))
        if metadata.get("context_id") != context["context_id"] or metadata.get("run_id") != context["run_id"]:
            raise ValueError(f"Context/run identity mismatch for {context['context_id']}")
        if metadata.get("dataset_hashes") != campaign["dataset_hashes"]:
            raise ValueError(f"Context dataset hashes mismatch for {context['context_id']}")
        if not (set(REQUIRED_RUN_INPUTS) - {"run_metadata.json"}).issubset(set(metadata.get("outputs", []))):
            raise ValueError(f"Run metadata has an incomplete output list for {context['context_id']}")
        input_records.extend(run_records.values())
        predictions = frames["changed_and_injected_predictions.csv"].copy()
        registry = frames["injection_registry.csv"]
        e4 = frames["physical_screening_results.csv"]
        if not {"timestamp", "configuration", "family", "is_candidate", "synthetic_fault_label", "experiment_id"}.issubset(predictions.columns):
            raise ValueError("Prediction artifact is missing required configuration-response columns")
        predictions["timestamp_utc"] = pd.to_datetime(predictions.timestamp, utc=True).map(lambda x: x.isoformat())
        predictions["synthetic_fault_label"] = _bool(predictions.synthetic_fault_label)
        expected = _expected_injected_timestamps(registry, context["context_id"])
        known_scenarios = {scenario["id"] for scenario in scenarios}
        if set(expected) != known_scenarios:
            raise ValueError(f"Injection registry scenario grid incomplete for {context['context_id']}")
        scenario_durations = {item["id"]: int(item["duration"]) for item in scenarios}
        for experiment_id, timestamps in expected.items():
            if len(timestamps) != scenario_durations[experiment_id]:
                raise ValueError(f"Injection registry timestamp denominator disagrees with scenario duration for {context['context_id']}/{experiment_id}")
        registry_target = registry.groupby("experiment_id").target_variable.first().to_dict()
        scenario_targets = {item["id"]: item["variable"] for item in scenarios}
        if registry_target != scenario_targets:
            raise ValueError(f"Injection registry target variables disagree with campaign scenarios for {context['context_id']}")
        injected = predictions.loc[predictions.synthetic_fault_label].copy()
        seen_keys: set[tuple[str, str]] = set()
        detail_rows = []
        for experiment_id, timestamps in expected.items():
            for timestamp in sorted(timestamps):
                group = injected.loc[injected.experiment_id.eq(experiment_id) & injected.timestamp_utc.eq(timestamp)]
                if len(group) != 12 or group.configuration.nunique() != 12:
                    raise ValueError(f"Expected 12 unique configurations for {context['context_id']}/{experiment_id}/{timestamp}; found {group.configuration.nunique()}")
                if group.configuration.duplicated().any() or set(group.family.unique()) != EXPECTED_FAMILIES:
                    raise ValueError(f"Incomplete or duplicate model family grid for {context['context_id']}/{experiment_id}/{timestamp}")
                family_counts = group.groupby("family").configuration.nunique().to_dict()
                if set(family_counts.values()) != {4}:
                    raise ValueError(f"Expected four configurations per model family for {context['context_id']}/{experiment_id}/{timestamp}")
                seen_keys.add((experiment_id, timestamp))
                scenario_variable = next(item["variable"] for item in scenarios if item["id"] == experiment_id)
                expected_e2_events.add((context["context_id"], experiment_id, timestamp, scenario_variable))
                flags = _bool(group.is_candidate)
                votes = int(flags.sum())
                base = {"context_id": context["context_id"], "experiment_id": experiment_id,
                        "timestamp_utc": timestamp, "injected_timestamp_units": len(timestamps),
                        "configuration_count": 12, "configuration_flag_count": votes}
                for row, flagged in zip(group.itertuples(index=False), flags.tolist()):
                    detail_rows.append({**base, "baseline": "configuration", "setting": str(row.configuration),
                                        "flagged": int(flagged), "denominator": 1})
                for family, family_rows in group.assign(_flag=flags.to_numpy()).groupby("family"):
                    n = int(family_rows.configuration.nunique())
                    detail_rows.append({**base, "baseline": f"family:{family}", "setting": "all",
                                        "flagged": int(family_rows._flag.sum()), "denominator": n})
                for threshold in BASELINES:
                    detail_rows.append({**base, "baseline": "E1_consensus", "setting": f"{threshold}/12",
                                        "flagged": int(votes >= threshold), "denominator": 1})
                # E4 must have exactly one row for the directly injected variable at each label timestamp.
                direct_rows = e4.loc[e4.experiment_id.eq(experiment_id)
                                     & pd.to_datetime(e4.timestamp, utc=True).map(lambda x: x.isoformat()).eq(timestamp)
                                     & e4.variable.eq(registry.loc[registry.experiment_id.eq(experiment_id), "target_variable"].iloc[0])]
                if len(direct_rows) != 1:
                    raise ValueError(f"Expected one directly injected-variable E4 row for {context['context_id']}/{experiment_id}/{timestamp}; found {len(direct_rows)}")
                detail_rows.append({**base, "baseline": "E4_direct_variable_screen", "setting": "existing broad rule",
                                    "flagged": int(_bool(direct_rows.screening_flag_faulted).iloc[0]), "denominator": 1})
        actual_keys = set(zip(injected.experiment_id.astype(str), injected.timestamp_utc.astype(str)))
        if actual_keys != seen_keys:
            raise ValueError(f"Injected prediction labels and registry disagree for context {context['context_id']}")
        all_detail.append(pd.DataFrame(detail_rows))
    _validate_e2_outputs(e2_detail, e2_paired, e2_manifest, expected_e2_events)
    detail = pd.concat(all_detail, ignore_index=True)
    detail["response_fraction"] = detail.flagged / detail.denominator
    context_summary = _context_response_summary(detail)
    summary = _across_context_summary(context_summary)
    expected_units = len(expected_e2_events)
    e1_detail = detail[(detail.baseline == "E1_consensus") & (detail.setting == "8/12")]
    if len(e1_detail) != expected_units:
        raise ValueError(f"Expected {expected_units} context × scenario × timestamp units; found {len(e1_detail)}")

    faulted = e2_detail[e2_detail.condition.eq("synthetic_faulted")].copy()
    if faulted.duplicated(["context_id", "experiment_id", "timestamp", "variable", "mode", "window_hours", "robust_z_threshold"]).any():
        raise ValueError("E2 faulted detail has duplicate experimental setting rows")
    e2_summary = (faulted.groupby(["experiment_id", "mode", "window_hours", "robust_z_threshold"], dropna=False)
                  .agg(screen_rows=("status", "size"),
                       supporting=("status", lambda s: int(s.eq("SUPPORTING").sum())),
                       conflicting=("status", lambda s: int(s.eq("CONFLICTING").sum())),
                       unavailable=("status", lambda s: int(s.eq("UNAVAILABLE").sum())))
                  .reset_index())
    e2_summary["supporting_fraction_available"] = e2_summary.supporting / (e2_summary.screen_rows - e2_summary.unavailable).replace(0, pd.NA)

    # Coverage stays a measurement-availability audit; E1/E4 records must exist and E2 rows must be complete.
    e2_paired["timestamp_utc"] = pd.to_datetime(e2_paired.timestamp, utc=True).map(lambda value: value.isoformat())
    event_keys = ["context_id", "experiment_id", "timestamp_utc"]
    e2_available = (e2_paired.assign(e2_available=e2_paired.synthetic_faulted.ne("UNAVAILABLE"))
                    .groupby(event_keys + ["mode", "window_hours", "robust_z_threshold"], as_index=False)
                    .e2_available.first())
    coverage_parts = []
    e1_units = detail[(detail.baseline == "E1_consensus") & (detail.setting == "8/12")]
    e4_units = detail[detail.baseline.eq("E4_direct_variable_screen")]
    e4_available_keys = set(zip(e4_units.context_id, e4_units.experiment_id, e4_units.timestamp_utc))
    for (ctx, experiment_id, timestamp), _ in e1_units.groupby(event_keys):
        if (ctx, experiment_id, timestamp) not in e4_available_keys:
            raise ValueError(f"E4 availability row missing for {ctx}/{experiment_id}/{timestamp}")
        e2rows = e2_available[(e2_available.context_id == ctx) & (e2_available.experiment_id == experiment_id)
                              & (e2_available.timestamp_utc == timestamp)]
        if len(e2rows) != 18:
            raise ValueError(f"Expected 18 E2 setting rows per injected timestamp; found {len(e2rows)}")
        for e2row in e2rows.to_dict("records"):
            e1_available, e2ok = 1, int(e2row["e2_available"])
            common = {"context_id": ctx, "experiment_id": experiment_id, "timestamp_utc": timestamp,
                      "mode": e2row["mode"], "window_hours": e2row["window_hours"],
                      "robust_z_threshold": e2row["robust_z_threshold"]}
            for combination, available, groups in (("A_E1", e1_available, 1),
                    ("B_E1_plus_E2", e1_available and e2ok, 2), ("D_E1_plus_E4", 1, 2),
                    ("E_E1_plus_E2_plus_E4", e1_available and e2ok, 3)):
                coverage_parts.append({**common, "combination": combination, "evidence_complete": int(available),
                                       "evidence_groups": groups,
                                       "coverage_limit": "Coverage audit only; no event/fault outcome is assigned"})
    for combination in ("C_E1_plus_E3", "E1_plus_E2_plus_E3_plus_E4"):
        for row in e1_units[event_keys].drop_duplicates().itertuples(index=False, name=None):
            ctx, experiment_id, timestamp = row
            coverage_parts.append({"context_id": ctx, "experiment_id": experiment_id, "timestamp_utc": timestamp,
                "mode": pd.NA, "window_hours": pd.NA, "robust_z_threshold": pd.NA,
                "combination": combination, "evidence_complete": 0,
                "evidence_groups": 2 if combination.startswith("C_") else 4,
                "coverage_limit": "Blocked: E3 station observations are unavailable"})
    coverage = pd.DataFrame(coverage_parts)
    coverage_summary = (coverage.groupby(["combination", "mode", "window_hours", "robust_z_threshold"], dropna=False)
                        .agg(units=("evidence_complete", "size"), complete_units=("evidence_complete", "sum"))
                        .reset_index())
    coverage_summary["coverage_fraction"] = coverage_summary.complete_units / coverage_summary.units

    output = (campaign_dir / "baseline_review_1") if output_dir is None else Path(output_dir)
    if not output.is_absolute():
        output = resolve_repo_path(root, output, expected=None, must_exist=False)
    else:
        output = Path(os.path.abspath(output))
        if not output.resolve(strict=False).is_relative_to(campaign_dir.resolve(strict=True)):
            raise ValueError("Baseline output directory must be a child of its campaign directory")
    output.mkdir(parents=True, exist_ok=True)
    intended = {
        "synthetic_baseline_response_detail.csv": detail,
        "synthetic_baseline_context_summary.csv": context_summary,
        "synthetic_baseline_response_summary.csv": summary,
        "synthetic_e2_setting_sensitivity.csv": e2_summary,
        "evidence_coverage_ablation.csv": coverage,
        "evidence_coverage_ablation_summary.csv": coverage_summary,
    }
    if any((output / name).exists() for name in intended):
        raise FileExistsError(f"Refusing to overwrite existing baseline review artifacts in {output}")
    for name, frame in intended.items():
        frame.to_csv(output / name, index=False)

    # Record every consumed source, including all E2 output files verified above.
    input_records.extend(artifact_record(root, campaign_dir / "e2_validation_review_1" / name,
                           experiment_id=campaign["campaign_id"])
                         for name in e2_manifest["outputs"])
    input_records.append(artifact_record(root, e2_dir / "e2_validation_manifest.json", experiment_id=campaign["campaign_id"]))
    for record in input_records:
        # Any artifact which is a saved CSV or manifest is now fully described and hash-addressed.
        record.setdefault("source_artifact_references", [campaign["campaign_id"]])
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True,
                                           stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "UNKNOWN"
    output_records = [artifact_record(root, output / name, experiment_id=campaign["campaign_id"],
                                     source_artifact_references=[r["path"] for r in input_records])
                      for name in intended]
    for record in output_records:
        record["code_revision"] = revision
    result_manifest = {
        "schema_version": 2, "status": "EXECUTED_SYNTHETIC_BASELINE_AND_SENSITIVITY_COMPARISON",
        "campaign_id": campaign["campaign_id"], "experiment_id": campaign["campaign_id"],
        "code_revision": revision, "objective": "Descriptive response to declared synthetic injections and coverage-only audit; no fitting or campaign regeneration.",
        "experimental_unit": "context × scenario × synthetically labelled timestamp; context is the aggregation unit for across-context ranges",
        "dataset_hashes": campaign["dataset_hashes"], "context_count": len(contexts), "scenario_count": len(scenarios),
        "injected_timestamp_units": int(expected_units), "configuration_count": 12,
        "configurations_per_family": 4, "families": sorted(EXPECTED_FAMILIES),
        "e2_source_directory": "e2_validation_review_1", "inputs": input_records,
        "output_directory": output.name, "output_files": list(intended), "outputs": output_records,
        "manifest_hash_note": "The manifest does not hash itself. Its final SHA-256 is stored in the separate .integrity.json sidecar.",
        "interpretation_limit": "Synthetic injection response only. Coverage measures availability, not outcome utility. No field performance is estimated.",
        "ablation_status": "COVERAGE_ONLY; outcome-level ablation and E3-dependent combinations remain unavailable",
    }
    manifest_path = output / "synthetic_baseline_comparison_manifest.json"
    manifest_path.write_text(json.dumps(result_manifest, indent=2) + "\n", encoding="utf-8")
    sidecar = output / "synthetic_baseline_comparison_manifest.integrity.json"
    sidecar.write_text(json.dumps({"manifest_path": manifest_path.relative_to(root).as_posix(),
                                   "sha256": sha256_file(manifest_path)}, indent=2) + "\n", encoding="utf-8")
    return detail, summary, result_manifest


if __name__ == "__main__":
    detail, summary, manifest = analyze()
    print(json.dumps({"status": manifest["status"], "context_timestamp_units": manifest["injected_timestamp_units"],
                      "contexts": manifest["context_count"], "scenarios": manifest["scenario_count"],
                      "detail_rows": len(detail), "summary_rows": len(summary),
                      "output_directory": manifest["output_directory"], "code_revision": manifest["code_revision"]}, indent=2))
