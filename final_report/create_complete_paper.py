from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pathlib import Path
from copy import deepcopy

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'final_report'; FIG=OUT/'ieee_figures'
TEMPLATE=Path(r'C:\Users\Dell\OneDrive\Desktop\wg_ieee_tmp\ieee-format-canonical.docx')
DOCX=OUT/'WeatherGuard_AI_Complete_IEEE_Research_Paper.docx'
doc=Document(str(TEMPLATE)); ps=doc.paragraphs
ps[0].text='Uncertainty-Aware Event-Level Verification of Weather Station Anomalies Using Model Stability, Temporal Consistency and Spatial Evidence'; ps[0].style='paper title'
for i in [1,2,3,5,6,7,8,9]: ps[i].text=''
ps[4].text='Harnoor Singh Thiara\n[Institution to be confirmed]\n[City, Country]'
ps[10].text=('Abstract—Automated weather-station anomaly screens can identify unusual records, but unusualness alone does not establish sensor failure. This study presents WeatherGuard AI, an uncertainty-aware, event-level framework that keeps model stability (E1), temporal consistency (E2), spatial corroboration (E3), and physical plausibility (E4) as separately interpretable evidence dimensions. We audit a processed five-year-plus weather series, saved prediction artifacts, controlled synthetic experiments, and a multi-phase station-provenance investigation. The processed dataset contains 44,879 rows, with 44,849 feature-ready rows; a chronological split contains 36,434 training and 8,415 test rows separated by a seven-day gap. E1 agreement thresholds select 432, 214, 123, 51, and 15 candidate timestamps at 4/12 through 12/12 agreement. A corrected synthetic campaign spans five selected contexts and eight injection scenarios; at 8/12 agreement, scenario response ranges from 0% to 100%. These are controlled response fractions, not field recall. For E3, source-level station comparisons exist, but provider lineage, sensor independence, and independent event adjudication remain insufficient; the event-validation outcome is INSUFFICIENT_INDEPENDENT_DATA. E3 is excluded from classifier voting. A reproducibility audit finds 42 mismatched cells among 100,980 saved prediction cells, all associated with Isolation Forest, with cause unresolved. Evidence supports candidate screening and an auditable research workflow, not calibrated fault diagnosis or validated operational performance.')
ps[10].style='Abstract'; ps[11].text='Index Terms—Anomaly detection, meteorological quality control, uncertainty, data provenance, station validation, spatial corroboration.'; ps[11].style='Keywords'; ps[12].text='Introduction'; ps[12].style='Heading 1'
for p in list(doc.paragraphs[13:89]): p._element.getparent().remove(p._element)
anchor=next(p for p in doc.paragraphs if p.text.startswith('IEEE conference templates contain guidance'))
# Keep title/author and abstract/index terms full width; start the two-column body after Index Terms.
break_ps=[p for p in doc.paragraphs if '<w:sectPr' in p._p.xml]
for bp in break_ps:
    sp=bp._p.find('.//'+qn('w:sectPr')); c=sp.find(qn('w:cols'))
    if c is None: c=OxmlElement('w:cols'); sp.append(c)
    c.set(qn('w:num'),'1' if bp is not anchor else '2'); c.set(qn('w:space'),'720' if bp is not anchor else '360')
    for ref in list(sp):
        if ref.tag in (qn('w:headerReference'),qn('w:footerReference')): sp.remove(ref)
abstract_end=doc.paragraphs[11]._p
ppr=abstract_end.get_or_add_pPr(); new_sect=deepcopy(anchor._p.find('.//'+qn('w:sectPr')))
cols=new_sect.find(qn('w:cols')); cols.set(qn('w:num'),'1'); cols.set(qn('w:space'),'720'); ppr.append(new_sect)
for t in list(doc.tables): t._element.getparent().remove(t._element)
for p in doc.paragraphs:
    for e in p._p.xpath('.//w:drawing|.//w:pict|.//w:object'): e.getparent().remove(e)
for s in doc.sections:
    for part in [s.footer,s.first_page_footer,s.even_page_footer,s.header,s.first_page_header,s.even_page_header]:
        for p in part.paragraphs: p.text=''
new=[]
def P(txt,style='Body Text'):
    p=doc.add_paragraph(style=style); p.add_run(txt); new.append(p._p); return p
def H(txt,n=1): return P(txt,f'Heading {n}')
def F(file,caption,w=3.18):
    p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.add_run().add_picture(str(FIG/file),width=Inches(w)); new.append(p._p)
    p=P(caption); p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY; p.paragraph_format.space_after=Pt(4); p.paragraph_format.first_line_indent=Inches(0)
    for r in p.runs: r.font.size=Pt(7.5)
def T(title,heads,rows,widths=None):
    p=P(title); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for r in p.runs: r.bold=True; r.font.size=Pt(8)
    t=doc.add_table(rows=1,cols=len(heads)); t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.autofit=False
    for j,v in enumerate(heads): t.rows[0].cells[j].text=v
    for row in rows:
        c=t.add_row().cells
        for j,v in enumerate(row): c[j].text=str(v)
    for ri,row in enumerate(t.rows):
        pr=row._tr.get_or_add_trPr(); pr.append(OxmlElement('w:cantSplit'))
        if ri==0:
            sh=OxmlElement('w:tblHeader'); sh.set(qn('w:val'),'true'); pr.append(sh)
            for c in row.cells:
                x=OxmlElement('w:shd'); x.set(qn('w:fill'),'DCE6EC'); c._tc.get_or_add_tcPr().append(x)
        for j,c in enumerate(row.cells):
            c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            if widths: c.width=Inches(widths[j])
            for p in c.paragraphs:
                p.paragraph_format.space_after=Pt(0); p.paragraph_format.line_spacing=1
                if ri < len(t.rows)-1: p.paragraph_format.keep_with_next=True
                for r in p.runs: r.font.size=Pt(7)
    new.append(t._tbl)

# I. Introduction
P('Weather stations provide observations for weather monitoring, climate analysis, and local decision support. Records can contain abrupt spikes, gradual drift, stuck values, missing blocks, and physically implausible combinations. Automated screening is valuable, but a statistical anomaly is only a departure from a learned or specified reference. It is not, by itself, evidence of sensor failure. We adopt the rule ANOMALY ≠ FAULT: a candidate requires contextual evidence and, where evidence is insufficient, the system should abstain from a fault conclusion.')
P('Meteorological quality control combines range, step, persistence, internal-consistency, and spatial checks. Network studies emphasize metadata, instrument exposure, maintenance, calibration, and quality flags alongside algorithms [1]–[4]. Unsupervised methods add scalable screening, but their outputs depend on representation, parameter settings, training period, and contamination by faults [5]–[9]. We assess an evidence workflow that exposes model stability, temporal history, spatial context, and physical plausibility as distinct dimensions rather than claiming a new universally accurate detector.')
P('This repository-grounded study audits saved E1/E2 summaries and synthetic responses, traces the multi-phase E3 provenance investigation, and reports an unresolved reproducibility discrepancy. Findings are separated into artifact-level facts, provisional descriptive evidence, and unresolved questions. Fig. 1 summarizes the evidence flow; Fig. 2 defines E1–E4.')
F('fig01_system_architecture.png','Fig. 1. WeatherGuard AI evidence flow and validation boundary. E2–E4 remain separate evidence records; E3 does not vote in or change classifier flags. Schematic, not measured performance.')

# II. Related Work
H('Related Work')
P('Fiebrich et al. describe mesoscale observation procedures, including limits, temporal behavior, and spatial consistency [1]. Estévez et al. review validation of automatic weather-station measurements and sensor-specific procedures [2]. Network standardization emphasizes metadata and harmonized QC conventions for cross-network comparison [3]. Later work identifies ongoing QA/QC challenges in heterogeneous meteorological time series [4], [10]. These studies motivate treating source lineage and variable semantics as part of the evidence.')
P('Isolation Forest isolates observations through random partitioning [5]; Local Outlier Factor compares local density with neighboring records [6]; and One-Class SVM estimates a boundary around training data [7]. These methods do not estimate fault probability without appropriate labels and calibration. General anomaly and time-series surveys document the dependence of results on task definitions, data, and evaluation protocols [8], [9]. WeatherGuard uses configuration agreement as E1 stability, not calibrated confidence.')
P('Spatial agreement is not a universal truth condition: real gradients, elevation, siting, sensor height, sampling intervals, and shared upstream products affect inter-station comparisons. E3 eligibility therefore depends on source identity, time, variable comparability, and independence. This is a focused narrative review, not a systematic search or meta-analysis.')

# III. Dataset and Data Provenance
H('Dataset and Data Provenance')
P('The primary modeling artifact, `verified_phase01/model_df.csv`, is a processed historical series covering 2021-01-05 through 2026-03-09. It is not a newly reconstructed raw dataset. Counts verify saved artifacts; upstream instrument identity and every prior transformation are not independently established.')
T('TABLE I. PRIMARY MODELING DATA AND SAVED PARTITION',['Quantity','Value'],[('Processed rows','44,879'),('Feature-ready rows','44,849'),('Training rows','36,434'),('Held-out test rows','8,415'),('Temporal separation','7 days'),('Prediction cells','100,980'),('Missing precipitation entries','6')],[2.1,1.25])
P('Table I reports artifact dimensions, not independent observations of sensor quality. The chronological split ends training at 2025-03-14 23:30 local time and starts testing at 2025-03-21 23:30. The seven-day gap reduces immediate leakage but does not ensure independence across regimes. Fig. 3 shows monthly processed-row distribution and missingness.')
F('fig03_dataset_coverage_missingness.png','Fig. 3. Monthly row coverage and missing-cell counts in the processed series. Dashed line marks the held-out segment after the seven-day gap; this does not represent raw-provider completeness.')
P('Phase 4 Meteostat 2.2.3 source-stratified collection disabled model filling, fill, and cleaning [12]. It contained 567 rows for WMO 42099 and 1,719 for WMO 42101, with 562 exact UTC timestamp overlaps. Phase 6 retrieved 1,390 VILD0 source rows (1,021 unique timestamps): 1,002 METAR and 388 GHCNh source rows with timestamp overlap. These are source-exposed records, not original provider payloads or proof of instrument independence. Fig. 4 plots record-level coordinates and row coverage; coordinates do not establish exact sensor positions.')
P('A legacy notebook used Meteostat 1.7.6 without explicit `model` or `flags`; the inspected API default enabled model data, and row-level source markers were absent from its reported 6,024-row-per-station output. No matching saved raw dataset was found in the repository. It cannot be reconciled as a direct-observation dataset with later source-stratified exports. Version, filling, method, date range, export path, or indexing may explain differences; no single cause is established.')
P('Meteostat VILD0 resolves to Ludhiana Airport (ICAO VILD) and a NOAA GHCNh record, not a surveyed sensor coordinate. WMO 42099 is a Ludhiana record; WMO 42101 is Patiala [13]. No VILD0–42099 alias or sensor relation is verified. Cross-source matching found likely mirrored/repackaged data, including 981 exact VILD METAR/GHCNh overlaps and a Patiala mirror pattern. Provisional zones are A 0–10 km, B 10–50 km, C 50–100 km, D 100–250 km, E >250 km; they are configurable boundaries, not validated radii. Only A and C occur in the current comparison.')
P('Phase 11 IEM returned 31 raw METAR-text records across five of eight event dates; three dates had no records. IEM uses multi-source downstream ingestion and documents its data as-is [11]; raw reports did not consistently provide unique provider identifiers. Two provisional archive-copy links and zero provider-ID-confirmed links were established. No independent event adjudication was completed. All eight events remain NOT_ADJUDICATED; latest outcome is INSUFFICIENT_INDEPENDENT_DATA.')
F('fig04_station_distribution_coverage.png','Fig. 4. Station-record locations and source-level row counts in Phases 4/6. Sensor siting and source independence are unverified; zones are provisional.')

# IV. Framework
H('Proposed WeatherGuard AI Framework')
P('WeatherGuard treats an anomaly as a candidate event accompanied by evidence records. An evidence ledger stores source, time, variable, quality/comparability, support or conflict status, and missingness. UNAVAILABLE is missing or ineligible evidence; CONFLICTING is disagreement from a comparable source; SUPPORTING is evidence consistent with the stated screen. These states are not diagnoses. Fig. 2 depicts this separation.')
F('fig02_e1_e4_framework.png','Fig. 2. E1–E4 dimensions and interpretation limits. Components remain separate; E3 is outside classifier voting and is not validated for event adjudication here.')
H('E1: Model Stability',2); P('E1 summarizes agreement among 12 configurations: four each for Isolation Forest (IF), Local Outlier Factor (LOF), and One-Class SVM (OCSVM). A timestamp is a candidate when the number of flags meets a selected threshold. Agreement measures sensitivity to these configurations, not probability or independent voting; models share data, features, and timestamps.')
H('E2: Temporal Consistency',2); P('E2 compares candidates with prior same-station history under configurable window, mode, minimum-observation, and deviation settings. SUPPORTING, NO_DETECTED_EVIDENCE, CONFLICTING, and UNAVAILABLE describe screen outcomes. No detected evidence is not evidence of station health; insufficient history is not a negative result.')
H('E3: Spatial Corroboration',2); P('E3 compares eligible observations across stations by variable and time. Eligibility requires lineage, compatible units/report semantics, acceptable timestamp alignment, and adequate independence. Exact and tolerance-window matches are separate. Regional agreement may contextualize a signal; disagreement needs spatial representativeness and measurement uncertainty. E3 records context only and cannot alter classifier flags.')
H('E4: Physical Plausibility',2); P('E4 applies broad bounds, missingness, and selected cross-variable checks. Rules require sensor-, unit-, climate-, and instrument-specific validation. A violation does not distinguish sensor failure from transmission error, conversion error, or rare real conditions.')
H('Event interpretation and abstention',2); P('The event-level unit is a bounded candidate episode, not one flag. The evidence ledger supports review, but no integrated fault threshold is validated. Without independent evidence or adjudicated reference, the result remains uncertain or unadjudicated.')

# V. Methodology
H('Methodology and Experimental Design')
P('The analysis was artifact-first: saved CSVs, manifests, reports, source code, and documentation were inspected; figures were generated from saved artifacts. No model was retrained, no weather observations were downloaded for this drafting task, and historical outputs were not overwritten. Results distinguish processed-data description, saved screen output, synthetic response, and provenance/coverage investigation. None yields adjudicated fault performance.')
H('E1 and E2 analyses',2); P('The saved grid contains 12 configurations × 8,415 test timestamps = 100,980 cells. E1 thresholds are 4/12 through 12/12; none was selected using independent labels. The E2 sensitivity file spans 123 candidates, five windows (1, 3, 6, 12, 24 h), three cutoffs (2.5, 3.5, 4.5), and two modes, totaling 3,690 combinations. A separate paired synthetic comparison has 2,880 units per condition.')
H('Synthetic campaign',2); P('Five selected contexts and eight injections—dewpoint inconsistency, gradual drift, intermittent noise, missing block, persistent offset, point drop, point spike, stuck sensor—form 160 context × scenario × injected-time units. We report corrected 8/12 E1 response and between-context ranges. Fixed injections do not estimate field recall or generalize to unobserved stations or fault patterns.')
H('E3 and E4 evaluation',2); P('Exact UTC matches are separated from tolerance matches, and valid-value pairs from common timestamps. Phase 6 comparisons failed the lineage eligibility gate. Phase 9 selected eight events; none was suitable for event validation. Phases 10/11 obtained no provider-ID-confirmed independently adjudicated fault or clean event. E4 uses saved broad physical-screen responses. Parity mismatches are reported without relabeling historical outputs or inferring a cause.')

# VI. Results
H('Experimental Results')
H('Dataset and station coverage',2); P('The primary table has 44,879 rows, 44,849 feature-ready; train/test partitions have 36,434/8,415 rows. Six precipitation cells are missing; engineered history features also have boundary missingness before feature-ready filtering. In Phase 6, station-record coordinates put VILD0 2.2699 km from 42099 (zone A) and 76.0392 km from 42101 (zone C). Exact source-stratified valid pairs: VILD0 METAR vs 42099 ISD-Lite—65 each for temperature, RH, wind speed, pressure; vs 42101 ISD-Lite—67 each. VILD0 METAR vs 42101 GHCNh—3 each for temperature, RH, wind speed, 113 pressure. VILD0 GHCNh vs 42101 GHCNh—117 each for temperature, RH, wind speed. No exact dewpoint, wind-direction, or precipitation pairs. Independence remains unestablished.')
H('E1 stability and thresholds',2); P('E1 candidates decline with stricter agreement: 432 at 4/12, 214 at 6/12, 123 at 8/12, 51 at 10/12, 15 at 12/12. Table II and Fig. 5 show family sensitivity: at least one/all four settings flag 521/94 IF, 635/182 LOF, and 575/157 OCSVM timestamps. Family counts overlap and are not true-positive rates.')
T('TABLE II. E1 MODEL-FAMILY CANDIDATE COUNTS',['Family','≥1 config.','All 4'],[('Isolation Forest','521','94'),('Local Outlier Factor','635','182'),('One-Class SVM','575','157')],[1.7,.8,.8])
F('fig05_model_family_candidate_counts.png','Fig. 5. Held-out timestamps flagged by at least one or all four configurations within each family (n=8,415); counts overlap and lack independent labels.')
H('E2 temporal results',2); P('At 6 h and cutoff 3.5, real-time mode reports 47 SUPPORTING and 76 NO_DETECTED_EVIDENCE across 123 E1 candidates. Retrospective mode reports 43 SUPPORTING, 76 NO_DETECTED_EVIDENCE, and 4 CONFLICTING. At 1 h, all are UNAVAILABLE under the minimum-three-observation rule. Fig. 6 and Fig. 7 present E1/E2 sensitivity and monthly candidate distribution.')
F('fig06_e1_e2_sensitivity.png','Fig. 6. E1 threshold counts and E2 sensitivity by history window and mode. E2 pooled statuses are descriptive, not adjudicated outcomes.')
F('fig07_monthly_candidate_distribution.png','Fig. 7. Monthly counts of saved 8/12 E1 candidate timestamps in Asia/Kolkata time. Candidate frequency is not fault prevalence.')
H('Synthetic response and E4',2); P('At E1 8/12, response is 100% for dewpoint inconsistency (15 units), point drops (5), and point spikes (5); 6.7% for intermittent noise (30) and persistent offset (30); and 0% for gradual drift (30), missing block (15), and stuck sensor (30). Table III gives the full corrected scenario summary. Across-context range is 0–16.7% for the two 6.7% scenarios; other outcomes are uniform in the summary. The E4 direct screen flags missing-block injections (100%) and none of the other selected cases. These small, selected synthetic units are not field sensitivity or recall.')
T('TABLE III. CORRECTED SYNTHETIC RESPONSE AT E1 8/12',['Scenario','Units','E1 mean'],[('Dewpoint inconsistency','15','100%'),('Gradual drift','30','0%'),('Intermittent noise','30','6.7%'),('Missing block','15','0%'),('Persistent offset','30','6.7%'),('Point drop','5','100%'),('Point spike','5','100%'),('Stuck sensor','30','0%')],[1.8,.65,.75])
F('fig09_synthetic_e1_e4_response.png','Fig. 8. Corrected five-context synthetic response at E1 8/12 and broad E4 screen; injected-unit fractions, not field performance.')
H('E3 spatial findings',2); P('Table IV reports Phase 4 exact-match neighbor differences for WMO 42099–42101: 562 overlapping timestamps. Phase 9 VILD METAR FM-15 vs Patiala FM-12: temperature n=595 (435 QC-good), bias +0.0437 °C, RMSE 1.508; dewpoint n=595 (456 QC-good), +2.280 °C, RMSE 3.251; wind speed n=594 (457 QC-good), −0.409 m/s, RMSE 1.038. Direction n=465, circular mean difference −8.18°, RMSE 64.27°. RH unavailable/derived; precipitation semantics incompatible; altimeter and sea-level pressure are not directly comparable. No preregistered tolerance, sensor linkage, independent lineage, or adjudicated reference exists; these are not event-level validation.')
T('TABLE IV. PHASE 4 EXACT-UTC NEIGHBOR COMPARISON',['Variable','Valid n','Bias','RMSE'],[('Temperature','560','−0.444 °C','1.927 °C'),('Relative humidity','560','+5.211 pp','10.657 pp'),('Wind speed','561','−1.112 km/h','4.433 km/h'),('Pressure','562','+1.003 hPa','1.177 hPa')],[1.22,.6,.8,.8])
F('fig08_e3_pair_coverage_heatmap.png','Fig. 9. Exact valid-pair coverage by source-stratified pair and variable in Phase 6. Pair counts are not common-index counts; independence is unestablished; tolerance matches are excluded.')
F('fig10_event_reference_status.png','Fig. 10. Reference acquisition and adjudication for eight events. None is independently adjudicated; decision: INSUFFICIENT_INDEPENDENT_DATA.')
H('Prediction parity',2); P('The parity investigation finds 42 mismatches among 100,980 cells, all associated with IF: 6, 4, 12, and 20 across its four settings. LOF and OCSVM match. Cause is unresolved; persisted labels are retained. Current evidence does not distinguish stochastic behavior, version changes, missing fitted-state artifacts, or pipeline differences.')

# VII. Discussion
H('Discussion')
P('The findings show why a detector candidate and its contextual evidence must remain separate. E1 exposes configuration sensitivity but no optimal threshold; E2 depends on history and screen settings; E4 flags missing blocks under the saved broad rules. None supplies independent fault truth. Spatial distance, overlap, or similarity does not prove independent instruments; disagreement does not prove fault because local weather and measurement differences can be real.')
P('E3 has two distinct outcomes: descriptive station comparisons exist and are reportable with units/counts/caveats, but Phase 9 is DESCRIPTIVE_ONLY and latest Phase 10/11 event adjudication is INSUFFICIENT_INDEPENDENT_DATA. E3 must remain outside classifier voting. An interface should distinguish unavailable from conflicting and supporting evidence and never convert missing observations into negative evidence. Current findings support research and human review, not automated maintenance decisions or fault probabilities.')

# VIII. Limitations
H('Limitations and Threats to Validity')
P('Upstream provenance, raw provider payloads, and station-to-sensor identity are incomplete; the legacy retrieval used model-filled defaults. The model target is unusualness, not adjudicated fault. E1/E2 are uncalibrated against independent labels, and configurations share features and data. Synthetic validity is limited to eight patterns, five contexts, and selected magnitudes/timestamps; results are not field precision, recall, or sensitivity.')
P('E3 is limited by uncertain sensor independence, sites, instruments, exposure, history, provider lineage, and semantics. Small pair counts and nonharmonized quality flags further limit inference. Eight events lack independent adjudication; E3 performance is not estimable. Zone radii are provisional. Reproducibility is qualified by the 42/100,980 IF mismatch and incomplete estimator/scaler provenance. Software tests cannot substitute for scientific replication. The latest recorded local suite passed 214 tests and five subtests; a CI missing-pytest failure was patched in workflow dependencies, but post-fix CI success was unavailable at drafting. This is software status only. The literature is narrative, and no prospective deployment, calibration, or operational utility evaluation was performed.')

# IX. Conclusion
H('Conclusion and Future Work')
P('WeatherGuard AI organizes anomaly review around E1 model stability, E2 temporal consistency, E3 spatial context, and E4 physical plausibility. Saved artifacts verify dataset/split counts, screen outcomes, synthetic responses, and the parity discrepancy; they do not establish field fault-detection accuracy. The scientific boundary remains ANOMALY ≠ FAULT. E3 descriptive comparisons exist, but independent provenance and adjudicated references remain insufficient; its event-level decision is INSUFFICIENT_INDEPENDENT_DATA and it remains isolated from classifier voting.')
P('Future work should retrieve traceable observations and report identifiers; verify sensors and station histories; establish coverage, pair validity, and variable semantics; and independently adjudicate events under a prespecified protocol. Only then should E3 and combined evidence be evaluated for fault-level precision, recall, calibration, abstention quality, and utility across stations/seasons. The 42 mismatches must remain visible until resolved.')
H('Acknowledgment',5); P('The author acknowledges maintainers of project open-source tools and providers of station metadata/archive interfaces. Data providers did not adjudicate events. [Institutional acknowledgment and funding to be confirmed.]')
H('References',5)
refs=[
'C. A. Fiebrich, C. R. Morgan, A. G. McCombs, P. K. Hall, and R. A. McPherson, “Quality assurance procedures for mesoscale meteorological data,” J. Atmos. Oceanic Technol., vol. 27, no. 10, pp. 1565–1582, 2010, doi: 10.1175/2010JTECHA1433.1.',
'J. Estévez, P. Gavilán, and J. V. Giráldez, “Guidelines on validation procedures for meteorological data from automatic weather stations,” J. Hydrol., vol. 402, nos. 1–2, pp. 144–154, 2011, doi: 10.1016/j.jhydrol.2011.02.031.',
'C. A. Fiebrich et al., “Toward the standardization of mesoscale meteorological networks,” J. Atmos. Oceanic Technol., vol. 37, no. 11, pp. 2033–2049, 2020, doi: 10.1175/JTECH-D-20-0078.1.',
'B. Faybishenko et al., “Challenging problems of quality assurance and quality control (QA/QC) of meteorological time series data,” Stoch. Environ. Res. Risk Assess., vol. 36, pp. 1049–1062, 2022, doi: 10.1007/s00477-021-02106-w.',
'F. T. Liu, K. M. Ting, and Z.-H. Zhou, “Isolation forest,” in Proc. 8th IEEE Int. Conf. Data Mining, 2008, pp. 413–422, doi: 10.1109/ICDM.2008.17.',
'M. M. Breunig, H.-P. Kriegel, R. T. Ng, and J. Sander, “LOF: Identifying density-based local outliers,” in Proc. ACM SIGMOD Int. Conf. Management of Data, 2000, pp. 93–104, doi: 10.1145/335191.335388.',
'B. Schölkopf, R. C. Williamson, A. J. Smola, J. Shawe-Taylor, and J. C. Platt, “Support vector method for novelty detection,” Neural Comput., vol. 13, no. 7, pp. 1443–1471, 2001, doi: 10.1162/089976601750264965.',
'N. Chandola, A. Banerjee, and V. Kumar, “Anomaly detection: A survey,” ACM Comput. Surv., vol. 41, no. 3, Art. no. 15, 2009, doi: 10.1145/1541880.1541882.',
'A. Blázquez-García, A. Conde, U. Mori, and J. A. Lozano, “A review on outlier/anomaly detection in time series data,” ACM Comput. Surv., vol. 54, no. 3, Art. no. 56, pp. 1–33, 2022, doi: 10.1145/3444690.',
'M. Stawowy, W. Olchowik, A. Rosiński, and T. Dąbrowski, “The analysis and modelling of the quality of information acquired from weather station sensors,” Remote Sens., vol. 13, no. 4, Art. no. 693, 2021, doi: 10.3390/rs13040693.',
'Iowa Environmental Mesonet, “ASOS-AWOS-METAR data download,” Iowa State University, online archive documentation. [Online]. Available: https://mesonet.agron.iastate.edu/request/download.phtml?network=TM__ASOS. Accessed: Nov. 19, 2026.',
'Meteostat, “Hourly data API,” Meteostat Python documentation. [Online]. Available: https://dev.meteostat.net/python/api/meteostat.hourly. Accessed: Nov. 19, 2026.',
'India Meteorological Department, “WIS2 station catalogue,” online station metadata service. [Online]. Available: https://wis2box.imd.gov.in/oapi/collections/stations/items?f=html. Accessed: Nov. 19, 2026.'
]
for x in refs:
    p=P(x,'references'); p.paragraph_format.keep_together=True
for el in new: anchor._p.addprevious(el)
for r in anchor.runs: r.text=''
for p in doc.paragraphs:
    if p.style.name.startswith('Heading'): p.paragraph_format.keep_with_next=True
doc.core_properties.title='Uncertainty-Aware Event-Level Verification of Weather Station Anomalies Using Model Stability, Temporal Consistency and Spatial Evidence'; doc.core_properties.author='Harnoor Singh Thiara'; doc.core_properties.subject='WeatherGuard AI research paper; artifact-grounded results and limitations'
doc.save(str(DOCX)); print(DOCX,'paragraphs',len(doc.paragraphs),'tables',len(doc.tables),'sections',len(doc.sections))
