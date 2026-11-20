# Phase 15 UI/UX Validation Checklist

- [ ] Inspect the prior UI implementation and test reports, five page renderers, map, playback, CSV validation, and existing tests.
- [ ] Exercise Home, Model, Research, Experiments, and About at 1440×900, 768×1024, and 390×844; capture page screenshots.
- [ ] Verify map marker selection, details, close/switch behavior, timestamp alignment, missing/unavailable states, and marker policy where browser tooling permits.
- [ ] Verify timeline range, play/pause, previous/next, speed, bounds, gaps, and synchronization between map, charts, and station details.
- [ ] Exercise CSV cases A–E without running inference or retraining.
- [ ] Check keyboard focus, accessible names, status/error messaging, and empty/missing artifact states.
- [ ] Fix only reproduced UI defects; add regression tests using existing dependencies.
- [ ] Run the full suite, app startup check, configured lint/type checks, and `git diff --check`; compare against 241 tests and 5 subtests.
- [ ] Write acceptance and refinement reports; save screenshots in `docs/ui_ux_validation/{Desktop,Tablet,Mobile}`.
- [ ] Confirm no commit, push, merge, dataset changes, or research-result changes.
