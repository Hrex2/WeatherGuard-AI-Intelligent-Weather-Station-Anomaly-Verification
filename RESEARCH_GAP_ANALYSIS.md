# Research Gap Analysis — 2026-11-16

| Area | Evidence in repository | Classification | Remaining gap |
|---|---|---|---|
| Baseline data | Passed Phase 01 manifest; loader verifies hashes, counts and column order | Already completed and validated (artifact integrity) | Independent reconstruction from raw acquisition not possible with bundled files |
| Model grid | 12 configurations and 100,980 saved labels; E1 family and threshold tables generated | Completed but needs interpretation | Assess sensitivity; no truth labels for accuracy/calibration |
| Prediction parity | Targeted reproduction: 42 differences, all Isolation Forest; LOF and SVM match | Completed but needs causal explanation | Historical estimator/scaler objects and full fit environment are absent |
| E2 | Segment-aware robust-departure/stuck screening; explicit real-time and retrospective modes | Implemented and software-tested; thresholds not validated | Window/threshold sensitivity and domain evaluation |
| E3 | Derived spatial summaries and provenance scaffold; no bundled raw neighbor time series or verified coordinates | Blocked by unavailable data | Traceable observations, source metadata, units, time coverage and valid coordinates |
| E4 | Broad physical screening helper and selected-reading integration | Implemented; validation incomplete | Variable-specific limits, relationship screening and stuck/change checks with tests and careful status labels |
| Synthetic faults | Reproducible temperature point-spike campaign with manifest | Completed for that scenario | Other scenarios, shared framework, reproducibility metadata and limits |
| Integrated evidence | E1/E2/E3/E4 are represented separately; selected-reading interpretation abstains | Partially implemented | Evidence thresholds and three-outcome rules cannot be validated without truth/coverage |
| Baselines / ablation / robustness | Helpers exist for matched episodes and synthetic controls; no complete study | Not implemented as final studies | Prespecified evaluation units and defensible available-data comparisons |
| Application | Six workspaces, saved results, explicit model run controls | In progress | Advanced investigation workspace interactions, isolated CSV run and thorough UI regression |
| Manuscript | Literature summaries, methods and status documents | Not implemented as full manuscript | Chapter draft tied to verified outputs, references and disclosed limitations |

## Decision

Continue with the independent E2 sensitivity evaluation, E1 interpretation and UI change validation. E3 remains explicitly unavailable until source observations and provenance are supplied. Do not call the research complete based on application readiness.
