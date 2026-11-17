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

## PR #2 audit remediation checkpoint — 2026-11-17

The prior baseline section above records the first-generation timestamp-level summaries. Corrected, reviewable outputs are now written separately under `research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/`; the historical files and campaign manifest remain unchanged. The corrected analysis reuses saved predictions, injection registries, E4 results and reviewed E2 outputs; it performs no estimator fitting, new synthetic campaign, or prediction regeneration.

The analysis separates configuration/timestamp observations, context × scenario responses, and across-context summaries. Across-context minimum and maximum values now range over five context responses, not individual timestamps. It verified 5 contexts, 8 scenarios and 160 context × scenario × timestamp units; the response detail has 3,360 rows and the across-context summary has 168 rows. For the existing 8/12 E1 threshold, the across-context mean/minimum/maximum responses are: dew-point inconsistency 1.000/1.000/1.000 (15 units); gradual drift 0/0/0 (30); intermittent noise 0.0667/0/0.1667 (30); missing block 0/0/0 (15); persistent offset 0.0667/0/0.1667 (30); point drop 1/1/1 (5); point spike 1/1/1 (5); stuck sensor 0/0/0 (30). These are synthetic-label response fractions, not event detection accuracy.

The review manifest records 29 input artifacts and all 6 outputs with hashes, sizes and applicable row/column metadata; the manifest’s own final SHA-256 is stored in a separate integrity sidecar. Reviewed E2 artifacts were verified before use (6,840 detail rows, 2,880 pairs, 813 summaries and 10 controls). Experiment Lab hides the reviewed outputs and displays an integrity warning if required manifests or files are missing or fail checks. The historical campaign manifest and first-generation baseline outputs are preserved.

Implementation revision: `1712e1289e961211538277cc2f8285ef9f1dbce8`. Final full-suite result and hosted Actions result are recorded in `TESTING_REPORT.md` and `NEXT_SESSION.md` after completion of the push verification.

## Research completion roadmap baseline — 2026-11-17

The verified software baseline is `main` at `852bc34e76ef4e5de15e48f0f1402f7bf0e9c1d1`. Phase 0 is complete; see `PHASE0_BASELINE_VERIFICATION.md`. Do not treat that gate as scientific completion. Phases 1–5 depend on source-verified station observations and independent event/fault/normal references, which are not present in the repository. The active local documentation checkpoint is `codex/research-completion-roadmap-phase0`.

## Phase 1A station preflight — 2026-11-17

Phase 1A status: **PARTIALLY_COMPLETE_EXTERNAL_DATA_ACCESS_REQUIRED**. The repository contains VILD0 plus four neighbor candidates: 42099, 42101, 42105 and 42096. Public Meteostat pages report station metadata and station-level hourly inventory periods for the first four; 42096 shows daily historical inventory only. Provider inventory is not proof of populated per-parameter rows or direct observation provenance. All seven parameter-level availability statuses remain `NOT_CHECKED`. Candidate suitability, distances, sources, and manual-access requirements are documented in `research_results/phase1a_station_preflight/PHASE1A_STATION_PREFLIGHT_REPORT.md`.

No raw observation files were downloaded. No historical prediction, Phase 01/03 snapshot, spatial comparison, or synthetic result was modified. The Meteostat package is not installed, its parameter inventory API was not called, and IMD Data Service Portal request/access terms remain unverified. E3 is not validated. Phase 1B must wait for source-verified station metadata and controlled, approved raw observation retrieval.

## Phase 1B identity and availability checkpoint — 2026-11-17

The Phase 1A section above is historical. Phase 1B queried 179 parameter/provider inventory metadata records from Meteostat 2.2.3 in an isolated temporary environment. This establishes provider inventory envelopes only; no weather rows/source flags were fetched. VILD0 and 42099 remain IDENTITY_UNRESOLVED. A provisional VILD0/42105 METAR inventory window covers 2021-01-05 through 2026-03-09 for five fields; 42105 remains a distant conditional regional candidate. IMD registration/procurement steps were confirmed from the public portal, but station/hourly availability remain unchecked. Status is PARTIALLY_COMPLETE_EXTERNAL_ACCESS_REQUIRED. Raw retrieval awaits explicit approval; E3 remains unvalidated and Phase 2 independent event/fault references remain outstanding. See research_results/phase1b_station_identity/PHASE1B_READINESS_REPORT.md and research_results/phase1b_station_identity/RAW_DATA_RETRIEVAL_PROPOSAL.md.
