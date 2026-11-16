# Next-stage implementation plan

## Delivered in this stage

- Five-workspace Streamlit application foundation: Command Center, Research Studio, Investigation Studio, Experiment Lab, and Model Evaluation.
- Read-only artifact loaders and prediction grid checks.
- Explicit manual baseline model execution, separated from historical saved predictions.
- Observation selection shared through Streamlit session state.
- E1–E4 panels with explicit support/conflict/unavailable/no-detected states; spatial state remains unavailable for adjudication where no validated threshold/provenance exists.
- Literature summaries and comparison matrix for five source papers, with DOI/publisher links and BibTeX.
- AppTest smoke checks and research data-contract tests.

## Remaining stages

1. Diagnose why current local model regeneration differs from saved Phase 03 predictions at 42 of 100,980 cells; do not hide or replace saved predictions.
2. Implement and validate the full synthetic campaign (all specified variables/fault types, temporal evaluation, versioned outputs, reproducibility, unaffected windows) and connect the remaining controls.
3. Complete Phase 02 using primary and neighboring station exports, coordinates/elevation, retrieval parameters, provider metadata, package version, and Drive/read-back hashes.
4. Validate an integrated evidence rule with explicit source states and tests; continue to abstain until independent spatial provenance and decision rules are defensible.
5. Implement the eight evidence ablations and sensitivity study after E1–E4 inputs are available.
6. Complete literature full-text review and references; the current five-paper summaries use publisher/institution metadata and accessible abstracts/sections, and are not an exhaustive systematic review.
7. Add executable UI results export, complete experiment history browser, and page-level workflow checks for missing artifacts and controlled experiments.
8. Capture actual running application screenshots and prepare a demo scenario only after local server validation.
