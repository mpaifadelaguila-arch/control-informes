"""
reportes_pdf.py — genera, sin ninguna llamada a IA, los PDF que alimentan los
Anexos del informe (anexos.py):

    generar_pdf_checklist_vt_por_tag(...) -> Anexo B: exporta cada hoja
        (línea) del VT-CHECK LIST ya parchado (checklist.py) tal cual, con
        su formato, colores y fotografías originales, vía LibreOffice --
        el Anexo B muestra el checklist real que llenó el inspector, no un
        resumen reconstruido.

    generar_pdf_psaim_por_tag(...)      -> Anexo C: resumen del cálculo de
        Rate de Corrosión / Vida Útil por línea (psaim.py), a partir del
        Excel PSAIM que se subió a la interfaz.
"""
import os
import shutil
import tempfile
from xml.sax.saxutils import escape

import openpyxl
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

import anexos
import psaim
from checklist import CELDA_LINEA, extraer_hoja_a_xlsx

_STYLES = getSampleStyleSheet()
_TITULO = ParagraphStyle("TituloAnexo", parent=_STYLES["Heading2"])
_CUERPO = ParagraphStyle("CuerpoAnexo", parent=_STYLES["BodyText"], spaceAfter=6)
_ETIQUETA = ParagraphStyle("EtiquetaAnexo", parent=_STYLES["BodyText"], fontName="Helvetica-Bold")


def generar_pdf_checklist_vt_por_tag(ruta_checklist_parchado, dir_salida):
    """Por cada hoja (línea) del VT-CHECK LIST ya parchado, exporta esa
    hoja sola -- con su formato, colores y fotografías originales
    intactos -- a un PDF independiente vía LibreOffice (checklist.
    extraer_hoja_a_xlsx aísla la hoja a nivel de XML crudo, igual que el
    parchado, para no perder ninguna fotografía en el camino)."""
    os.makedirs(dir_salida, exist_ok=True)
    wb = openpyxl.load_workbook(ruta_checklist_parchado)

    rutas = {}
    with tempfile.TemporaryDirectory() as tmp_hojas:
        for i, nombre_hoja in enumerate(wb.sheetnames):
            ws = wb[nombre_hoja]
            tag_val = ws[CELDA_LINEA].value
            if not tag_val:
                continue
            tag = str(tag_val).strip()

            ruta_hoja_xlsx = os.path.join(tmp_hojas, f"hoja_{i}.xlsx")
            extraer_hoja_a_xlsx(ruta_checklist_parchado, nombre_hoja, ruta_hoja_xlsx)

            ruta_pdf_generado = anexos.convertir_xlsx_a_pdf(ruta_hoja_xlsx, tmp_hojas)
            if not ruta_pdf_generado:
                continue

            ruta_pdf_final = os.path.join(dir_salida, f"Checklist_VT_{_slug(tag)}.pdf")
            shutil.copyfile(ruta_pdf_generado, ruta_pdf_final)
            rutas[tag] = ruta_pdf_final

    return rutas


def _slug(texto):
    return "".join(c if c.isalnum() else "_" for c in str(texto)).strip("_")


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
