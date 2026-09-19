"""
anexos.py — páginas separadoras de anexo (formato EXACTO replicado del
formato real ya establecido, extraído a nivel de content-stream de los PDF
de referencia del usuario — sección 13.4, geometría y tipografía CONFIRMADAS,
nunca inventar un diseño nuevo) y fusión (merge) con el contenido real de
cada anexo (sección 8.3).
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFont, stringWidth
from pypdf import PdfReader, PdfWriter

PAGE_W, PAGE_H = 595.92, 841.92
MARGIN = 0.85 * 28.3465  # ~0.85 cm en puntos

FONT_NAME = "CambriaLike"
_FONT_REGISTERED = False


def _find_cambria():
    candidatos = [
        r"C:\Windows\Fonts\cambria.ttc",
        r"C:\Windows\Fonts\Cambria.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
    return None


def _ensure_font():
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    path = _find_cambria()
    if path is None:
        raise RuntimeError(
            "No se encontró ninguna fuente serif para los separadores de "
            "anexo (ni Cambria ni un respaldo). Instalar Cambria o ajustar "
            "anexos._find_cambria()."
        )
    try:
        registerFont(TTFont(FONT_NAME, path, subfontIndex=0))
    except Exception:
        registerFont(TTFont(FONT_NAME, path))
    _FONT_REGISTERED = True


def _draw_centered_block(c, lines_with_sizes):
    _ensure_font()
    line_gap = 1.25
    heights = [size * line_gap for _, size in lines_with_sizes]
    total_h = sum(heights)
    y = PAGE_H / 2 + total_h / 2 - heights[0] * 0.35

    for (text, size), h in zip(lines_with_sizes, heights):
        c.setFont(FONT_NAME, size)
        w = stringWidth(text, FONT_NAME, size)
        x = (PAGE_W - w) / 2
        c.drawString(x, y - size * 0.8, text)
        y -= h


def _draw_border(c):
    c.setLineWidth(0.75)
    c.rect(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN)


def _build_pdf(out_path, lines_with_sizes):
    c = canvas.Canvas(out_path, pagesize=(PAGE_W, PAGE_H))
    _draw_border(c)
    _draw_centered_block(c, lines_with_sizes)
    c.showPage()
    c.save()


def separador_anexo_a(out_path):
    _build_pdf(out_path, [
        ("Anexo A.", 24),
        ("Ubicación de Zona de Examinación.", 18),
        ("(P&ID).", 18),
    ])


def separador_anexo_b(out_path, indice, tag):
    _build_pdf(out_path, [
        (f"Anexo B.{indice}", 24),
        ("Reporte de Inspección Visual.", 18),
        (str(tag), 18),
    ])


def separador_anexo_c(out_path, indice, tag):
    _build_pdf(out_path, [
        (f"Anexo C.{indice}", 24),
        ("Reporte de Ultrasonido.", 18),
        (f"Línea {tag}", 18),
        ("(PSAIM)", 18),
    ])


def merge_pdfs(out_path, *pdf_paths):
    writer = PdfWriter()
    for p in pdf_paths:
        if p is None or not os.path.exists(str(p)):
            continue
        reader = PdfReader(str(p))
        for page in reader.pages:
            writer.add_page(page)
    with open(out_path, "wb") as f:
        writer.write(f)


def construir_anexos(*args, **kwargs):
    """Versión completamente flexible y tolerante a fallos para la construcción de anexos."""
    avisos = []
    generados = []

    # Extraer parámetros de manera tolerante a diferentes firmas de llamadas
    config = args[0] if len(args) > 0 else kwargs.get("config")
    out_dir = args[1] if len(args) > 1 else (kwargs.get("out_dir") or kwargs.get("dir_salida") or "salida_informes")

    if not config or not isinstance(config, dict):
        avisos.append("Paso de anexos omitido o ejecutado sin bloque de configuración válido.")
        return generados, avisos

    os.makedirs(out_dir, exist_ok=True)
    lineas = config.get("lineas", [])

    # Anexo A
    sep_a = os.path.join(out_dir, "_sep_A.pdf")
    separador_anexo_a(sep_a)
    anexos_cfg = config.get("anexos", {})
    pid_pdf = anexos_cfg.get("pid_pdf")
    out_a = os.path.join(out_dir, "Anexo A - (PID).pdf")
    if pid_pdf and os.path.exists(str(pid_pdf)):
        merge_pdfs(out_a, sep_a, pid_pdf)
    else:
        merge_pdfs(out_a, sep_a)
    generados.append(out_a)

    isometricos = anexos_cfg.get("isometricos", {})
    checklists_vt = anexos_cfg.get("checklists_vt_pdf", {})

    for i, ln in enumerate(lineas, start=1):
        tag = ln.get("tag", f"Linea_{i}")
        sep_b = os.path.join(out_dir, f"_sep_B{i}.pdf")
        separador_anexo_b(sep_b, i, tag)
        out_b = os.path.join(out_dir, f"Anexo B.{i} - {tag}.pdf")
        contenido = [p for p in (isometricos.get(tag), checklists_vt.get(tag)) if p and os.path.exists(str(p))]
        merge_pdfs(out_b, sep_b, *contenido)
        generados.append(out_b)

    psaim_pdfs = anexos_cfg.get("psaim_pdf", {})
    j = 1
    for ln in lineas:
        if str(ln.get("alcance", "")).upper() != "LINEAS":
            continue
        tag = ln.get("tag", f"Linea_{j}")
        sep_c = os.path.join(out_dir, f"_sep_C{j}.pdf")
        separador_anexo_c(sep_c, j, tag)
        out_c = os.path.join(out_dir, f"Anexo C.{j} - {tag}.pdf")
        contenido = psaim_pdfs.get(tag)
        if contenido and os.path.exists(str(contenido)):
            merge_pdfs(out_c, sep_c, contenido)
        else:
            merge_pdfs(out_c, sep_c)
        generados.append(out_c)
        j += 1

    return generados, avisos
