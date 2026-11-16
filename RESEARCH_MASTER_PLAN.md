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
| Independent E2 temporal verification | Implemented; 22,140-row six-variable E1-selected sensitivity plus 6,840 exploratory screen evaluations across five synthetic fault contexts and 10 matched controls | Outputs show 1,008/2,880 paired status changes, including 270 `UNAVAILABLE` missing readings; supporting temporal evidence also appears in matched controls. No adjudicated labels; not field validation. |
| E3 station corroboration | Blocked by unverified raw station data/provenance | Preserve unavailable state pending traceable station exports |
| E4 physical screening | Broad measurement/relationship screens implemented and compared on synthetic injections | Validate variable-specific rules with traceable station metadata; do not diagnose hardware from screening flags |
| Synthetic campaign | Temperature dose series plus five-context × eight-scenario matrix executed; aggregate summaries and context runs are saved | Interpret only as explicitly synthetic detector behavior; no field-accuracy claims |
| Integrated E1–E4 interpretation | Partially implemented | Require independent evidence, retain abstention and audit statuses |
| Baseline, ablation, robustness | Synthetic baseline response and E1/E2/E4 setting sensitivity executed; coverage-only ablation shows E2 availability and the E3 block | No outcome-level ablation or real-world accuracy is supportable without E3 observations and adjudicated labels |
| Investigation UI and separate CSV analysis | Multi-context, E2 paired screens, synthetic baseline, setting sensitivity and evidence-coverage tables shown after hash checks | Continue UI review and preserve synthetic/historical separation |
| Manuscript | Not drafted as a full report | Draft only traceable results and disclose unavailable phases |

## Quality gates

Do not modify verified snapshots, replace the primary data, change the train/test split, silently fit models, infer station coordinates, or treat unavailable evidence as negative. Every new run records its data hashes, code commit, configuration, feature order, environment, outputs and limitations. Scientific validation remains distinct from software tests.

## Phase 1 audit checkpoint

AUD-01 through AUD-08 have been corrected and regression-tested. AUD-09 is explicitly documented as a selection-dependence limitation; AUD-10 remains blocked by absent verified neighbor observations; AUD-11 research records are synchronized. `RESEARCH_GAP_ANALYSIS.md` contains per-finding status. Phase 1 passed 66 tests, Python compilation and Phase 03's 11-CSV integrity check. The current suite passes 69 tests and compilation after multi-context/E2 preparation. CI is defined in `.github/workflows/research-quality.yml`.
