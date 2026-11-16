# Refactoring and Notebook Audit Report

## Source identity and preservation

Selected source (from the direct file reference): `C:/Users/Dell/OneDrive/Desktop/Copy_of_Weather_Anomaly_Detection_2 (6)_phase01.ipynb`. It is valid nbformat 4 JSON, **4,104,749 bytes**, **222 cells**, all code cells, SHA-256 `14df99bfe9cd1b25e8370bc35fd004ad9c44a550e53adc1b079f0c611ee082dc`. The source was not modified. The archive notebook has the same SHA-256, preserving every original cell, saved output, execution count, and notebook metadata.

The complete cell inventory is `cell_audit_inventory.csv`; it covers every cell's purpose, variable names referenced/defined, imported libraries, file/source literals, prior-cell dependencies, output MIME types/previews and saved errors. Dependencies are static AST estimates; notebook runtime state can add conditional dependencies. `cell_migration_manifest.csv` maps all 222 original cells to their section disposition and unchanged archive location.

## Audit findings

- Source contains no Markdown cells and has 156 cells with saved outputs. Saved output payloads include 121 stream outputs, 160 display outputs and 23 image representations. The notebook also preserves two saved errors: cell 143 has a `TypeError` involving `isinf` on unsupported input types; cell 156 has a `NameError` because `strong_single_family` is undefined in that execution state. These are historical outputs, not rerun results.
- Cells 156 and 157 have identical normalized source. One exact duplicate implementation is consolidated in the clean workflow into reusable episode construction; cell 157 and its saved output remain untouched in the archive.
- Cells 49–52 use different segment-size thresholds (6 versus 100) and selections; they are not equivalent duplicates. They remain historical archive analyses.
- Cell 53 uses previous-row temperature difference and a shifted previous-six-observation rolling mean. Cell 129 adds exact one-hour continuity for the named hourly change. The clean module preserves the previous-row version as `temp_change_row`, and defines `temp_change_1h` only when the timestamp interval is exactly one hour. The rolling mean remains previous-six-observation and shifted. The canonical feature name uses `6obs`, clarifying that cadence can be irregular. Existing model predictions must not be reused as if their features were unchanged.
- Cell 55 computes precipitation median before the split; cell 56 splits that prepared data. Cell 57 rebuilds features and fits the precipitation median on training data only. The clean workflow uses train-only imputation and records missingness. Historical figures are not presumed reproduced.
- Cells 64–65 add monthly sine/cosine features and define another split. Their month/12 formula is retained in `add_month_cycle`; one explicit cutoff and train-only scaling now govern the canonical path.
- Cells 160–192 and 193–211 contain overlapping temporal, matched-control, synthetic injection, spatial, provenance and integrated-evidence prototypes. Non-equivalent experiments remain archived; reusable APIs consolidate the supported mechanics. No unsupported historical p-values or candidate counts were copied into the master as results.
- Cells 212–220 contain earlier/repeated audits. Cell 220 is not promoted as authoritative. Revised Phase 01 cell 221 is retained as the reference audit and its logic is exposed as `phase01_integrity_audit`, requiring explicit inputs rather than notebook `globals()`.
- Static Python compilation passes for the source after stripping its two Colab `!pip` magic lines (cells 0 and 16); those are valid IPython cells. The master notebook contains ordinary Python code only.

## Deliverables and changes

- New master: `Weather_Station_Anomaly_Detection_Master.ipynb`, **33 cells** (17 Markdown section headers/explanations and 16 code cells). It follows Sections 00–16 in the requested order. Data retrieval and model fitting are off by default.
- Exploratory archive: original 222-cell notebook copied byte-for-byte, including saved outputs.
- Reusable package: `src/weather_research/` contains audit, validation, feature engineering, preprocessing, retrieval, models/stability, temporal events, matched controls, synthetic faults, spatial evidence, physical quality and integrated evidence.
- Cell inventory and migration manifest cover all source cells. All **222** original cells remain in the archive; **0** source cells were deleted. One exact duplicate cell is not separately represented in the canonical workflow.
- Existing `experiment_registry.csv` rows and IDs were preserved; `REFACTOR-01` was appended.
- `record.md`, `DEPENDENCY_MAP.md`, `PROJECT_STATUS.md`, `README.md`, and `requirements.txt` document the workflow.

## Scientific definitions and limitations

The strict hourly feature and train-only preprocessing are leakage-aware. The training/test cutoff is explicit; any actual temporal gap is reported, not filled. Model prediction generation is opt-in and timestamp-indexed. Model agreement remains an agreement measure, not a probability. Episode thresholds are configurable (1/2/3 hours); matched-control inference resamples chronologically ordered episode pairs in declared blocks and requires sensitivity to block length. Synthetic injections are labeled only as injected faults and constrained by broad screening bounds (except missingness/dropout); these bounds are not sensor calibration specifications. Spatial availability is separate from disagreement and comparisons require a caller-specified tolerance. Integrated classification abstains when evidence is incomplete or conflicting.

The master workflow has **not** been run on real VILD0 data. No Pipeline B raw frame, station CSV/manifest, or Colab model objects were available. Therefore Phase 01 is **NOT VERIFIED on real data**, historical models were not retrained, and no empirical findings are claimed.


## Second-pass audit corrections (2026-11-15)

- Fixed stale test count in project status (the delivered suite now runs 31 tests, not 14).
- Confirmed prior decision-log claims about Phase 02 refer to the separate historical `Weather_Anomaly_Research` folder. The delivered clean package has no cell 222, Phase 02 validator/report, provider inventory, or station coverage/readback audit. Updated package documentation and registry to say so.
- Added explicit status for Sections 00–16 in the notebook. Sections 04, 10–14 and 16 are partial; Section 15 is not implemented.
- Stability now requires the same complete timestamp set for every configuration and raises on missing votes; it no longer converts missing rows to normal votes.
- Synthetic injection now requires a calibration cutoff, rejects point-spike intervals and temporal injections across timestamp/segment gaps, and rejects missing model outputs during scoring. Added canonical feature recomputation and a test proving the injected value cannot enter its own shifted rolling reference.
- Matched controls are post-candidate and non-overlapping, and a helper reports block-length sensitivity. This does not validate the observational sign-flip assumptions; matched-control inference remains exploratory.
- Integrated outcomes require complete E1/E2/E3/E4 fields for either confident outcome; otherwise the result is uncertain.
- Added clean-process package import/path validation and Colab setup instructions. Actual hosted Colab and Drive execution remain unverified.


## Final targeted bug-fix audit (2026-11-15)

- Fixed repeated-spike labels: only timestamps whose values were changed are positive. Registry rows still span the full observed injection interval and include interval endpoints, a per-timestamp modification flag, and a JSON list of exact injected timestamps. Pointwise evaluation consumes this timestamp-level label series.
- Added explicit physical `missing` and `cross_variable_inconsistency` fields, with separate nonnumeric, infinite, below-range and above-range screening flags. Missing values are flagged and never treated as physically valid; these broad screens are not synthetic or observed fault labels.
- Added stable unique IDs to each master notebook cell. The exploratory archive remains byte-identical; its declared nbformat 4.0 does not require IDs.
- Final regression suite: **31 passed, 0 failed**. No real-data validation, model retraining, or hosted Colab execution is claimed. See `FINAL_BUGFIX_REPORT.md`.
