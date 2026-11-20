$ErrorActionPreference='Stop'
$docx=(Resolve-Path 'research_results/phase14_ieee_paper_revision/WeatherGuard_AI_IEEE_Revised.docx').Path
$fig=(Resolve-Path 'research_results/phase14_ieee_paper_revision/figures').Path
$word=New-Object -ComObject Word.Application
$word.Visible=$false; $word.DisplayAlerts=0
$doc=$word.Documents.Open($docx,$false,$false)
function Set-ParaText($index,$text){ $p=$doc.Paragraphs.Item($index); $r=$p.Range.Duplicate; $r.End=$r.End-1; $r.Text=$text }
function Find-Text($text){ $sel=$word.Selection; $sel.SetRange(0,$doc.Content.End); $f=$sel.Find; $f.ClearFormatting(); $f.Text=$text; $f.Forward=$true; $f.Wrap=0; if(-not $f.Execute()){throw "Could not find text: $text"}; return $sel }
function Set-StyleForText($text,$style){$sel=Find-Text $text; $pr=$sel.Paragraphs.Item(1).Range; try{$pr.ListFormat.RemoveNumbers()}catch{}; $pr.Style=$style}

Set-ParaText 1 'Provenance-Aware Evidence Review of Weather-Station Anomalies Using Model Stability, Temporal Consistency, and Spatial Context'
$abstract='Abstract—An unusual weather-station reading does not prove a sensor fault. We audit WeatherGuard AI, which records model stability, temporal screening, spatial comparisons, and physical checks separately. On 8,415 held-out timestamps and 160 synthetic cases, E1 duplicates baseline votes, E2 flags 1,661 timestamps, E4 flags none, and E3 has no eligible independent observations. The baseline-driven policy marks 123 suspicious and 8,292 insufficient. Forty-two of 100,980 predictions disagree; the cause is unresolved. Without adjudicated fault labels, performance is unknown. This work contributes an auditable evidence-review method.'
Set-ParaText 11 $abstract
Set-ParaText 16 'This repository-grounded study examines the saved baseline, temporal and physical screens, controlled synthetic responses, and a multi-phase spatial-provenance investigation. Phase 12 tests evidence coverage, overlap, dependency, and ablation while preserving the baseline policy. Results distinguish verified artifact counts from descriptive signals and unresolved validation gaps. Figures 1–2 summarize the framework; Figures 11–14 and Tables V–VI report the Phase 12 evidence analysis.'
Set-ParaText 20 'Fiebrich et al. describe mesoscale observation procedures, including limits, temporal behavior, and spatial consistency [1]. Estévez et al. review validation procedures for automatic weather-station measurements [2]. Network standardization emphasizes metadata, sensor siting, maintenance, and harmonized quality assurance [3]. Faybishenko et al. discuss challenges in quality assurance and processing of heterogeneous meteorological time series [4], while Stawowy et al. model information quality from weather-station sensors [10]. These studies motivate treating source lineage and variable semantics as part of the evidence.'
Set-ParaText 72 'The event-level unit is a bounded candidate episode, not one flag. In Phase 12, SUSPICIOUS follows the saved 8/12 baseline candidate flag; all other timestamps are INSUFFICIENT_EVIDENCE. No NORMAL, ANOMALOUS, or fault label is assigned. E2 and E4 do not vote, and descriptive E3 is decision-ineligible. Without independent evidence or adjudicated reference, the result remains uncertain or unadjudicated.'
Set-ParaText 76 'The saved grid contains 12 configurations × 8,415 test timestamps = 100,980 cells. E1 thresholds are 4/12 through 12/12; none was selected using independent labels. The E2 sensitivity file spans 123 candidates, five windows (1, 3, 6, 12, 24 h), three cutoffs (2.5, 3.5, 4.5), and two modes, totaling 3,690 combinations. A separate E2 synthetic paired review contains 2,880 setting-level rows across 18 settings, with 160 underlying pair identifiers repeated across settings; those rows are not independent experimental units.'
Set-ParaText 106 'Across all 8,415 held-out timestamps, E2 produced 1,661 SUPPORTING flags. Forty-seven coincide with the 123 baseline/E1 8-of-12 candidates; 1,614 lie outside that candidate set. Paired support-indicator agreement is 79.9%, positive Jaccard is 0.027, and phi is 0.057. Agreement is largely due to joint negatives. The candidate-conditioned 6 h analysis reports 47 of 123 E1 candidates as supporting; this subset view is not an additional 47 cases and is not event validation.'
Set-ParaText 153 'Source-level spatial comparisons remain descriptive. Phase 04 temperature, humidity, wind, and pressure summaries compare Meteostat-returned 42099 and 42101 records, without proving original-report or instrument independence. Phase 09 variable comparisons likewise were not eligible for candidate-event validation. In Phase 12, 123 candidates had neighbor-indexed descriptions but none was decision-eligible: of 246 neighbor rows, 32 had exact timestamps, 61 had nonzero offsets, and 153 lacked an offset; median absolute available offset was 60 min. Independent lineage remains unverified (Fig. 13 and Table VI).'
Set-ParaText 185 'The parity investigation identifies 42 mismatches among 100,980 saved prediction cells, all associated with Isolation Forest; the four settings contribute 6, 4, 12, and 20 mismatches. LOF and One-Class SVM cells match in that comparison. The cause is unresolved. We retain the historical outputs and make no claim of exact reproducibility.'
Set-ParaText 187 'The results support conservative screening and evidence accounting, not fault diagnosis. E1 summarizes the same saved model labels as the baseline: Phase 12 found identical vote counts and 8/12 flags for all 8,415 timestamps. It therefore adds no separately identified input in this implementation. E2 supplies a distinct temporal-screen profile (1,661 support flags), but its validity and incremental predictive value are unknown without independent adjudicated events. Paired association statistics are descriptive and do not show that the evidence sources are independent.'
Set-ParaText 188 'E3 cannot yet provide validated independent spatial corroboration. Earlier phases document station-record comparisons and limited report-system distinctions, but exact sensor lineage, independent source identity, variable comparability, event-level alignment, and adjudication are incomplete. E3 remains decision-ineligible and outside classifier voting. E4 produced no positive flags and found no missing measured-variable values in the Phase 12 window; this outcome neither proves that observations were fault-free nor establishes that the screen is ineffective. Ablation category stability follows from a decision rule that remains baseline-driven; evidence profiles change and zero category changes do not imply component equivalence.'
Set-ParaText 190 'The primary series is a processed snapshot. Its manifest verifies file integrity and split dimensions, not original provider lineage or instrument history. The legacy Meteostat notebook omitted explicit model and flags settings; its 6,024-row outputs cannot be reconciled to later source-stratified exports or treated as direct observations. Independent, provider-identified and independently adjudicated sensor-fault labels are unavailable. Consequently, accuracy, precision, recall, F1, false-alarm rate, and fault-detection performance are not estimable.'
Set-ParaText 191 'Further limitations include E1 dependence on baseline labels, shared processed primary-station inputs for E2/E4, zero E4 positive flags in the evaluated window, unresolved E3 source independence and timestamp alignment, one principal station, one temporal holdout, and synthetic injections on five selected contexts. The 42/100,980 Isolation Forest mismatches remain unexplained. The 8/12 threshold and screening rules are not independently calibrated. Future studies require raw reports with stable identifiers, verified station and sensor histories, prespecified event adjudication, cross-station and forward-time evaluation, and a reproducibility audit of estimator and preprocessing artifacts before performance claims.'
Set-ParaText 193 'WeatherGuard AI establishes a provenance-aware workflow for conservative review of suspicious weather-station observations. It keeps configuration stability, temporal screening, physical checks, and spatial context distinguishable; documents when evidence is missing or ineligible; and exposes structural dependence in the saved model screen. The present artifacts do not establish validated event-level spatial corroboration, sensor-fault detection, or superior predictive accuracy. ANOMALY ≠ FAULT.'
Set-ParaText 194 'Next work should obtain provenance-verified independent station observations, preserve provider report identifiers and instrument metadata, adjudicate candidate events under a prespecified protocol, resolve the Isolation Forest parity mismatch, and evaluate calibrated screens across stations and time. These are proposed experiments, not completed results.'
Set-ParaText 196 'The author acknowledges the maintainers of project software and the providers of station metadata and archive interfaces. The inspected materials do not establish institutional affiliation, funding, or event adjudication by these providers; these statements require author confirmation before submission.'
$ref7=Find-Text 'Support vector method for novelty detection'; $ref7.Text='Estimating the Support of a High-Dimensional Distribution'

# Match the IEEE template: single-column title and one author; two-column abstract/body.
$doc.Sections.Item(2).PageSetup.TextColumns.SetCount(1)
foreach($n in @(4,5)){$doc.Sections.Item($n).PageSetup.TextColumns.SetCount(2)}

$discussion=Find-Text 'Discussion'
$block=@"
Phase 12: Evidence Contribution, Dependency, and Ablation
The authoritative run evaluated the same 8,415 held-out timestamps without retraining, threshold tuning, or external data. E1 and baseline vote counts and candidate flags were identical at every timestamp. E2 generated 1,661 support flags; E4 generated none and found no missing values in this window. E3 had zero decision-eligible observations. Component associations below describe paired indicators, not accuracy or independent evidence.
TABLE V. PHASE 12 PAIRED SUPPORT INDICATORS
[TABLE_PHASE12_COMPONENTS]
Table V reports matched timestamps; “left-only/right-only” follows the pair order. E4 has a constant-zero support indicator, so phi is undefined. Its zero-positive result is not evidence of ineffectiveness.
[FIG_PHASE12_E1]
Fig. 11. E1 and baseline vote dependency on the matched held-out timestamps. E1 summarizes the same 12 saved labels and the existing 8/12 screen.
[FIG_PHASE12_OVERLAP]
Fig. 12. Paired support-indicator overlap for E1, E2, and E4. Joint negatives dominate raw agreement; overlap is descriptive, not independent validation.
TABLE VI. PHASE 12 E3 COVERAGE AND ASSESSMENT STATUS
[TABLE_PHASE12_E3]
Figure 13 shows that candidate-indexed neighbor rows do not imply synchronous independent observations. Figure 14 shows category stability under the fixed baseline-derived assessment rule. Across the sensitivity configurations and leave-one-component-out comparisons, category changes were zero: 123 timestamps remained SUSPICIOUS and 8,292 remained INSUFFICIENT_EVIDENCE; none was NORMAL or ANOMALOUS. This follows from the unchanged baseline-only category policy and does not show that the evidence profiles are equivalent.
[FIG_PHASE12_E3]
Fig. 13. E3 neighbor timestamp offsets for candidate-indexed comparisons. Exact matches do not establish source independence; missing offsets remain insufficient evidence.
[FIG_PHASE12_ABLATION]
Fig. 14. Assessment-category stability across Phase 12 evidence configurations. The category rule is baseline-derived, so stability is not a test of equal evidence contribution.
"@
$discussion=Find-Text 'Discussion'; $insert=$doc.Range($discussion.Range.Start,$discussion.Range.Start); $insert.InsertBefore($block+"`r")
Set-StyleForText 'Phase 12: Evidence Contribution, Dependency, and Ablation' 'Heading 2'
Set-StyleForText 'TABLE V. PHASE 12 PAIRED SUPPORT INDICATORS' 'Body Text'
Set-StyleForText 'TABLE VI. PHASE 12 E3 COVERAGE AND ASSESSMENT STATUS' 'Body Text'
foreach($caption in @('TABLE V. PHASE 12 PAIRED SUPPORT INDICATORS','TABLE VI. PHASE 12 E3 COVERAGE AND ASSESSMENT STATUS')){$sel=Find-Text $caption; $pr=$sel.Paragraphs.Item(1).Range; $pr.Font.Name='Times New Roman'; $pr.Font.Size=8; $pr.Font.Bold=-1; $pr.ParagraphFormat.Alignment=1; $pr.ParagraphFormat.KeepWithNext=-1; $pr.ParagraphFormat.SpaceAfter=3}
Set-StyleForText 'The authoritative run evaluated the same 8,415 held-out timestamps' 'Body Text'
Set-StyleForText 'Table V reports matched timestamps' 'Body Text'
Set-StyleForText 'Figure 13 shows that candidate-indexed neighbor rows' 'Body Text'

function Replace-PlaceholderWithTable($placeholder,$data){
 $sel=Find-Text $placeholder; $range=$sel.Range; try{$range.ListFormat.RemoveNumbers()}catch{}; $range.Text=''; $range.Style='Normal'; $table=$doc.Tables.Add($range,$data.Count,$data[0].Count); $table.Borders.Enable=1; $table.AutoFitBehavior(2); $table.Range.Font.Name='Times New Roman'; $table.Range.Font.Size=7.5; $table.Range.ParagraphFormat.SpaceAfter=0; $table.Range.ParagraphFormat.SpaceBefore=0
 for($r=0;$r -lt $data.Count;$r++){for($c=0;$c -lt $data[$r].Count;$c++){$cell=$table.Cell($r+1,$c+1); $cell.Range.Text=$data[$r][$c]; try{$cell.Range.ListFormat.RemoveNumbers()}catch{}; $cell.Range.Style='Normal'; $cell.Range.Font.Name='Times New Roman'; $cell.Range.Font.Size=7.5; $cell.Range.ParagraphFormat.Alignment=1}}
 $table.Rows.Item(1).Range.Bold=-1; $table.Rows.Item(1).HeadingFormat=-1; try{$table.Rows.AllowBreakAcrossPages=0}catch{}
}
$component=@(
 @('Pair','Both positive','Left-only / right-only','Agreement / Jaccard / phi'),
 @('E1 vs. E2','47','76 / 1,614','79.9168% / 0.02706 / 0.05653'),
 @('E1 vs. E4','0','123 / 0','98.5383% / 0 / undefined'),
 @('E2 vs. E4','0','1,661 / 0','80.2614% / 0 / undefined')
)
Replace-PlaceholderWithTable '[TABLE_PHASE12_COMPONENTS]' $component
$e3=@(
 @('Measure','Phase 12 result','Interpretation'),
 @('E3 decision-eligible observations','0 / 8,415','No verified independent lineage'),
 @('Descriptive-only / insufficient','123 / 8,292','Not corroborating outcomes'),
 @('Candidate-indexed neighbor rows','246','Two neighbor IDs per candidate'),
 @('Timestamp relation','32 exact; 61 nonzero; 153 missing','Exact alignment does not prove independence'),
 @('Median absolute available offset','60 min','Available offsets only'),
 @('Assessment distribution','123 SUSPICIOUS; 8,292 INSUFFICIENT_EVIDENCE','0 NORMAL; 0 ANOMALOUS'),
 @('LOO category changes','0','Category remains baseline-driven')
)
Replace-PlaceholderWithTable '[TABLE_PHASE12_E3]' $e3
$e3Caption=Find-Text 'TABLE VI. PHASE 12 E3 COVERAGE AND ASSESSMENT STATUS'
$tableRange=$doc.Range($e3Caption.Range.End,$doc.Content.End)
for($i=1;$i -le $doc.Tables.Count;$i++){if($doc.Tables.Item($i).Range.Start -gt $e3Caption.Range.Start){$e3table=$doc.Tables.Item($i); break}}
if($e3table){for($r=1;$r -lt $e3table.Rows.Count;$r++){$e3table.Rows.Item($r).Range.ParagraphFormat.KeepWithNext=-1}}
# Prevent figure captions from splitting across columns/pages.

function Replace-PlaceholderWithImage($placeholder,$filename){
 $sel=Find-Text $placeholder; $range=$sel.Range; try{$range.ListFormat.RemoveNumbers()}catch{}; $range.Text=''; $range.Style='Normal'; $image=$doc.InlineShapes.AddPicture((Join-Path $fig $filename),$false,$true,$range); $image.LockAspectRatio=-1; $image.Width=228.95
}
Replace-PlaceholderWithImage '[FIG_PHASE12_E1]' 'fig03_e1_baseline_dependency.png'
Replace-PlaceholderWithImage '[FIG_PHASE12_OVERLAP]' 'fig02_component_overlap.png'
Replace-PlaceholderWithImage '[FIG_PHASE12_E3]' 'fig07_e3_timestamp_offsets.png'
Replace-PlaceholderWithImage '[FIG_PHASE12_ABLATION]' 'fig06_assessment_stability.png'
foreach($caption in @('Fig. 11. E1 and baseline vote dependency on the matched held-out timestamps. E1 summarizes the same 12 saved labels and the existing 8/12 screen.','Fig. 12. Paired support-indicator overlap for E1, E2, and E4. Joint negatives dominate raw agreement; overlap is descriptive, not independent validation.','Fig. 13. E3 neighbor timestamp offsets for candidate-indexed comparisons. Exact matches do not establish source independence; missing offsets remain insufficient evidence.','Fig. 14. Assessment-category stability across Phase 12 evidence configurations. The category rule is baseline-derived, so stability is not a test of equal evidence contribution.')){$sel=Find-Text $caption; $pr=$sel.Paragraphs.Item(1).Range; try{$pr.ListFormat.RemoveNumbers()}catch{}; $pr.Style='Body Text'; $pr.Font.Name='Times New Roman'; $pr.Font.Size=8; $pr.Font.Bold=0; $pr.ParagraphFormat.Alignment=0; $pr.ParagraphFormat.SpaceBefore=0; $pr.ParagraphFormat.SpaceAfter=3; $pr.ParagraphFormat.KeepWithNext=-1}
# Keep the existing Figure 8 graphic with its caption, and keep the Phase 12
# E3 table heading and full table together at the next available page start.
$fig8=Find-Text 'Fig. 8.'; $captionPara=$fig8.Paragraphs.Item(1); for($i=2;$i -le $doc.Paragraphs.Count;$i++){if($doc.Paragraphs.Item($i).Range.Start -eq $captionPara.Range.Start){$doc.Paragraphs.Item($i-1).Range.ParagraphFormat.KeepWithNext=-1; break}}
$doc.Save(); $doc.Close(0); $word.Quit()
Write-Output 'Wrote revised DOCX.'
