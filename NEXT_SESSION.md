# Next Session Handoff — Research Completion Roadmap (2026-11-17)

## Verified baseline

- PR #2 is merged. Refreshed `main`: `852bc34e76ef4e5de15e48f0f1402f7bf0e9c1d1`.
- Final PR head: `c51ab63e7aa47f386d0f4c08e28576be153f18d0`; PR-head GitHub Actions run #15 succeeded.
- Full suite: 84 passed, 0 failed, 0 skipped. Compileall and `git diff --check` passed.
- Phase 01: 44,879 observations, 36,434 train rows and 8,415 test rows; source hashes and schemas verified.
- Phase 03: all 11 manifest-listed CSV outputs pass hashes, row counts and ordered-column checks; this is artifact identity, not historical generation provenance.
- PR #2 campaign: five contexts/eight scenarios, reviewed E2 and baseline review outputs verify; historical outputs remain frozen.
- Baseline verification report: `PHASE0_BASELINE_VERIFICATION.md`.

## Current research limits and next dependencies

No traceable raw observation exports or source/retrieval metadata are bundled for VILD0 or neighbors 42099, 42101, 42105 and 42096. Reported coordinates/distances and coverage are not verified. No independent maintenance, fault, normal-operation or regional-event adjudication set exists. Therefore do not run empirical E3, claim real-world accuracy, perform outcome-level ablation, or use E1–E4 outputs to create reference labels.

Next: obtain source-backed station inventory, raw primary/neighbor exports and retrieval metadata; separately obtain maintenance/operator records and independent regional event references. Preserve raw inputs and hashes before cleaning. Then audit temporal coverage/missingness and alignment, and implement E3 with explicit unavailable states. Continue to preserve all saved predictions and synthetic outputs.
