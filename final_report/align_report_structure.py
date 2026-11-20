from pathlib import Path

path = Path(__file__).with_name('WeatherGuard_AI_Preliminary_Research_Report.md')
text = path.read_text(encoding='utf-8')
text = text.replace('# WeatherGuard AI Intelligent Weather Station Anomaly Verification',
                    '# WeatherGuard AI Uncertainty Aware Event Level Verification of Weather Station Anomalies')
text = text.replace('**Report date:** 17 November 2026', '**Report date:** 18 November 2026')

contents = '''## Contents

1. Introduction  
2. Research Problem and Objectives  
3. Literature Review  
4. Dataset and Preprocessing  
5. Proposed Methodology  
6. Experimental Design  
7. Results  
8. System Implementation  
9. Discussion  
10. Limitations  
11. Future Work  
12. Conclusion  
References  
Appendices and Reproducibility Information

## Figures

1. WeatherGuard AI evidence architecture and E1–E4 framework  
2. E1 consensus threshold sensitivity  
3. E1 model-family candidate counts  
4. Corrected five-context synthetic scenario response  
5. E2 status distribution by paired condition  
6. Evidence availability ablation

## Tables

1. Snapshot and chronological split  
2. E1 consensus counts  
3. E1 family-level candidates  
4. Corrected context response at 8/12 E1 consensus  
5. E2 paired status counts  
6. Evidence availability ablation  
7. Evidence status by research phase
'''
start = text.index('## Contents')
end = text.index('## Abbreviations')
text = text[:start] + contents + '\n' + text[end:]

heading_map = {
    '# 2. Literature Review': '# 3. Literature Review',
    '## 2.1 Meteorological quality control': '## 3.1 Meteorological quality control',
    '## 2.2 Time-series anomaly detection': '## 3.2 Time-series anomaly detection',
    '## 2.3 Evidence fusion and research gap': '## 3.3 Evidence fusion and research gap',
    '## 2.4 Literature review method': '## 3.4 Literature review method',
    '# 3. Dataset and Preprocessing': '# 4. Dataset and Preprocessing',
    '## 3.1 Processed historical snapshot': '## 4.1 Processed historical snapshot',
    '## 3.2 Chronological partition and model preprocessing': '## 4.2 Chronological partition and model preprocessing',
    '## 3.3 Data integrity and provenance': '## 4.3 Data integrity and provenance',
    '## 3.4 Station acquisition readiness and E3 status': '## 4.4 Station acquisition readiness and E3 status',
    '# 4. Proposed Methodology': '# 5. Proposed Methodology',
    '## 4.1 Evidence framework': '## 5.1 Evidence framework',
    '## 4.2 Integrated interpretation and abstention': '## 5.2 Integrated interpretation and abstention',
    '# 5. Experimental Design': '# 6. Experimental Design',
    '## 5.1 Historical prediction analysis': '## 6.1 Historical prediction analysis',
    '## 5.2 Controlled synthetic studies': '## 6.2 Controlled synthetic studies',
    '## 5.3 E2 paired synthetic study': '## 6.3 E2 paired synthetic study',
    '## 5.4 Baseline comparison and availability ablation': '## 6.4 Baseline comparison and availability ablation',
    '## 5.5 Distinguishing experiment types': '## 6.5 Distinguishing experiment types',
    '# 6. Results': '# 7. Results',
    '## 6.1 Dataset characteristics': '## 7.1 Dataset and model configuration',
    '## 6.2 Model configuration and E1 stability': '## 7.2 E1 threshold analysis',
    '## 6.3 E2 temporal sensitivity': '## 7.3 E2 temporal findings',
    '## 6.4 Five-context synthetic response': '## 7.4 Five-context synthetic fault campaign',
    '## 6.5 Model-family comparison': '## 7.5 Model-family response comparison',
    '## 6.6 E2 paired status results': '## 7.6 E2 paired comparison',
    '## 6.7 E4 screening response': '## 7.7 E4 screening findings',
    '## 6.8 Corrected synthetic baseline comparison': '## 7.8 Synthetic baseline analysis',
    '## 6.9 Evidence coverage ablation': '## 7.9 Evidence availability ablation',
    '## 6.10 Prediction parity discrepancy': '## 7.10 Prediction parity issue',
    '# 7. System Implementation': '# 8. System Implementation',
    '## 7.1 Application architecture': '## 8.1 Application architecture',
    '## 7.2 Services and research modules': '## 8.2 Services and research modules',
    '## 7.3 Software verification': '## 8.3 Software verification',
    '## 7.4 Evidence display and uncertainty': '## 8.4 Evidence display and uncertainty',
    '# 8. Discussion': '# 9. Discussion',
    '# 9. Limitations and Future Work': '# 10. Limitations',
    '## 9.1 Limitations': '',
    '## 9.2 Prioritized next work': '# 11. Future Work',
    '# 10. Conclusion': '# 12. Conclusion',
    '# References': '# 13. References',
    '# Appendices': '# 14. Appendices and Reproducibility Information',
}
for old, new in heading_map.items():
    text = text.replace(old, new)

# Add the three named algorithm explanations requested in the drafting prompt.
anchor = '### E1: model stability\n'
algorithm_text = '''### Isolation Forest

Isolation Forest identifies observations that can be isolated from the feature sample by relatively short paths through random partitions [8]. It contributes one unsupervised view of unusualness. Its binary saved flags are not estimates of sensor-failure probability.

### Local Outlier Factor

LOF compares an observation's local density with the density of its neighbors [9]. The neighborhood size and feature scaling affect which observations appear locally sparse. The project evaluates four neighborhood settings and interprets their outputs as configuration-sensitive candidates.

### One-Class SVM

One-Class SVM estimates a boundary around the training distribution and flags observations outside the estimated support [10]. Its `nu` parameter influences the boundary and expected outlier fraction. In the saved project protocol, this family uses training-fitted scaling; incomplete archived fit provenance limits exact historical reproduction.

'''
if algorithm_text not in text:
    text = text.replace(anchor, algorithm_text + anchor, 1)

# Keep six analytical figures, in report order, with captions and source notes.
figure_specs = {
    'fig01_architecture.png': (1, 'WeatherGuard AI evidence architecture and E1–E4 framework. E3 is pending empirical data; the interpretation categories are proposed, not validated.',
        'Source: audited project architecture and evidence modules at the Phase 1C checkpoint. The diagram distinguishes available components from pending spatial observations; it does not report model performance.'),
    'fig04_e1_consensus_threshold.png': (2, 'E1 candidate counts by configuration-agreement threshold. The denominator is 8,415 saved test timestamps; no independent outcome labels are available.',
        'Source: `research_results/e1_threshold_sensitivity.csv`; evidence claims E1T1–E1T5. This chart shows threshold sensitivity, not an optimized decision boundary.'),
    'fig05_e1_family_comparison.png': (3, 'Unique test timestamps flagged by at least one or all four settings within each model family.',
        'Source: `research_results/e1_family_comparison.csv`; evidence claims E1F1–E1F3. These are saved unlabeled candidate counts, not comparative accuracy.'),
    'fig06_synthetic_scenario_response.png': (4, 'Corrected context response at E1 8/12. Bars show five-context means; whiskers show the minimum–maximum context response. Synthetic injections only.',
        'Source: corrected `baseline_review_1/synthetic_baseline_response_summary.csv`, filtered to `E1_consensus` and `8/12`; claims SC01–SC08. Context fractions are computed before their across-context mean and range.'),
    'fig07_e2_paired_status.png': (5, 'E2 status distribution for same-time unmodified readings and synthetic faulted readings. Each condition contains 2,880 setting-level evaluations.',
        'Source: reviewed `e2_multicontext_fault_detail.csv`, grouped by condition and status. Rows repeat 160 underlying pair IDs across 18 settings; SUPPORTING is not a fault diagnosis.'),
    'fig10_evidence_coverage.png': (6, 'Fraction of 160 synthetic experimental units with required evidence available for each combination. This is coverage, not outcome utility.',
        'Source: corrected `baseline_review_1/evidence_coverage_ablation_summary.csv`; denominator 160 context × scenario × injected-timestamp units. Coverage cannot establish decision accuracy.'),
}
lines = text.splitlines()
out=[]
for line in lines:
    if line.startswith('!['):
        src=line.rsplit('(',1)[-1].rstrip(')')
        name=src.split('/')[-1]
        if name not in figure_specs:
            continue
        n, caption, source = figure_specs[name]
        out.append(f'![Figure {n}. {caption}]({src})')
        out.append('')
        out.append('**' + source.split(':',1)[0] + ':**' + source.split(':',1)[1])
        out.append('')
        continue
    out.append(line)
text='\n'.join(out)+'\n'

# Keep prose figure references consistent with the selected six figures.
text=text.replace('(Table 2; Figure 3)', '(Table 2; Figure 2)')
text=text.replace('(Table 3; Figure 4)', '(Table 3; Figure 3)')
text=text.replace('(Table 5; Figure 9)', '(Table 6; Figure 6)')

# Clarify that E2's 2,880 observations are repeated setting rows, not independent event pairs.
text=text.replace('There are 2,880 paired comparisons across conditions, modes and settings.',
                  'There are 2,880 paired setting-level rows across conditions, modes and settings; they represent 160 underlying pair IDs repeated over 18 settings, not 2,880 independent events.')
text=text.replace('Among 2,880 same-time pairs, the status changed after injection in 1,008 (35.0%).',
                  'Among 2,880 paired setting-level rows, status changed after injection in 1,008 (35.0%). The underlying 160 pair IDs recur across 18 settings, so the row proportion is descriptive and not an independent-event estimate.')
text=text.replace('Status changed in 1,008 pairs;', 'Status changed in 1,008 setting-level rows;')

path.write_text(text, encoding='utf-8')
print('Aligned report headings, figure set and methodology subsections.')
