# Decision Log — Cleaned Package Scope

## Scope correction for historical entries

The following 2026-11-15 Phase 00/01/02 entries were copied from the separate `Weather_Anomaly_Research` working folder. They describe historical work on a different notebook snapshot. They are not evidence that the corresponding cell, validator, report or output is included in this cleaned package. In particular, this package contains no Phase 02 audit cell 222, `validate_phase02_audit.py`, Phase 02 report, provider-inventory output, or Drive read-back artifacts. The master package's `retrieval.py` and `spatial.py` are partial helpers, not the full Phase 02 audit.

## Historical log retained (external working-folder scope)

- Cell 221 correction and a Phase 02 cell 222 were previously recorded in `Weather_Anomaly_Research`; those records remain in that separate folder. Real Phase 01/02 data were not executed there.
- Synthetic validators referenced in the source decision log ran in that prior workspace, not in this delivery. The cleaned package now has its own `tests/test_research.py`; it does not bundle the earlier Phase 02 validator.

## 2026-11-15 — Cleaned package audit

- The user-selected source notebook was copied into the exploratory archive byte-for-byte. The master notebook was built separately.
- Added a 17-section implementation-status table, correcting the earlier overstatement that all sections were implemented. Section 02 is partial and the full Phase 02 audit is not delivered; Section 15 is not implemented.
- Corrected model stability so unequal/missing configuration timestamps raise errors instead of being filled as normal votes.
- Required an explicit calibration boundary for synthetic faults; blocked point spikes over multiple timestamps and temporal faults across gaps/segments; rejected missing detection outputs. Added clean/fault feature recomputation with shifted-reference checks.
- Tightened evidence abstention for incomplete inputs, matched controls to post-candidate non-overlapping windows, and added block-length sensitivity support.
- Corrected test count/status and registry claims; appended `SECOND-PASS-01`.
- Verification: 28 package tests passed; 16 master code cells ran sequentially without real data/retrieval/model execution. Colab/Drive and real weather data remain unverified.

## 2026-11-16 — Codex continuation

- Verified saved Phase 01 snapshot SHA-256 values against the included manifest.
- Verified Phase 03 prediction grid and corrected Jaccard structure. The local clean refit differs from saved labels in 42 configuration/timestamp cells; retain this discrepancy for diagnosis.
- Added and executed a same-time temperature-spike dose series. The local synthetic outputs do not establish real-world anomaly performance.
- Did not run live retrieval or Colab.
