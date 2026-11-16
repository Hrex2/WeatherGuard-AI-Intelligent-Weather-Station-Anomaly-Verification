# Anomaly Investigation Workspace — Implementation Notes

## Historical investigation

`Investigate a Reading` combines the saved Phase 03 prediction grid, a date/family-filtered model-by-time heatmap, timestamp selector, variable timeline, distribution and data-quality views, family-level binary-label comparisons, and a selected-reading detail column. The heatmap samples wide date ranges for display only; the timestamp selector retains access to every prediction timestamp. The 8/12 row is calculated from the full saved grid and is unavailable when any of the 12 predictions are missing.

Only observed variables found in the selected observation table are offered. Variable summaries use chronological values and prior-only rolling statistics. The location component renders no marker unless manifest coordinates are numeric and in range; current VILD0 coordinates are unavailable. Neighbor data do not establish E3.

## Independent E2 screening

`services/temporal_service.py` reads measured observations and no model predictions or consensus episodes. It estimates local sampling cadence, splits context when the gap exceeds 1.5× the median interval, and computes a prior-window median/MAD departure. Real-time mode uses only prior and selected measurements. Retrospective mode is explicit and may inspect following values for persistence/return-to-baseline context. Missing selected readings or insufficient same-segment context yield `UNAVAILABLE`.

The current robust-departure threshold (3.5 robust scales) and minimum context (3 observations) are exploratory screening defaults, not validated meteorological criteria. The E2 status describes temporal behavior and cannot diagnose a sensor. Retrospective `CONFLICTING` means an unusual point returns toward the previous local median; it is not proof of a fault. The integrated event outcome remains uncertain.

## New CSV workflow

The Weather Data workspace accepts CSV uploads up to 25 MB. It requires explicit timestamp and six-variable mappings, declared source units, unique timestamps, and hourly median cadence. It uses the existing 11-feature protocol and a chronological 80/20 split with training-only median imputation. Validation occurs before fitting; model fitting occurs only after the dedicated run button. Each run gets a unique ignored output directory and stores a hash and metadata, not the raw upload or estimator objects. Upload analysis is a distinct result/detail view; direct reuse of the historical investigation drawer and cross-dataset comparison are not yet wired.

## Parity investigation

`scripts/investigate_prediction_mismatches.py` reproduces the saved grid once and writes row-level differences plus feature vectors and current protocol/environment metadata. It reproduces 42 differences, all Isolation Forest; LOF and One-Class SVM match. Historical estimator/scaler objects and complete fit provenance are absent, so the cause remains unresolved. The saved prediction CSV is untouched.

## E1 saved-label analysis

`scripts/analyze_saved_e1.py` derives configuration counts, family summaries, pairwise Jaccard/disagreement, and 4/6/8/10/12 threshold sensitivity directly from the verified saved labels. It does not refit models. These are model-output agreement statistics, not probabilities or real-world performance measures.
