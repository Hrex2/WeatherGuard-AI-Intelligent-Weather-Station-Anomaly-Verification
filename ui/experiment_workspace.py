"""Experiment reader that presents saved results and their limits by evidence stage."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.chart_theme import style_chart
SECTIONS = ["E1 · Model Stability", "E2 · Temporal Consistency", "E3 · Spatial Evidence",
            "E4 · Physical Plausibility", "Phase 12 · Contribution and Ablation",
            "Phase 13 · Research Synthesis", "Phase 14 · IEEE Paper", "Synthetic Campaigns"]
PHASE12 = Path("research_results/phase12_evidence_contribution/20261119T144632Z")


def _load_summary(root: Path) -> dict | None:
    try:
        result = json.loads((root / PHASE12 / "phase12_summary.json").read_text(encoding="utf-8"))
        return result if result.get("observations") == 8415 and result.get("run_id") == "20261119T144632Z" else None
    except (OSError, ValueError, TypeError):
        return None


def render_experiment_workspace(root, data: dict, hashes: dict, render_synthetic_campaigns) -> None:
    root = Path(root)
    st.markdown("<div class='wg-eyebrow'>EXPERIMENTS · SAVED EVIDENCE</div>", unsafe_allow_html=True)
    st.title("Experiment Lab")
    st.caption("Browse saved analyses by evidence component. Synthetic results remain separate from observations and do not estimate field fault-detection performance.")
    nav, content = st.columns([0.82, 2.45], gap="large")
    with nav:
        st.markdown("#### Experiment sections")
        section = st.radio("Experiment sections", SECTIONS, key="experiment_section_navigation", label_visibility="collapsed")
    with content:
        summary = _load_summary(root)
        if section == "E1 · Model Stability":
            st.header("E1 · Model Stability")
            st.write("E1 summarizes agreement across the saved Isolation Forest, Local Outlier Factor, and One-Class SVM configurations. Phase 12 found the E1 vote counts and 8/12 candidate flags identical to the baseline-derived votes for all 8,415 held-out timestamps.")
            st.metric("Baseline 8/12 candidates", f"{int(data['stability'].configuration_votes.ge(8).sum()):,}")
            st.warning("E1 duplicates the baseline signal in the audited artifact set. Configuration agreement is not calibrated confidence and supplies no independent validation.")
            cfg = data["configuration_results"]
            if {"configuration", "anomalies"}.issubset(cfg.columns):
                fig = px.bar(cfg, x="configuration", y="anomalies", color="family" if "family" in cfg else None,
                             title="Saved flags by model configuration", labels={"anomalies": "Flagged held-out timestamps"})
                st.plotly_chart(style_chart(fig, 330), width="stretch")
        elif section == "E2 · Temporal Consistency":
            st.header("E2 · Temporal Consistency")
            st.write("E2 compares a candidate with the same station’s prior measurements. The saved screen provides temporal context, but event truth and incremental predictive value are not independently adjudicated.")
            if summary:
                record = next(row for row in summary["coverage"] if row["component"] == "E2")
                st.metric("Descriptive support flags", f"{record['supporting_n']:,} / {record['observations']:,}")
            st.info("These are temporal-screen flags, not 1,661 confirmed weather events or sensor faults.")
        elif section == "E3 · Spatial Evidence":
            st.header("E3 · Spatial Evidence")
            st.error("Decision-ineligible: independent provider lineage and event adjudication are insufficient.")
            if summary:
                e3 = summary["E3"]
                eligible_count = summary["observations"] if e3["decision_eligible"] else 0
                cards = st.columns(4)
                cards[0].metric("Eligible observations", f"{eligible_count:,} / {summary['observations']:,}")
                cards[1].metric("Neighbor-indexed rows", f"{e3['indexed_rows']:,}")
                cards[2].metric("Exact timestamp rows", f"{e3['exact_timestamp_rows']:,}")
                cards[3].metric("Missing timestamp offsets", f"{e3['missing_offset_rows']:,}")
                st.write("Pairwise station comparisons remain descriptive. Equal timestamps, nearby locations, or a high correlation do not establish independent sources or verify a shared event.")
                st.caption("E3 is isolated context and does not vote in or alter classification decisions. Missing spatial evidence is not contradictory evidence.")
        elif section == "E4 · Physical Plausibility":
            st.header("E4 · Physical Plausibility")
            if summary:
                record = next(row for row in summary["coverage"] if row["component"] == "E4")
                st.metric("Positive support flags", f"{record['supporting_n']:,} / {record['observations']:,}")
                st.metric("Observations with missing measured variables", f"{summary['E4_observations_with_any_missing_variable']:,}")
            st.write("The broad plausibility screen produced no positive support flags in the evaluated Phase 12 window. That outcome does not show that every reading is correct or that the screen is ineffective.")
        elif section == "Phase 12 · Contribution and Ablation":
            st.header("Phase 12 · Evidence Contribution and Ablation")
            if not summary:
                st.error("Verified Phase 12 summary unavailable; no values are substituted.")
            else:
                metrics = st.columns(5)
                metrics[0].metric("Held-out timestamps", f"{summary['observations']:,}")
                metrics[1].metric("E2 flags", f"{next(x['supporting_n'] for x in summary['coverage'] if x['component']=='E2'):,}")
                metrics[2].metric("E3 eligible", f"{summary['E3']['decision_eligible']}")
                metrics[3].metric("E4 flags", f"{next(x['supporting_n'] for x in summary['coverage'] if x['component']=='E4'):,}")
                metrics[4].metric("Prediction mismatches", "42 / 100,980")
                distribution = summary["assessment_distribution"]
                assessment_rows = [{"Assessment": name, "Timestamps": int(distribution.get(name, 0))}
                                   for name in ("SUSPICIOUS", "INSUFFICIENT_EVIDENCE", "NORMAL", "ANOMALOUS")]
                st.dataframe(pd.DataFrame(assessment_rows), hide_index=True, width="stretch")
                sensitivity = pd.DataFrame(summary["sensitivity"])
                st.caption(f"Sensitivity configurations: {len(sensitivity)}. Zero category changes under a fixed baseline-derived rule do not establish equivalent component utility.")
                fig_path = root / "research_results" / "phase14_1_final_corrections" / "fig14_assessment_stability_corrected.png"
                if fig_path.is_file():
                    st.image(str(fig_path), caption="Assessment counts and category stability under the fixed policy.", use_container_width=True)
                st.dataframe(sensitivity[["configuration_id", "observations", "SUSPICIOUS", "INSUFFICIENT_EVIDENCE", "NORMAL", "ANOMALOUS", "assessment_changes_vs_P0"]], hide_index=True, width="stretch")
                st.warning("All zero-change results follow from the fixed baseline-derived policy. Evidence profiles changed; zero category changes do not show equal component utility.")
        elif section == "Phase 13 · Research Synthesis":
            st.header("Phase 13 · Research Synthesis")
            path = root / "research_results" / "phase13_research_synthesis" / "PHASE13_FINAL_RESEARCH_SYNTHESIS.md"
            if path.is_file():
                st.markdown(path.read_text(encoding="utf-8"))
            else:
                st.info("Phase 13 synthesis is not present in this checkout.")
        elif section == "Phase 14 · IEEE Paper":
            st.header("Phase 14 · IEEE Paper")
            paper_dir = root / "research_results" / "phase14_1_final_corrections"
            pdf = paper_dir / "WeatherGuard_AI_IEEE_Final_Corrected_v3.pdf"
            docx = paper_dir / "WeatherGuard_AI_IEEE_Final_Corrected_v3.docx"
            st.write("The paper documents evidence scope, unresolved provenance, synthetic limits, and the 42/100,980 reproducibility mismatch. Its availability depends on the local research artifact directory.")
            if pdf.is_file():
                st.download_button("Download IEEE paper PDF", pdf.read_bytes(), file_name=pdf.name, mime="application/pdf", key="experiment_paper_pdf")
            if docx.is_file():
                st.download_button("Download editable IEEE paper", docx.read_bytes(), file_name=docx.name, mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="experiment_paper_docx")
            if not pdf.is_file() and not docx.is_file():
                st.info("The local Phase 14 paper files are unavailable in this checkout.")
        else:
            render_synthetic_campaigns(root, data, hashes)
