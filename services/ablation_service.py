"""Reproducible ablation masks for the existing evidence integration policy."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from services.evidence_integration import (
    COMPONENT_IDS, component_record, integrate_evidence,
)

ABLATION_CONFIGURATIONS = {
    "A0": {"name": "Baseline only", "components": ()},
    "A1": {"name": "Baseline + E1", "components": ("E1",)},
    "A2": {"name": "Baseline + E2", "components": ("E2",)},
    "A3": {"name": "Baseline + E3 descriptive context", "components": ("E3",)},
    "A4": {"name": "Baseline + E4", "components": ("E4",)},
    "A5": {"name": "Baseline + E1 + E2 + E4", "components": ("E1", "E2", "E4")},
    "A6": {"name": "Full E1–E4 (E3 descriptive only)", "components": COMPONENT_IDS},
}


def apply_component_subset(full_result: dict[str, Any], included_components: Iterable[str],
                           configuration_name: str) -> dict[str, Any]:
    """Mask evidence objects without changing baseline outputs or implying negatives.

    A disabled component is represented as NOT_APPLICABLE for this ablation,
    distinct from an executed component returning NO_DETECTED_EVIDENCE.
    """
    included = tuple(included_components)
    if len(set(included)) != len(included) or set(included) - set(COMPONENT_IDS):
        raise ValueError("ablation contains duplicate or unknown component IDs")
    timestamp = full_result["timestamp"]
    baseline = deepcopy(full_result["baseline_prediction"])
    full_components = full_result["components"]
    masked = {}
    for component_id in COMPONENT_IDS:
        if component_id in included:
            masked[component_id] = deepcopy(full_components[component_id])
        else:
            masked[component_id] = component_record(
                component_id, "NOT_APPLICABLE", "NOT_APPLICABLE",
                "Excluded by ablation configuration",
                "This component was disabled for this ablation; its evidence was not interpreted as negative.",
                timestamp, {"ablation_configuration": configuration_name},
                ["Component disabled by design; no evidence is inferred."],
                decision_eligible=False,
            )
    result = integrate_evidence(baseline, masked, timestamp)
    result["ablation_configuration"] = configuration_name
    result["included_components"] = list(included)
    return result


def ablate(full_result: dict[str, Any], configuration_id: str) -> dict[str, Any]:
    if configuration_id not in ABLATION_CONFIGURATIONS:
        raise KeyError(f"unknown ablation configuration: {configuration_id}")
    config = ABLATION_CONFIGURATIONS[configuration_id]
    return apply_component_subset(full_result, config["components"], config["name"])


def assessment_change_count(reference_results: list[dict[str, Any]],
                            comparison_results: list[dict[str, Any]]) -> int:
    if len(reference_results) != len(comparison_results):
        raise ValueError("assessment comparisons require the same observation count")
    reference_times = [row["timestamp"] for row in reference_results]
    comparison_times = [row["timestamp"] for row in comparison_results]
    if reference_times != comparison_times:
        raise ValueError("assessment comparisons require identical ordered timestamps")
    return sum(
        left["integrated_assessment"]["category"] != right["integrated_assessment"]["category"]
        for left, right in zip(reference_results, comparison_results)
    )
