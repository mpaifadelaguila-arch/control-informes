"""
inventario.py — motor de procesamiento y generación de documentos.
"""
import io
import os
import zipfile
import openpyxl
import pandas as pd
from docx import Document

PSI_PER_KGCM2 = 14.2233

def generar_documentos_completos(df_m3m6, df_cons, fotos_unidad, ruta_plantilla_base, plantilla_excel_obj=None, df_psaim=None):
    grupo_id = "22-GLP-GT-023"
    if df_cons is not None and len(df_cons) > 0:
        for col in df_cons.columns:
            if "grupo" in str(col).lower():
                val_g = df_cons.iloc[0][col]
                if pd.notna(val_g):
                    grupo_id = str(val_g)
                    break

    if ruta_plantilla_base and os.path.exists(ruta_plantilla_base):
        doc = Document(ruta_plantilla_base)
        for paragraph in doc.paragraphs:
            if "GRUPO" in paragraph.text.upper():
                for run in paragraph.runs:
                    if "GRUPO" in run.text.upper():
                        run.text = run.text.replace(run.text, f"GRUPO {grupo_id}")
    else:
        doc = Document()
        doc.add_heading(f"INFORME DE INTEGRIDAD - {grupo_id}", 0)

    output_word = io.BytesIO()
    doc.save(output_word)
    bytes_word = output_word.getvalue()

    output_excel = io.BytesIO()
    if plantilla_excel_obj is not None:
        wb_excel = openpyxl.load_workbook(plantilla_excel_obj)
    else:
        wb_excel = openpyxl.Workbook()
        ws = wb_excel.active
        ws.title = "VT-Checklist"
        if df_cons is not None:
            for r_idx, row in enumerate(df_cons.itertuples(index=False), 1):
                for c_idx, val in enumerate(row, 1):
                    ws.cell(row=r_idx, column=c_idx, value=val)
    wb_excel.save(output_excel)
    bytes_excel = output_excel.getvalue()

    output_anexos = io.BytesIO()
    with zipfile.ZipFile(output_anexos, 'w', zipfile.ZIP_DEFLATED) as zipf:
        total_lineas = len(df_m3m6) if df_m3m6 is not None else 13
        for i in range(1, total_lineas + 1):
            nombre_anexo = f"Anexo_Separador_Linea_{i:02d}.pdf"
            contenido_pdf = (
                b"%PDF-1.4\n"
                b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
                b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
                b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n"
                b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
                b"5 0 obj\n<< /Length 62 >>\nstream\n"
                f"BT /F1 16 Tf 50 700 Td (ANEXO DE INSPECCION VISUAL - LINEA {i:02d}) Tj ET\n".encode("latin-1") +
                b"endstream\nendobj\n"
                b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000228 00000 n \n0000000317 00000 n \n"
                b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n410\n%%EOF"
            )
            zipf.writestr(nombre_anexo, contenido_pdf)
    bytes_anexos = output_anexos.getvalue()

    return bytes_word, bytes_excel, bytes_anexos
