#!/usr/bin/env python3
"""
Genera INFORME.pdf a partir de INFORME.md (o el PDF de otro .md de la carpeta del proyecto).

    python tools/informe_pdf.py                          # INFORME.md -> INFORME.pdf
    python tools/informe_pdf.py LABORATORIO_HACKRF.md    # -> LABORATORIO_HACKRF.pdf

1) Convierte el Markdown a HTML (módulo `markdown`, viene con RadioConda) con estilos para hoja A4.
2) Lo imprime a PDF con Microsoft Edge en modo sin ventana (viene con Windows), usando un perfil temporal
   para no tocar el navegador del usuario.
El HTML intermedio queda en build/<nombre>.html. Las imágenes se buscan desde la carpeta del proyecto.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import markdown

ROOT = pathlib.Path(__file__).resolve().parent.parent
EDGE = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]

CSS = """
@page { size: A4; margin: 17mm 15mm 17mm 15mm;
        @bottom-center { content: counter(page) " / " counter(pages); font-size: 8pt; color: #666; } }
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; font-size: 10pt; line-height: 1.42; color: #111; }
h1 { font-size: 19pt; text-align: center; margin: 0 0 10pt 0; color: #0b3a6b; }
h2 { font-size: 14pt; color: #0b3a6b; border-bottom: 1.5px solid #0b3a6b; padding-bottom: 2pt; margin-top: 18pt;
     break-after: avoid; }
h3 { font-size: 11.5pt; color: #133f6e; margin-top: 12pt; break-after: avoid; }
p { margin: 5pt 0; text-align: justify; }
ul, ol { margin: 4pt 0 4pt 0; padding-left: 18pt; }
li { margin: 2pt 0; }
code { font-family: Consolas, "Courier New", monospace; font-size: 8.8pt; background: #f2f4f7; padding: 0 2px;
       border-radius: 2px; }
pre { font-family: Consolas, "Courier New", monospace; font-size: 7.3pt; line-height: 1.25; background: #f5f7fa;
      border: 1px solid #dde3ea; border-radius: 3px; padding: 6pt 8pt; white-space: pre; overflow: hidden;
      break-inside: avoid; }
pre code { background: none; padding: 0; font-size: inherit; }
p:has(+ ul), p:has(+ ol) { break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 8pt 0; font-size: 8.3pt; break-inside: avoid; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
th { background: #e8eef5; color: #0b3a6b; font-weight: 600; }
th, td { border: 1px solid #c9d3de; padding: 2.5pt 4pt; vertical-align: top; }
img { display: block; max-width: 100%; margin: 8pt auto 2pt auto; break-inside: avoid; }
p.caption { font-size: 8.6pt; color: #333; margin: 0 4% 10pt 4%; text-align: justify; break-before: avoid; break-inside: avoid; }
p.caption code { font-style: normal; font-size: 7.8pt; background: none; padding: 0; }
p.caption.tabla { margin: 9pt 0 2pt 0; break-before: auto; break-after: avoid; }
hr { border: none; border-top: 1px solid #ccc; margin: 10pt 0; }
.titulo p { text-align: center; margin: 2pt 0; }
h4 { font-size: 10.3pt; color: #133f6e; margin: 10pt 0 2pt 0; break-after: avoid; }
.ecuacion { position: relative; text-align: center; font-family: "Cambria Math", Cambria, "Times New Roman", serif;
            font-size: 11pt; margin: 6pt 0 7pt 0; break-inside: avoid; }
.ecuacion .num { position: absolute; right: 0; font-size: 10pt; }
p.ref { text-indent: -21pt; margin: 3pt 0 3pt 21pt; text-align: left; font-size: 9.2pt; }
"""


def tipografia(html):
    """Subíndices en Eb/N0, Es/N0 y N0, y números como 206 473 sin cortar de renglón. No toca etiquetas ni código."""
    partes = re.split(r"(<[^>]+>)", html)
    en_codigo = 0
    for i, parte in enumerate(partes):
        if parte.startswith("<"):
            if re.match(r"<(code|pre)\b", parte):
                en_codigo += 1
            elif re.match(r"</(code|pre)>", parte):
                en_codigo -= 1
        elif not en_codigo:
            parte = parte.replace("Eb/N0", "E<sub>b</sub>/N<sub>0</sub>").replace("Es/N0", "E<sub>s</sub>/N<sub>0</sub>")
            parte = re.sub(r"\bN0\b", "N<sub>0</sub>", parte)
            partes[i] = re.sub(r"(?<=\d) (?=\d{3}\b)", " ", parte)
    return "".join(partes)


def build_html(src):
    md = src.read_text(encoding="utf-8")
    titulo = next((l[2:].strip() for l in md.splitlines() if l.startswith("# ")), src.stem)
    body = tipografia(markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"]))
    # epígrafes de figura y de tabla: párrafos que empiezan con "Figura" o "Tabla"
    body = body.replace("<p><em>Figura", '<p class="caption"><em>Figura')
    body = body.replace("<p><em>Tabla", '<p class="caption tabla"><em>Tabla')
    # bloque de título: lo que está antes de la primera línea horizontal
    head, sep, rest = body.partition("<hr />")
    body = '<div class="titulo">%s</div>%s%s' % (head, sep, rest)
    html = ('<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>%s</title><base href="%s/">'
            '<style>%s</style></head><body>%s</body></html>' % (titulo, ROOT.as_uri(), CSS, body))
    out = ROOT / "build" / (src.stem + ".html")
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def print_pdf(html, OUT):
    edge = next((e for e in EDGE if os.path.exists(e)), shutil.which("msedge"))
    if not edge:
        sys.exit("No se encontró Microsoft Edge: abrí build/INFORME.html en un navegador e imprimilo como PDF.")
    profile = tempfile.mkdtemp(prefix="edge_informe_")
    try:
        subprocess.run([edge, "--headless=new", "--disable-gpu", "--no-first-run", "--no-pdf-header-footer",
                        "--user-data-dir=" + profile, "--print-to-pdf=" + str(OUT), html.as_uri()],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    if not OUT.exists():
        sys.exit("Edge no generó el PDF")
    print("escrito", OUT.relative_to(ROOT), "(%d kB)" % (OUT.stat().st_size // 1024))


if __name__ == "__main__":
    src = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "INFORME.md"
    print_pdf(build_html(src), src.with_suffix(".pdf"))
