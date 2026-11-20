"""Section navigation and evidence-grounded education for the saved model protocol."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from services.model_metadata import build_model_education

SECTIONS = [
    "Introduction", "Data Acquisition", "Preprocessing", "Model Selection",
    "Model Training", "Model Evaluation", "Results", "Conclusion",
]


def render_model_workspace(data: dict, root, hashes: dict, render_saved_results) -> None:
    education = build_model_education(data)
    st.markdown("<div class='wg-eyebrow'>MODEL · SAVED RESEARCH PROTOCOL</div>", unsafe_allow_html=True)
    st.title("Model")
    st.caption("Explore the archived unsupervised screening protocol. Opening this page does not train or refit a model.")
    nav, content = st.columns([0.78, 2.5], gap="large")
    with nav:
        st.markdown("#### Sections")
        section = st.radio("Model sections", SECTIONS, key="model_section_navigation", label_visibility="collapsed")
    with content:
        if section == "Introduction":
            st.header("What the model screen does")
            st.write("WeatherGuard compares historical observations with patterns learned by three unsupervised model families. Configuration agreement is a stability signal; it is not calibrated confidence, a probability of failure, or a diagnosis.")
            cards = st.columns(3)
            for card, family in zip(cards, education["profiles"].values()):
                with card.container(border=True):
                    st.markdown(f"**{family['name']}**")
                    st.write(family["simple"])
            st.info("A model flag identifies an unusual observation for review. ANOMALY ≠ FAULT.")
        elif section == "Data Acquisition":
            st.header("Data used by the saved protocol")
            observations = data["observations"]
            facts = st.columns(4)
            facts[0].metric("Processed rows", f"{len(observations):,}")
            facts[1].metric("Training rows", f"{education['train_rows']:,}")
            facts[2].metric("Held-out rows", f"{education['test_rows']:,}")
            facts[3].metric("Saved configurations", f"{data['predictions'].configuration.nunique()}")
            st.write(f"The processed primary series spans {observations.index.min():%Y-%m-%d} through {observations.index.max():%Y-%m-%d}. It is a verified local snapshot; the checks establish file integrity and split dimensions, not complete provider or instrument lineage.")
            st.caption("The separate 6,024-row legacy Meteostat output has unresolved retrieval settings and cannot be treated as verified direct observations.")
        elif section == "Preprocessing":
            st.header("Features and preprocessing")
            st.write("The saved protocol uses six weather measurements, three recent-temperature features, and two seasonal month encodings.")
            feature_rows = []
            for group, features in education["feature_groups"].items():
                feature_rows.extend({"Feature group": group, "Feature": name,
                                     "Meaning": education["feature_labels"][name][0],
                                     "Unit": education["feature_labels"][name][1]} for name in features)
            st.dataframe(pd.DataFrame(feature_rows), hide_index=True, width="stretch")
            st.write("The split is chronological. LOF and One-Class SVM scalers are fitted on training rows only; Isolation Forest inputs remain unscaled. These transformations belong to the archived protocol.")
        elif section == "Model Selection":
            st.header("Three model families")
            family_key = st.selectbox("Algorithm", list(education["profiles"]),
                                      format_func=lambda key: education["profiles"][key]["name"],
                                      key="model_workspace_family")
            profile = education["profiles"][family_key]
            st.info(profile["simple"])
            st.write(profile["why"])
            st.caption(profile["difference"])
            configs = pd.DataFrame(profile["configs"])
            visible = [name for name in ("name", "parameter", "value", "anomalies", "anomaly_percentage") if name in configs]
            st.dataframe(configs[visible].rename(columns={
                "name": "Configuration", "parameter": "Varied setting", "value": "Value",
                "anomalies": "Saved flags", "anomaly_percentage": "Flagged (%)",
            }), hide_index=True, width="stretch")
            with st.expander("Technical description and known behavior"):
                st.write(profile["technical"])
                st.write("**Useful for:** " + profile["detects_well"])
                st.write("**Can miss or misread:** " + profile["may_miss"])
        elif section == "Model Training":
            st.header("Training and temporal split")
            split = pd.DataFrame([
                {"Partition": "Training", "Start": education["training_start"], "End": education["training_end"], "Rows": education["train_rows"]},
                {"Partition": "Held-out test", "Start": education["testing_start"], "End": education["testing_end"], "Rows": education["test_rows"]},
            ])
            st.dataframe(split, hide_index=True, width="stretch")
            st.warning("Fitted estimator objects are not stored with the archived results. This page does not retrain models. A future upload refit is a separate, explicit workflow and produces isolated outputs.")
        elif section == "Model Evaluation":
            st.header("What can be evaluated from these artifacts")
            results = data["configuration_results"].copy()
            col1, col2, col3 = st.columns(3)
            col1.metric("Prediction cells", f"{len(data['predictions']):,}")
            col2.metric("Held-out timestamps", f"{education['test_rows']:,}")
            col3.metric("8/12 candidates", f"{int(data['stability'].configuration_votes.ge(8).sum()):,}")
            if {"family", "anomalies"}.issubset(results.columns):
                chart = px.bar(results, x="family", y="anomalies", color="family",
                               labels={"family": "Model family", "anomalies": "Saved flags"},
                               title="Saved configuration flag counts", color_discrete_sequence=px.colors.sequential.Teal)
                st.plotly_chart(chart, width="stretch")
            st.warning("Independent fault labels are unavailable. Accuracy, precision, recall, F1, false-alarm rate, and fault-detection performance cannot be calculated.")
            st.caption("The known saved/local prediction mismatch is 42 of 100,980 cells; its cause remains unresolved.")
        elif section == "Results":
            render_saved_results(data, root, hashes)
        else:
            st.header("Conclusion")
            st.write("The saved models support conservative screening of unusual historical observations. E1 configuration agreement duplicates the baseline signal in the audited Phase 12 run. The outputs do not establish calibrated confidence, verified anomaly truth, or sensor-fault detection.")
            st.info("Configuration agreement is not calibrated confidence. ANOMALY ≠ FAULT.")
