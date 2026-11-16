"""Reusable, leakage-aware utilities for the weather station research project."""

from .features import add_segments, engineer_features, add_month_cycle
from .preprocessing import chronological_split, prepare_train_test
from .models import default_model_configs, fit_predict_configurations, stability_summary
from .temporal import build_episodes
from .quality import physical_quality_flags
from .spatial import spatial_evidence
from .evidence import classify_evidence
from .audit import phase01_integrity_audit
from .synthetic_campaign import run_temperature_spike_campaign, load_verified_snapshots

__all__ = [
    "add_segments", "engineer_features", "add_month_cycle", "chronological_split",
    "prepare_train_test", "default_model_configs",
    "fit_predict_configurations", "stability_summary", "build_episodes",
    "physical_quality_flags", "spatial_evidence", "classify_evidence",
    "phase01_integrity_audit",
    "run_temperature_spike_campaign", "load_verified_snapshots",
]
