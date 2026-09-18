"""
anexos.py — páginas separadoras de anexo (formato EXACTO replicado del
formato real ya establecido, extraído a nivel de content-stream de los PDF
de referencia del usuario — sección 13.4, geometría y tipografía CONFIRMADAS,
nunca inventar un diseño nuevo) y fusión (merge) con el contenido real de
cada anexo (sección 8.3).

Formato confirmado por análisis de content-stream de 3 PDF reales:
    - Página A4 (595.92 x 841.92 pt).
    - Un solo borde de página vía tabla de 1 celda, margen ~0.85cm.
    - Sin color, sin encabezado, sin logos, sin código de informe.
    - Fuente Cambria, peso regular (NO bold).
    - Primera línea ("Anexo X.") a 24pt, líneas siguientes a 18pt.
    - Bloque de texto centrado vertical y horizontalmente.

Estructura de texto por tipo (sección 13.4):
    Anexo A:    "Anexo A."              / "Ubicación de Zona de Examinación." / "(P&ID)."
    Anexo B.x:  "Anexo B.{i}"           / "Reporte de Inspección Visual."     / "<TAG>"
    Anexo C.x:  "Anexo C.{i}"           / "Reporte de Ultrasonido."           / "Línea <TAG>" / "(PSAIM)"

Fórmula de conteo (checklist de insumos, sección 3):
    total de anexos = 1 (A) + N líneas (B) + M líneas con Alcance=LINEAS (C)
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
    """Busca Cambria como fuente del sistema (Windows: ships con Office/
    Windows). Si no está disponible (ej. este entorno de desarrollo en la
    nube), usa una serif regular de respaldo y avisa — en la computadora
    real del usuario (Windows) sí debería encontrar Cambria."""
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
    """Dibuja un bloque de líneas centrado horizontal y verticalmente en la
    página, cada línea con su propio tamaño de fuente (24pt la primera,
    18pt las siguientes)."""
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
    """Fusiona (merge) los PDF dados, en orden, en un solo archivo — técnica
    de la sección 8.3, usada para unir el separador con el contenido real
    (isométrico marcado, checklist VT, reporte PSAIM, P&ID)."""
    writer = PdfWriter()
    for p in pdf_paths:
        if p is None or not os.path.exists(p):
            continue
        reader = PdfReader(p)
        for page in reader.pages:
            writer.add_page(page)
    with open(out_path, "wb") as f:
        writer.write(f)


def construir_anexos(config, out_dir):
    """Orquesta la construcción de TODOS los anexos de un grupo (A + N B's +
    M C's), fusionando cada separador con el contenido real cuando está
    disponible en `config['anexos']`. Si `config['anexos']` no está (insumo
    todavía no entregado), el paso completo se salta con un aviso — el
    resto del pipeline (informe, checklist) igual se genera (sección 11.7).
    Devuelve (rutas_generadas, avisos)."""
    avisos = []
    generados = []

    anexos_cfg = config.get("anexos")
    if not anexos_cfg:
        avisos.append(
            "Paso de anexos omitido: falta el bloque 'anexos' en el config "
            "(P&ID/isométricos todavía no entregados)."
        )
        return generados, avisos

    os.makedirs(out_dir, exist_ok=True)
    lineas = config["lineas"]

    # Anexo A (una sola vez para todo el grupo)
    sep_a = os.path.join(out_dir, "_sep_A.pdf")
    separador_anexo_a(sep_a)
    pid_pdf = anexos_cfg.get("pid_pdf")
    out_a = os.path.join(out_dir, "Anexo A - (PID).pdf")
    if pid_pdf and os.path.exists(pid_pdf):
        merge_pdfs(out_a, sep_a, pid_pdf)
    else:
        avisos.append("Anexo A: falta el P&ID real, se dejó solo el separador.")
        merge_pdfs(out_a, sep_a)
    generados.append(out_a)

    isometricos = anexos_cfg.get("isometricos", {})
    checklists_vt = anexos_cfg.get("checklists_vt_pdf", {})

    for i, ln in enumerate(lineas, start=1):
        tag = ln["tag"]
        sep_b = os.path.join(out_dir, f"_sep_B{i}.pdf")
        separador_anexo_b(sep_b, i, tag)
        out_b = os.path.join(out_dir, f"Anexo B.{i} - {tag}.pdf")
        contenido = [p for p in (isometricos.get(tag), checklists_vt.get(tag)) if p]
        if not contenido:
            avisos.append(f"Anexo B.{i} ({tag}): falta isométrico/checklist real, "
                           "se dejó solo el separador.")
        merge_pdfs(out_b, sep_b, *contenido)
        generados.append(out_b)

    psaim_pdfs = anexos_cfg.get("psaim_pdf", {})
    j = 1
    for ln in lineas:
        if str(ln.get("alcance", "")).upper() != "LINEAS":
            continue
        tag = ln["tag"]
        sep_c = os.path.join(out_dir, f"_sep_C{j}.pdf")
        separador_anexo_c(sep_c, j, tag)
        out_c = os.path.join(out_dir, f"Anexo C.{j} - {tag}.pdf")
        contenido = psaim_pdfs.get(tag)
        if not contenido:
            avisos.append(f"Anexo C.{j} ({tag}): falta el reporte PSAIM en PDF real, "
                           "se dejó solo el separador.")
            merge_pdfs(out_c, sep_c)
        else:
            merge_pdfs(out_c, sep_c, contenido)
        generados.append(out_c)
        j += 1

    return generados, avisos
