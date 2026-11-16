# Final Bug-Fix Report

**Date:** 2026-11-15 (Asia/Kolkata)

## Issues and corrections

- **High — Repeated-spike labels:** The fault interval was labeled entirely positive even though only selected readings changed. Labels now mark only changed timestamps. The registry retains every timestamp in the observed interval, records its start/end, flags which row changed, and stores the exact injected timestamp list. Evaluation uses this timestamp-level truth.
- **Medium — Physical missingness:** Quality flags now distinguish missing, nonnumeric, infinite, below-screening, above-screening, and cross-variable inconsistency. Missing observations are explicitly flagged and not treated as physically valid. Broad screening remains separate from sensor-fault labels.
- **Low — Notebook cell IDs:** Unique stable IDs were added to all 33 master notebook cells (nbformat 4.5). The exploratory archive is nbformat 4.0, so IDs are not required; it remains byte-identical, preserving historical source, outputs, execution counts and metadata.

## Verification

- Command: `python -B -m unittest discover -s tests -v`
- **31 passed; 0 failed.**
- Added regression checks for repeated-spike labels and registry timestamps, missing readings in each of six weather variables, and notebook ID requirements. Existing suite exercises other fault types, feature engineering, model stability, train-only preprocessing and integrated evidence abstention.
- No real weather data were validated, no models were retrained, and no complete hosted Colab run is claimed. Phase 01 remains **NOT VERIFIED** on real data.

See `SECOND_PASS_AUDIT.md` for the broader audit and remaining research limitations.
