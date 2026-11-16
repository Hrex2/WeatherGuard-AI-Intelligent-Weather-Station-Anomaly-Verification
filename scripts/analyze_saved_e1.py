"""Derive E1 agreement and sensitivity tables from saved labels only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from services.data_service import load_project_data
from services.model_metadata import build_model_education


def analyze(root=ROOT):
    data, _, hashes = load_project_data(root)
    predictions = data["predictions"].copy()
    wide = predictions.pivot(index="timestamp", columns="configuration", values="is_candidate").astype(bool)
    metadata = predictions.drop_duplicates("configuration").set_index("configuration")
    config = pd.DataFrame({"configuration": wide.columns})
    education = build_model_education(data)
    lookup = {item["name"]: item for profile in education["profiles"].values() for item in profile["configs"]}
    config["family"] = config.configuration.map(metadata.family)
    config["parameter"] = config.configuration.map(lambda name: lookup[name]["parameter"])
    config["parameter_value"] = config.configuration.map(lambda name: lookup[name]["value"])
    config["anomaly_count"] = [int(wide[name].sum()) for name in config.configuration]
    config["anomaly_pct"] = config.anomaly_count / len(wide) * 100
    config["normal_count"] = len(wide) - config.anomaly_count

    family_votes = pd.DataFrame(index=wide.index)
    for family, names in metadata.groupby("family").groups.items():
        family_votes[family] = wide[list(names)].sum(axis=1)
    family_summary = pd.DataFrame([{"family": family, "any_config_count": int((family_votes[family] > 0).sum()),
        "all_four_count": int((family_votes[family] == 4).sum()),
        "mean_config_votes": float(family_votes[family].mean()),
        "mean_fraction_flagged": float((family_votes[family] / 4).mean())}
        for family in family_votes.columns])

    threshold_rows = []
    vote_count = wide.sum(axis=1)
    for threshold in (4, 6, 8, 10, 12):
        selected = vote_count.ge(threshold)
        threshold_rows.append({"threshold": f"{threshold}/12", "timestamps": int(selected.sum()),
                               "pct_of_test_timestamps": float(selected.mean() * 100),
                               "interpretation": "Sensitivity threshold only; not an optimal cutoff or calibrated probability."})
    overlap = pd.DataFrame(index=wide.columns, columns=wide.columns, dtype=float)
    for left in wide.columns:
        for right in wide.columns:
            union = wide[left] | wide[right]
            overlap.loc[left, right] = float((wide[left] & wide[right]).sum() / union.sum()) if union.any() else float("nan")
    pair_rows = []
    for i, left in enumerate(wide.columns):
        for right in wide.columns[i + 1:]:
            pair_rows.append({"configuration_a": left, "family_a": metadata.loc[left, "family"],
                              "configuration_b": right, "family_b": metadata.loc[right, "family"],
                              "jaccard_overlap": overlap.loc[left, right],
                              "coflag_count": int((wide[left] & wide[right]).sum()),
                              "disagreement_count": int((wide[left] ^ wide[right]).sum())})
    out = root / "research_results"
    out.mkdir(exist_ok=True)
    config.to_csv(out / "e1_configuration_comparison.csv", index=False)
    family_summary.to_csv(out / "e1_family_comparison.csv", index=False)
    pd.DataFrame(threshold_rows).to_csv(out / "e1_threshold_sensitivity.csv", index=False)
    pd.DataFrame(pair_rows).to_csv(out / "e1_pairwise_overlap.csv", index=False)
    summary = {"source": "Saved Phase 03 binary labels; no refit performed.", "prediction_rows": len(predictions),
               "timestamps": len(wide), "configurations": len(wide.columns), "data_hashes": hashes,
               "any_model_timestamps": int(vote_count.gt(0).sum()),
               "threshold_counts": {row["threshold"]: row["timestamps"] for row in threshold_rows},
               "limitation": "Agreement describes saved binary model outputs, not calibrated event or sensor-failure probabilities."}
    (out / "e1_analysis_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(analyze(), indent=2))
