"""Focused portability, integrity and aggregation tests on temporary artifacts."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_synthetic_baseline_comparison import (
    _across_context_summary, _context_response_summary, _validate_e2_outputs, analyze,
)
from services.research_artifact_integrity import (
    artifact_record, multicontext_artifact_state, resolve_repo_path,
    verify_artifact_record, verify_baseline_manifest, verify_e2_manifest,
)


DATASET_HASHES = {"model_df": "a" * 64, "X_train_multi": "b" * 64, "X_test_multi": "c" * 64}
FAMILIES = ["IsolationForest"] * 4 + ["LocalOutlierFactor"] * 4 + ["OneClassSVM"] * 4
CONFIGS = [f"{family}_{i}" for family in ("IF", "LOF", "SVM") for i in range(4)]
SCENARIOS = [
    ("TEMP_POINT_SPIKE", "temp", 1), ("TEMP_POINT_DROP", "temp", 1),
    ("TEMP_PERSISTENT_OFFSET", "temp", 2), ("TEMP_STUCK_SENSOR", "temp", 1),
    ("TEMP_GRADUAL_DRIFT", "temp", 1), ("TEMP_MISSING_BLOCK", "temp", 1),
    ("TEMP_INTERMITTENT_NOISE", "temp", 1), ("DEWPOINT_TEMP_INCONSISTENCY", "dwpt", 1),
]
E2_SETTINGS = [(mode, window, cutoff) for mode in ("real_time", "retrospective")
               for window in (3, 6, 12) for cutoff in (2.5, 3.5, 4.5)]


def _write_csv(path: Path, frame: pd.DataFrame) -> dict:
    frame.to_csv(path, index=False)
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "rows": len(frame)}


def build_fixture(root: Path) -> tuple[Path, dict]:
    campaign_id = "fault_matrix_multicontext_46ae5d119d"
    campaign_dir = root / "research_results" / campaign_id
    campaign_dir.mkdir(parents=True)
    contexts = []
    context_run_data = []
    for context_index in range(2):
        context_id = f"CTX_{context_index}"
        run_id = f"fault_matrix_fixture_{context_index}"
        run_dir = root / "research_results" / run_id
        run_dir.mkdir(parents=True)
        start = pd.Timestamp("2025-04-09 17:30", tz="Asia/Kolkata") + pd.Timedelta(days=context_index * 40)
        registries, prediction_rows, e4_rows, expected_events = [], [], [], []
        hour = 0
        for scenario_index, (experiment_id, variable, duration) in enumerate(SCENARIOS):
            timestamps = [start + pd.Timedelta(hours=hour + offset) for offset in range(duration)]
            hour += duration + 2
            registries.append({"experiment_id": experiment_id, "target_variable": variable,
                               "injected_timestamps_json": json.dumps([ts.isoformat() for ts in timestamps])})
            for timestamp_index, timestamp in enumerate(timestamps):
                expected_events.append((context_id, experiment_id, timestamp.tz_convert("UTC").isoformat(), variable))
                # A two-timestamp fault makes the old timestamp-range summary differ from
                # the required range of context-level responses.
                if experiment_id == "TEMP_PERSISTENT_OFFSET":
                    n_flags = 12 if (context_index == 0 and timestamp_index == 0) else 0
                else:
                    n_flags = 0
                for index, (configuration, family) in enumerate(zip(CONFIGS, FAMILIES)):
                    prediction_rows.append({"timestamp": timestamp.isoformat(), "configuration": configuration,
                        "family": family, "is_candidate": index < n_flags, "synthetic_fault_label": True,
                        "experiment_id": experiment_id})
                e4_rows.append({"timestamp": timestamp.isoformat(), "variable": variable,
                                "experiment_id": experiment_id, "screening_flag_faulted": False})
        predictions = pd.DataFrame(prediction_rows)
        registry = pd.DataFrame(registries)
        e4 = pd.DataFrame(e4_rows)
        _write_csv(run_dir / "changed_and_injected_predictions.csv", predictions)
        _write_csv(run_dir / "physical_screening_results.csv", e4)
        _write_csv(run_dir / "injection_registry.csv", registry)
        metadata = {"run_id": run_id, "context_id": context_id, "dataset_hashes": DATASET_HASHES,
                    "outputs": ["changed_and_injected_predictions.csv", "physical_screening_results.csv", "injection_registry.csv"]}
        (run_dir / "run_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        run_directory = str(run_dir.relative_to(root)).replace("/", "\\")
        contexts.append({"context_id": context_id, "timestamp": start.isoformat(),
                         "run_directory": run_directory, "run_id": run_id})
        context_run_data.append((context_id, expected_events, run_dir))

    scenarios = [{"id": experiment_id, "variable": variable, "kind": "fixture", "duration": duration}
                 for experiment_id, variable, duration in SCENARIOS]
    campaign = {"campaign_id": campaign_id, "status": "EXECUTED_LOCAL_SYNTHETIC_MULTICONTEXT",
                "context_count": len(contexts), "contexts": contexts, "scenarios": scenarios,
                "dataset_hashes": DATASET_HASHES}
    (campaign_dir / "campaign_manifest.json").write_text(json.dumps(campaign), encoding="utf-8")
    _write_csv(campaign_dir / "context_selection.csv", pd.DataFrame({"context_id": [x["context_id"] for x in contexts]}))
    _write_csv(campaign_dir / "context_scenario_summary.csv", pd.DataFrame({
        "context_id": [x["context_id"] for x in contexts], "experiment_id": ["TEMP_POINT_SPIKE"] * len(contexts)}))
    _write_csv(campaign_dir / "context_family_summary.csv", pd.DataFrame({
        "context_id": [x["context_id"] for x in contexts], "experiment_id": ["TEMP_POINT_SPIKE"] * len(contexts),
        "family": ["IsolationForest"] * len(contexts)}))

    e2_dir = campaign_dir / "e2_validation_review_1"
    e2_dir.mkdir()
    details, pairs = [], []
    for context_id, event_rows, _ in context_run_data:
        for ctx, experiment_id, timestamp, variable in event_rows:
            for mode, window, cutoff in E2_SETTINGS:
                pair_id = f"{ctx}:{experiment_id}:{timestamp}:{variable}:{mode}:{window}:{cutoff}"
                clean_status = "NO_DETECTED_EVIDENCE"
                fault_status = "UNAVAILABLE" if experiment_id == "TEMP_MISSING_BLOCK" else "SUPPORTING"
                for condition, status, label in (("clean_same_timestamp", clean_status, False),
                                                  ("synthetic_faulted", fault_status, True)):
                    details.append({"context_id": ctx, "experiment_id": experiment_id,
                        "timestamp": timestamp, "variable": variable, "condition": condition,
                        "synthetic_label": label, "pair_id": pair_id, "mode": mode,
                        "window_hours": window, "robust_z_threshold": cutoff, "status": status})
                pairs.append({"pair_id": pair_id, "context_id": ctx, "experiment_id": experiment_id,
                    "timestamp": timestamp, "variable": variable, "mode": mode,
                    "window_hours": window, "robust_z_threshold": cutoff,
                    "clean_same_timestamp": clean_status, "synthetic_faulted": fault_status,
                    "status_changed_by_injection": clean_status != fault_status})
    detail_frame, pair_frame = pd.DataFrame(details), pd.DataFrame(pairs)
    summary_frame = pd.DataFrame(columns=["condition", "experiment_id", "variable", "mode", "window_hours",
        "robust_z_threshold", "status", "reading_count"])
    controls_frame = pd.DataFrame(columns=["timestamp", "matched_context_id", "matched_context_timestamp", "matching_rule"])
    output_frames = {"e2_matched_controls.csv": controls_frame,
        "e2_multicontext_fault_detail.csv": detail_frame,
        "e2_multicontext_fault_paired.csv": pair_frame,
        "e2_multicontext_fault_summary.csv": summary_frame}
    output_integrity = {name: _write_csv(e2_dir / name, frame) for name, frame in output_frames.items()}
    e2_manifest = {"status": "EXECUTED_EXPLORATORY_SYNTHETIC_E2", "campaign_id": campaign_id,
        "dataset_hashes": DATASET_HASHES, "output_directory": e2_dir.name,
        "outputs": list(output_frames), "output_integrity": output_integrity,
        "paired_injection_rows": len(pair_frame), "evaluated_rows": len(detail_frame),
        "controls_selected": 0, "modes": ["real_time", "retrospective"],
        "windows_hours": [3, 6, 12], "robust_deviation_thresholds": [2.5, 3.5, 4.5]}
    (e2_dir / "e2_validation_manifest.json").write_text(json.dumps(e2_manifest), encoding="utf-8")
    return campaign_dir, {"observations": DATASET_HASHES["model_df"],
                          "train": DATASET_HASHES["X_train_multi"], "test": DATASET_HASHES["X_test_multi"]}


class TestPortableResearchPaths(unittest.TestCase):
    def test_posix_windows_nested_paths_and_independent_current_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "research_results" / "run_1" / "deep"
            expected.mkdir(parents=True)
            before = Path.cwd()
            other = root / "elsewhere"
            other.mkdir()
            try:
                os.chdir(other)
                self.assertEqual(resolve_repo_path(root, "research_results/run_1/deep", expected="directory"), Path(os.path.abspath(expected)))
                self.assertEqual(resolve_repo_path(root, r"research_results\run_1\deep", expected="directory"), Path(os.path.abspath(expected)))
            finally:
                os.chdir(before)

    def test_path_safety_and_missing_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                resolve_repo_path(root, "missing/file.csv")
            for unsafe in ("../outside", r"..\outside", "/tmp/absolute", r"C:\outside", r"\\server\share"):
                with self.subTest(path=unsafe), self.assertRaises(ValueError):
                    resolve_repo_path(root, unsafe)

    def test_historical_windows_manifest_paths_resolve_from_repo_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "research_results" / "fault_matrix_6ff4e167232b"
            target.mkdir(parents=True)
            resolved = resolve_repo_path(root, r"research_results\fault_matrix_6ff4e167232b", expected="directory")
            self.assertEqual(resolved, Path(os.path.abspath(target)))


class TestBaselineAggregationAndPipeline(unittest.TestCase):
    def test_context_aggregation_distinguishes_timestamp_and_context_ranges(self):
        detail = pd.DataFrame([
            {"context_id": "A", "experiment_id": "multi", "timestamp_utc": "a1", "baseline": "E1_consensus", "setting": "8/12", "flagged": 1, "denominator": 1},
            {"context_id": "A", "experiment_id": "multi", "timestamp_utc": "a2", "baseline": "E1_consensus", "setting": "8/12", "flagged": 0, "denominator": 1},
            {"context_id": "B", "experiment_id": "multi", "timestamp_utc": "b1", "baseline": "E1_consensus", "setting": "8/12", "flagged": 0, "denominator": 1},
            {"context_id": "B", "experiment_id": "multi", "timestamp_utc": "b2", "baseline": "E1_consensus", "setting": "8/12", "flagged": 0, "denominator": 1},
        ])
        context = _context_response_summary(detail)
        across = _across_context_summary(context).iloc[0]
        self.assertEqual(context.context_response_fraction.tolist(), [0.5, 0.0])
        self.assertEqual(across.context_count, 2)
        self.assertEqual(across.timestamp_unit_count, 4)
        self.assertEqual(across.mean_context_response_fraction, 0.25)
        self.assertEqual(across.minimum_context_response_fraction, 0.0)
        self.assertEqual(across.maximum_context_response_fraction, 0.5)

    def test_temporary_campaign_pipeline_reproduces_multi_timestamp_context_summary_and_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign, phase_hashes = build_fixture(root)
            detail, summary, manifest = analyze(campaign, repo_root=root)
            output = campaign / "baseline_review_1"
            self.assertEqual(manifest["context_count"], 2)
            self.assertEqual(manifest["scenario_count"], 8)
            self.assertEqual(manifest["injected_timestamp_units"], 18)
            self.assertEqual(len(detail[(detail.baseline == "E1_consensus") & (detail.setting == "8/12")]), 18)
            persistent = summary[(summary.experiment_id == "TEMP_PERSISTENT_OFFSET")
                                 & (summary.baseline == "E1_consensus") & (summary.setting == "8/12")].iloc[0]
            self.assertEqual(persistent.context_count, 2)
            self.assertEqual(persistent.timestamp_unit_count, 4)
            self.assertEqual(persistent.mean_context_response_fraction, 0.25)
            self.assertEqual(persistent.minimum_context_response_fraction, 0.0)
            self.assertEqual(persistent.maximum_context_response_fraction, 0.5)
            family = summary[(summary.experiment_id == "TEMP_PERSISTENT_OFFSET")
                             & (summary.baseline == "family:IsolationForest")
                             & (summary.setting == "all")].iloc[0]
            self.assertEqual(family.mean_context_response_fraction, 0.25)
            recomputed = _across_context_summary(_context_response_summary(detail))
            pd.testing.assert_frame_equal(
                summary.sort_values(["baseline", "setting", "experiment_id"]).reset_index(drop=True),
                recomputed.sort_values(["baseline", "setting", "experiment_id"]).reset_index(drop=True),
                check_dtype=False)
            loaded_manifest, outputs = verify_baseline_manifest(root, campaign, output, DATASET_HASHES)
            self.assertEqual(set(outputs), set(loaded_manifest["output_files"]))
            self.assertEqual(len(outputs["synthetic_baseline_response_detail.csv"]), 21 * 18)
            coverage_summary = outputs["evidence_coverage_ablation_summary.csv"]
            coverage_detail = outputs["evidence_coverage_ablation.csv"]
            self.assertTrue(coverage_summary.loc[coverage_summary.combination.str.contains("E3"), "complete_units"].eq(0).all())
            self.assertTrue(coverage_summary.loc[coverage_summary.combination.eq("D_E1_plus_E4"), "coverage_fraction"].eq(1.0).all())
            self.assertTrue(coverage_summary.loc[coverage_summary.combination.eq("A_E1"), "coverage_fraction"].eq(1.0).all())
            self.assertTrue(coverage_detail.loc[coverage_detail.combination.eq("E_E1_plus_E2_plus_E4"), "evidence_groups"].eq(3).all())
            self.assertTrue(coverage_detail.loc[coverage_detail.combination.eq("C_E1_plus_E3"), "evidence_groups"].eq(2).all())
            self.assertIn("Coverage audit only", " ".join(coverage_detail.coverage_limit.unique()))
            self.assertTrue((coverage_detail.loc[coverage_detail.combination.eq("B_E1_plus_E2"), "evidence_complete"] == 0).any())
            # The application uses this state to either show results or display its warning.
            state = multicontext_artifact_state(root, phase_hashes)
            self.assertTrue(state["verified"], state["warning"])
            source = campaign / "context_scenario_summary.csv"
            source_bytes = source.read_bytes()
            source.write_bytes(source_bytes + b"\n")
            input_failure = multicontext_artifact_state(root, phase_hashes)
            self.assertFalse(input_failure["verified"])
            self.assertIn("integrity verification failed", input_failure["warning"])
            source.write_bytes(source_bytes)
            e2_source = campaign / "e2_validation_review_1" / "e2_multicontext_fault_detail.csv"
            e2_bytes = e2_source.read_bytes()
            e2_source.write_bytes(e2_bytes + b"\n")
            e2_failure = multicontext_artifact_state(root, phase_hashes)
            self.assertFalse(e2_failure["verified"])
            self.assertIn("integrity verification failed", e2_failure["warning"])
            e2_source.write_bytes(e2_bytes)
            target = output / "synthetic_baseline_response_summary.csv"
            target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            failed = multicontext_artifact_state(root, phase_hashes)
            self.assertFalse(failed["verified"])
            self.assertIn("integrity verification failed", failed["warning"])
            target.write_text(target.read_text(encoding="utf-8").rstrip() + "\n", encoding="utf-8")
            target.unlink()
            missing_failure = multicontext_artifact_state(root, phase_hashes)
            self.assertFalse(missing_failure["verified"])
            self.assertIn("does not exist", missing_failure["warning"].lower())

    def test_baseline_rejects_missing_context_input_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign, _ = build_fixture(root)
            contexts = json.loads((campaign / "campaign_manifest.json").read_text())["contexts"]
            (root / contexts[0]["run_directory"].replace("\\", "/") / "injection_registry.csv").unlink()
            with self.assertRaises(FileNotFoundError):
                analyze(campaign, repo_root=root)
            self.assertFalse((campaign / "baseline_review_1" / "synthetic_baseline_response_detail.csv").exists())

    def test_baseline_rejects_incomplete_configuration_grid_and_missing_column(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign, _ = build_fixture(root)
            context = json.loads((campaign / "campaign_manifest.json").read_text())["contexts"][0]
            run = resolve_repo_path(root, context["run_directory"], expected="directory")
            predictions_path = run / "changed_and_injected_predictions.csv"
            predictions = pd.read_csv(predictions_path)
            predictions.iloc[1:].to_csv(predictions_path, index=False)
            with self.assertRaisesRegex(ValueError, "Expected 12 unique configurations"):
                analyze(campaign, repo_root=root)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign, _ = build_fixture(root)
            context = json.loads((campaign / "campaign_manifest.json").read_text())["contexts"][0]
            run = resolve_repo_path(root, context["run_directory"], expected="directory")
            predictions_path = run / "changed_and_injected_predictions.csv"
            pd.read_csv(predictions_path).drop(columns="family").to_csv(predictions_path, index=False)
            with self.assertRaisesRegex(ValueError, "missing required configuration-response columns"):
                analyze(campaign, repo_root=root)


class TestE2AndArtifactContracts(unittest.TestCase):
    def _mini_e2(self):
        rows, pairs = [], []
        for mode, window, cutoff in E2_SETTINGS:
            timestamp = "2025-01-01T00:00:00+00:00"
            pair_id = f"C:E:{timestamp}:temp:{mode}:{window}:{cutoff}"
            for condition, label, status in (("clean_same_timestamp", False, "NO_DETECTED_EVIDENCE"),
                                              ("synthetic_faulted", True, "SUPPORTING")):
                rows.append({"pair_id": pair_id, "context_id": "C", "experiment_id": "E", "timestamp": timestamp,
                    "variable": "temp", "mode": mode, "window_hours": window, "robust_z_threshold": cutoff,
                    "condition": condition, "synthetic_label": label, "status": status})
            pairs.append({"pair_id": pair_id, "context_id": "C", "experiment_id": "E", "timestamp": timestamp,
                "variable": "temp", "mode": mode, "window_hours": window, "robust_z_threshold": cutoff,
                "clean_same_timestamp": "NO_DETECTED_EVIDENCE", "synthetic_faulted": "SUPPORTING",
                "status_changed_by_injection": True})
        detail, paired = pd.DataFrame(rows), pd.DataFrame(pairs)
        manifest = {"paired_injection_rows": len(paired), "evaluated_rows": len(detail), "controls_selected": 0,
            "modes": ["real_time", "retrospective"], "windows_hours": [3, 6, 12],
            "robust_deviation_thresholds": [2.5, 3.5, 4.5]}
        return detail, paired, manifest

    def test_e2_pair_and_denominator_fail_closed_and_unavailable_is_valid(self):
        detail, paired, manifest = self._mini_e2()
        detail.loc[detail.condition.eq("synthetic_faulted") & detail.window_hours.eq(3), "status"] = "UNAVAILABLE"
        paired.loc[paired.window_hours.eq(3), "synthetic_faulted"] = "UNAVAILABLE"
        paired.loc[paired.window_hours.eq(3), "status_changed_by_injection"] = True
        _validate_e2_outputs(detail, paired, manifest, {("C", "E", "2025-01-01T00:00:00+00:00", "temp")})
        with self.assertRaisesRegex(ValueError, "missing clean/faulted pair"):
            _validate_e2_outputs(detail.iloc[1:].copy(), paired, manifest)
        duplicate = pd.concat([paired, paired.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "duplicate paired"):
            _validate_e2_outputs(detail, duplicate, manifest)
        invalid = paired.copy()
        invalid.loc[0, "synthetic_faulted"] = "MAYBE"
        with self.assertRaisesRegex(ValueError, "invalid status"):
            _validate_e2_outputs(detail, invalid, manifest)
        wrong_denominator = {**manifest, "paired_injection_rows": len(paired) + 1}
        with self.assertRaisesRegex(ValueError, "denominator"):
            _validate_e2_outputs(detail, paired, wrong_denominator)
        clean_labeled = detail.copy()
        clean_labeled.loc[clean_labeled.condition.eq("clean_same_timestamp"), "synthetic_label"] = True
        with self.assertRaisesRegex(ValueError, "clean same-time"):
            _validate_e2_outputs(clean_labeled, paired, manifest)

    def test_artifact_record_checks_hash_rows_columns_missing_and_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "table.csv"
            pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_csv(target, index=False)
            record = artifact_record(root, target)
            self.assertEqual(verify_artifact_record(root, record, required_columns=["a", "b"]).shape, (2, 2))
            with self.assertRaisesRegex(ValueError, "required columns"):
                verify_artifact_record(root, record, required_columns=["missing"])
            wrong_rows = {**record, "rows": 3}
            with self.assertRaisesRegex(ValueError, "row count"):
                verify_artifact_record(root, wrong_rows)
            target.write_text("a,b\n1,3\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "size mismatch|SHA-256 mismatch"):
                verify_artifact_record(root, record)
            target.unlink()
            with self.assertRaises(FileNotFoundError):
                verify_artifact_record(root, record)

    def test_missing_campaign_state_is_explicit_and_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            state = multicontext_artifact_state(Path(directory), {"observations": "a", "train": "b", "test": "c"})
            self.assertFalse(state["verified"])
            self.assertIsNone(state["bundle"])
            self.assertIn("integrity verification failed", state["warning"])


if __name__ == "__main__":
    unittest.main()
