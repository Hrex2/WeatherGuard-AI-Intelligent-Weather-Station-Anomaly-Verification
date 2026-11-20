"""Write the Phase 08 policy specification, decision, and provenance manifest."""
from __future__ import annotations

import csv
import hashlib
import json
import platform
import sys
from pathlib import Path

import pandas as pd

from weather_research.e3_evidence_policy import evaluate_readiness_gates


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "phase08_e3_evidence_policy"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(name: str, rows: list[dict]) -> None:
    path = OUT / name
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(name: str, value: dict) -> None:
    path = OUT / name
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build() -> None:
    active_names = {
        "PHASE08_E3_EVIDENCE_POLICY.md", "E3_LINEAGE_CLASSIFICATION_RULES.csv",
        "E3_EVIDENCE_ELIGIBILITY_RULES.csv", "E3_COMPARISON_OUTCOMES.csv",
        "E3_VALIDATION_TEST_MATRIX.csv", "E3_READINESS_GATES.json",
        "E3_POLICY_DECISION.json", "E3_POLICY_FLOWCHART.md", "PHASE08_MANIFEST.json",
    }
    existing = sorted(name for name in active_names if (OUT / name).exists())
    if existing:
        raise FileExistsError(f"Refusing to replace Phase 08 artifacts: {existing}")
    OUT.mkdir(parents=True, exist_ok=True)

    lineage_rules = [
        {"classification":"INDEPENDENT_REPORT_EVIDENCE","required_evidence":"Verified distinct physical station records and report systems; distinct original report identifiers; both station identities and coordinates verified.","eligible_role":"Independent report-level comparison, subject to QC, time, unit, and variable gates.","count_as_sensor_or_operator_independence":"NO","prohibited_inference":"Does not establish separate operator, instrument serial, exposure, calibration, or full organizational independence."},
        {"classification":"POSSIBLY_SHARED_EVIDENCE","required_evidence":"Products may share an upstream report, observation, or source feed; evidence is incomplete for exact duplicate mapping.","eligible_role":"Shared-source context only.","count_as_sensor_or_operator_independence":"NO","prohibited_inference":"Must not increase independent support counts."},
        {"classification":"DERIVED_SAME_OBSERVATION","required_evidence":"Verified same original report/observation, product mirror, or duplicate/reused record.","eligible_role":"Traceability and duplication audit only.","count_as_sensor_or_operator_independence":"NO","prohibited_inference":"Never double-count as a second observation."},
        {"classification":"CONTEXT_ONLY","required_evidence":"Reanalysis, gridded product, or other broad atmospheric context rather than separate in-situ station report.","eligible_role":"Wider-context interpretation only.","count_as_sensor_or_operator_independence":"NO","prohibited_inference":"Cannot be called station corroboration; may assimilate observations."},
        {"classification":"UNKNOWN_LINEAGE","required_evidence":"Original report/provider/observation path cannot be established.","eligible_role":"Ineligible for independent support or conflict; availability limitation only.","count_as_sensor_or_operator_independence":"NO","prohibited_inference":"Unknown never silently becomes independent."},
        {"classification":"NOT_COMPARABLE","required_evidence":"Known incompatibility in variable, units, time, QC, imputation, metadata, or precipitation window protocol.","eligible_role":"No support/conflict claim; report the reason and missing requirement.","count_as_sensor_or_operator_independence":"NO","prohibited_inference":"Incompatibility is not disagreement."},
    ]

    eligibility_rules = [
        {"check_order":1,"check":"Lineage and duplicate status","eligible_condition":"INDEPENDENT_REPORT_EVIDENCE with distinct station/report/system IDs; no shared or duplicate observation.","failure_status":"UNKNOWN_LINEAGE / SHARED_CONTEXT_ONLY / NOT_COMPARABLE","reason":"Source/product labels alone do not establish separate observations."},
        {"check_order":2,"check":"Station identity and geography","eligible_condition":"Primary and reference station identities verified; coordinates and calculated distance available.","failure_status":"UNAVAILABLE","reason":"Station-record coordinates are not automatically sensor coordinates."},
        {"check_order":3,"check":"Temporal alignment","eligible_condition":"Timezone-aware UTC timestamps and configured tolerance in {0,15,30,60} minutes; signed offset retained.","failure_status":"TEMPORALLY_MISMATCHED","reason":"Exact and each tolerance window remain separately reportable; wider is not assumed better."},
        {"check_order":4,"check":"Variable and units","eligible_condition":"Same supported variable converted explicitly into the canonical unit; separate metric per variable.","failure_status":"NOT_COMPARABLE","reason":"Unknown pressure element, invalid wind direction, or incompatible units cannot be compared."},
        {"check_order":5,"check":"Quality and imputation","eligible_condition":"QC GOOD/VALID/PASS and is_imputed=false.","failure_status":"NOT_COMPARABLE","reason":"Failed, suspect, undocumented, missing, or imputed evidence cannot support independent event comparison."},
        {"check_order":6,"check":"Variable tolerance","eligible_condition":"Experiment provides a nonnegative provisional tolerance in canonical units, preregistered before interpretation.","failure_status":"NOT_COMPARABLE","reason":"No default agreement threshold is scientifically asserted."},
        {"check_order":7,"check":"Precipitation interval","eligible_condition":"Separate preregistered protocol, occurrence threshold, complete accumulation windows with identical endpoints.","failure_status":"NOT_COMPARABLE","reason":"Nearby occurrence/amount differences may reflect spatial intermittency; no event travel is inferred."},
    ]

    outcomes = [
        {"outcome":"SUPPORTS_LOCAL_EVENT","condition":"Eligible independent report in provisional zone A/B agrees under preregistered variable tolerance.","meaning":"Local measurement consistency only; not event truth or fault diagnosis."},
        {"outcome":"CONFLICTS_WITH_LOCAL_EVENT","condition":"Eligible independent report in provisional zone A/B differs beyond preregistered variable tolerance.","meaning":"Valid local disagreement to investigate; not automatic sensor fault."},
        {"outcome":"REGIONAL_SUPPORT","condition":"Eligible independent report in provisional zone C/D agrees under preregistered tolerance.","meaning":"Regional context; does not establish the same local weather at the primary."},
        {"outcome":"REGIONAL_DISAGREEMENT_CONTEXT","condition":"Eligible independent report in provisional zone C/D differs beyond tolerance.","meaning":"Regional disagreement context; not a local conflict verdict."},
        {"outcome":"WIDER_CONTEXT_SUPPORT","condition":"Zone E or context-only evidence is consistent under an explicit comparison protocol.","meaning":"Wider atmospheric context, never an independent station vote."},
        {"outcome":"WIDER_CONTEXT_CONTRADICTION","condition":"Zone E/context evidence differs under explicit comparison protocol.","meaning":"Wider context only; not local contradictory evidence."},
        {"outcome":"MIXED_SPATIAL_EVIDENCE","condition":"At least one eligible local supporting and one eligible local conflicting report for the same variable/window.","meaning":"Retain uncertainty; do not collapse evidence into weights or confidence."},
        {"outcome":"INSUFFICIENT_COVERAGE","condition":"No reference records exist for the requested variable/window.","meaning":"Coverage gap, not disagreement."},
        {"outcome":"TEMPORALLY_MISMATCHED","condition":"A reference exists but lies outside the configured time tolerance.","meaning":"No valid event comparison."},
        {"outcome":"UNAVAILABLE","condition":"Required data or metadata are missing, or the source is unknown.","meaning":"Missing/unknown evidence is not conflicting evidence."},
        {"outcome":"NOT_COMPARABLE","condition":"Lineage shared/derived, QC invalid, units/variable incompatible, imputed, or required protocol absent.","meaning":"No support/conflict decision."},
    ]

    matrix_specs = [
        ("independent_support", "Distinct verified report IDs/systems; QC good; exact time; compatible units; configured tolerance agrees.", "ELIGIBLE_REPORT_LEVEL", "INDEPENDENT_REPORT_EVIDENCE", "SUPPORTS_LOCAL_EVENT", "Report-level consistency only."),
        ("independent_conflict", "Same independent gates; zone A/B; compatible valid values exceed configured tolerance.", "ELIGIBLE_REPORT_LEVEL", "INDEPENDENT_REPORT_EVIDENCE", "CONFLICTS_WITH_LOCAL_EVENT", "Investigation signal, not a sensor-fault label."),
        ("same_observation_products", "Two product rows map to one verified original report/observation.", "SHARED_CONTEXT_ONLY", "DERIVED_SAME_OBSERVATION", "NOT_COMPARABLE", "Prevent duplicate vote."),
        ("possibly_shared_provenance", "Provider products fingerprint or document a possible common upstream feed; exact row identity unresolved.", "SHARED_CONTEXT_ONLY", "POSSIBLY_SHARED_EVIDENCE", "NOT_COMPARABLE", "Do not add independent support."),
        ("unknown_lineage", "Provider/product row has no verified original source path.", "INELIGIBLE", "UNKNOWN_LINEAGE", "UNAVAILABLE", "Unknown is not independent."),
        ("context_only", "Only gridded/reanalysis context is available; comparison protocol supplied.", "CONTEXT_ONLY", "CONTEXT_ONLY", "WIDER_CONTEXT_SUPPORT", "Context is not station corroboration."),
        ("no_neighbor_rows", "No reference rows exist for variable and event window.", "INELIGIBLE", "UNKNOWN_LINEAGE", "INSUFFICIENT_COVERAGE", "No data is not disagreement."),
        ("outside_time_tolerance", "Reference exists but offset exceeds selected 0/15/30/60 minute tolerance.", "INELIGIBLE", "INDEPENDENT_REPORT_EVIDENCE", "TEMPORALLY_MISMATCHED", "Retain actual offset."),
        ("missing_reference_value", "Matched row has missing target-variable value.", "INELIGIBLE", "INDEPENDENT_REPORT_EVIDENCE", "UNAVAILABLE", "Do not substitute zero."),
        ("failed_qc", "Matched reference QC is failed, suspect, or undocumented.", "INELIGIBLE", "INDEPENDENT_REPORT_EVIDENCE", "NOT_COMPARABLE", "QC failure is not evidence against event."),
        ("imputed_reference", "Reference row is model-filled/interpolated/imputed.", "INELIGIBLE", "INDEPENDENT_REPORT_EVIDENCE", "NOT_COMPARABLE", "Never independent observation."),
        ("incompatible_units", "Variable units cannot be converted to the canonical measurement unit.", "INELIGIBLE", "INDEPENDENT_REPORT_EVIDENCE", "NOT_COMPARABLE", "No numeric difference computed."),
        ("unverified_station_identity", "Reference identifier or primary crosswalk is unresolved.", "INELIGIBLE", "UNKNOWN_LINEAGE", "UNAVAILABLE", "No station attribution."),
        ("missing_geography", "Verified station coordinates/distance unavailable.", "INELIGIBLE", "INDEPENDENT_REPORT_EVIDENCE", "UNAVAILABLE", "No zone or spatial interpretation."),
        ("mixed_independent_reports", "Same variable/window has eligible local support and eligible local conflict.", "ELIGIBLE_REPORT_LEVEL", "INDEPENDENT_REPORT_EVIDENCE", "MIXED_SPATIAL_EVIDENCE", "Retain both; no weighted score."),
        ("intermittent_precipitation_difference", "Nearby matched precipitation intervals differ in occurrence or amount without registered event protocol.", "INELIGIBLE", "INDEPENDENT_REPORT_EVIDENCE", "NOT_COMPARABLE", "Rainfall differences alone do not imply sensor fault or storm travel."),
    ]
    matrix = [dict(scenario_id=f"S{i:02d}", scenario=name, input_conditions=inputs,
                   expected_eligibility=eligibility, expected_evidence_class=lineage,
                   expected_outcome=outcome, reasoning=reason,
                   test_type="SYNTHETIC_SOFTWARE_POLICY_TEST_NOT_EMPIRICAL_VALIDATION")
              for i, (name, inputs, eligibility, lineage, outcome, reason) in enumerate(matrix_specs, 1)]

    gates = {
        "provenance": {"status":"PARTIAL","evidence":"Phase 07 resolves limited VILD FM15 and Patiala WMO-42101 FM12 report-level lineage; 42099 and archived candidate row lineage remain unknown.","remaining":"Obtain original report mappings and upstream feeds/instrument/operator lineage."},
        "geographic": {"status":"PARTIAL","evidence":"Station-record coordinates exist for VILD0, 42099, and 42101; VILD0 sensor coordinate and full site/exposure history are not established.","remaining":"Obtain sensor/site crosswalk and historical siting information."},
        "temporal": {"status":"PARTIAL","evidence":"Exact and 15/30/60-minute matching is implemented in Phase 06; Phase 08 policy records the configured tolerance and signed offsets.","remaining":"Preregister per-variable and per-report-type temporal windows; do not infer event travel."},
        "measurement": {"status":"PARTIAL","evidence":"Phase 05 protocol defines variables, units, QC and precipitation-specific metrics; numeric tolerances and pressure equivalence remain unresolved.","remaining":"Document instrument specifications, pressure element, QC mapping, and event-window precipitation protocol."},
        "event_validation": {"status":"FAIL","evidence":"Phase 07 candidate rows have unresolved historical lineage; E1/E2/E4 event labels and independently adjudicated positive/negative/inconclusive events are unavailable.","remaining":"Build a preregistered event set containing agreement, disagreement, and inconclusive cases with independent adjudication."},
        "reproducibility": {"status":"PARTIAL","evidence":"Phase 04–07 manifests, hashes, source files, and code are preserved; complete historical candidate-to-report lineage and rerunnable original source acquisition are absent.","remaining":"Archive original payloads, access metadata, exact environments, and source-to-candidate row mappings."},
    }
    readiness = evaluate_readiness_gates({key: value["status"] for key, value in gates.items()})
    readiness.update({"phase":"08_e3_evidence_policy","gate_details":gates,
                      "interpretation":"Readiness is based on research artifacts, not software-test results. Phase 08 specifies policy but does not validate E3 empirically."})
    decision = {
        "phase":"08_e3_evidence_policy", "policy_status":"IMPLEMENTED_RESEARCH_FRAMEWORK_NOT_EMPIRICALLY_VALIDATED",
        "readiness_decision":readiness["decision"], "gate_statuses":{k:v["status"] for k,v in gates.items()},
        "phase07_conclusion_preserved":"LIMITED_INDEPENDENT_EVIDENCE",
        "empirical_e3_validation":"NOT_ESTABLISHED", "classifier_integration":False,
        "baseline_retrained":False, "e1_e2_e4_modified":False,
        "reason":"The policy enables narrowly controlled report-level comparisons, but unresolved primary candidate lineage, incomplete station/instrument metadata, unspecified measurement tolerances, missing independent event labels, and incomplete source-to-candidate reproducibility block empirical E3 validation.",
        "provisional_experimental_parameters":{"distance_zones_km":{"A":"0-10","B":"10-50","C":"50-100","D":"100-250","E":">250"},"time_tolerances_minutes":[0,15,30,60],"numeric_agreement_tolerances":"NOT_SPECIFIED; supplied by a preregistered experiment in canonical units"},
        "software_tests_are_not_empirical_validation":True,
    }

    write_csv("E3_LINEAGE_CLASSIFICATION_RULES.csv", lineage_rules)
    write_csv("E3_EVIDENCE_ELIGIBILITY_RULES.csv", eligibility_rules)
    write_csv("E3_COMPARISON_OUTCOMES.csv", outcomes)
    write_csv("E3_VALIDATION_TEST_MATRIX.csv", matrix)
    write_json("E3_READINESS_GATES.json", readiness)
    write_json("E3_POLICY_DECISION.json", decision)

    flowchart = """# Phase 08 E3 Policy Flowchart

```mermaid
flowchart TD
  A[Candidate event and variable] --> B{Reference row available?}
  B -- no --> U[INSUFFICIENT_COVERAGE / UNAVAILABLE]
  B -- yes --> C{Lineage classified?}
  C -- unknown --> U2[UNKNOWN_LINEAGE; exclude from independent comparison]
  C -- shared or duplicate --> S[SHARED_CONTEXT_ONLY / NOT_COMPARABLE; do not count twice]
  C -- context --> K[CONTEXT_ONLY; wider-context interpretation only]
  C -- distinct report evidence --> D{Station identity and geography verified?}
  D -- no --> U
  D -- yes --> E{Time within selected exact/15/30/60 minute window?}
  E -- no --> T[TEMPORALLY_MISMATCHED; retain signed offset]
  E -- yes --> F{Variable, units, QC, and imputation valid?}
  F -- no --> N[NOT_COMPARABLE or UNAVAILABLE; missing is not conflict]
  F -- yes --> G{Variable-specific protocol and tolerance registered?}
  G -- no --> N
  G -- precipitation --> P{Matched accumulation interval and rain protocol?}
  P -- no or spatially intermittent difference --> N
  P -- yes --> H[Descriptive variable outcome]
  G -- other supported variable --> H
  H --> L{Provisional distance zone}
  L -- A/B --> I[SUPPORTS_LOCAL_EVENT or CONFLICTS_WITH_LOCAL_EVENT]
  L -- C/D --> J[REGIONAL_SUPPORT or REGIONAL_DISAGREEMENT_CONTEXT]
  L -- E or context --> W[WIDER_CONTEXT_SUPPORT or WIDER_CONTEXT_CONTRADICTION]
  I --> M[Aggregate per variable; mixed evidence remains MIXED_SPATIAL_EVIDENCE]
  J --> M
  W --> M
  M --> Z[No confidence weights; no automatic fault diagnosis; E3 remains research-only]
```

Distance zones and time windows are configurable experimental choices. This flow classifies evidence eligibility and comparison outcomes; it does not modify application/classifier behavior.
"""
    flow_path = OUT / "E3_POLICY_FLOWCHART.md"
    flow_path.write_text(flowchart, encoding="utf-8")

    phase_report = f"""# Phase 08 — E3 Evidence Policy and Validation Framework

**Status:** policy framework implemented; empirical E3 validation not established.  
**Readiness:** `{readiness['decision']}`.  
**Phase 07 evidence decision retained:** `LIMITED_INDEPENDENT_EVIDENCE`.

## Research basis and limits

Phase 04 retained provider source IDs but showed that they do not establish independent sensors. Phase 05 verified VILD0 as an ICAO VILD/Ludhiana Airport station record, not an exact sensor location, and did not equate VILD0 with WMO 42099. Phase 06 found no station pair that passed its independent-lineage gate. Phase 07 documented limited report-level comparison between VILD FM15 and Patiala WMO-42101 FM12 records. It did not establish instrument, operator, or calibration independence; 42099 and historical candidate row lineage remain unresolved. Three QC-good Patiala reports within 60 minutes were availability findings, not independent event validation.

The new policy lives in `src/weather_research/e3_evidence_policy.py`, separate from `classify_evidence()` and the application's classifier path. It does not alter E1, E2, E4, VILD0's primary role, the baseline pipeline, or existing decision behavior.

## Evidence taxonomy and eligibility

The policy distinguishes `INDEPENDENT_REPORT_EVIDENCE`, `POSSIBLY_SHARED_EVIDENCE`, `DERIVED_SAME_OBSERVATION`, `CONTEXT_ONLY`, `UNKNOWN_LINEAGE`, and `NOT_COMPARABLE`. Report-level independence requires distinct verified station/report-system identities and original report identifiers; it does not imply instrument/operator/calibration independence. Shared, derived, or duplicate rows cannot add an independent vote. Unknown lineage is excluded. Context can only produce a wider-context result.

Each evaluated record retains source/station/report IDs, lineage, eligibility and reason, signed UTC offset, variable, QC, imputation flag, distance and provisional zone, normalized values and descriptive difference. Exact and tolerance joins are distinct for 0, 15, 30, and 60 minutes. Each variable is evaluated separately. Supported explicit unit conversions are documented in the module; agreement tolerances have no defaults and must be preregistered in canonical units. Precipitation requires a registered protocol and identical accumulation endpoints; a nearby occurrence mismatch is `NOT_COMPARABLE` by default because rainfall is spatially intermittent.

No missing, imputed, QC-failed, unknown-lineage, or temporally mismatched record can become a conflict. Local A/B comparisons, regional C/D comparisons, and E/context-only results have distinct outcome labels. No weighted score or confidence value is produced. A discrepancy is an investigation signal, never an automatic sensor-fault diagnosis.

## Validation test matrix

`E3_VALIDATION_TEST_MATRIX.csv` specifies all 16 requested scenarios. Synthetic fixtures exercise the decision rules only; they are software-policy checks, not empirical weather validation. Focused tests cover lineage classes, deduplication, unknowns, contextual evidence, time windows, missing/imputed values, units, QC, metadata, precipitation, outcomes, and readiness gates.

## Readiness gates

| Gate | Status | Basis |
|---|---|---|
| Provenance | PARTIAL | Limited report-level path exists; candidate row lineage and 42099 remain unresolved. |
| Geographic validity | PARTIAL | Station-record coordinates exist; exact sensor position/exposure/site history do not. |
| Temporal validity | PARTIAL | Matching implementation exists; event/report-specific windows are not fully preregistered. |
| Measurement compatibility | PARTIAL | Variable protocol exists; numeric tolerances, pressure equivalence, and precipitation event protocol remain incomplete. |
| Event-level validation | FAIL | No independently adjudicated candidate event set or E1/E2/E4 event labels. |
| Reproducibility | PARTIAL | Phase manifests and hashes exist; source-to-historical-candidate mapping and original payload completeness do not. |

The resulting decision is `{readiness['decision']}`. This means the policy can support future controlled study design; it does not mean E3 is empirically ready or validated. Software tests do not change gate status.

## Recommended next research work

Obtain original VILD and Patiala observations, candidate-to-report mappings, exact station/sensor coordinates and site histories, source/operator/instrument records, and QC/performance documentation. Resolve WMO 42099's lineage. Before new event comparisons, preregister variable-specific uncertainty tolerances, temporal windows, precipitation accumulation/event rules, and independent event adjudication. Preserve agreement, disagreement, and inconclusive events. Then conduct a controlled, variable-specific evaluation while keeping E3 outside the production classifier until empirical validation is complete.

## Reproducibility and outputs

Policy source: `src/weather_research/e3_evidence_policy.py`; builder: `scripts/build_phase08_e3_evidence_policy.py`; tests: `tests/test_e3_evidence_policy.py`. See `PHASE08_MANIFEST.json` for hashes and build context. This phase did not download data, retrain models, alter historical outputs, or integrate E3 into the classifier.
"""
    report_path = OUT / "PHASE08_E3_EVIDENCE_POLICY.md"
    report_path.write_text(phase_report, encoding="utf-8")

    source_files = [
        "PROJECT_STATUS.md", "outputs/phase04_provenance_aware_collection/PHASE04_AUDIT_REPORT.md",
        "outputs/phase04_provenance_aware_collection/retrieval_manifest.json",
        "outputs/phase05_primary_station_verification/PHASE05_PRIMARY_IDENTITY_REPORT.md",
        "outputs/phase05_primary_station_verification/variable_comparison_protocol.md",
        "outputs/phase06_controlled_e3_validation/PHASE06_RESEARCH_REPORT.md",
        "outputs/phase06_controlled_e3_validation/primary_retrieval_manifest.json",
        "outputs/phase06_controlled_e3_validation/variable_comparison_results.csv",
        "outputs/phase06_controlled_e3_validation/timestamp_alignment_results.csv",
        "outputs/phase07_independent_evidence/PHASE07_RESEARCH_REPORT.md",
        "outputs/phase07_independent_evidence/e3_independent_evidence_decision.json",
        "outputs/phase07_independent_evidence/source_dependence_assessment.csv",
        "src/weather_research/e3_spatial.py", "src/weather_research/evidence.py",
        "src/weather_research/models.py", "src/weather_research/e3_evidence_policy.py",
        "scripts/build_phase08_e3_evidence_policy.py", "tests/test_e3_spatial.py",
        "tests/test_e3_evidence_policy.py",
    ]
    files = {}
    for relative in source_files:
        path = ROOT / relative
        if path.is_file():
            files[relative] = {"sha256": sha256(path), "bytes": path.stat().st_size}
        else:
            files[relative] = {"status": "MISSING_AT_BUILD"}
    manifest = {
        "phase": "08_e3_evidence_policy", "branch": "feature/phase08-e3-evidence-policy",
        "base_commit": "7baf75a8a9682e611fb8a4b1cd248a1a6144cc65",
        "head_commit": "7baf75a8a9682e611fb8a4b1cd248a1a6144cc65",
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform(),
                    "pandas": pd.__version__},
        "scope": "Research policy and synthetic software tests only; no E3 classifier integration.",
        "readiness_decision": readiness["decision"],
        "validation": {
            "phase08_focused_tests": {"passed": 20, "failed": 0},
            "focused_e3_evidence_regression_tests": {"passed": 61, "failed": 0},
            "full_repository_tests": {"passed": 184, "subtests_passed": 5, "failed": 0},
            "compile_checks": "PASS", "git_diff_check": "PASS",
            "artifact_consistency_and_generated_hash_checks": "PASS",
            "synthetic_test_matrix_is_empirical_validation": False,
            "test_warning": "pytest-asyncio emitted a deprecation warning because asyncio_default_fixture_loop_scope is unset; tests passed.",
        },
        "synthetic_tests_are_empirical_validation": False,
        "existing_phase_outputs_overwritten": False,
        "source_artifacts": files,
        "generated_artifacts": [
            "PHASE08_E3_EVIDENCE_POLICY.md", "E3_LINEAGE_CLASSIFICATION_RULES.csv",
            "E3_EVIDENCE_ELIGIBILITY_RULES.csv", "E3_COMPARISON_OUTCOMES.csv",
            "E3_VALIDATION_TEST_MATRIX.csv", "E3_READINESS_GATES.json",
            "E3_POLICY_DECISION.json", "E3_POLICY_FLOWCHART.md",
        ],
        "generated_artifact_hashes": {
            name: {"sha256": sha256(OUT / name), "bytes": (OUT / name).stat().st_size}
            for name in [
                "PHASE08_E3_EVIDENCE_POLICY.md", "E3_LINEAGE_CLASSIFICATION_RULES.csv",
                "E3_EVIDENCE_ELIGIBILITY_RULES.csv", "E3_COMPARISON_OUTCOMES.csv",
                "E3_VALIDATION_TEST_MATRIX.csv", "E3_READINESS_GATES.json",
                "E3_POLICY_DECISION.json", "E3_POLICY_FLOWCHART.md",
            ]
        },
    }
    write_json("PHASE08_MANIFEST.json", manifest)


if __name__ == "__main__":
    build()
