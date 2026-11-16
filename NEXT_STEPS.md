# Next steps

1. Resolve the 42-cell local/saved Phase 03 prediction mismatch. Record sklearn, NumPy, pandas, and model implementation versions from the original run if available. Reproduce the saved 12-configuration prediction table exactly before interpreting changes against it.
2. Extend the reusable campaign to dewpoint, humidity, precipitation, wind speed, and pressure offsets with justified magnitudes and explicit physical-screening intent.
3. Add temperature step, drift, stuck-value, repeated-value, seeded noise, and short dropout experiments. Enforce segment and timestamp-gap constraints and verify propagation using hand-calculated fixtures.
4. Add complete experiment registry, configuration, observation, event, propagation, prediction-change, unaffected-window, and run-manifest outputs for each campaign type.
5. Supply the original primary and neighbor observation files plus retrieval/read-back metadata. Then implement the Phase 02 inventory, actual cadence/gaps/missingness, timestamp alignment, hash, software version, and provenance confidence report. Do not initiate downloads implicitly.
6. Integrate actual E1–E4 rows with explicit `SUPPORTED`, `NOT_SUPPORTED`, `UNAVAILABLE`, `CONFLICTING`, and `NOT_EVALUATED` states, preserving unavailable values.
7. Implement and execute the eight evidence ablations and sensitivity checks only after synthetic ground truth and evidence inputs are aligned.
8. Update README, PROJECT_STATUS, experiment registry, decision log, record, and notebook execution sections after validated outputs exist.
9. Verify in Colab against the same snapshot hashes and record Colab environment and outputs separately from this local run.
