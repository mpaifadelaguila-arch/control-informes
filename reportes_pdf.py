"""
reportes_pdf.py — genera, sin ninguna llamada a IA, los PDF que alimentan los
Anexos del informe (anexos.py):

    generar_pdf_checklist_por_tag(...)  -> Anexo B: hoja de hallazgos VT por
        línea, con las fotos de campo ya incrustadas en el VT-CHECK LIST
        parchado (checklist.py) más el texto de Hallazgo/Recomendación que
        generó recomendaciones.py.

    generar_pdf_psaim_por_tag(...)      -> Anexo C: resumen del cálculo de
        Rate de Corrosión / Vida Útil por línea (psaim.py), a partir del
        Excel PSAIM que se subió a la interfaz.
"""
import io
import os
from xml.sax.saxutils import escape

import openpyxl
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage

import psaim
from checklist import (
    CELDA_LINEA, _bloques_por_item, _fotos_por_hoja, _procesar_bloque, imagenes_del_bloque,
)

_STYLES = getSampleStyleSheet()
_TITULO = ParagraphStyle("TituloAnexo", parent=_STYLES["Heading2"])
_CUERPO = ParagraphStyle("CuerpoAnexo", parent=_STYLES["BodyText"], spaceAfter=6)
_ETIQUETA = ParagraphStyle("EtiquetaAnexo", parent=_STYLES["BodyText"], fontName="Helvetica-Bold")


def generar_pdf_checklist_por_tag(ruta_checklist_parchado, dir_salida):
    """Lee el VT-CHECK LIST real ya parchado (checklist.parchar_checklist_vt)
    y arma, por TAG de línea (una hoja por línea, ver checklist.py), un PDF
    con las fotos de campo y el texto de Hallazgo/Recomendación de cada
    ítem con marca O/R."""
    os.makedirs(dir_salida, exist_ok=True)
    wb = openpyxl.load_workbook(ruta_checklist_parchado)
    fotos_por_hoja = _fotos_por_hoja(ruta_checklist_parchado)

    rutas = {}
    for nombre_hoja in wb.sheetnames:
        ws = wb[nombre_hoja]
        fotos_hoja = fotos_por_hoja.get(nombre_hoja, {})
        tag_val = ws[CELDA_LINEA].value
        if not tag_val:
            continue
        tag = str(tag_val).strip()

        items_pdf = []
        for item, categoria, marca, fila_ini, fila_fin in _bloques_por_item(ws):
            for info in _procesar_bloque(ws, fotos_hoja, item, categoria, marca, fila_ini, fila_fin):
                imgs = imagenes_del_bloque(fotos_hoja, info["fila_ini_sub"], info["fila_fin_sub"])
                items_pdf.append((categoria, info["hallazgo"], info["recomendacion"], imgs))

        if not items_pdf:
            continue

        nombre_archivo = f"Checklist_VT_{_slug(tag)}.pdf"
        ruta_pdf = os.path.join(dir_salida, nombre_archivo)
        _construir_pdf_checklist_tag(tag, items_pdf, ruta_pdf)
        rutas[tag] = ruta_pdf

    return rutas


def _slug(texto):
    return "".join(c if c.isalnum() else "_" for c in str(texto)).strip("_")


def _construir_pdf_checklist_tag(tag, items, ruta_pdf):
    doc = SimpleDocTemplate(
        ruta_pdf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
    )
    story = [Paragraph(f"Reporte de Inspección Visual (VT) — Línea {escape(tag)}", _TITULO), Spacer(1, 12)]

    for categoria, hallazgo, recomendacion, imgs in items:
        story.append(Paragraph(escape(str(categoria or "SIN DATO")), _ETIQUETA))
        story.append(Paragraph(escape(hallazgo) if hallazgo else "SIN DATO", _CUERPO))
        if recomendacion:
            story.append(Paragraph("Recomendación Técnica", _ETIQUETA))
            story.append(Paragraph(escape(recomendacion), _CUERPO))
        for img_bytes in imgs:
            try:
                rl_img = RLImage(io.BytesIO(img_bytes))
                rl_img._restrictSize(14 * cm, 10 * cm)
                story.append(rl_img)
                story.append(Spacer(1, 10))
            except Exception:
                continue
        story.append(Spacer(1, 16))

    doc.build(story)


def generar_pdf_psaim_por_tag(psaim_por_tag, filas_tecnicas, dir_salida):
    """Arma, por TAG, un PDF de una página con el cálculo de Rate de
    Corrosión y Vida Útil (psaim.py) a partir del Excel PSAIM subido."""
    os.makedirs(dir_salida, exist_ok=True)
    clase_por_tag = {f["tag"]: f.get("clase", "") for f in filas_tecnicas}
    rutas = {}

    for tag, datos in psaim_por_tag.items():
        rate = psaim.rate_corrosion_mm_anio(datos["rcr_mpy"])
        vida = psaim.vida_util_display(datos["vida_util_anios"], clase_por_tag.get(tag, ""))

        nombre_archivo = f"PSAIM_{_slug(tag)}.pdf"
        ruta_pdf = os.path.join(dir_salida, nombre_archivo)
        doc = SimpleDocTemplate(
            ruta_pdf, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
        )
        story = [
            Paragraph(f"Reporte de Ultrasonido (PSAIM) — Línea {escape(tag)}", _TITULO),
            Spacer(1, 12),
            Paragraph("RCR (dato de cabecera del PSAIM)", _ETIQUETA),
            Paragraph(f"{datos['rcr_mpy']:g} MPY", _CUERPO),
            Paragraph("Rate de Corrosión", _ETIQUETA),
            Paragraph(f"{rate:g} mm/año", _CUERPO),
            Paragraph("Vida Remanente (mínimo de TML Vida Útil)", _ETIQUETA),
            Paragraph(
                f"{escape(str(vida))} años (según Clase API 570: {escape(str(clase_por_tag.get(tag, 'SIN DATO')))})",
                _CUERPO,
            ),
            Paragraph("Puntos de medición (TML) considerados", _ETIQUETA),
            Paragraph(str(datos.get("n_tml", "SIN DATO")), _CUERPO),
        ]
        doc.build(story)
        rutas[tag] = ruta_pdf

    return rutas
