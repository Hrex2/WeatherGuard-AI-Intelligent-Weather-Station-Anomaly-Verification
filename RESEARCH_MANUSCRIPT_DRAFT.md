# Uncertainty-Aware Event-Level Verification of Weather Station Anomalies Using Model Stability, Temporal Consistency and Spatial Evidence

**Status:** Preliminary research draft, not submission-ready. Software outputs are traceable; E3 is unavailable, E2 thresholds are exploratory, and no real-observation fault labels are bundled.

## Abstract (draft)

This work investigates an uncertainty-aware workflow for examining unusual weather-station observations. The implemented baseline uses a processed VILD0 observation snapshot, causal weather features, a chronological train/test split and saved binary predictions from twelve configurations spanning Isolation Forest, Local Outlier Factor and One-Class SVM. Model agreement is treated as descriptive stability rather than a probability. An independent temporal screen compares a selected reading with prior local history and, in a separately labelled retrospective mode, examines whether unusual values persist or return toward baseline. Spatial corroboration remains unavailable because the project does not include validated neighboring-station time series and complete provenance. Physical checks are broad screening rules only. The system abstains from asserting a weather event or sensor fault when evidence is insufficient. Saved-label threshold counts and a local-refit parity audit are reported as software/model-output analyses, not labeled performance. Further validation with traceable multi-station observations and adjudicated fault/event labels is required.

## 1. Introduction (draft)

Weather observations that depart from expected patterns may represent unusual atmospheric conditions, station-specific measurement problems, or insufficient evidence. Anomaly detection alone does not distinguish these explanations. The research question is whether model stability, independent temporal behavior, spatial observations and physical screening can organize evidence while preserving uncertainty.

The prototype contribution is an evidence-oriented review workflow that separates model outputs from event interpretation and explicitly represents unavailable information. The present repository supports a verified processed baseline and saved prediction grid but does not provide real station fault labels or validated neighbor time series. Claims are therefore limited to implementation behavior and descriptive output comparisons.

## 2. Background and related work (draft)

Existing literature notes and references are catalogued in `research_content/literature.json` and `references.bib`. Each publication record and citation must be checked against the original publisher or repository before a thesis submission. This draft does not add unverified references or quote publication findings that have not been reviewed.

## 3. Research questions and evidence framework (draft)

- **E1:** How consistently do configurations and model families flag the same timestamps?
- **E2:** Does a measured value depart from prior local time-series behavior, and does that departure persist in retrospective review?
- **E3:** Do verified neighboring stations show similar observations? This question is currently unanswerable from the bundled raw evidence.
- **E4:** Are readings missing, outside broad screening bounds, or inconsistent with simple physical relationships? These checks are screening flags, not instrument diagnoses.

Evidence states are kept distinct: supporting, conflicting, unavailable, and no detected evidence. Missing evidence is not interpreted as a negative result. Model agreement is not calibrated probability.

## 4. Data and preprocessing (verified artifact scope)

The application validates Phase 01 manifest hashes, row counts and feature order. The processed observation table has 44,879 rows; saved training and test matrices contain 36,434 and 8,415 rows. The processed table spans 2021-01-05 19:30 +05:30 to 2026-03-09 23:30 +05:30. It is not the raw acquisition. Twelve saved configurations produce 100,980 labels across 8,415 held-out timestamps. The research archive does not contain raw provider observations, and source reconstruction is not established by these checks.

The current model protocol uses eleven inputs: six measured variables, causal temperature change and prior rolling features, and month sine/cosine. Existing split and feature snapshots are preserved. No replacement data source was introduced.

## 5. Model configurations (verified implementation)

Four Isolation Forest contamination settings (0.01, 0.02, 0.03, 0.05), four LOF neighbor counts (10, 20, 30, 50), and four One-Class SVM nu settings (0.01, 0.02, 0.03, 0.05) are present. Isolation Forest uses 200 estimators and random state 42. LOF and One-Class SVM use training-only standardized features; Isolation Forest uses unscaled features. No fitted historical estimators are stored, and application refits require an explicit action.

## 6. Preliminary results (saved labels only)

On the 8,415 saved test timestamps, the number meeting each agreement threshold is 432 at 4/12, 214 at 6/12, 123 at 8/12, 51 at 10/12, and 15 at 12/12. At least one configuration flags 521 timestamps for Isolation Forest, 635 for LOF and 575 for One-Class SVM. Within-family counts and pairwise Jaccard/disagreement tables are in `research_results/`. Thresholds are sensitivity views, not calibrated cutoffs. These quantities do not establish accuracy, event truth, or sensor-fault probability.

A current-environment reproduction differs from saved predictions at 42 of 100,980 cells, at 42 timestamps. All differences occur in Isolation Forest (6 for IF_0.01, 4 for IF_0.02, 12 for IF_0.03, and 20 for IF_0.05); LOF and One-Class SVM match. Row-level features and execution metadata are in `research_results/prediction_mismatch_investigation.csv`. The archived fitted estimator/scaler and complete historical execution environment are absent, so the discrepancy is reproduced but not causally explained. Historical labels were not overwritten.

An additional synthetic matrix tested eight patterns once at a held-out interval. Across twelve configurations, injected-label flag rates ranged from 0/36 for a three-observation missing block to 11/12 for both a +10 °C point spike and a −10 °C point drop. A six-observation stuck pattern received 5/72 configuration/time flags; a +20 °C dew-point perturbation received 24/36. These are results for one synthetic interval, not real-world performance. The complete table, family comparison and exact injections are in `SYNTHETIC_FAULT_MATRIX_REPORT.md` and `research_results/fault_matrix_02bd147f5cce/`.

## 7. Independent temporal screen (implementation result, exploratory)

The temporal service uses observations only, estimates the local median cadence, and refuses to bridge gaps larger than 1.5 times that cadence. Real-time mode compares a selected reading with prior context only. Retrospective mode is explicitly separate and can assess persistence or return toward the earlier median. A 3.5 scaled-MAD departure threshold, six-hour context, three-row minimum and four-equal-reading stuck screen are exploratory implementation defaults. Synthetic tests establish code behavior and no-lookahead invariance, not meteorological validity. E2 statuses do not diagnose hardware.

An initial sensitivity run evaluated all 123 saved 8/12 candidates across 1/3/6/12/24-hour windows, 2.5/3.5/4.5 robust-deviation cutoffs, and both modes (3,690 results). The one-hour window was unavailable for every candidate because the configured three-row context minimum could not be met. At six hours and 3.5, real-time screening marked 47 supporting and 76 with no detected departure. Retrospective screening marked 43 supporting, 76 with no detected evidence, and 4 conflicting with persistence. These model-selected observations are not independent labels; the results demonstrate sensitivity to screening settings, not temporal verification accuracy.

A follow-up crossed the same 123 E1-selected candidates with all six measured variables, five windows, three cutoffs and both modes (22,140 results). At six hours and 3.5, real-time support counts for temperature, dew point, relative humidity, precipitation, wind speed and pressure were 47, 44, 46, 44, 39 and 26; retrospective conflict counts were 4, 11, 5, 32, 17 and 7. This is a variable-sensitivity description on a model-selected sample. It does not estimate independent event/fault detection performance or calibrate E2 thresholds. Full details and grouped counts are in `research_results/e2_variable_sensitivity.csv`, `research_results/e2_variable_sensitivity_summary.csv` and the JSON manifest; the run is reproducible with `scripts/evaluate_e2_variable_sensitivity.py`.

## 8. Spatial, physical and integrated interpretation (limitations)

VILD0 coordinates are null in the provenance manifest, and verified neighboring observations are not available. The application correctly shows no map marker and keeps E3 unavailable. E4 uses broad physical screening rules and simple checks; no calibration history or labeled fault truth is present. The integrated interpretation remains uncertain where independent evidence is insufficient. The research does not currently demonstrate the three outcome categories as validated predictions.

In the additional synthetic matrix, existing E4 screening flags changed on 11 injected timestamp-variable rows. This included all three missing-temperature rows and cross-variable dew-point/temperature flags for selected point-drop, stuck, noise and dew-point perturbation injections. These results show the rule implementation responds to the selected synthetic conditions; they do not validate physical limits or diagnose a faulty sensor.

A follow-up evaluated the same eight scenarios at five held-out contexts chosen by pre-injection temperature level and six-hour variability. One train-only twelve-configuration fit and its clean comparator were reused for all 40 context/scenario cases. The configuration-by-injected-timestamp response fraction varied across contexts: point spike 0.667–1.000, point drop 0.667–0.917, persistent offset 0.042–0.361, stuck 0–0.319, drift 0–0.056, missing block 0–0.333, intermittent noise 0–0.292, and dew-point offset 0.667–0.806. No prediction changes fell outside the declared feature-propagation window; E4 screening changed on 36 injected timestamp-variable rows. These are synthetic-only responses from one shared fit, not field performance or verified false-positive estimates. Context-level, family-level and per-configuration artifacts are in `research_results/fault_matrix_multicontext_46ae5d119d/`; the methods and limitations are in `MULTICONTEXT_FAULT_MATRIX_REPORT.md`.

An independent temporal screen was additionally evaluated for the direct injection variable, against the same-time unmodified series, at 3/6/12-hour windows, 2.5/3.5/4.5 cutoffs and real-time/retrospective modes. Across 2,880 paired comparisons, 1,008 statuses changed; 270 changes were missing blocks becoming `UNAVAILABLE`, not positive evidence. Excluding those, faulted readings were `SUPPORTING` in 961/2,610 screen rows and same-time unmodified readings in 691/2,880. Ten matched unmodified controls produced `SUPPORTING` in 272/1,080 rows. Because controls are not adjudicated clean, these repeated screen outcomes do not estimate sensitivity, specificity or accuracy. Detailed tables and settings are saved with the campaign artifacts.

A secondary synthetic comparison reused the 160 labelled context × scenario × timestamp units. At the 8/12 E1 threshold, all point spike, point drop and dew-point inconsistency labels were flagged; the fractions were 0.067 for both persistent offsets and intermittent noise, and 0 for missing blocks, drift and stuck runs. E1 sensitivity to threshold, family-specific response, direct-variable E4 screening and E2 settings are reported in `SYNTHETIC_BASELINE_COMPARISON_REPORT.md`. These are fractions on known synthetic shifts and cannot estimate performance on real station faults. A coverage-only ablation found E2 available for 145/160 labels per setting (missing-temperature injections were `UNAVAILABLE`); E3-dependent combinations had no complete coverage. This does not evaluate outcome quality or the benefit of each evidence component.

## 9. Conclusions and future work

The current project demonstrates reproducible artifact checks, saved model-stability summaries, interactive review, temporal-screen comparisons, a synthetic baseline response comparison and an eight-scenario matrix evaluated at five contexts. It does not establish real-world anomaly-detection performance or a validated event/fault classifier. The baseline and ablation work is descriptive synthetic response and evidence availability only. E3 source data, independent real-world E2 validation, outcome-level ablation, robustness beyond the saved sensitivity grids, integrated evaluation against adjudicated outcomes, full reference verification and field validation remain outstanding.

## Traceability

- Saved E1 derivation: `scripts/analyze_saved_e1.py` and `research_results/e1_*`.
- Prediction parity: `scripts/investigate_prediction_mismatches.py` and `research_results/prediction_mismatch_investigation.*`.
- Methods and interface limits: `ANOMALY_INVESTIGATION_DESIGN.md`.
- Reproduction and phase status: `EXPERIMENT_TRACKER.md`, `RESEARCH_GAP_ANALYSIS.md`, `NEXT_SESSION.md`.

## PR #2 audit remediation checkpoint — 2026-11-17

The prior baseline section above records the first-generation timestamp-level summaries. Corrected, reviewable outputs are now written separately under `research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/`; the historical files and campaign manifest remain unchanged. The corrected analysis reuses saved predictions, injection registries, E4 results and reviewed E2 outputs; it performs no estimator fitting, new synthetic campaign, or prediction regeneration.

The analysis separates configuration/timestamp observations, context × scenario responses, and across-context summaries. Across-context minimum and maximum values now range over five context responses, not individual timestamps. It verified 5 contexts, 8 scenarios and 160 context × scenario × timestamp units; the response detail has 3,360 rows and the across-context summary has 168 rows. For the existing 8/12 E1 threshold, the across-context mean/minimum/maximum responses are: dew-point inconsistency 1.000/1.000/1.000 (15 units); gradual drift 0/0/0 (30); intermittent noise 0.0667/0/0.1667 (30); missing block 0/0/0 (15); persistent offset 0.0667/0/0.1667 (30); point drop 1/1/1 (5); point spike 1/1/1 (5); stuck sensor 0/0/0 (30). These are synthetic-label response fractions, not event detection accuracy.

The review manifest records 29 input artifacts and all 6 outputs with hashes, sizes and applicable row/column metadata; the manifest’s own final SHA-256 is stored in a separate integrity sidecar. Reviewed E2 artifacts were verified before use (6,840 detail rows, 2,880 pairs, 813 summaries and 10 controls). Experiment Lab hides the reviewed outputs and displays an integrity warning if required manifests or files are missing or fail checks. The historical campaign manifest and first-generation baseline outputs are preserved.

Implementation revision: `1712e1289e961211538277cc2f8285ef9f1dbce8`. Final full-suite result and hosted Actions result are recorded in `TESTING_REPORT.md` and `NEXT_SESSION.md` after completion of the push verification.
