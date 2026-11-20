$ErrorActionPreference = 'Stop'
$source = (Resolve-Path 'research_results/phase14_ieee_paper_revision/WeatherGuard_AI_IEEE_Revised.docx').Path
$outDir = (Resolve-Path 'research_results/phase14_1_final_corrections').Path
$docx = Join-Path $outDir 'WeatherGuard_AI_IEEE_Final_Corrected_v2.docx'
$fig14 = Join-Path $outDir 'fig14_assessment_stability_corrected.png'
Copy-Item -LiteralPath $source -Destination $docx -Force

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open($docx, $false, $false)

function Find-Selection([string]$text) {
    $selection = $word.Selection
    $selection.SetRange(0, $doc.Content.End)
    $find = $selection.Find
    $find.ClearFormatting()
    $find.Text = $text
    $find.Forward = $true
    $find.Wrap = 0
    if (-not $find.Execute()) { throw "Text not found: $text" }
    return $selection
}

# Make the synthetic denominator explicit in the abstract.
$abstractUnit = Find-Selection '160 synthetic cases'
$abstractUnit.Text = '160 synthetic injection units'

# Distinguish Table III (E1) from the separate E4 results in Figure 8.
$tableTitle = Find-Selection 'TABLE III. CORRECTED SYNTHETIC RESPONSE AT E1 8/12'
$tableTitle.Text = 'TABLE III. E1 SYNTHETIC RESPONSE AT 8/12 CONSENSUS'
$fig8Caption = Find-Selection 'Corrected five-context synthetic response at E1 8/12 and broad E4 screen; injected-unit fractions, not field performance.'
$fig8Caption.Text = 'Scenario-level E1 response at 8/12 and separate E4 missing-block flags. Synthetic injection units only; not field sensitivity or fault-detection accuracy.'

# Replace the zero-height-only chart while retaining the existing caption paragraph.
$fig14Caption = Find-Selection 'Assessment-category stability across Phase 12 evidence configurations.'
$fig14Paragraph = $fig14Caption.Paragraphs.Item(1)
if ($fig14Paragraph.Range.InlineShapes.Count -ne 1) { throw 'Figure 14 paragraph did not contain exactly one inline image.' }
$oldFigure = $fig14Paragraph.Range.InlineShapes.Item(1)
$oldStart = $oldFigure.Range.Start
$oldFigure.Delete()
$imageRange = $doc.Range($oldStart, $oldStart)
$newFigure = $doc.InlineShapes.AddPicture($fig14, $false, $true, $imageRange)
$newFigure.LockAspectRatio = -1
$newFigure.Width = 228.95
$fig14Caption = Find-Selection 'Assessment-category stability across Phase 12 evidence configurations.'
$fig14CaptionStart = $fig14Caption.Start
$fig14CaptionEnd = $fig14Caption.Paragraphs.Item(1).Range.End - 1
$fig14Caption.SetRange($fig14CaptionStart, $fig14CaptionEnd)
$fig14Caption.Text = 'Assessment-category counts and zero changes under the fixed baseline-derived policy. Stability does not demonstrate equal component utility.'
$fig14Format = $fig14Caption.Paragraphs.Item(1).Range.ParagraphFormat
$fig14Format.Alignment = 0
$fig14Format.LeftIndent = 0
$fig14Format.FirstLineIndent = 0
$fig14Format.RightIndent = 0
$fig14Format.KeepTogether = -1
$fig14Format.SpaceAfter = 4

# Keep the Phase 12 overlap heatmap and its explanatory caption intact and apart from Table VI.
$fig12Caption = Find-Selection 'Paired support-indicator overlap for E1, E2, and E4.'
$fig12CaptionStart = $fig12Caption.Start
$fig12CaptionEnd = $fig12Caption.Paragraphs.Item(1).Range.End - 1
$fig12Caption.SetRange($fig12CaptionStart, $fig12CaptionEnd)
$fig12Caption.Text = 'Paired support-indicator overlap for E1, E2, and E4; joint negatives dominate agreement, so overlap is descriptive, not independent validation.'
$fig12Paragraph = $fig12Caption.Paragraphs.Item(1)
if ($fig12Paragraph.Range.InlineShapes.Count -ne 1) { throw 'Figure 12 paragraph did not contain exactly one inline image.' }
$fig12Paragraph.Range.InlineShapes.Item(1).LockAspectRatio = -1
$fig12Paragraph.Range.InlineShapes.Item(1).Width = 228.95
$breakAt = $fig12Paragraph.Range.InlineShapes.Item(1).Range.End
$doc.Range($breakAt, $breakAt).InsertParagraphAfter()
$fig12Caption = Find-Selection 'Paired support-indicator overlap for E1, E2, and E4; joint negatives dominate agreement, so overlap is descriptive, not independent validation.'
$fig12CaptionParagraph = $fig12Caption.Paragraphs.Item(1).Range
for ($i = 2; $i -le $doc.Paragraphs.Count; $i++) {
    if ($doc.Paragraphs.Item($i).Range.Start -eq $fig12CaptionParagraph.Start) {
        $doc.Paragraphs.Item($i - 1).Range.ParagraphFormat.KeepWithNext = -1
        break
    }
}
$fig12Format = $fig12CaptionParagraph.ParagraphFormat
$fig12Format.Alignment = 0
$fig12Format.LeftIndent = 0
$fig12Format.FirstLineIndent = 0
$fig12Format.RightIndent = 0
$fig12Format.KeepTogether = -1
$fig12Format.SpaceBefore = 0
$fig12Format.SpaceAfter = 6
$table6Heading = Find-Selection 'TABLE VI. PHASE 12 E3 COVERAGE AND ASSESSMENT STATUS'
$table6Heading.Paragraphs.Item(1).Range.ParagraphFormat.KeepWithNext = -1
$table6Heading.Paragraphs.Item(1).Range.ParagraphFormat.SpaceBefore = 4

# Set a space after Roman-numeral list labels for consistent IEEE section headings.
$limitationsHeading = Find-Selection 'Limitations and Threats to Validity'
$headingPara = $limitationsHeading.Paragraphs.Item(1).Range
if ($headingPara.ListFormat.ListType -ne 0) {
    $headingPara.ListFormat.ListTemplate.ListLevels.Item(1).TrailingCharacter = 1
}

$doc.Save()
$doc.Close(0)
$word.Quit()
Write-Output "Wrote $docx"
