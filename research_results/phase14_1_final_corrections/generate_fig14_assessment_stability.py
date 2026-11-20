"""Create a non-empty, artifact-verified Phase 12 assessment graphic."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "research_results/phase12_evidence_contribution/20261119T144632Z"
OUT = Path(__file__).resolve().parent / "fig14_assessment_stability_corrected.png"


def main() -> None:
    summary = json.loads((RUN / "phase12_summary.json").read_text(encoding="utf-8"))
    configurations = summary["sensitivity"]
    distribution = summary["assessment_distribution"]
    n = int(summary["observations"])

    assert n == 8415
    assert len(configurations) == 10
    assert all(int(row["observations"]) == n for row in configurations)
    assert all(int(row["assessment_changes_vs_P0"]) == 0 for row in configurations)
    assert all(int(row["assessment_changes_vs_P4"]) == 0 for row in configurations)
    assert distribution == {"INSUFFICIENT_EVIDENCE": 8292, "SUSPICIOUS": 123}
    counts = {
        "INSUFFICIENT_EVIDENCE": int(distribution.get("INSUFFICIENT_EVIDENCE", 0)),
        "SUSPICIOUS": int(distribution.get("SUSPICIOUS", 0)),
        "NORMAL": int(distribution.get("NORMAL", 0)),
        "ANOMALOUS": int(distribution.get("ANOMALOUS", 0)),
    }
    assert sum(counts.values()) == n

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7})
    fig = plt.figure(figsize=(3.2, 1.9), facecolor="white")
    fig.text(0.5, 0.965, "Phase 12 assessment results", ha="center", va="top", fontsize=8, weight="bold", color="#182B3A")
    fig.text(0.5, 0.855, "0 category changes across 10 configurations (8,415 timestamps each)", ha="center", va="top", fontsize=6.1, color="#34495E")

    ax = fig.add_axes([0.39, 0.23, 0.56, 0.53])
    labels = ["INSUFFICIENT_EVIDENCE", "SUSPICIOUS", "NORMAL", "ANOMALOUS"]
    values = [counts[label] for label in labels]
    colors = ["#287A8A", "#D88732", "#A9B4BE", "#7E8A95"]
    y = list(range(len(labels)))
    bars = ax.barh(y, values, height=0.58, color=colors, edgecolor="none")
    ax.set_yticks(y, labels, fontsize=5.7)
    ax.invert_yaxis()
    ax.set_xlim(0, n * 1.13)
    ax.set_xticks([0, 4000, 8000], ["0", "4,000", "8,000"], fontsize=5.4)
    ax.grid(axis="x", color="#D9E1E7", linewidth=0.5)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#AAB7C2")
    ax.tick_params(axis="y", length=0, pad=3)
    ax.tick_params(axis="x", length=2, colors="#52616B", pad=1)
    for bar, value in zip(bars, values):
        x = value + (105 if value else 60)
        ax.text(x, bar.get_y() + bar.get_height() / 2, f"{value:,}", va="center", ha="left", fontsize=5.8, color="#182B3A")

    fig.text(0.5, 0.07, "Fixed baseline-derived categories; stability is not component equivalence.", ha="center", va="bottom", fontsize=5.3, color="#52616B")
    fig.savefig(OUT, dpi=400, bbox_inches="tight", pad_inches=0.035)
    plt.close(fig)
    print(f"Wrote {OUT}; verified n={n}, configs={len(configurations)}, distribution={counts}")


if __name__ == "__main__":
    main()
