"""Paper-oriented reading view assembled from the repository's saved evidence."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st


PAPER_SECTIONS = [
    "Abstract", "Introduction", "Related Work", "Dataset and Data Provenance",
    "Proposed Framework", "Methodology", "Experimental Results", "Discussion",
    "Limitations", "Conclusion", "References",
]
PHASE12 = Path("research_results/phase12_evidence_contribution/20261119T144632Z")


def _phase12(root: Path) -> dict | None:
    path = root / PHASE12 / "phase12_summary.json"
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        return result if result.get("observations") == 8415 else None
    except (OSError, ValueError, TypeError):
        return None


def render_research_workspace(root, data: dict) -> None:
    root = Path(root)
    st.markdown("<div class='wg-eyebrow'>RESEARCH · PAPER READER</div>", unsafe_allow_html=True)
    st.title("Research")
    st.caption("Read the study by section. Counts and figures below are loaded from saved project artifacts; the evidence limits remain part of the interpretation.")
    nav, reading = st.columns([0.78, 2.5], gap="large")
    with nav:
        st.markdown("#### Contents")
        section = st.radio("Paper sections", PAPER_SECTIONS, key="research_section_navigation", label_visibility="collapsed")
    with reading:
        if section == "Abstract":
            st.header("Provenance-Based Review of Weather-Station Anomalies")
            st.markdown("Anomalies in weather data do not necessarily indicate sensor faults. This paper reviews evidence recorded by the WeatherGuard AI system. In the Phase 12 audit of 8,415 held-out timestamps, E1 reproduces baseline votes, E2 flags 1,661 timestamps, E4 produces no positive flags, and E3 has no eligible independent observations. The baseline-derived policy marks 123 timestamps as **SUSPICIOUS** and 8,292 as **INSUFFICIENT_EVIDENCE**. Forty-two of 100,980 prediction cells disagree; the cause remains unresolved. Independent adjudicated fault labels are unavailable, so detection performance cannot be estimated.")
            st.markdown("**Index terms—** Anomaly detection, meteorological quality control, uncertainty, data provenance, station validation, spatial corroboration.")
        elif section == "Introduction":
            st.header("I. Introduction")
            st.write("Weather-station records can contain abrupt spikes, gradual drift, repeated values, missing blocks, and physically implausible combinations. Automated screening helps prioritize review, but a statistical anomaly is not proof of instrument failure.")
            st.info("ANOMALY ≠ FAULT. A candidate reading needs context; where evidence is missing or ineligible, the system should not infer a fault.")
            st.write("The study asks how model stability, temporal patterns, spatial context, and physical screening can be presented separately when independently adjudicated fault labels are unavailable.")
        elif section == "Related Work":
            st.header("II. Related Work")
            path = root / "research_content" / "literature.json"
            try:
                papers = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                papers = []
            if not papers:
                st.info("The literature metadata file is unavailable in this checkout.")
            for paper in papers:
                with st.expander(f"{paper['year']} · {paper['title']}", expanded=False):
                    st.markdown(f"**Authors:** {paper['authors']}  \n**Venue:** {paper['venue']}  \n**DOI:** [{paper['doi']}]({paper['url']})")
                    st.write(paper["objective"])
                    st.write("**Method and findings:** " + paper["data_and_method"] + " " + paper["findings"])
                    st.caption("Limits and relevance: " + paper["limitations"] + " " + paper["relevance"])
        elif section == "Dataset and Data Provenance":
            st.header("III. Dataset and Data Provenance")
            obs = data["observations"]
            facts = st.columns(4)
            facts[0].metric("Processed rows", f"{len(obs):,}")
            facts[1].metric("Features", f"{len(data['train'].columns)}")
            facts[2].metric("Train / test rows", f"{len(data['train']):,} / {len(data['test']):,}")
            facts[3].metric("Prediction cells", f"{len(data['predictions']):,}")
            st.write(f"The processed series spans {obs.index.min():%Y-%m-%d} through {obs.index.max():%Y-%m-%d}. The included manifest verifies hashes, columns, and row counts. It does not establish the full original provider lineage or instrument history.")
            st.warning("The legacy Meteostat notebook omits model-fill and flag settings. Its 6,024-row output cannot be confirmed as direct observations or reconciled to later source-stratified exports.")
            st.caption("Station-record coordinates and comparison records do not by themselves verify sensor location, source independence, or event-level corroboration.")
        elif section == "Proposed Framework":
            st.header("IV. Proposed WeatherGuard AI Framework")
            descriptions = [
                ("E1 · Model stability", "Agreement across saved model configurations. The Phase 12 results show dependence on the baseline vote signal; agreement is not calibrated confidence."),
                ("E2 · Temporal consistency", "Historical screening of an observation against prior same-station values. Its 1,661 flags are descriptive and not independently adjudicated."),
                ("E3 · Spatial evidence", "Neighbor comparisons are retained as context. Independent lineage and synchronized event observations are insufficient, so E3 is decision-ineligible."),
                ("E4 · Physical plausibility", "Broad physical and missing-data screening. No positive E4 support flags occurred in the Phase 12 window; this does not establish sensor health."),
            ]
            cols = st.columns(2)
            for idx, (title, body) in enumerate(descriptions):
                with cols[idx % 2].container(border=True):
                    st.markdown(f"**{title}**")
                    st.write(body)
            st.warning("E3 is not classifier voting. Missing evidence and contradictory evidence remain distinct states.")
        elif section == "Methodology":
            st.header("V. Methodology")
            st.write("Analysis uses saved processed observations, model predictions, stability summaries, spatial comparisons, and physical-screen outputs. Synthetic injections are controlled tests of declared responses; they do not estimate field fault-detection accuracy.")
            st.dataframe(pd.DataFrame([
                {"Stage": "Input", "Saved evidence": f"{len(data['observations']):,} processed rows; chronological train/test split"},
                {"Stage": "Model screen", "Saved evidence": f"{data['predictions'].configuration.nunique()} configurations; {len(data['predictions']):,} prediction cells"},
                {"Stage": "Temporal", "Saved evidence": "Same-station historical checks; 1,661 Phase 12 support flags"},
                {"Stage": "Spatial", "Saved evidence": "Descriptive comparisons; no decision-eligible independent observations"},
                {"Stage": "Physical", "Saved evidence": "Broad plausibility screen; zero positive support flags in evaluated window"},
            ]), hide_index=True, width="stretch")
            st.caption("Model/evidence thresholds and the baseline policy are unchanged by this interface.")
        elif section == "Experimental Results":
            st.header("VI. Experimental Results")
            summary = _phase12(root)
            if summary is None:
                st.error("The verified Phase 12 summary is not available; no substitute values are shown.")
            else:
                coverage = {row["component"]: row for row in summary.get("coverage", [])}
                cards = st.columns(5)
                cards[0].metric("Held-out timestamps", f"{summary['observations']:,}")
                cards[1].metric("E2 support flags", f"{coverage.get('E2', {}).get('supporting_n', 0):,}")
                cards[2].metric("E3 eligible", f"{coverage.get('E3', {}).get('available_n', 0):,}")
                cards[3].metric("E4 support flags", f"{coverage.get('E4', {}).get('supporting_n', 0):,}")
                cards[4].metric("Baseline candidates", f"{summary.get('baseline_E1_dependency', {}).get('candidate_n', 0):,}")
                st.write("The fixed baseline-derived policy produced 123 SUSPICIOUS and 8,292 INSUFFICIENT_EVIDENCE assessments. It produced no NORMAL or ANOMALOUS classifications. These are assessment counts, not verified fault outcomes.")
                figure = root / "research_results" / "phase14_1_final_corrections" / "fig14_assessment_stability_corrected.png"
                if figure.is_file():
                    st.image(str(figure), caption="Phase 12 assessment distribution and category stability under the fixed baseline-derived policy.", width="stretch")
                st.caption("Zero category changes do not show equal evidence contribution; the policy remains baseline-driven.")
        elif section == "Discussion":
            st.header("VII. Discussion")
            st.write("The artifacts support conservative screening and evidence accounting, not diagnosis. E1 duplicates baseline-derived votes. E2 contributes a distinct temporal profile but has no independent event labels. E3 remains ineligible for classification because source lineage, time alignment, comparability, and adjudication are incomplete. E4 produced no positive support flags in the evaluated interval.")
            st.write("The 42 prediction mismatches among 100,980 cells remain unexplained. The cause is unresolved; these mismatches are not silently reconciled.")
        elif section == "Limitations":
            st.header("VIII. Limitations and Threats to Validity")
            st.write("The primary series is a processed snapshot. Provider lineage and instrument history are incomplete. The legacy Meteostat notebook omitted model-fill and flag hyperparameters; direct-observation status and comparison with later stratified exports cannot be established. No independent provider-identified sensor-fault labels exist, so accuracy, precision, recall, F1, false-alarm rate, and fault-detection performance cannot be estimated.")
            st.write("Other limits include the single primary station, one temporal holdout, unresolved E3 independence and time alignment, selected synthetic contexts, non-independent tuning of the 8/12 threshold and screens, and the unresolved prediction mismatch. These constrain generalization and interpretation.")
        elif section == "Conclusion":
            st.header("IX. Conclusion and Future Work")
            st.write("WeatherGuard AI provides a traceable workflow for reviewing unusual weather-station observations while recording unavailable evidence. The available artifacts do not establish validated event-level spatial corroboration, sensor-fault detection, or improved predictive accuracy.")
            st.write("Future work requires traceable independent observations, provider identifiers and instrument histories, prespecified event adjudication, a resolved prediction-parity discrepancy, and forward-time evaluation across multiple stations.")
            st.info("An anomaly is a reason to investigate. It is not a confirmed fault.")
        elif section == "References":
            st.header("References")
            path = root / "research_content" / "literature.json"
            try:
                papers = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                papers = []
            for idx, paper in enumerate(papers, start=1):
                st.markdown(f"[{idx}] {paper['authors']} ({paper['year']}). *{paper['title']}*. {paper['venue']}. [DOI: {paper['doi']}]({paper['url']})")
            if not papers:
                st.info("Bibliographic records are unavailable in this checkout.")

        st.divider()
        figure_roots = [root / "research_results" / "phase13_research_synthesis" / "figures",
                        root / "final_report" / "ieee_figures",
                        root / "research_results" / "phase14_1_final_corrections"]
        figure_paths = sorted({path for folder in figure_roots if folder.is_dir()
                               for path in folder.glob("*.png") if path.is_file()})
        if figure_paths:
            with st.expander("Browse saved research figures"):
                selected_figure = st.selectbox("Figure artifact", figure_paths,
                                               format_func=lambda path: path.relative_to(root).as_posix(),
                                               key="research_figure_gallery")
                st.image(str(selected_figure), caption=selected_figure.stem.replace("_", " "), width="stretch")
        paper_dir = root / "research_results" / "phase14_1_final_corrections"
        for label, filename, mime in [
            ("Download IEEE paper (.docx)", "WeatherGuard_AI_IEEE_Final_Corrected_v3.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            ("Download IEEE paper (.pdf)", "WeatherGuard_AI_IEEE_Final_Corrected_v3.pdf", "application/pdf"),
        ]:
            path = paper_dir / filename
            if path.is_file():
                st.download_button(label, path.read_bytes(), file_name=filename, mime=mime, key=f"research_download_{path.suffix}")
