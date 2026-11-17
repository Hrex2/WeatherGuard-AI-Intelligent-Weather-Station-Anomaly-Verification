# Phase 0 Baseline Verification — 2026-11-17

## Repository checkpoint

- GitHub reports PR #2 **merged**. Refreshed and fast-forwarded local `main` to `852bc34e76ef4e5de15e48f0f1402f7bf0e9c1d1`, the merge commit for PR #2. The remote main before refresh was `0a279597c3d6cc0eed6088150bfe59ec13e7c99d`; local main was previously at `830d3159e05ae11ec310e1627359f454d456ec23`.
- The final PR #2 head was `c51ab63e7aa47f386d0f4c08e28576be153f18d0`. The PR is closed and merged, not draft or pending review.
- Started the local documentation checkpoint branch `codex/research-completion-roadmap-phase0` from refreshed `main`. Worktree was clean at branch creation.

## Verification

- `python -B -m unittest discover -s tests -v`: **84 passed, 0 failed, 0 skipped**.
- `python -m compileall -q app.py services ui src/weather_research tests scripts`: passed.
- `git diff --check`: passed.
- GitHub Actions run #15 on the final PR head `c51ab63e7aa47f386d0f4c08e28576be153f18d0`: **success** (tests, compilation, patch whitespace). The merge commit itself had no separately returned PR-triggered workflow run; PR-head CI is green.
- Direct read-only loader verification passed: Phase 01 processed observation/train/test snapshots (44,879 / 36,434 / 8,415 rows), all three SHA/shape contracts, and all 11 Phase 03 CSV identities. PR #2 artifacts verified: 40 context-scenario rows, 6,840 reviewed E2 detail rows, 3,360 baseline response detail rows, 29 baseline source inputs, and six baseline output files. No artifacts were regenerated or rewritten.

## Freeze and integrity status

Historical Phase 03 predictions, original single-context results, the multi-context campaign, reviewed E2 outputs and first-generation baseline artifacts remain unchanged. The PR #2 baseline review is separately versioned at `research_results/fault_matrix_multicontext_46ae5d119d/baseline_review_1/`. Scoped `.gitattributes` rules preserve exact manifested bytes across Windows and Linux checkouts. No integrity mismatches or missing declared artifacts were found in the verified Phase 01, Phase 03, E2 and baseline sets.

## Roadmap blockers

Phase 1 is not ready for empirical E3 construction. The archive identifies VILD0 as the primary station and lists candidate neighbors 42099, 42101, 42105 and 42096, but coordinates, provider provenance and raw station series are missing. Reported neighbor counts/distances are historical claims, not independently verified inventory. Phase 2 also lacks independent maintenance records and adjudicated regional-event/normal references. Do not infer those labels from model outputs or from the processed VILD0 snapshot. Obtain traceable raw exports and source metadata before running E3 or real-world evaluation.
