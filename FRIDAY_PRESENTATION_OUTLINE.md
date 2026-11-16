# WeatherGuard AI — 11-slide presentation outline

Keep the deck to about 5–6 minutes, leaving time for the live interface. Use screenshots captured from the actual rehearsed app; do not invent values or state that unavailable evidence has been validated.

## 1. Title and introduction

**WeatherGuard AI — Intelligent Weather Station Anomaly Verification**  
Research: “Uncertainty-Aware Event-Level Verification of Weather Station Anomalies Using Model Stability, Temporal Consistency and Spatial Evidence.”

Speaker cue: this is a working research prototype for historical weather observations.

## 2. Problem statement

Weather observations can be unusual because of real atmospheric events, sensor/measurement problems, or limited evidence. An anomaly flag describes statistical unusualness; it does not explain the cause.

## 3. Why verification matters

Weather quality workflows use different checks: physical ranges, temporal behavior, internal consistency, station context, and neighboring observations. A single outlier detector cannot replace those checks or human review.

## 4. Existing research and gap

The project bibliography includes meteorological quality procedures, automatic-station validation guidance, network standardization, time-series QA/QC, and sensor information-quality work. The project question is how to present model stability together with temporal, spatial, and physical evidence while representing uncertainty. Do not claim this combination is wholly novel or validated.

## 5. Proposed WeatherGuard framework

Diagram: historical data → integrity validation → feature engineering → unsupervised models → E1 model stability → E2 temporal consistency → E3 spatial corroboration → E4 physical screening → cautious event-level interpretation.

Outcomes are research targets: regionally supported unusual event, station-specific suspicious observation, or uncertain/insufficient evidence. Current application defaults to uncertainty.

## 6. Dataset and preprocessing

Show only sourced facts: VILD0 processed snapshot; 44,879 rows; six weather variables plus four derived/segment columns; 2021-01-05 to 2026-03-09 IST. Model train/test matrices contain 36,434 and 8,415 rows. Phase 01 hashes, row counts, and column order are checked at load time. Original raw retrieval/provenance is not bundled.

## 7. Machine-learning models

Four configurations each for Isolation Forest, Local Outlier Factor, and One-Class SVM; 12 saved configurations total. Explain that unsupervised methods are useful for exploratory ranking where ground-truth fault labels are unavailable, but this prevents supervised accuracy claims.

## 8. E1–E4 evidence framework

- **E1:** saved 12-configuration votes available; agreement is not probability.
- **E2:** saved episode context is available but is consensus-derived, so independent temporal evidence is not yet established.
- **E3:** unavailable for reliable verification due to missing raw neighbor series, coordinates/provider provenance, and validated comparison thresholds.
- **E4:** broad physical screening exists; flags are not station-fault labels and missingness alone is not positive fault evidence.

## 9. Synthetic experiment and results

Controlled point spike at 2025-09-02 07:30 IST. Target votes: clean 0; +2 °C 6; +5 °C 9; +10 °C 11; +15 °C 12. All injected target rows were flagged by at least one model; 8/12 was reached by +5 °C. These are synthetic response results only. 10/15/20/21 config predictions changed anywhere; zero beyond the expected feature-propagation window. Local refit parity mismatch: 42 of 100,980 cells.

## 10. Limitations and current status

No real fault labels, no verified neighbor observations/provenance, no calibrated probabilities, and no validated integrated E1–E4 outcome rule. Model refit mismatch remains unresolved. No live-feed claim. Results are an honest prototype status, not a completed scientific validation.

## 11. Future work and conclusion

Complete station provenance and neighbor coverage; independently evaluate temporal/spatial/physical evidence; validate evidence rules with expert review or labeled data; diagnose prediction parity; run ablations; broaden reproducible synthetic fault campaigns. WeatherGuard currently demonstrates how multiple saved model configurations and cautious evidence framing can support investigation.
