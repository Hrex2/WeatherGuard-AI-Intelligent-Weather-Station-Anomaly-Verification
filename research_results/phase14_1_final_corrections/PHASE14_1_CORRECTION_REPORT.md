# Phase 14.1 Correction Report

## Source selection

The requested `/mnt/data/WeatherGuard_AI_IEEE_Revised(1).docx` was not present in the available filesystem. I used the latest repository copy, `research_results/phase14_ieee_paper_revision/WeatherGuard_AI_IEEE_Revised.docx`, as the correction source. The original Phase 14 DOCX/PDF were not overwritten. Phase 12 evidence was read from the authoritative run `research_results/phase12_evidence_contribution/20261119T144632Z/`.

## Corrections made

1. **Figure 14 replaced.** The previous source in `scripts/run_phase12_analysis.py` plotted `assessment_changes_vs_P0` as ordinary bars. Every value is zero, so the plot rendered axes without visible marks. The replacement, `fig14_assessment_stability_corrected.png`, shows the category counts and an explicit “0 category changes” callout for ten configurations of 8,415 timestamps each. Its generator verifies the counts and zero-change values against `phase12_summary.json` before writing the image. The caption states that stability follows the fixed baseline-derived policy and does not establish component equivalence.
2. **Author metadata retained transparently.** Repository text search found the existing placeholders but no confirmed author institution, department, or location. `[Institution to be confirmed]` and `[City, Country]` remain; no affiliation was inferred.
3. **Synthetic terminology clarified.** The abstract now says “160 synthetic injection units.” Table III is explicitly titled as the E1 synthetic response at 8/12; the Figure 8 caption identifies E4 missing-block flags separately. Both captions state that these are synthetic results, not field performance.
4. **Figure 12/Table VI layout corrected.** The Figure 12 graphic and caption are separate consecutive paragraphs, kept together, with left alignment and spacing before Table VI. The caption retains the interpretation that joint negatives dominate agreement and overlap is descriptive, not independent validation.
5. **Section VIII heading spacing corrected.** The numbered heading list now uses a space after its Roman numeral; the same numbering style applies consistently to the other Roman-numeral headings.
6. **Figure 14 caption simplified.** Duplicate policy wording was removed while retaining the fixed-policy caveat.

## Numerical verification

The Phase 12 summary reports 8,415 timestamps and ten configurations (P0–P6, L1–L3), each covering 8,415 timestamps. All configurations report zero category changes versus P0 and P4. Category totals are 123 SUSPICIOUS, 8,292 INSUFFICIENT_EVIDENCE, zero NORMAL, and zero ANOMALOUS. The updated figure generator asserts those values and stops if the authoritative summary differs.

The six Word table cell sets in the corrected paper were compared with the Phase 14 source and were identical. No research result, threshold, dataset, Phase 12 output, or assessment policy was changed. The revised paper continues to state E1’s baseline dependency, E2’s 1,661 descriptive flags, E3’s zero decision-eligible independent observations, E4’s zero positive support flags in the evaluated window, and the unresolved 42/100,980 prediction mismatches. It does not claim predictive performance or validated fault detection. ANOMALY ≠ FAULT remains prominent.

## Output and scope

The corrected editable file is `WeatherGuard_AI_IEEE_Final_Corrected_v2.docx`; its PDF was exported from that DOCX. The final PDF has six A4 pages. No model was trained, weather data were downloaded, application code or thresholds were changed, or Phase 12 output was overwritten. No commit or push was made.
