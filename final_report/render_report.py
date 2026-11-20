from pathlib import Path
import html, re

root=Path(__file__).resolve().parent
source=root/'WeatherGuard_AI_Preliminary_Research_Report.md'
lines=source.read_text(encoding='utf-8').splitlines()

def inline(s):
    s=html.escape(s).replace('BREAK_SENTINEL','<br/>')
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    s=re.sub(r'\*([^*]+)\*',r'<em>\1</em>',s)
    s=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'<a href="\2">\1</a>',s)
    return s

out=[]; i=0; para=[]; list_type=None
def flush_para():
    global para
    if para:
        out.append('<p>'+inline(' '.join(para))+'</p>'); para=[]
def close_list():
    global list_type
    if list_type: out.append(f'</{list_type}>'); list_type=None

while i<len(lines):
    line=lines[i]
    if not line.strip(): flush_para(); close_list(); i+=1; continue
    if line.startswith('|'):
        flush_para(); close_list(); rows=[]
        while i<len(lines) and lines[i].startswith('|'):
            cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-{3,}:?',c) for c in cells): rows.append(cells)
            i+=1
        if rows:
            out.append('<table><thead><tr>'+''.join(f'<th>{inline(c)}</th>' for c in rows[0])+'</tr></thead><tbody>')
            for row in rows[1:]: out.append('<tr>'+''.join(f'<td>{inline(c)}</td>' for c in row)+'</tr>')
            out.append('</tbody></table>')
        continue
    m=re.match(r'^(#{1,3})\s+(.*)',line)
    if m:
        flush_para(); close_list(); level=len(m.group(1)); text=m.group(2)
        cls=' class="cover-title"' if level==1 and i<3 else ''
        out.append(f'<h{level}{cls}>{inline(text)}</h{level}>'); i+=1; continue
    if line.startswith('!['):
        flush_para(); close_list(); m=re.match(r'!\[(.*?)\]\((.*?)\)',line)
        if m:
            alt=html.escape(m.group(1)); src=html.escape(m.group(2)); out.append(f'<figure><img src="{src}"/><figcaption>{alt}</figcaption></figure>')
        i+=1; continue
    if line.startswith('> '):
        flush_para(); close_list(); out.append('<blockquote>'+inline(line[2:])+'</blockquote>'); i+=1; continue
    if re.match(r'^\d+\.\s+',line):
        flush_para()
        if list_type!='ol': close_list(); out.append('<ol>'); list_type='ol'
        out.append('<li>'+inline(re.sub(r'^\d+\.\s+','',line))+'</li>'); i+=1; continue
    if line.startswith('- '):
        flush_para()
        if list_type!='ul': close_list(); out.append('<ul>'); list_type='ul'
        out.append('<li>'+inline(line[2:])+'</li>'); i+=1; continue
    if re.fullmatch(r'---+',line.strip()): flush_para(); close_list(); out.append('<hr/>'); i+=1; continue
    para.append(line.strip()+(' BREAK_SENTINEL ' if line.endswith('  ') else '')); i+=1
flush_para(); close_list()
body='\n'.join(out)
# Cover page content followed by a clean page break.
body=body.replace('<h2>Abstract</h2>','<p style="page-break-before:always"></p><h2>Abstract</h2>',1)
doc='''<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page { size: 8.5in 11in; margin: .78in .78in .75in .78in; }
body { font-family: Cambria, Georgia, serif; font-size: 10.5pt; line-height: 1.28; color:#192633; }
h1 { font-family: Arial,sans-serif; color:#174A70; font-size:20pt; margin:24pt 0 10pt; page-break-before:always; }
h1.cover-title { page-break-before:avoid; font-size:25pt; line-height:1.18; margin:80pt 0 18pt; color:#163D59; text-align:center; }
h2 { font-family: Arial,sans-serif; color:#174A70; font-size:15pt; margin:20pt 0 8pt; page-break-after:avoid; }
h3 { font-family: Arial,sans-serif; color:#218C8D; font-size:11.5pt; margin:14pt 0 5pt; page-break-after:avoid; }
p { margin:0 0 8pt; text-align:justify; }
table { border-collapse:collapse; width:100%; margin:10pt 0 14pt; font-size:8.5pt; page-break-inside:auto; }
tr { page-break-inside:avoid; }
th { background:#174A70; color:white; font-family:Arial,sans-serif; text-align:left; }
td,th { border:0.5pt solid #D9D9D9; padding:5pt 6pt; vertical-align:middle; }
tbody tr:nth-child(even) { background:#EFF5F8; }
figure { text-align:center; margin:12pt 0 15pt; page-break-inside:avoid; }
img { width:6.35in; height:auto; }
figcaption { font-size:8.5pt; color:#425563; font-style:italic; margin-top:5pt; }
blockquote { margin:12pt 22pt; color:#2D4658; font-style:italic; }
li { margin:0 0 4pt; }
.pagebreak { page-break-before:always; }
code { font-family:Consolas,monospace; font-size:9pt; }
a { color:#174A70; text-decoration:none; }
</style></head><body>'''+body+'</body></html>'
(root/'WeatherGuard_AI_Preliminary_Research_Report.html').write_text(doc,encoding='utf-8')
print('HTML generated')
