# Phase 14 IEEE Paper Revision Report

## Source audit

- Existing paper used as the structural and content source: `final_report/WeatherGuard_AI_Complete_IEEE_Research_Paper.docx` (with the paired source PDF inspected for prior pagination only).
- IEEE template found and inspected: `D:/Download/ieee-format.docx`. No `ieee-format(1).docx` was found in the checked Downloads, Desktop, or repository locations.
- Consolidated findings were taken from `research_results/phase13_research_synthesis/PHASE13_FINAL_RESEARCH_SYNTHESIS.md`, the Phase 13 claims/results/traceability registers, Phase 01–11 evidence cited by those registers, and authoritative Phase 12 run `research_results/phase12_evidence_contribution/20261119T144632Z/`.
- Phase 12 numbers and plots were checked against the timestamped report, summary JSON, overlap, coverage, sensitivity and E3 CSVs. The original paper’s embedded figures/tables were preserved; four Phase 12 figures and two editable Word tables were added.

## Revision approach

The title was narrowed to “Provenance-Aware Evidence Review…” because the prior “event-level verification” phrasing could imply validated event truth that the project does not have. The abstract and discussion now state the evidence boundary directly: anomaly does not equal fault; no fault labels exist; predictive performance is unknown; E3 is decision-ineligible; E1 duplicates the saved baseline signal; E2 is descriptive; E4 has zero supporting flags; and the 42/100,980 parity mismatch remains unexplained.

The paper retains the existing nine-section IEEE conference structure, author name, original experimental summaries, and reference list. New Phase 12 sections distinguish paired indicator association from validation and explain why zero category changes follow from the unchanged baseline-derived policy. Reference [7] was corrected to match the title associated with its DOI.

## Formatting and production

The revised DOCX was created as a separate editable file. Word section properties were aligned to the inspected template: A4 page size, one-column title/author block, and two-column abstract/body. The PDF was exported from that revised DOCX and rasterized at 90 dpi for visual review. All six final pages were inspected. Figure 8 and its caption remain together; the Phase 12 E3 table is no longer split.

One minor layout issue remains: the Fig. 12 caption wraps across a column break. It is noted in `PHASE14_FINAL_VALIDATION.md`; the figure and caption are readable, but the caption should be tightened before submission. The author affiliation and city/country fields also remain explicit placeholders pending author confirmation.

## Scope boundary

No models were retrained, no observations were downloaded, and no application, thresholds, assessment policy, historical experiment output, source paper, or template was modified. No commit, push, or merge was made.
