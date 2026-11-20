# WeatherGuard AI IEEE Research Paper v4 — Revision Summary

## Deliverables

- `WeatherGuard_AI_IEEE_Research_Paper_v4.pdf` — final review copy.
- `WeatherGuard_AI_IEEE_Research_Paper_v4.docx` — editable Word source.
- `qa/page-1.png` through `qa/page-7.png` — rendered pages used for layout inspection.

The v4 paper retains the v3 title, section structure, IEEE-style two-column A4 layout, all 14 figures, all six tables, and the existing 13 references. The v3 source files were not changed. The PDF renders to seven pages; all pages were inspected for layout, legibility, captions and reference placement.

## Changes made

- Added Harnoor Singh Thiara and Nisha Majumder as coauthors with the shared affiliation supplied by the authors.
- Revised the abstract and clarified the contribution as a provenance-aware evidence review, not a validated fault detector.
- Expanded the method description to state the 44,879 processed rows, 44,849 feature-ready rows, chronological 36,434/8,415 split, seven-day gap, 11 features, and 12 saved model configurations.
- Kept the real-series E2 analysis (123 candidates, five windows, three cutoffs, two modes) separate from the 2,880 synthetic pair-setting rows.
- Clarified that Jaccard overlap describes agreement rather than correctness; the 8/12 threshold is descriptive, not calibrated.
- Retained the E3 result of zero decision-eligible independent observations and explained the source-lineage and temporal-alignment limitations.
- Clarified that E4 screening is not calibration or diagnosis, and that synthetic injection and coverage-ablation results are not real-world performance measures.
- Preserved the unresolved 42/100,980 prediction-cell mismatch and avoided assigning a cause.
- Strengthened the discussion, limitations, and future work while retaining the principle “ANOMALY ≠ FAULT.”

## Verification and remaining author attention

The Word source contains 14 inline figures and six tables. The exported PDF is seven A4 pages. The final review did not run models, download data, or generate new experimental results. Technical claims were checked against the repository evidence and Phase 12/13/14.1 reports. Reference verification relies on the earlier Phase 14 audit; no new external bibliography search was performed for this revision.

Before submission, the authors should confirm the spelling/order of names and the supplied affiliation, add any required funding or acknowledgment details, and check the final reference metadata and access dates against the venue requirements. The substantive research gaps remain: no independently adjudicated real sensor-fault labels, no independent decision-eligible E3 evidence, incomplete end-to-end operational integration, and unresolved prediction parity mismatches. The paper therefore makes no real-world fault-detection accuracy claim.
