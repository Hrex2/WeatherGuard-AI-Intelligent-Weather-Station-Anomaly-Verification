# Phase 13 — Limitations and Future Work

## Limitations

1. **Ground truth and event adjudication:** No independent, adjudicated anomaly or fault labels are available. Precision, recall, F1, false-positive rate, and fault-detection accuracy cannot be estimated.
2. **Observation provenance:** Integrity hashes establish byte identity for saved files, not original provider lineage. Processed historical observations cannot be fully traced to raw provider reports, instruments, calibration histories, or quality-control transformations.
3. **E3 independence and alignment:** Station identity is only partially resolved; source and instrument independence are unverified for candidate-event pairs. Many candidate-indexed comparisons are asynchronous or lack offsets. E3 remains descriptive and decision-ineligible.
4. **Prediction reproducibility:** 42 of 100,980 saved prediction cells disagree in the parity investigation, all associated with Isolation Forest. The cause and exact training/scaler provenance remain unresolved.
5. **Synthetic scope:** The five-context, eight-scenario injection experiment tests controlled responses on selected data contexts. It does not reproduce field fault distributions or establish real-world predictive performance. Repeated setting-level rows must not be treated as independent samples.
6. **Screen thresholds and calibration:** The 8/12 E1 threshold and E2/E4 heuristics are exploratory. There is no independent calibration, uncertainty calibration, or pre-registered operational cost function.
7. **Dependence between components:** E1 is exactly derived from the baseline labels. E2 and E4 inspect processed data from the same primary station. E3 lineage is unresolved. Component flags must not be interpreted as independent votes.
8. **Scope and transfer:** Evidence centers on one primary station and a single temporal split. External station, climate, season, sensor, and provider generalization are untested.
9. **Literature scope:** `research_content/literature.json` contains a focused narrative set of five meteorological QA/QC sources, not a systematic review. It does not establish novelty across the full anomaly-detection literature.

## Ranked future work

1. **Acquire reference-grade observations and labels:** Secure raw provider reports with stable IDs, source documentation, station coordinates, sensor/instrument history, calibration and QC metadata. Pre-register blinded event adjudication and separate “unusual weather” from “instrument fault.”
2. **Resolve the reproducibility mismatch:** Reconstruct estimator, scaler, random seeds, package versions, training rows, and serialization; reproduce all prediction cells and document why the 42 Isolation Forest cells differ.
3. **Validate E3 prospectively:** Establish station and report lineage, assess source independence, use variable-specific measurement comparability, enforce time tolerances, and evaluate against adjudicated events. Keep missing evidence distinct from contradictory evidence.
4. **Evaluate across stations and time:** Use station-held-out and forward-chaining evaluation, independent event sets, and appropriate uncertainty intervals. Avoid leakage from feature construction or temporal neighborhoods.
5. **Calibrate screens and decision costs:** Pre-register thresholds and operational consequences; measure false alarms, missed events, abstention, and calibration using independent labels. Do not optimize on the current test window.
6. **Report synthetic experiments as stress tests:** Expand injection realism and context diversity, document unit of analysis, and use simulation only as complementary evidence, never a substitute for field labels.
7. **Update the manuscript and literature review:** Reconcile earlier claims with Phase 12 dependency and coverage findings, verify all references and captions, and update the pre-Phase-12 IEEE paper before submission.
