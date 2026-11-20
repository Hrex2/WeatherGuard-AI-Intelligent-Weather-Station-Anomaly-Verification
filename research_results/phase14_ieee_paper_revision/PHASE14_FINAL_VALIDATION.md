# Phase 14 Final Validation

## Deliverables and formatting

- Editable DOCX: `WeatherGuard_AI_IEEE_Revised.docx`
- PDF exported from that DOCX: `WeatherGuard_AI_IEEE_Revised.pdf`
- PDF page count: 6. Page geometry: A4 (595.32 × 841.92 pt).
- DOCX structure audit: 14 inline figures and 6 Word tables.
- Main paper uses IEEE-style two-column body; title/author block is single column. The document follows the available `D:/Download/ieee-format.docx`; the specifically named `ieee-format(1).docx` was not available.
- All six PDF pages were rendered to `qa/final_render_last/page-1.png` through `page-6.png` at 90 dpi and visually inspected.

## Checks passed

- No page is blank; no text overlap or clipping was observed on the six inspected pages.
- Title, abstract, index terms, section hierarchy, figures, tables, acknowledgment, and reference list are present.
- Tables V and VI remain intact; the E3 table no longer splits its final row.
- Figure 8 and its caption remain together.
- The revised PDF was regenerated from the final DOCX after correcting reference [7].
- Bibliographic metadata for references [1]–[10] was checked against publisher/DOI records; [11]–[13] were checked against the cited provider documentation/endpoints. Reference [7]’s incorrect title was corrected to match its DOI.
- Original figures and tables remain distinguishable from the four authoritative Phase 12 plots and two Phase 12 tables added in this revision.

## Remaining formatting and submission items

- Minor layout defect: the Fig. 12 caption wraps across the two-column boundary. It remains legible, but should be tightened before submission.
- `[Institution to be confirmed]` and `[City, Country]` remain in the author block. Replace only after author confirmation.
- A final author review should confirm acknowledgment wording, institutional affiliation, and the current online documentation access dates.

## Scientific limitations carried into the paper

- No independent adjudicated fault/event labels; accuracy, precision, recall, F1, false-alarm rate, and fault-detection performance are not estimable.
- E1 reproduces the saved baseline vote counts and candidate flags; it adds no identified independent input.
- E2’s 1,661 support flags and paired statistics are descriptive, not validated predictive evidence.
- E3 has zero decision-eligible independent observations; timestamp indexing does not prove source independence or corroboration.
- E4 has zero support flags in the evaluated window; this neither proves fault-free data nor screen ineffectiveness.
- The 42 of 100,980 prediction-cell mismatch, all associated with Isolation Forest, remains unexplained.
- Synthetic responses are controlled injections, not field performance; thresholds are not independently calibrated.

## Readiness

The paper is ready for academic review as an evidence-bounded research draft. It is not submission-ready until the author details and the minor Fig. 12 caption wrap are resolved and the author approves the final references and acknowledgments. No commit or push was made; source research outputs, the original paper, and the template were preserved.
