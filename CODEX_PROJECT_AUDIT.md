# Codex project audit — 2026-11-16

## Scope and evidence inspected

Audited the November 15 archive extracted to this folder. Inspected all Python modules, the 31-test suite, both notebooks and their saved cell counts, the Phase 01 manifest and CSV snapshots, Phase 03 prediction/stability/Jaccard/episode/spatial outputs, the cell migration and cell audit CSVs, experiment registry, and the README/status/testing/bug-fix/audit/refactoring/dependency/decision/timeline documents. No source raw acquisition file or neighbor observation CSV is included; the spatial comparison CSVs are derived summaries.

The source archive and pre-existing Desktop project folder were left untouched. The project being changed is the extracted archive copy.

## Baseline

- Baseline command: `python -B -m unittest discover -s tests -v`
- Result before changes: 31 tests, 0 failures, 0 errors.
- Phase 01 manifest `audit_passed` is true. All four saved CSV SHA-256 hashes matched the manifest exactly: `model_df`, `X_multi`, `X_train_multi`, and `X_test_multi`.
- Saved frame sizes reconcile to 44,879 rows in `model_df`, 44,849 feature-ready rows, 36,434 train rows, and 8,415 test rows. `model_df` is processed data, not raw acquisition.
- Master notebook: 187 cells, 170 code cells, outputs in 149 cells, 153 non-null execution counts, and 9 saved error outputs. Exploratory archive: 222 cells, outputs in 156 cells, 160 non-null execution counts, and 2 saved historical error outputs. These are notebook artifacts, not proof of current runtime success.
- Cell migration manifest and inventory each contain 222 records.
- Phase 03 predictions: 100,980 rows = 8,415 timestamps × 12 configurations; zero duplicate timestamp/configuration pairs and zero missing candidate labels. The verified Jaccard table is 12×12 with diagonal 1 and nontrivial off-diagonal values. The 8/12 threshold selects 123 timestamps.

## Existing research and software state

The package already includes canonical feature engineering, chronological preprocessing, model configuration and stability APIs, episode building, spatial availability comparisons, physical screening, fault injection, matched-episode helpers, and a rule-based evidence classifier. Historical Phase 01 and Phase 03 outputs are included. They are stored research artifacts and were not regenerated from raw acquisition here.

The package’s status documents predate this archive’s included Phase 01 and Phase 03 snapshots and describe them as absent or unverified. This audit reconciles that inconsistency: stored Phase 01 hashes/counts and Phase 03 structural outputs were verified locally, while independent real-data reconstruction is still not established.

## Issues and limits found

- No raw primary-station acquisition or neighbor observation time series are bundled. Phase 02 station-level provenance and actual coverage cannot be reconstructed from derived comparisons alone.
- The 12-model local clean refit differs from the saved Phase 03 predictions at 42 of 100,980 configuration/timestamp cells. This may reflect environment/version or model-run differences and is recorded as a parity discrepancy; fault deltas are compared to the same local clean fit.
- Existing package evidence logic was tested on small synthetic fixtures only. It does not yield calibrated probabilities.
- The notebooks contain saved errors and historical execution state; the full notebooks were not rerun because that would entail unrelated exploratory/acquisition behavior.
- No original-observation truth labels exist. No real-data accuracy metrics are defensible.

## Changes made in this checkpoint

- Added `src/weather_research/synthetic_campaign.py`, a reusable, explicit runner for the controlled +2/+5/+10/+15 °C same-time spike dose series. It loads the verified snapshots, hashes source files, checks baseline prediction alignment, fits the train-only seasonal scaler and model configurations, keeps caller inputs immutable, and writes campaign tables and a manifest.
- Executed the controlled synthetic campaign locally on the included processed snapshots. Results are in `outputs/synthetic_fault_campaign/` and are synthetic findings only.
- Aligned evidence outcome labels with the requested three names and added transparent supporting/against/missing/conflicting evidence text and a non-calibrated uncertainty description.
- Updated tests for the outcome names.
- Created the requested audit, handoff, changelog, and next-steps records.

## Audit disposition

Phase 01 stored snapshot: verified for hash and internal manifest counts; this does not substitute for raw-data reconstruction. Phase 03 stored outputs: structurally verified; local refit parity needs review. Synthetic validation: controlled temperature point-spike series executed. Phase 02, complete fault matrix, complete E1–E4 feature pipeline and ablation remain incomplete.

## Follow-up outputs

A Phase 02 report and station manifest were added using only supplied project-history values. All absent coordinates, provider details, retrieval metadata, per-variable coverage and raw neighbor files remain null/unverified. The manifest is an inventory scaffold, not a completed provenance audit.

The executed campaign recorded target configuration votes of 0 (clean), 6 (+2 C), 9 (+5 C), 11 (+10 C), and 12 (+15 C). Compared with the matching local clean refit, the total changed config/timestamp predictions were 10, 15, 20, and 21. Each magnitude had one timestamp with a new candidate outside the injected one-point label (within the six-following-observation feature propagation window); there were zero changes beyond the declared seven-timestamp affected window. These are synthetic-label evaluation outputs only.

## Application implementation follow-up

The continuation now includes five Streamlit workspaces, read-only artifact services, explicit manual model execution, an opt-in controlled campaign form, source-linked literature summaries, and evidence views that abstain under missing/uncalibrated inputs. The expanded suite passes 35 tests. Localhost socket access was denied by the sandbox, so HTTP health and browser screenshots were not captured. The application is a functioning tested foundation, not the complete product requested: full synthetic fault coverage, complete E1–E4 integration, ablation, station provenance, and literature full-text review remain outstanding.
