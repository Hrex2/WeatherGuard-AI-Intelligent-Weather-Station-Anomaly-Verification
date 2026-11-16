"""Compare existing model, consensus, temporal and physical screens on known injections.

This is a synthetic response comparison, not a field accuracy study. Unmodified
held-out rows are not treated as verified negatives.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / "research_results" / "fault_matrix_multicontext_46ae5d119d"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def analyze(campaign_dir: Path = CAMPAIGN) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    manifest_path = campaign_dir / "campaign_manifest.json"
    campaign = json.loads(manifest_path.read_text(encoding="utf-8"))
    context_rows = []
    for context in campaign["contexts"]:
        run_dir = ROOT / Path(context["run_directory"])
        predictions = pd.read_csv(run_dir / "changed_and_injected_predictions.csv")
        predictions["timestamp"] = pd.to_datetime(predictions.timestamp, utc=True)
        injected = predictions.loc[predictions.synthetic_fault_label.astype(bool)].copy()
        for (experiment_id, timestamp), group in injected.groupby(["experiment_id", "timestamp"], sort=True):
            votes = int(group.is_candidate.astype(bool).sum())
            n_configs = int(group.configuration.nunique())
            if n_configs != 12:
                raise ValueError(f"Expected 12 model configurations for {context['context_id']} {experiment_id} {timestamp}; found {n_configs}")
            base = {"context_id": context["context_id"], "experiment_id": experiment_id,
                    "timestamp_utc": timestamp.isoformat(), "injected_configuration_rows": n_configs,
                    "e1_votes": votes}
            for family, family_rows in group.groupby("family"):
                context_rows.append({**base, "baseline": f"family:{family}", "setting": "all",
                                     "flagged": int(family_rows.is_candidate.astype(bool).sum()),
                                     "denominator": int(family_rows.configuration.nunique())})
            for threshold in (4, 6, 8, 10, 12):
                context_rows.append({**base, "baseline": "E1_consensus", "setting": f"{threshold}/12",
                                     "flagged": int(votes >= threshold), "denominator": 1})

        e4_path = run_dir / "physical_screening_results.csv"
        e4 = pd.read_csv(e4_path)
        registry = pd.read_csv(run_dir / "injection_registry.csv")
        target_variable = registry.groupby("experiment_id").target_variable.first().to_dict()
        direct = e4[e4.apply(lambda r: r.variable == target_variable.get(r.experiment_id), axis=1)]
        for (experiment_id, timestamp), group in direct.groupby(["experiment_id", "timestamp"], sort=True):
            context_rows.append({"context_id": context["context_id"], "experiment_id": experiment_id,
                                 "timestamp_utc": pd.Timestamp(timestamp).tz_convert("UTC").isoformat(),
                                 "injected_configuration_rows": 12, "e1_votes": pd.NA,
                                 "baseline": "E4_direct_variable_screen", "setting": "existing broad rule",
                                 "flagged": int(group.screening_flag_faulted.astype(bool).any()), "denominator": 1})

    detail = pd.DataFrame(context_rows)
    detail["response_fraction"] = detail.flagged / detail.denominator
    summary = (detail.groupby(["baseline", "setting", "experiment_id"], dropna=False)
               .agg(context_timestamp_units=("response_fraction", "size"),
                    mean_response_fraction=("response_fraction", "mean"),
                    minimum_context_fraction=("response_fraction", "min"),
                    maximum_context_fraction=("response_fraction", "max"))
               .reset_index())

    e2_path = campaign_dir / "e2_multicontext_fault_detail.csv"
    e2_detail = pd.read_csv(e2_path)
    faulted = e2_detail[e2_detail.condition.eq("synthetic_faulted")].copy()
    e2_summary = (faulted.groupby(["experiment_id", "mode", "window_hours", "robust_z_threshold"], dropna=False)
                  .agg(screen_rows=("status", "size"),
                       supporting=("status", lambda s: int(s.eq("SUPPORTING").sum())),
                       conflicting=("status", lambda s: int(s.eq("CONFLICTING").sum())),
                       unavailable=("status", lambda s: int(s.eq("UNAVAILABLE").sum())))
                  .reset_index())
    e2_summary["supporting_fraction_available"] = e2_summary.supporting / (e2_summary.screen_rows - e2_summary.unavailable).replace(0, pd.NA)
    output = campaign_dir
    detail_path, summary_path, e2_summary_path = (output / "synthetic_baseline_response_detail.csv",
                                                   output / "synthetic_baseline_response_summary.csv",
                                                   output / "synthetic_e2_setting_sensitivity.csv")
    detail.to_csv(detail_path, index=False)
    summary.to_csv(summary_path, index=False)
    e2_summary.to_csv(e2_summary_path, index=False)
    try:
        code_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        code_revision = "UNKNOWN"
    run_manifest = {
        "status": "EXECUTED_SYNTHETIC_BASELINE_AND_SENSITIVITY_COMPARISON",
        "campaign_id": campaign["campaign_id"],
        "code_revision": code_revision,
        "objective": "Compare fixed model-family and E1 consensus response, direct-variable E4 screening, and E2 settings on identical synthetic injection timestamps.",
        "experimental_unit": "context × scenario × synthetically labelled timestamp; E2 setting rows are repeated screens over those same timestamps",
        "dataset_hashes": campaign["dataset_hashes"],
        "source_artifacts": {"campaign_manifest_sha256": sha256(manifest_path),
                             "e2_detail_sha256": sha256(e2_path)},
        "outputs": [detail_path.name, summary_path.name, e2_summary_path.name],
        "interpretation_limit": "Synthetic injection response fractions only. Unmodified rows are not verified negatives; no real-world accuracy, precision, recall, or causal superiority is estimated.",
        "context_count": campaign["context_count"],
        "scenario_count": len(campaign["scenarios"]),
        "injected_timestamp_units": int(detail[detail.baseline.eq("E1_consensus") & detail.setting.eq("8/12")].shape[0]),
    }
    (output / "synthetic_baseline_comparison_manifest.json").write_text(json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8")
    return detail, summary, run_manifest


if __name__ == "__main__":
    detail, summary, manifest = analyze()
    print(json.dumps({"status": manifest["status"], "context_timestamp_units": manifest["injected_timestamp_units"],
                      "detail_rows": len(detail), "summary_rows": len(summary), "code_revision": manifest["code_revision"]}, indent=2))
