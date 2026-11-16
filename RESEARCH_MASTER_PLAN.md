# WeatherGuard AI Research Master Plan

**Research:** Uncertainty-Aware Event-Level Verification of Weather Station Anomalies Using Model Stability, Temporal Consistency and Spatial Evidence.
**Continuation baseline:** `0a27959` (`main`, 2026-11-16), which merged PR #1 and the validated earlier research branch. Active work is on `codex/research-validation-v2`.

## Verified starting point

The Phase 01 manifest and hashes are checked by the application loader. The processed snapshot contains 44,879 observations; saved train and test matrices contain 36,434 and 8,415 rows. Phase 03 has 100,980 labels on 8,415 timestamps × 12 configurations; 123 timestamps meet the stored 8/12 threshold. The repository contains a controlled synthetic temperature point-spike campaign. These are artifact integrity and implementation checks, not raw-source reconstruction or real-world fault validation.

## Work inventory and sequence

| Workstream | Current status | Next action |
|---|---|---|
| Preserve Phase 01 and historical Phase 03 artifacts | Phase 01 snapshot hashes preserved; new Phase 03 integrity manifest covers 11 saved CSVs and Phase 01 references | Keep immutable; the new hash manifest verifies identity, not historical model-generation provenance |
| Prediction parity (42/100,980) | Reproduced; causal explanation unresolved | Preserve row-level audit; historical fit/scaler provenance is absent |
| E1 comparison and threshold sensitivity | Saved-label comparison generated | Review family/configuration overlap and 4/6/8/10/12 threshold sensitivity |
| Independent E2 temporal verification | Implemented; 22,140-row six-variable sensitivity across the 123 E1-selected timestamps; cadence/run correctness audit fixed | Test against the multi-context injection campaign and matched unmodified windows; E1-selected results remain descriptive |
| E3 station corroboration | Blocked by unverified raw station data/provenance | Preserve unavailable state pending traceable station exports |
| E4 physical screening | Broad measurement/relationship screens implemented and compared on synthetic injections | Validate variable-specific rules with traceable station metadata; do not diagnose hardware from screening flags |
| Synthetic campaign | Temperature dose series plus five-context × eight-scenario matrix executed; aggregate summaries and context runs are saved | Analyze by family/context, evaluate E2 paired to same-time clean series and matched controls, then surface multi-context results in Experiment Lab |
| Integrated E1–E4 interpretation | Partially implemented | Require independent evidence, retain abstention and audit statuses |
| Baseline, ablation, robustness | Not implemented as final studies | Define estimands and use available evidence only; no claims without labels |
| Investigation UI and separate CSV analysis | AppTest-verified; selected-variable E2 wired; hourly uploads now enforce every adjacent interval | Compare multi-context saved results after validation |
| Manuscript | Not drafted as a full report | Draft only traceable results and disclose unavailable phases |

## Quality gates

Do not modify verified snapshots, replace the primary data, change the train/test split, silently fit models, infer station coordinates, or treat unavailable evidence as negative. Every new run records its data hashes, code commit, configuration, feature order, environment, outputs and limitations. Scientific validation remains distinct from software tests.

## Phase 1 audit checkpoint

AUD-01 through AUD-08 have been corrected and regression-tested. AUD-09 is explicitly documented as a selection-dependence limitation; AUD-10 remains blocked by absent verified neighbor observations; AUD-11 research records are synchronized. `RESEARCH_GAP_ANALYSIS.md` contains per-finding status. Phase 1 passed 66 tests, Python compilation and Phase 03's 11-CSV integrity check. The current suite passes 69 tests and compilation after multi-context/E2 preparation. CI is defined in `.github/workflows/research-quality.yml`.
