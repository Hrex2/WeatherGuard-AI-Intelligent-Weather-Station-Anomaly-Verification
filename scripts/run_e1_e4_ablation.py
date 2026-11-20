"""Run the controlled E1–E4 structural ablation on saved held-out outputs.

No model fit, random sampling, network request, or source-artifact write occurs.
The default run directory is unique so past experiment outputs are preserved.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from services.data_service import load_project_data, prediction_wide
from services import evidence_integration as evidence
from services.ablation_service import (
    ABLATION_CONFIGURATIONS, ablate, apply_component_subset,
)


ADAPTERS = {"E1": evidence._e1, "E2": evidence._e2, "E3": evidence._e3, "E4": evidence._e4}
STATUS_ORDER = ("AVAILABLE", "DESCRIPTIVE_ONLY", "INSUFFICIENT_DATA", "UNAVAILABLE", "ERROR", "NOT_APPLICABLE")
ASSESSMENT_ORDER = ("SUSPICIOUS", "INSUFFICIENT_EVIDENCE", "NORMAL", "ANOMALOUS")
CONFIG_CHART_LABELS = {
    "A0": "Baseline", "A1": "+E1", "A2": "+E2", "A3": "+E3",
    "A4": "+E4", "A5": "+E1, E2, E4", "A6": "Full E1–E4",
}


def _json_default(value):
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if pd.isna(value):
        return None
    return str(value)


def _empty_output_directory(requested: str | None) -> Path:
    if requested:
        path = Path(requested)
        if not path.is_absolute():
            path = ROOT / path
    else:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = ROOT / "research_results" / f"e1_e4_ablation_study_{run_id}"
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"Output directory is not empty; choose a new run directory: {path}")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _component_status(row: dict, component_id: str) -> str:
    return row["components"][component_id]["execution_status"]


def _make_plots(summary: dict, config_frame: pd.DataFrame, output_dir: Path) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.titleweight": "bold"})
    names = config_frame["configuration_name"].tolist()
    x = np.arange(len(names))

    fig, ax = plt.subplots(figsize=(11, 5.3))
    ax.bar(x, config_frame["mean_available_components_per_observation"], color="#2584a8",
           label="Mean available included components")
    ax.set_ylabel("Available components per observation")
    ax.set_xticks(x, [f"{cid}\n{CONFIG_CHART_LABELS[cid]}" for cid in config_frame["ablation_id"]])
    ax.tick_params(axis="x", pad=6)
    ax.grid(axis="y", alpha=.25)
    ax2 = ax.twinx()
    ax2.plot(x, config_frame["evidence_coverage_pct"], color="#e29a27", marker="o", linewidth=2,
             label="Evidence coverage")
    ax2.set_ylabel("Observations with ≥1 available included component (%)")
    ax2.set_ylim(0, 105)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False)
    ax.set_title("Ablation comparison: evidence availability under fixed baseline outputs")
    fig.subplots_adjust(bottom=.21, left=.09, right=.91, top=.86)
    fig.savefig(output_dir / "ablation_comparison.png", dpi=180, facecolor="white")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    suspicious = config_frame["suspicious_assessments"].to_numpy()
    insufficient = config_frame["insufficient_evidence_assessments"].to_numpy()
    ax.bar(x, suspicious, color="#e39a28", label="SUSPICIOUS")
    ax.bar(x, insufficient, bottom=suspicious, color="#8793a3", label="INSUFFICIENT_EVIDENCE")
    ax.set_xticks(x, [f"{cid}\n{CONFIG_CHART_LABELS[cid]}" for cid in config_frame["ablation_id"]])
    ax.set_ylabel("Observations")
    ax.set_title("Assessment distribution by ablation configuration")
    ax.grid(axis="y", alpha=.22)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(.5, 1.13), ncols=2)
    fig.subplots_adjust(top=.84, bottom=.18)
    fig.savefig(output_dir / "assessment_distribution.png", dpi=180, facecolor="white")
    plt.close(fig)

    full_counts = summary["configurations"]["A6"]["component_status_counts"]
    fig, ax = plt.subplots(figsize=(8.6, 4.8), constrained_layout=True)
    bottoms = np.zeros(4)
    colors = {"AVAILABLE": "#2584a8", "DESCRIPTIVE_ONLY": "#e3a22c", "INSUFFICIENT_DATA": "#8793a3",
              "UNAVAILABLE": "#b5bdc7", "ERROR": "#bc4a4a", "NOT_APPLICABLE": "#dedede"}
    for status in STATUS_ORDER:
        values = np.array([full_counts[cid].get(status, 0) for cid in evidence.COMPONENT_IDS]) / summary["observations_evaluated"] * 100
        ax.bar(evidence.COMPONENT_IDS, values, bottom=bottoms, color=colors[status], label=status.replace("_", " "))
        bottoms += values
    ax.set_ylim(0, 100)
    ax.set_ylabel("Evaluation timestamps (%)")
    ax.set_title("Full architecture component coverage and availability")
    ax.legend(frameon=False, ncols=3, loc="upper center", bbox_to_anchor=(.5, -0.12))
    ax.grid(axis="y", alpha=.2)
    fig.savefig(output_dir / "component_coverage.png", dpi=180, facecolor="white")
    plt.close(fig)

    loo = pd.DataFrame(summary["leave_one_out"])
    fig, ax = plt.subplots(figsize=(8.5, 4.7))
    loo_names = [f"Without {x}" for x in loo["removed_component"]]
    loo_x = np.arange(len(loo))
    bar_width = .36
    changed = loo["assessment_changes"].to_numpy()
    component_coverage = loo["component_available_observations_before_removal"].to_numpy()
    ax.bar(loo_x - bar_width / 2, changed, bar_width, color="#bc4a4a", label="Assessment changes")
    ax.bar(loo_x + bar_width / 2, component_coverage, bar_width, color="#2584a8", label="Available component evidence removed")
    ax.set_ylabel("Observations")
    ax.set_xticks(loo_x, loo_names)
    ax.set_title("Leave-one-component-out: decisions and component coverage")
    ax.grid(axis="y", alpha=.22)
    for i, row in loo.iterrows():
        ax.text(i - bar_width / 2, row["assessment_changes"], f"{row['assessment_changes']:,}", ha="center", va="bottom", fontsize=8)
        ax.text(i + bar_width / 2, row["component_available_observations_before_removal"],
                f"{row['component_available_observations_before_removal']:,}", ha="center", va="bottom", fontsize=8)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(.5, -.15), ncols=2)
    fig.subplots_adjust(top=.85, bottom=.19, left=.1, right=.9)
    fig.savefig(output_dir / "leave_one_out_comparison.png", dpi=180, facecolor="white")
    plt.close(fig)

    e3 = summary["e3_contextual_ablation"]
    fig, ax = plt.subplots(figsize=(7.8, 4.7))
    labels = ["A5 · without E3", "A6 · E3 context shown"]
    suspicious_counts = [e3["without_e3_suspicious"], e3["with_e3_suspicious"]]
    insufficient_counts = [e3["without_e3_insufficient"], e3["with_e3_insufficient"]]
    ax.bar(labels, suspicious_counts, color="#e39a28", label="SUSPICIOUS")
    ax.bar(labels, insufficient_counts, bottom=suspicious_counts, color="#8793a3", label="INSUFFICIENT_EVIDENCE")
    ax.set_ylabel("Observations")
    ax.set_title("E3 contextual ablation: identical decision distribution")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(.5, -.15), ncols=2)
    fig.subplots_adjust(top=.86, bottom=.2, left=.1, right=.9)
    fig.text(.5, .95,
             f"{e3['descriptive_observation_count']:,} descriptive-only observations; {e3['assessment_changes']} decision changes",
             ha="center", va="center", fontsize=9, color="#475569")
    ax.grid(axis="y", alpha=.2)
    fig.savefig(output_dir / "E3_contextual_ablation.png", dpi=180, facecolor="white")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    ax.bar(x, config_frame["mean_processing_time_ms_per_observation"], color="#2a8f75")
    ax.set_xticks(x, [f"{cid}\n{CONFIG_CHART_LABELS[cid]}" for cid in config_frame["ablation_id"]])
    ax.set_ylabel("Estimated milliseconds per observation")
    ax.set_title("Processing-time comparison (single-run component timings)")
    ax.grid(axis="y", alpha=.22)
    fig.subplots_adjust(bottom=.18, left=.09, right=.96, top=.88)
    fig.savefig(output_dir / "processing_time_comparison.png", dpi=180, facecolor="white")
    plt.close(fig)


def run(output_dir: Path) -> dict:
    run_started = time.perf_counter()
    data, manifest, input_hashes = load_project_data(ROOT)
    observations = data["observations"]
    predictions = data["predictions"]
    timestamps = prediction_wide(predictions).index.sort_values()
    if not timestamps.isin(observations.index).all():
        raise ValueError("Saved baseline timestamps do not all have exact processed observations")
    if len(timestamps) != len(data["test"]):
        raise ValueError("Saved baseline evaluation timestamps do not match the held-out test count")
    spatial_tables, spatial_sources = evidence.load_spatial_tables(ROOT)

    timed_component_seconds = defaultdict(float)
    observations_rows: list[dict] = []
    loo_rows: list[dict] = []
    e3_rows: list[dict] = []
    category_sequences = {config_id: [] for config_id in ABLATION_CONFIGURATIONS}
    baseline_digest = hashlib.sha256()
    input_timestamp_signature = hashlib.sha256("\n".join(ts.isoformat() for ts in timestamps).encode()).hexdigest()
    adapter_context = defaultdict(list)

    for ordinal, timestamp in enumerate(timestamps, start=1):
        per_observation_times = {}
        timed_adapters = {}
        for component_id, adapter in ADAPTERS.items():
            def timed_adapter(*, _cid=component_id, _adapter=adapter, **kwargs):
                started = time.perf_counter()
                try:
                    return _adapter(**kwargs)
                finally:
                    elapsed = time.perf_counter() - started
                    per_observation_times[_cid] = elapsed
                    timed_component_seconds[_cid] += elapsed
            timed_adapters[component_id] = timed_adapter

        full_started = time.perf_counter()
        full_result = evidence.run_integrated_assessment(
            timestamp, "VILD0", observations, predictions, data["stability"], data["episodes"],
            spatial_tables, spatial_sources, "temp", component_adapters=timed_adapters,
        )
        full_elapsed = time.perf_counter() - full_started
        if full_result["timestamp"] != timestamp.isoformat():
            raise AssertionError("integrated assessment returned an altered timestamp")
        baseline_json = json.dumps(full_result["baseline_prediction"], sort_keys=True, default=_json_default)
        baseline_digest.update(baseline_json.encode())
        baseline_digest.update(b"\n")

        ablated_by_id = {}
        assembly_seconds = {}
        for config_id, config in ABLATION_CONFIGURATIONS.items():
            assembly_started = time.perf_counter()
            result = ablate(full_result, config_id)
            assembly_seconds[config_id] = time.perf_counter() - assembly_started
            ablated_by_id[config_id] = result
            category = result["integrated_assessment"]["category"]
            category_sequences[config_id].append(category)
            if result["timestamp"] != timestamp.isoformat():
                raise AssertionError("ablation changed the observation timestamp")
            if result["baseline_prediction"] != full_result["baseline_prediction"]:
                raise AssertionError("ablation modified the saved baseline prediction")

            active = config["components"]
            included_component_seconds = sum(per_observation_times.get(cid, 0.0) for cid in active)
            estimated_total_ms = (included_component_seconds + assembly_seconds[config_id]) * 1000
            components = result["components"]
            statuses = {cid: components[cid]["execution_status"] for cid in evidence.COMPONENT_IDS}
            available_count = sum(status == "AVAILABLE" for status in statuses.values())
            eligible_count = sum(components[cid]["decision_eligible"] and statuses[cid] == "AVAILABLE"
                                 for cid in evidence.COMPONENT_IDS)
            descriptive_count = sum(status == "DESCRIPTIVE_ONLY" for status in statuses.values())
            conflict_ids = [cid for cid, item in components.items() if item["evidence_result"] == "CONFLICTING_EVIDENCE"]
            error_ids = [cid for cid, item in components.items() if item["execution_status"] == "ERROR"]
            e3_detail = components["E3"].get("details", []) if components["E3"]["execution_status"] == "DESCRIPTIVE_ONLY" else []
            observations_rows.append({
                "ablation_id": config_id,
                "configuration_name": config["name"],
                "timestamp": timestamp.isoformat(),
                "station_id": "VILD0",
                "baseline_status": full_result["baseline_prediction"]["execution_status"],
                "baseline_configuration_votes": full_result["baseline_prediction"]["configuration_votes"],
                "baseline_configuration_count": full_result["baseline_prediction"]["configuration_count"],
                "baseline_candidate_8_of_12": full_result["baseline_prediction"]["candidate_8_of_12"],
                "integrated_assessment": category,
                "included_components": "+".join(active) if active else "none",
                **{f"{cid}_execution_status": statuses[cid] for cid in evidence.COMPONENT_IDS},
                **{f"{cid}_evidence_result": components[cid]["evidence_result"] for cid in evidence.COMPONENT_IDS},
                "available_component_count": available_count,
                "decision_eligible_available_component_count": eligible_count,
                "descriptive_only_component_count": descriptive_count,
                "evidence_coverage": available_count > 0,
                "decision_eligible_coverage": eligible_count > 0,
                "evidence_conflict_count": len(conflict_ids),
                "evidence_conflict_components": "+".join(conflict_ids),
                "component_execution_failure_count": len(error_ids),
                "component_execution_failure_ids": "+".join(error_ids),
                "E3_descriptive_row_count": len(e3_detail),
                "estimated_processing_time_ms_per_observation": estimated_total_ms,
            })

        # LOO reference: the project's full eligible evidence set A5.
        eligible = ablated_by_id["A5"]
        eligible_components = ABLATION_CONFIGURATIONS["A5"]["components"]
        eligible_available = sum(eligible["components"][cid]["execution_status"] == "AVAILABLE" for cid in eligible_components)
        for removed in ("E1", "E2", "E4"):
            remaining = tuple(cid for cid in eligible_components if cid != removed)
            loo = apply_component_subset(full_result, remaining, f"A5 without {removed}")
            loo_available = sum(loo["components"][cid]["execution_status"] == "AVAILABLE" for cid in remaining)
            loo_rows.append({
                "timestamp": timestamp.isoformat(), "removed_component": removed,
                "A5_assessment": eligible["integrated_assessment"]["category"],
                "without_component_assessment": loo["integrated_assessment"]["category"],
                "assessment_changed": eligible["integrated_assessment"]["category"] != loo["integrated_assessment"]["category"],
                "A5_available_component_count": eligible_available,
                "without_component_available_count": loo_available,
                "removed_component_status": full_result["components"][removed]["execution_status"],
                "baseline_candidate_preserved": loo["baseline_prediction"] == full_result["baseline_prediction"],
            })

        # E3 contextual comparison: A5 and A6 differ only by E3 display context.
        no_e3, with_e3 = ablated_by_id["A5"], ablated_by_id["A6"]
        e3 = with_e3["components"]["E3"]
        e3_details = e3.get("details", []) if e3["execution_status"] == "DESCRIPTIVE_ONLY" else []
        e3_rows.append({
            "timestamp": timestamp.isoformat(),
            "without_E3_assessment": no_e3["integrated_assessment"]["category"],
            "with_E3_assessment": with_e3["integrated_assessment"]["category"],
            "assessment_changed": no_e3["integrated_assessment"]["category"] != with_e3["integrated_assessment"]["category"],
            "E3_execution_status": e3["execution_status"],
            "E3_evidence_result": e3["evidence_result"],
            "E3_decision_eligible": e3["decision_eligible"],
            "E3_descriptive_rows": len(e3_details),
            "baseline_prediction_preserved": with_e3["baseline_prediction"] == no_e3["baseline_prediction"],
        })

        if ordinal % 1000 == 0:
            print(f"Evaluated {ordinal:,}/{len(timestamps):,} saved baseline timestamps")

    rows = pd.DataFrame(observations_rows)
    loo_frame = pd.DataFrame(loo_rows)
    e3_frame = pd.DataFrame(e3_rows)
    if not rows.groupby("ablation_id").timestamp.nunique().eq(len(timestamps)).all():
        raise AssertionError("ablation configurations did not evaluate identical observation timestamps")
    if not rows.groupby("timestamp").baseline_candidate_8_of_12.nunique().eq(1).all():
        raise AssertionError("baseline prediction differs across ablation configurations")

    # Add pairwise decision-change counts against baseline-only and full architecture.
    piv = rows.pivot(index="timestamp", columns="ablation_id", values="integrated_assessment")
    if not (piv.nunique(axis=1) <= 1).all():
        raise AssertionError("unexpected ablation decision change: inspect baseline-preserving decision rules")
    metrics = []
    status_metrics = {}
    for config_id, config in ABLATION_CONFIGURATIONS.items():
        subset = rows.loc[rows.ablation_id.eq(config_id)]
        n = len(subset)
        statuses_by_component = {}
        for cid in evidence.COMPONENT_IDS:
            counts = subset[f"{cid}_execution_status"].value_counts().to_dict()
            statuses_by_component[cid] = {status: int(counts.get(status, 0)) for status in STATUS_ORDER}
        status_metrics[config_id] = statuses_by_component
        metrics.append({
            "ablation_id": config_id,
            "configuration_name": config["name"],
            "included_components": "+".join(config["components"]) if config["components"] else "none",
            "observations_evaluated": n,
            "baseline_predictions_available": int(subset.baseline_status.eq("AVAILABLE").sum()),
            "evidence_coverage_pct": round(100 * subset.evidence_coverage.mean(), 6),
            "decision_eligible_evidence_coverage_pct": round(100 * subset.decision_eligible_coverage.mean(), 6),
            "descriptive_context_observations": int(subset.descriptive_only_component_count.gt(0).sum()),
            "suspicious_assessments": int(subset.integrated_assessment.eq("SUSPICIOUS").sum()),
            "insufficient_evidence_assessments": int(subset.integrated_assessment.eq("INSUFFICIENT_EVIDENCE").sum()),
            "normal_assessments": int(subset.integrated_assessment.eq("NORMAL").sum()),
            "anomalous_assessments": int(subset.integrated_assessment.eq("ANOMALOUS").sum()),
            "evidence_conflict_count": int(subset.evidence_conflict_count.sum()),
            "observations_with_conflicting_evidence": int(subset.evidence_conflict_count.gt(0).sum()),
            "component_execution_failure_count": int(subset.component_execution_failure_count.sum()),
            "observations_with_component_failure": int(subset.component_execution_failure_count.gt(0).sum()),
            "assessment_changes_vs_A0": int((piv[config_id] != piv["A0"]).sum()),
            "assessment_changes_vs_A6": int((piv[config_id] != piv["A6"]).sum()),
            "mean_available_components_per_observation": round(float(subset.available_component_count.mean()), 6),
            "mean_processing_time_ms_per_observation": round(float(subset.estimated_processing_time_ms_per_observation.mean()), 6),
            **{f"{cid}_included": cid in config["components"] for cid in evidence.COMPONENT_IDS},
            **{f"{cid}_available_count": statuses_by_component[cid]["AVAILABLE"] for cid in evidence.COMPONENT_IDS},
            **{f"{cid}_available_pct": round(100 * statuses_by_component[cid]["AVAILABLE"] / n, 6) for cid in evidence.COMPONENT_IDS},
            **{f"{cid}_descriptive_only_count": statuses_by_component[cid]["DESCRIPTIVE_ONLY"] for cid in evidence.COMPONENT_IDS},
            **{f"{cid}_insufficient_data_count": statuses_by_component[cid]["INSUFFICIENT_DATA"] for cid in evidence.COMPONENT_IDS},
            **{f"{cid}_unavailable_count": statuses_by_component[cid]["UNAVAILABLE"] for cid in evidence.COMPONENT_IDS},
            **{f"{cid}_error_count": statuses_by_component[cid]["ERROR"] for cid in evidence.COMPONENT_IDS},
            **{f"{cid}_not_applicable_count": statuses_by_component[cid]["NOT_APPLICABLE"] for cid in evidence.COMPONENT_IDS},
        })
    config_frame = pd.DataFrame(metrics)

    loo_summary = []
    for removed, subset in loo_frame.groupby("removed_component", sort=False):
        ref_available = subset.A5_available_component_count
        without_available = subset.without_component_available_count
        loo_summary.append({
            "reference_configuration": "A5 · Baseline + E1 + E2 + E4",
            "comparison_configuration": f"A5 without {removed}",
            "removed_component": removed,
            "observations_evaluated": len(subset),
            "assessment_changes": int(subset.assessment_changed.sum()),
            "reference_suspicious_assessments": int(subset.A5_assessment.eq("SUSPICIOUS").sum()),
            "without_component_suspicious_assessments": int(subset.without_component_assessment.eq("SUSPICIOUS").sum()),
            "component_available_observations_before_removal": int(subset.removed_component_status.eq("AVAILABLE").sum()),
            "mean_available_components_before_removal": round(float(ref_available.mean()), 6),
            "mean_available_components_after_removal": round(float(without_available.mean()), 6),
            "available_component_coverage_change_pct": round(float(100 * (without_available.gt(0).mean() - ref_available.gt(0).mean())), 6),
            "component_available_observation_pct_removed": round(float(100 * subset.removed_component_status.eq("AVAILABLE").mean()), 6),
            "baseline_preserved_for_all_observations": bool(subset.baseline_candidate_preserved.all()),
        })

    e3_summary = {
        "reference_configuration": "A5 · Baseline + E1 + E2 + E4",
        "context_configuration": "A6 · Full E1–E4 with E3 descriptive only",
        "observations_evaluated": len(e3_frame),
        "assessment_changes": int(e3_frame.assessment_changed.sum()),
        "without_e3_suspicious": int(e3_frame.without_E3_assessment.eq("SUSPICIOUS").sum()),
        "with_e3_suspicious": int(e3_frame.with_E3_assessment.eq("SUSPICIOUS").sum()),
        "without_e3_insufficient": int(e3_frame.without_E3_assessment.eq("INSUFFICIENT_EVIDENCE").sum()),
        "with_e3_insufficient": int(e3_frame.with_E3_assessment.eq("INSUFFICIENT_EVIDENCE").sum()),
        "descriptive_observation_count": int(e3_frame.E3_execution_status.eq("DESCRIPTIVE_ONLY").sum()),
        "descriptive_comparison_rows_shown": int(e3_frame.E3_descriptive_rows.sum()),
        "insufficient_data_observation_count": int(e3_frame.E3_execution_status.eq("INSUFFICIENT_DATA").sum()),
        "decision_eligible_true_count": int(e3_frame.E3_decision_eligible.sum()),
        "baseline_preserved_for_all_observations": bool(e3_frame.baseline_prediction_preserved.all()),
    }

    total_run_seconds = time.perf_counter() - run_started
    config_summary = {}
    for config_id in ABLATION_CONFIGURATIONS:
        row = config_frame.loc[config_frame.ablation_id.eq(config_id)].iloc[0].to_dict()
        row["component_status_counts"] = status_metrics[config_id]
        row["component_processing_seconds_measured_in_full_pass"] = {
            cid: round(timed_component_seconds[cid], 6) for cid in ABLATION_CONFIGURATIONS[config_id]["components"]
        }
        config_summary[config_id] = row

    manifest_files = {
        "observation_dataset_sha256": input_hashes.get("observations"),
        "test_dataset_sha256": input_hashes.get("test"),
        "saved_prediction_sha256": input_hashes.get("phase03:model_predictions.csv"),
        "saved_stability_sha256": input_hashes.get("phase03:stability_results_verified.csv"),
    }
    summary = {
        "study_id": output_dir.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_type": "STRUCTURAL_OPERATIONAL_CONTRIBUTION_ANALYSIS_NOT_PREDICTIVE_VALIDATION",
        "observations_evaluated": len(timestamps),
        "processed_observations_total": len(observations),
        "training_rows_excluded_no_saved_baseline_predictions": len(data["train"]),
        "baseline_test_rows": len(data["test"]),
        "evaluation_period_start": timestamps.min().isoformat(),
        "evaluation_period_end": timestamps.max().isoformat(),
        "timestamp_sequence_sha256": input_timestamp_signature,
        "preserved_baseline_prediction_sequence_sha256": baseline_digest.hexdigest(),
        "phase01_manifest_audit_passed": manifest.get("audit_passed"),
        "input_artifact_hashes": manifest_files,
        "same_saved_baseline_preserved_in_all_configurations": True,
        "same_timestamp_sequence_used_in_all_configurations": True,
        "model_retrained": False,
        "new_data_downloaded": False,
        "original_research_artifacts_modified": False,
        "preprocessing": "No new preprocessing; repository loader verified Phase 01 datasets and Phase 03 artifact integrity.",
        "baseline_definition_caveat": (
            "The saved baseline candidate_8_of_12 field is computed from the same 12 configuration labels summarized by E1. "
            "Consequently A0 and A1 are not independent baselines, and removing the E1 evidence record cannot remove the preserved baseline candidate signal."
        ),
        "decision_policy": "Existing conservative integration behavior only: SUSPICIOUS when the preserved saved baseline meets its existing 8/12 screen; otherwise INSUFFICIENT_EVIDENCE. No NORMAL or ANOMALOUS inference is made.",
        "ground_truth_available": False,
        "predictive_metrics": {"accuracy": None, "precision": None, "recall": None, "f1": None,
                               "reason": "No suitable independently adjudicated event/fault labels are available."},
        "processing_time_method": (
            "Each E1–E4 adapter was timed once per observation during a shared full pass. For each ablation, mean component time sums the measured times of included components; measured baseline orchestration/masking time is added. "
            "This is a single-run operational estimate, not a controlled performance benchmark. Outputs were cached only to compare decisions and coverage; original model outputs were never recomputed."
        ),
        "full_component_pass_seconds": round(sum(timed_component_seconds.values()), 6),
        "total_study_wall_seconds": round(total_run_seconds, 6),
        "configurations": config_summary,
        "leave_one_out": loo_summary,
        "e3_contextual_ablation": e3_summary,
        "research_limitations": [
            "E3 remains descriptive-only or insufficient-data and is never decision-eligible.",
            "E3 candidate-time indexing does not guarantee exact neighbor observation timestamp alignment; source table offsets are retained in details.",
            "E1 is aliased with the preserved baseline 8/12 candidate signal, preventing an independent E1 decision effect estimate.",
            "E2 and E4 add screens and evidence coverage, but current integrated decision rules do not use them to change category.",
            "Ablation results describe structure, coverage, assessment behavior, and single-run processing time only; they are not predictive-performance validation.",
            "ANOMALY ≠ FAULT; suspicious model candidates are not confirmed faults.",
        ],
    }

    rows.to_csv(output_dir / "ablation_results.csv", index=False)
    config_frame.to_csv(output_dir / "ablation_configuration_summary.csv", index=False)
    loo_frame.to_csv(output_dir / "leave_one_out_results.csv", index=False)
    e3_frame.to_csv(output_dir / "E3_contextual_ablation.csv", index=False)
    pd.DataFrame(loo_summary).to_csv(output_dir / "leave_one_out_summary.csv", index=False)
    (output_dir / "ablation_summary.json").write_text(json.dumps(summary, indent=2, default=_json_default) + "\n", encoding="utf-8")
    _make_plots(summary, config_frame, output_dir)
    return summary


def _write_report(summary: dict, output_dir: Path) -> None:
    configs = summary["configurations"]
    lines = [
        "# WeatherGuard E1–E4 Contribution and Ablation Study",
        "",
        f"**Run:** `{summary['study_id']}`  ",
        f"**Evaluation observations:** {summary['observations_evaluated']:,} saved held-out timestamps  ",
        f"**Period:** {summary['evaluation_period_start']} to {summary['evaluation_period_end']}  ",
        "**Study type:** Structural/operational contribution analysis, not predictive-performance validation.",
        "",
        "## Methodology",
        "",
        "The same verified processed observations, exact saved Phase 03 baseline prediction grid, 8/12 screen, preprocessing, and held-out timestamp sequence were reused in every configuration. The baseline grid has 12 saved configuration outputs per timestamp. The 36,464 training rows were not assessed because no saved baseline prediction rows exist for them. Evidence coverage is the percentage of observations with at least one included component in `AVAILABLE`; E3 `DESCRIPTIVE_ONLY` context is counted separately and does not count as decision-eligible evidence coverage.",
        "",
        "No model was retrained, no external data were downloaded, no thresholds were introduced, and no original research artifact was modified. Components were computed once per observation; configurations were then compared by masking component records. A disabled component is `NOT_APPLICABLE`, never negative evidence.",
        "Processing times are single-run estimates: measured adapter time for included components plus the time to assemble and summarize the ablation result. The seven configurations were not separately cold-start benchmarked; timings are operational comparisons, not performance claims.",
        "",
        "## Configuration comparison",
        "",
        "| ID | Configuration | SUSPICIOUS | INSUFFICIENT_EVIDENCE | Evidence coverage | E3 context obs. | Conflicts | Execution failures | Mean ms / observation | Assessment changes vs A0 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for config_id, row in configs.items():
        lines.append(
            f"| {config_id} | {row['configuration_name']} | {row['suspicious_assessments']:,} | "
            f"{row['insufficient_evidence_assessments']:,} | {row['evidence_coverage_pct']:.2f}% | "
            f"{row['descriptive_context_observations']:,} | {row['evidence_conflict_count']:,} | {row['component_execution_failure_count']:,} | "
            f"{row['mean_processing_time_ms_per_observation']:.4f} | {row['assessment_changes_vs_A0']:,} |"
        )
    lines += [
        "",
        "![Ablation comparison](ablation_comparison.png)",
        "",
        "![Assessment distribution](assessment_distribution.png)",
        "",
        "![Component coverage](component_coverage.png)",
        "",
        "![Processing time](processing_time_comparison.png)",
        "",
        "## Component availability in A6",
        "",
        "| Component | AVAILABLE | DESCRIPTIVE_ONLY | INSUFFICIENT_DATA | ERROR | NOT_APPLICABLE |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for cid, counts in configs["A6"]["component_status_counts"].items():
        lines.append(f"| {cid} | {counts['AVAILABLE']:,} | {counts['DESCRIPTIVE_ONLY']:,} | {counts['INSUFFICIENT_DATA']:,} | {counts['ERROR']:,} | {counts['NOT_APPLICABLE']:,} |")
    lines += [
        "",
        "## Leave-one-component-out analysis",
        "",
        "The reference is A5 (baseline + E1 + E2 + E4). Baseline predictions remain fixed in every comparison.",
        "",
        "| Removed | Assessment changes | Observations with removed component available | Mean available components before → after |",
        "|---|---:|---:|---:|",
    ]
    for row in summary["leave_one_out"]:
        lines.append(f"| {row['removed_component']} | {row['assessment_changes']:,} | {row['component_available_observations_before_removal']:,} | {row['mean_available_components_before_removal']:.3f} → {row['mean_available_components_after_removal']:.3f} |")
    lines += [
        "",
        "![Leave-one-out comparison](leave_one_out_comparison.png)",
        "",
        "## E3 contextual ablation",
        "",
        f"Adding E3 descriptive context changed {summary['e3_contextual_ablation']['assessment_changes']:,} of {summary['observations_evaluated']:,} integrated assessments. E3 descriptive rows were available at {summary['e3_contextual_ablation']['descriptive_observation_count']:,} timestamps ({summary['e3_contextual_ablation']['descriptive_comparison_rows_shown']:,} comparison rows total). E3 was decision-eligible in {summary['e3_contextual_ablation']['decision_eligible_true_count']:,} cases.",
        "",
        "![E3 contextual ablation](E3_contextual_ablation.png)",
        "",
        "## Interpretation",
        "",
        "The saved baseline candidate output is itself calculated from the 12 model-configuration labels summarized by E1. Under the required baseline-preservation control, A0 and A1 are therefore not independent. Removing the E1 evidence record does not remove the preserved baseline's 8/12 candidate signal. A zero assessment change for E1 is not evidence that E1 has no role; its role is embedded in the baseline definition and cannot be independently identified by this design.",
        "",
        "E2 and E4 provide temporal and broad physical screening information. They can change evidence coverage, but do not change categories under the existing conservative integration policy. E3 adds descriptive comparison context where a candidate-time-indexed row exists; it is not used as independent corroboration and does not change categories. A candidate-time match does not establish exact neighbor timestamp alignment; row-level offsets remain visible in the E3 output.",
        "",
        "## Research limitations",
        "",
        "There are no suitable independently adjudicated event/fault labels, so accuracy, precision, recall, and F1 are unsupported and were not calculated. `SUSPICIOUS` denotes the saved 8/12 model screen for review, not an anomalous weather event or sensor fault. `INSUFFICIENT_EVIDENCE` is not equivalent to normal. E3's independent station lineage, exact alignment, and event adjudication remain unresolved. Processing times are single-run operational estimates and not controlled benchmarks.",
        "",
        "Detailed per-observation outputs are in `ablation_results.csv`; the aggregate table is `ablation_configuration_summary.csv`; the assessment-change and E3 detail tables are also provided as CSV. See `ablation_summary.json` for hashes, counts, timing method, and limitations.",
        "",
        "## Reproduction",
        "",
        "```powershell",
        f"python scripts/run_e1_e4_ablation.py --output-dir {output_dir.relative_to(ROOT).as_posix()}",
        "```",
        "",
    ]
    (output_dir / "ABLATION_STUDY_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def render_existing_output(output_dir: Path) -> None:
    """Re-render figures/report from this run's saved result tables only."""
    summary_path = output_dir / "ablation_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    config_frame = pd.read_csv(output_dir / "ablation_configuration_summary.csv")
    loo_frame = pd.read_csv(output_dir / "leave_one_out_summary.csv")
    if "component_available_observation_pct_removed" not in loo_frame:
        loo_detail = pd.read_csv(output_dir / "leave_one_out_results.csv")
        component_coverage = (
            loo_detail.assign(is_available=loo_detail.removed_component_status.eq("AVAILABLE"))
            .groupby("removed_component", sort=False).is_available.mean().mul(100).to_dict()
        )
        loo_frame["component_available_observation_pct_removed"] = loo_frame.removed_component.map(component_coverage)
    summary["leave_one_out"] = loo_frame.to_dict("records")
    summary_path.write_text(json.dumps(summary, indent=2, default=_json_default) + "\n", encoding="utf-8")
    _make_plots(summary, config_frame, output_dir)
    _write_report(summary, output_dir)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", help="New or empty output directory; defaults to a unique research_results run folder.")
    parser.add_argument("--render-existing", action="store_true", help="Re-render charts/report from CSV and JSON outputs in --output-dir without rerunning components.")
    args = parser.parse_args()
    if args.render_existing:
        if not args.output_dir:
            parser.error("--render-existing requires --output-dir")
        path = Path(args.output_dir)
        if not path.is_absolute():
            path = ROOT / path
        render_existing_output(path)
        print(f"Rendered existing study artifacts from saved outputs in: {path}")
        return
    output_dir = _empty_output_directory(args.output_dir)
    summary = run(output_dir)
    _write_report(summary, output_dir)
    print(f"Output directory: {output_dir}")
    print(f"Evaluated observations: {summary['observations_evaluated']:,}")
    for config_id, metric in summary["configurations"].items():
        print(f"{config_id}: SUSPICIOUS={metric['suspicious_assessments']:,}; INSUFFICIENT_EVIDENCE={metric['insufficient_evidence_assessments']:,}; coverage={metric['evidence_coverage_pct']:.2f}%; mean_ms={metric['mean_processing_time_ms_per_observation']:.4f}")
    print(f"E3 assessment changes: {summary['e3_contextual_ablation']['assessment_changes']:,}")
    print(f"Total wall seconds: {summary['total_study_wall_seconds']:.2f}")


if __name__ == "__main__":
    main()
