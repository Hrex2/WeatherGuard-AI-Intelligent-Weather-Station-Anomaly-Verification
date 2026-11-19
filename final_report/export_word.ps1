$ErrorActionPreference = 'Stop'
$base = (Resolve-Path (Join-Path $PSScriptRoot '.')).Path
$html = Join-Path $base 'WeatherGuard_AI_Preliminary_Research_Report.html'
$docx = Join-Path $base 'WeatherGuard_AI_Preliminary_Research_Report.docx'
$pdf = Join-Path $base 'WeatherGuard_AI_Preliminary_Research_Report.pdf'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Open($html, $false, $true)
$abstractRange = $doc.Content.Duplicate
$abstractFind = $abstractRange.Find
$abstractFind.Text = 'Abstract'
if ($abstractFind.Execute()) { $abstractRange.Collapse(1); $abstractRange.InsertBreak(7) }
foreach ($section in $doc.Sections) {
    $section.PageSetup.PageWidth = 612
    $section.PageSetup.PageHeight = 792
    $section.PageSetup.TopMargin = 54
    $section.PageSetup.BottomMargin = 54
    $section.PageSetup.LeftMargin = 58
    $section.PageSetup.RightMargin = 58
    $footer = $section.Footers.Item(1).Range
    $footer.ParagraphFormat.Alignment = 1
    $footer.Text = 'WeatherGuard AI | Preliminary Research Report | '
    $end = $footer.Duplicate
    $end.Collapse(0)
    $doc.Fields.Add($end, 33) | Out-Null
}
$doc.SaveAs2($docx, 16)
$doc.ExportAsFixedFormat($pdf, 17)
$doc.Close(0)
$word.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) | Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
Write-Output "Created $docx and $pdf"
