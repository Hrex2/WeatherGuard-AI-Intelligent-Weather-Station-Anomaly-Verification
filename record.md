# Change Timeline — Cleaned Research Package

## 2026-11-15 (Asia/Kolkata)

- Selected the user-referenced source `Copy_of_Weather_Anomaly_Detection_2 (6)_phase01.ipynb`; verified valid nbformat-4 JSON, 4,104,749 bytes, 222 code cells, SHA-256 `14df99bfe9cd1b25e8370bc35fd004ad9c44a550e53adc1b079f0c611ee082dc`. The source was not edited.
- Inspected source and saved outputs. 156 cells contain outputs (121 stream outputs, 160 display outputs, 23 image representations, 2 saved historical errors). Exact duplicate code-source pair: cells 156/157.
- Created `cell_audit_inventory.csv` with one row per source cell, static variable references/definitions, prior-cell dependencies, saved-output MIME/preview and error text.
- Copied all source cells, execution counts, metadata and saved outputs into the exploratory archive notebook.
- Built 17-section master notebook (33 cells) and reusable modules for validation, causal feature engineering, preprocessing, retrieval, models/stability, episodes, matched-control inference, synthetic fault injection, spatial availability/comparison, physical flags and integrated outcomes.
- Created migration manifest for all 222 source cells. No source cells or historical outputs were deleted; one exact duplicate source cell is not repeated in the canonical workflow and remains in the archive.
- First-pass test-suite count was 20 passed, 0 failed at that milestone; this count was superseded by the second-pass suite (31 passed, 0 failed).
- Compiled and executed the 16 master code cells sequentially in local Python 3.12.9 with data loading, retrieval and model execution disabled; no errors. This is not a Colab/real-data validation.
- Preserved existing experiment registry and appended `REFACTOR-01`; created reports and dependency documentation.

## Current limitations

No real Pipeline B data, Phase 00 station CSVs/manifest, or Colab runtime artifacts were included. Phase 01 remains unverified on real data and historical model results are not reproduced.

- Extended the explicit Phase 01 audit API with per-segment feature comparisons, exact excluded-row reasons, precipitation and split value reconciliation, duplicate reporting, six-variable quality summaries, lag-1 dependence and month summaries. Added train/test feature and matrix parity checks.
- Final clean-path sequential execution and final test run succeeded; registry code digest: `5f4abf3bf8e95f8562cc0405607e150801b3485d6b3b95b09d0fc0bb757e8a47`.


## 2026-11-15 — Second-pass audit and corrections

- Re-ran the delivered suite and reconciled stale reports: **31 tests passed, 0 failed**.
- Corrected `PROJECT_STATUS.md`, `TESTING_REPORT.md`, README, refactoring/dependency reports and registry to report the same suite count and actual section statuses.
- Clarified `decision_log.md`: the Phase 02 cell 222/validator/report references are historical work in the separate `Weather_Anomaly_Research` folder, not artifacts in this cleaned package. Phase 02 is not implemented here.
- Fixed stability to raise on missing or unequal configuration prediction timestamps rather than silently count them as normal; validated common test rows and family metadata.
- Required a calibration cutoff for synthetic faults, rejected temporal injections crossing timestamp gaps/segments, made point-spike scope explicit, rejected missing prediction labels, and added canonical feature recomputation tests.
- Tightened integrated evidence completeness/abstention, post-candidate non-overlapping control windows, block-length sensitivity and Colab package root discovery.
- Added explicit implementation status for every notebook section. Ablation remains not implemented; other partial sections are marked as such.
- Executed all 16 notebook code cells sequentially with external data/retrieval/model execution disabled. Verified fresh-process package imports from a separate working directory.
- Removed `__pycache__`/`.pyc` and empty `notebooks`/`reports` directories. Source/archive hashes remain identical; no real weather data were read.


## 2026-11-15 — Final targeted bug-fix audit

- Corrected repeated-spike ground truth to label only values that changed. Preserved all observed timestamps in the interval registry and added interval endpoints, per-row `value_modified`, and exact injected timestamp JSON. Added timestamp-level score regression.
- Added explicit missing flags for all six base weather variables and cross-variable inconsistency flags; retained separate nonnumeric, infinite and screening-bound flags. Physical screening remains distinct from sensor-fault truth.
- Added stable unique IDs to all 33 master notebook cells. Kept the nbformat-4.0 exploratory archive byte-identical because the declared format does not require cell IDs.
- Added regression coverage for repeated spikes, missing observations in all six variables, fault types, feature engineering, model stability, integrated abstention and notebook IDs.
- Ran `python -B -m unittest discover -s tests -v`: **31 passed, 0 failed**. No real-data verification or complete Colab execution is claimed.

## 2026-11-16 — Codex continuation

- Extracted and audited the supplied November 15 archive in a separate checkpoint folder; original Desktop tree was not modified.
- Added a reusable synthetic campaign runner and executed +2/+5/+10/+15 C held-out temperature spikes at 2025-09-02 07:30 IST.
- Added explicit evidence explanation fields and updated outcome labels.
- Full details and limitations are in CODEX_PROJECT_AUDIT.md and CODEX_HANDOFF.md.
