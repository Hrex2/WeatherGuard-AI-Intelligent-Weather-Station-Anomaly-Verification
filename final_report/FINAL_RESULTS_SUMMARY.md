# Final results summary

This summary is tied to the local Phase 1C source commit `07edecdad90c36b98c0e2ad789f4d5c07bed728e`. Evidence identities are recorded in `FINAL_EVIDENCE_REGISTER.csv`; hashes establish file identity, not scientific provenance.

- **Processed snapshot:** 44,879 rows; 44,849 feature-ready rows. Train/test contain 36,434/8,415 rows with a seven-day temporal gap. The persisted feature matrix contains nine base columns; the model service derives two cyclical month terms at runtime.
- **Prediction grid:** 100,980 configuration-time records across 12 configurations and 8,415 test timestamps. A later parity investigation lists 42 mismatches, all associated with Isolation Forest; cause remains unresolved.
- **E1:** 4/12, 6/12, 8/12, 10/12 and 12/12 consensus thresholds select 432, 214, 123, 51 and 15 timestamps. These are candidate counts, not calibrated probabilities or accuracy.
- **E2:** reviewed outputs contain 6,840 evaluations, 2,880 paired setting-level rows, 160 underlying pair IDs repeated over 18 settings, and 10 matched controls. Status changed in 1,008 setting-level rows; 270 missing-block evaluations became unavailable. Supporting statuses are temporal evidence only.
- **Synthetic campaign:** five preselected contexts, eight scenarios, 40 context-scenario combinations and 160 corrected context × scenario × injected-timestamp units. At 8/12 E1, corrected mean response ranges by scenario from 0% to 100%, with pronounced between-context variation. These are not field recall estimates.
- **E4:** direct physical-screen synthetic outcomes detect the injected missing blocks in the reviewed baseline comparison; other modeled injections receive no E4 response in that summary. Rules remain broad screening heuristics.
- **Coverage ablation:** E1-only and E1+E4 cover 160/160 units; E1+E2 and E1+E2+E4 cover 145/160; E1+E3 and the full E1+E2+E3+E4 combination cover 0/160 because E3 evidence is unavailable. This measures coverage only.
- **Test-report reconciliation:** the latest full-suite run located in `TESTING_REPORT.md` records 98 passed, 0 failed and 0 skipped; Phase 0 separately records 84. The 140-passed figure supplied in the request was not corroborated by repository documentation in this checkpoint.
- **Field evidence:** Phase 1A–1C acquired provider metadata and inspected an adapter, but no real observation rows were retrieved and no empirical E3 comparison was completed.
