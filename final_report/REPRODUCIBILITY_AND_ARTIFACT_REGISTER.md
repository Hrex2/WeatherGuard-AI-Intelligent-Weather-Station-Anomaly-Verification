# Reproducibility and artifact register

## Source checkpoint

- Repository: local WeatherGuard AI checkout
- Source branch: `codex/phase1c-controlled-metar-pilot`
- Source commit: `07edecdad90c36b98c0e2ad789f4d5c07bed728e`
- Report branch: `codex/one-day-research-report`
- Source working tree was clean at report start. The report artifacts are derived from saved files and do not modify historical research outputs.

## Reproduction boundary

The report and evidence register are derived from saved CSV/JSON artifacts at the source checkpoint. Their hashes, source paths and row filters are listed in `FINAL_EVIDENCE_REGISTER.csv`. This publication snapshot is not a one-command report-generation product; the Markdown narrative is maintained as a reviewed source document. No models were fitted, predictions regenerated, campaigns rerun, provider data retrieved or historical files altered for this report.

## Key source artifacts

| Artifact group | Location | Integrity/interpretation |
|---|---|---|
| Phase 01 processed data | `verified_phase01/` | Historical manifest and hashes; processed data, no raw provenance reconstruction |
| Phase 03 predictions | `phase03_model_revalidation/` | Saved prediction grid and integrity manifest; 42 parity mismatches remain unresolved |
| E1 results | `research_results/e1_*.csv` | Saved candidate/stability summaries, no independent truth labels |
| E2 reviewed outputs | `research_results/fault_matrix_multicontext_46ae5d119d/e2_validation_review_1/` | Reviewed output manifest and status comparisons; synthetic screens |
| Corrected synthetic baseline | `research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/` | Manifest plus integrity sidecar; corrected aggregation and coverage-only ablation |
| Station acquisition phases | `research_results/phase1a_station_preflight/`, `phase1b_station_identity/`, `phase1c_metar_pilot/` | Provider inventory/adapter inspection; no raw observation retrieval |

## Verification performed

Counts asserted from saved artifacts: 44,879 processed rows; 44,849 feature-ready rows; 36,434 training rows; 8,415 test rows; 100,980 prediction rows; 6,840 E2 evaluations; 2,880 paired setting-level rows representing 160 underlying pair IDs repeated over 18 settings; 10 matched controls; 42 parity mismatch rows. Source file hashes and row filters are recorded claim-by-claim in `FINAL_EVIDENCE_REGISTER.csv`.

A passing artifact hash confirms byte identity against the referenced saved artifact at report generation. It does not establish that the original experiment was scientifically valid, independently reproduced or correctly labeled.
