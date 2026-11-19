"""Dashboard renderer for the conservative integrated evidence result."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services.evidence_integration import COMPONENT_IDS, load_spatial_tables, run_integrated_assessment

STATUS_COLOR = {
    "AVAILABLE": "#38BDF8", "DESCRIPTIVE_ONLY": "#FBBF24",
    "INSUFFICIENT_DATA": "#94A3B8", "UNAVAILABLE": "#94A3B8",
    "ERROR": "#F87171", "NOT_APPLICABLE": "#94A3B8",
}
ASSESSMENT_COLOR = {
    "NORMAL": "#34D399", "SUSPICIOUS": "#FBBF24",
    "ANOMALOUS": "#F87171", "INSUFFICIENT_EVIDENCE": "#94A3B8",
}


def build_dashboard_assessment(data: dict, root: str, timestamp,
                               station_id: str, variable: str = "temp") -> dict:
    spatial, sources = load_spatial_tables(root)
    return run_integrated_assessment(
        timestamp=timestamp, station_id=station_id,
        observations=data["observations"], predictions=data["predictions"],
        stability=data["stability"], episodes=data["episodes"],
        spatial_tables=spatial, spatial_sources=sources,
        primary_variable=variable,
    )


def render_integrated_evidence_panel(result: dict) -> None:
    baseline = result["baseline_prediction"]
    assessment = result["integrated_assessment"]
    category = assessment["category"]
    color = ASSESSMENT_COLOR.get(category, "#94A3B8")
    st.markdown(
        f"<div style='border:1px solid {color};border-radius:10px;padding:10px 12px;margin:.3rem 0 .7rem;'>"
        f"<div style='font-size:.7rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.1em;'>Integrated assessment · conservative triage</div>"
        f"<div style='font-size:1.15rem;font-weight:750;color:{color};'>{category.replace('_', ' ')}</div>"
        f"<div style='font-size:.78rem;color:#cbd5e1;'>{assessment['reason']}</div></div>",
        unsafe_allow_html=True,
    )
    if baseline["execution_status"] == "AVAILABLE":
        votes = baseline.get("configuration_votes")
        count = baseline.get("configuration_count")
        st.metric("Saved baseline prediction", f"{votes}/{count} candidates" if votes is not None else "Unavailable")
        st.caption("Unchanged saved Phase 03 model outputs · no model was refit for this assessment.")
    else:
        st.metric("Saved baseline prediction", baseline["execution_status"].replace("_", " ").title())

    st.markdown("**E1–E4 evidence breakdown**")
    for component_id in COMPONENT_IDS:
        component = result["components"][component_id]
        state = component["execution_status"]
        status_color = STATUS_COLOR.get(state, "#94a3b8")
        eligible = "decision-eligible" if component["decision_eligible"] else "display only"
        st.markdown(
            f"<div style='border-left:3px solid {status_color};padding:5px 8px;margin:5px 0;background:#111c2e;'>"
            f"<b>{component_id} · {component['component_name']}</b> · "
            f"<span style='color:{status_color};'>{state.replace('_', ' ')}</span> · {eligible}<br>"
            f"<span style='color:#dbe4ef;font-size:.82rem;'>{component['evidence_label']}</span><br>"
            f"<span style='color:#94a3b8;font-size:.75rem;'>{component['explanation']}</span></div>",
            unsafe_allow_html=True,
        )
        if component["limitations"]:
            st.caption("Limitations: " + " ".join(component["limitations"]))
        if component.get("details"):
            with st.expander(f"{component_id} details", expanded=False):
                details = component["details"]
                if isinstance(details, dict) and component_id == "E2":
                    st.json({k: v for k, v in details.items() if k not in {"timestamp"}})
                elif isinstance(details, list) and details:
                    st.dataframe(pd.DataFrame(details), hide_index=True, width="stretch")
                elif isinstance(details, dict):
                    st.json(details)
                else:
                    st.info("No component-level detail rows are available.")
    st.caption(result["research_boundary"])
    with st.expander("Integration summary: support, conflict, and unavailable evidence"):
        st.markdown("**Supporting screens:** " + (", ".join(assessment["supporting_evidence"]) or "None detected"))
        st.markdown("**Contradictory screens:** " + (", ".join(assessment["contradictory_evidence"]) or "None detected"))
        st.markdown("**Restricted descriptive evidence:** " + (", ".join(assessment["restricted_descriptive_evidence"]) or "None"))
        st.markdown("**Unavailable / insufficient / failed:** " + (", ".join(assessment["unavailable_evidence"]) or "None"))
        st.caption("Only the unchanged baseline's existing 8/12 screen can trigger SUSPICIOUS triage. No combined classifier is validated; E3 never changes the assessment.")
