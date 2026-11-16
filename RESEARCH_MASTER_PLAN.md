# WeatherGuard AI Research Master Plan

**Research:** Uncertainty-Aware Event-Level Verification of Weather Station Anomalies Using Model Stability, Temporal Consistency and Spatial Evidence.
**Continuation baseline:** `830d315` (`main`, 2026-11-16). Active work is on `codex/autonomous-research-loop`.

## Verified starting point

The Phase 01 manifest and hashes are checked by the application loader. The processed snapshot contains 44,879 observations; saved train and test matrices contain 36,434 and 8,415 rows. Phase 03 has 100,980 labels on 8,415 timestamps × 12 configurations; 123 timestamps meet the stored 8/12 threshold. The repository contains a controlled synthetic temperature point-spike campaign. These are artifact integrity and implementation checks, not raw-source reconstruction or real-world fault validation.

## Work inventory and sequence

| Workstream | Current status | Next action |
|---|---|---|
| Preserve Phase 01 and historical Phase 03 artifacts | Already completed and validated for hashes/schema | Keep immutable; verify loader regression |
| Prediction parity (42/100,980) | Reproduced; causal explanation unresolved | Preserve row-level audit; historical fit/scaler provenance is absent |
| E1 comparison and threshold sensitivity | Saved-label comparison generated | Review family/configuration overlap and 4/6/8/10/12 threshold sensitivity |
| Independent E2 temporal verification | Implemented and software-tested | Evaluate window/threshold sensitivity and scientific meaning; cutoffs are exploratory |
| E3 station corroboration | Blocked by unverified raw station data/provenance | Preserve unavailable state pending traceable station exports |
| E4 physical screening | Implemented, classification needs validation | Test multi-variable ranges, relationships, stuck and change flags; do not diagnose hardware |
| Synthetic campaign | Temperature point spike executed | Extend fault types with independent run IDs/manifests and retain synthetic-only labels |
| Integrated E1–E4 interpretation | Partially implemented | Require independent evidence, retain abstention and audit statuses |
| Baseline, ablation, robustness | Not implemented as final studies | Define estimands and use available evidence only; no claims without labels |
| Investigation UI and separate CSV analysis | In progress | Finish interaction/AppTest, docs and regression checks |
| Manuscript | Not drafted as a full report | Draft only traceable results and disclose unavailable phases |

## Quality gates

Do not modify verified snapshots, replace the primary data, change the train/test split, silently fit models, infer station coordinates, or treat unavailable evidence as negative. Every new run records its data hashes, code commit, configuration, feature order, environment, outputs and limitations. Scientific validation remains distinct from software tests.
