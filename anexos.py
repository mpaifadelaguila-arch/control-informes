"""
anexos.py — páginas separadoras de anexo (formato EXACTO replicado del
formato real ya establecido, extraído a nivel de content-stream de los PDF
de referencia del usuario — sección 13.4, geometría y tipografía CONFIRMADAS,
nunca inventar un diseño nuevo) y fusión (merge) con el contenido real de
cada anexo (sección 8.3).
"""
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFont, stringWidth
from pypdf import PdfReader, PdfWriter

PAGE_W, PAGE_H = 595.92, 841.92
MARGIN = 0.85 * 28.3465  # ~0.85 cm en puntos

FONT_NAME = "CambriaLike"
FONT_NAME_BOLD = "CambriaLike-Bold"
# Fuentes base de reportlab (siempre disponibles, sin archivo externo) -- se
# usan como respaldo cuando el contenedor de despliegue (p.ej. Streamlit
# Cloud) no tiene instalada ninguna fuente serif de sistema.
FALLBACK_FONT_NAME = "Times-Roman"
FALLBACK_FONT_NAME_BOLD = "Times-Bold"
_FONT_REGISTERED = False


def _find_cambria():
    """Devuelve (ruta_regular, ruta_bold) de la primera fuente serif de
    sistema disponible -- la MISMA fuente para toda página generada por
    reportlab en el compilado (separadores de anexo Y el resumen PSAIM),
    para que no se note un cambio de tipografía entre ellas.

    Caladea va primero porque es la fuente sustituta oficial de Cambria
    (metric-compatible, del proyecto Chrome OS Core Fonts): es la MISMA
    que usa LibreOffice para sustituir Cambria al convertir el Informe
    Word a PDF en el servidor (paquete 'fonts-crosextra-caladea' listado
    en packages.txt), así que con ella las páginas generadas por
    reportlab quedan visualmente iguales al resto del Word convertido --
    Liberation Serif / DejaVu Serif solo quedan de respaldo si ni
    siquiera Caladea está instalada."""
    candidatos = [
        (r"C:\Windows\Fonts\cambria.ttc", None),
        (r"C:\Windows\Fonts\Cambria.ttf", r"C:\Windows\Fonts\Cambriab.ttf"),
        (
            "/usr/share/fonts/truetype/crosextra/Caladea-Regular.ttf",
            "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf",
        ),
        (
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        ),
        ("/usr/share/fonts/truetype/msttcorefonts/Cambria.ttf", None),
    ]
    for regular, bold in candidatos:
        if os.path.exists(regular):
            return regular, (bold if bold and os.path.exists(bold) else None)
    return None, None


def _ensure_font():
    """Registra la fuente serif de sistema (regular y, si existe, negrita)
    si hay alguna disponible; si no hay ninguna en el contenedor (caso
    típico de un despliegue en la nube), cae de respaldo a Times-Roman /
    Times-Bold, que reportlab trae incorporadas y no requieren ningún
    archivo de fuente externo."""
    global _FONT_REGISTERED, FONT_NAME, FONT_NAME_BOLD
    if _FONT_REGISTERED:
        return
    regular, bold = _find_cambria()
    if regular is None:
        FONT_NAME = FALLBACK_FONT_NAME
        FONT_NAME_BOLD = FALLBACK_FONT_NAME_BOLD
        _FONT_REGISTERED = True
        return
    try:
        registerFont(TTFont(FONT_NAME, regular, subfontIndex=0))
    except Exception:
        registerFont(TTFont(FONT_NAME, regular))
    if bold:
        try:
            registerFont(TTFont(FONT_NAME_BOLD, bold, subfontIndex=0))
        except Exception:
            registerFont(TTFont(FONT_NAME_BOLD, bold))
    else:
        FONT_NAME_BOLD = FONT_NAME
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


_CARACTERES_INVALIDOS_ARCHIVO = '<>:"/\\|?*'


def nombre_archivo_seguro(texto):
    """Sanea un TAG de línea para usarlo en un nombre de archivo: los TAG
    reales pueden traer '/' (p.ej. 1 1/2"-22-18-11), que en cualquier
    sistema de archivos se interpreta como separador de carpetas y rompe
    la escritura del PDF."""
    texto = str(texto)
    for c in _CARACTERES_INVALIDOS_ARCHIVO:
        texto = texto.replace(c, "-")
    return texto


def _convertir_a_pdf(ruta_archivo, dir_salida):
    """Convierte un .docx o .xlsx a .pdf usando LibreOffice en modo
    headless -- único motor de renderizado real disponible en el
    servidor sin licencia de Office (requiere el paquete 'libreoffice'
    listado en packages.txt para que Streamlit Cloud lo instale en el
    contenedor de despliegue). Cada llamada usa un perfil de usuario
    temporal propio (nunca uno fijo compartido): con un perfil fijo se
    detectó contenido de una conversión anterior filtrándose en la
    siguiente cuando se llama repetidas veces seguidas (p.ej. una
    conversión por línea del checklist VT). Devuelve la ruta del PDF
    generado, o None si LibreOffice no está disponible o falla la
    conversión -- nunca debe tumbar el resto del proceso."""
    import shutil
    import subprocess
    import tempfile

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    with tempfile.TemporaryDirectory(prefix="lo_profile_") as perfil_dir:
        try:
            subprocess.run(
                [
                    soffice,
                    "--headless",
                    "--norestore",
                    f"-env:UserInstallation=file://{perfil_dir}",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(dir_salida),
                    str(ruta_archivo),
                ],
                check=True,
                timeout=120,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return None
    ruta_pdf = os.path.join(dir_salida, os.path.splitext(os.path.basename(str(ruta_archivo)))[0] + ".pdf")
    return ruta_pdf if os.path.exists(ruta_pdf) else None


def convertir_docx_a_pdf(ruta_docx, dir_salida):
    return _convertir_a_pdf(ruta_docx, dir_salida)


def convertir_xlsx_a_pdf(ruta_xlsx, dir_salida):
    return _convertir_a_pdf(ruta_xlsx, dir_salida)


def construir_informe_compilado(ruta_word, anexos_generados, out_dir, nombre_salida):
    """Arma el 'Informe Compilado al 100%': el Informe Word convertido a
    PDF, seguido de todos los anexos ya generados por construir_anexos()
    (Anexo A, B.1..B.N, C.1..C.N, en ese mismo orden), fusionados en un
    solo PDF -- tal como se entrega el expediente técnico completo.

    Devuelve (ruta_pdf, aviso). `ruta_pdf` es None si no se pudo generar
    (p.ej. LibreOffice no disponible en el servidor), en cuyo caso
    `aviso` trae el motivo para mostrarlo en la interfaz sin interrumpir
    el resto del proceso."""
    os.makedirs(out_dir, exist_ok=True)
    ruta_informe_pdf = convertir_docx_a_pdf(ruta_word, out_dir)
    if not ruta_informe_pdf:
        return None, (
            "No se pudo generar el Informe Compilado en PDF: falló la "
            "conversión del Informe Word a PDF en el servidor (LibreOffice "
            "no está disponible o no pudo procesar el archivo)."
        )
    ruta_salida = os.path.join(out_dir, f"{nombre_archivo_seguro(nombre_salida)}.pdf")
    merge_pdfs(ruta_salida, ruta_informe_pdf, *anexos_generados)
    return ruta_salida, None


def _normalizar_tag(texto):
    """Normaliza un TAG de línea SOLO para buscar coincidencias entre
    archivos distintos (Detalle de grupo, VT-CHECK LIST, PSAIM) -- nunca
    para mostrarlo. Unifica mayúsculas, espacios (incluye NBSP y espacios
    dobles) y comillas tipográficas de pulgada (”, “, ″, ' ...) a una
    comilla recta simple, que es la diferencia más común entre cómo un
    TAG se escribe en un Excel y en otro."""
    if texto is None:
        return ""
    texto = str(texto).strip().upper().replace("\xa0", " ")
    texto = re.sub(r"\s+", " ", texto)
    for comilla in ("”", "“", "″", "’", "‘"):
        texto = texto.replace(comilla, '"')
    return texto.replace("'", '"')


def _buscar_por_tag(diccionario, tag):
    """Busca `tag` en `diccionario` por igualdad exacta primero: si no
    aparece (p.ej. el Detalle de grupo trae 4"-22-71-11 y el VT-CHECK LIST
    lo escribió con una comilla tipográfica o un espacio de más), reintenta
    por coincidencia normalizada antes de darlo por no encontrado -- para
    que un detalle de formato entre dos archivos no deje un Anexo B/C sin
    su checklist o su PSAIM."""
    if not diccionario:
        return None
    if tag in diccionario:
        return diccionario[tag]
    objetivo = _normalizar_tag(tag)
    if not objetivo:
        return None
    for clave, valor in diccionario.items():
        if _normalizar_tag(clave) == objetivo:
            return valor
    return None


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
        out_b = os.path.join(out_dir, f"Anexo B.{i} - {nombre_archivo_seguro(tag)}.pdf")
        pdf_checklist = _buscar_por_tag(checklists_vt, tag)
        if checklists_vt and not pdf_checklist:
            avisos.append(
                f"Anexo B.{i} ({tag}): el VT-CHECK LIST se cargó pero no se encontró la hoja "
                "de esta línea (el TAG no calzó ni exacto ni normalizado) -- el anexo quedó "
                "solo con el separador, sin el checklist."
            )
        contenido = [p for p in (_buscar_por_tag(isometricos, tag), pdf_checklist) if p and os.path.exists(str(p))]
        merge_pdfs(out_b, sep_b, *contenido)
        generados.append(out_b)

    incluir_anexo_c = args[2] if len(args) > 2 else kwargs.get("incluir_anexo_c", True)
    if not incluir_anexo_c:
        return generados, avisos

    psaim_pdfs = anexos_cfg.get("psaim_pdf", {})
    j = 1
    for ln in lineas:
        if str(ln.get("alcance", "")).upper() != "LINEAS":
            continue
        tag = ln.get("tag", f"Linea_{j}")
        sep_c = os.path.join(out_dir, f"_sep_C{j}.pdf")
        separador_anexo_c(sep_c, j, tag)
        out_c = os.path.join(out_dir, f"Anexo C.{j} - {nombre_archivo_seguro(tag)}.pdf")
        contenido = _buscar_por_tag(psaim_pdfs, tag)
        if contenido and os.path.exists(str(contenido)):
            merge_pdfs(out_c, sep_c, contenido)
        else:
            merge_pdfs(out_c, sep_c)
        generados.append(out_c)
        j += 1

    return generados, avisos
