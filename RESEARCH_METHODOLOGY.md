# Research methodology and verified limits

## Objective

Investigate whether model-configuration stability, temporal event structure, neighboring observations, and physical sensor-quality screens can inform an event-level interpretation of unusual weather observations while retaining uncertainty.

## Existing baseline

The supplied processed Pipeline B snapshots contain 44,879 rows in `model_df`; 44,849 feature-ready rows are partitioned into 36,434 training and 8,415 testing rows. The saved model matrix comprises six weather variables, three temperature history features, and month sine/cosine terms in the preserved order. The stored test predictions comprise twelve configurations spanning Isolation Forest, Local Outlier Factor, and One-Class SVM.

The test period follows a chronological split with a seven-day gap. Temperature history semantics in historical features are a grouped previous-row difference and a prior-six-observation shifted rolling mean. A one-hour episode definition is used for saved candidate profiles and respects segment identifiers.

## Evidence groups

- **E1:** votes/configuration and model-family behavior. Agreement is not probability.
- **E2:** candidate episode duration, gaps, and variable evolution. Candidate episodes are not known fault events.
- **E3:** descriptive comparisons to available neighbor artifacts. Neighbor provenance and coverage are incomplete; missing matches remain unavailable.
- **E4:** broad screening flags, missingness, temporal rates, persistence, and cross-variable checks where implemented. Screening flags are not ground-truth faults.

The three-way outcomes are regional support, station-specific suspicion, and uncertainty. The current integrated outcome implementation remains a scaffold and the app abstains where support cannot be defensibly determined.

## Controlled synthetic pilot

Four point spikes (+2, +5, +10, +15 °C) were injected at one test timestamp, 2025-09-02 07:30 +05:30. The training rows and scaler fit were retained. The current local clean model fit differs from stored Phase 03 predictions at 42 of 100,980 configuration/timestamp pairs; pilot deltas therefore use the matching local clean fit and record the parity issue. No real-world detection performance is inferred.

## Literature positioning

The cited meteorological QA papers establish a diverse family of range, temporal, persistence, spatial, metadata, and workflow checks. They motivate evidence categories but do not validate this project's model thresholds or establish novelty. The sensor-information paper's certainty-factor approach is reported as that paper's specific method; WeatherGuard does not reuse it as an unvalidated probability.
