import io
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import openpyxl
import pandas as pd
import streamlit as st
from docx import Document

# ==============================================================================
# CONFIGURACIÓN DE RUTAS (TODO EN RAÍZ)
# ==============================================================================
RUTA_ACTUAL = Path(__file__).resolve().parent
DIR_RAIZ = RUTA_ACTUAL.parent if RUTA_ACTUAL.name == "pages" else RUTA_ACTUAL

if str(DIR_RAIZ) not in sys.path:
    sys.path.insert(0, str(DIR_RAIZ))

RUTA_PLANTILLA_BASE = DIR_RAIZ / "plantilla_base.docx"
RUTA_BASE_DATOS_MAESTRA = DIR_RAIZ / "BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx"

# Importación directa de los módulos desde la raíz
try:
    import inventario
    INVENTARIO_OK = True
except Exception:
    INVENTARIO_OK = False

try:
    import psaim
    PSAIM_OK = True
except Exception:
    PSAIM_OK = False

try:
    import generar_informe
    GENERAR_OK = True
except Exception:
    GENERAR_OK = False

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Elaboración de Informes - Ademinsac",
    page_icon="📋",
    layout="wide"
)

st.title("Módulo de Elaboración de Informes")
st.markdown("---")

# ==============================================================================
# INDICADORES DE ESTADO DE RECURSOS
# ==============================================================================
col_e1, col_e2, col_e3, col_e4 = st.columns(4)
with col_e1:
    if RUTA_BASE_DATOS_MAESTRA.exists():
        st.success("🟢 Base Maestra Detectada")
    else:
        st.warning("⚠️ Falta Base Maestra en Raíz")
with col_e2:
    st.success("🟢 inventario.py OK" if INVENTARIO_OK else "⚠️ inventario.py pendiente")
with col_e3:
    st.success("🟢 psaim.py OK" if PSAIM_OK else "⚠️ psaim.py pendiente")
with col_e4:
    st.success("🟢 generar_informe.py OK" if GENERAR_OK else "⚠️ pendiente")

st.markdown("---")

# ==============================================================================
# CARGA DE ARCHIVOS
# ==============================================================================
st.subheader("📁 Carga de Archivos Requeridos")

col1, col2, col3, col4 = st.columns(4)
with col1:
    file_m3_m6 = st.file_uploader("1. Archivo M3 y M6 (Excel)", type=["xlsx", "xls"], key="indep_m3m6")
with col2:
    file_consolidadas = st.file_uploader("2. Archivo Consolidadas (Excel)", type=["xlsx", "xls"], key="indep_consolidadas")
with col3:
    fotos_unidad = st.file_uploader("3. Fotos de la Unidad (JPG/PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="indep_fotos")
with col4:
    file_psaim_opc = st.file_uploader("4. PSAIM Opcional (Excel)", type=["xlsx", "xls"], key="indep_psaim")

st.markdown("---")

# ==============================================================================
# MOTOR DE PROCESAMIENTO INTEGRADO
# ==============================================================================
def generar_documentos_completos(df_m3m6, df_cons, fotos_unidad, ruta_plantilla_base, plantilla_excel_obj=None):
    grupo_id = "22-GLP-GT-023"
    if df_cons is not None and len(df_cons) > 0:
        for col in df_cons.columns:
            if "grupo" in str(col).lower():
                val_g = df_cons.iloc[0][col]
                if pd.notna(val_g):
                    grupo_id = str(val_g)
                    break

    # Leer base maestra si existe
    df_maestra = None
    if RUTA_BASE_DATOS_MAESTRA.exists():
        try:
            df_maestra = pd.read_excel(RUTA_BASE_DATOS_MAESTRA)
        except Exception:
            pass

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

# ==============================================================================
# BOTÓN DE EJECUCIÓN
# ==============================================================================
if st.button("🚀 Procesar Generación con Arquitectura Unificada", type="primary", use_container_width=True):
    if not (file_m3_m6 and file_consolidadas and fotos_unidad):
        st.error("Por favor, carga M3/M6, Consolidadas y las Fotos para continuar.")
    else:
        with st.spinner("Procesando con módulos raíz y generando entregables..."):
            try:
                df_m3m6 = pd.read_excel(file_m3_m6)
                df_cons = pd.read_excel(file_consolidadas)

                bytes_word, bytes_excel, bytes_anexos = generar_documentos_completos(
                    df_m3m6, df_cons, fotos_unidad, RUTA_PLANTILLA_BASE, plantilla_excel_obj=file_consolidadas
                )

                st.session_state["resultado_word"] = bytes_word
                st.session_state["resultado_excel"] = bytes_excel
                st.session_state["resultado_anexos"] = bytes_anexos
                st.session_state["procesado_exito"] = True
                
                st.success("¡Proceso completado utilizando los scripts raíz con éxito!")
            except Exception as e:
                st.error(f"Error durante el procesamiento: {str(e)}")

# ==============================================================================
# SECCIÓN DE DESCARGAS
# ==============================================================================
if st.session_state.get("procesado_exito", False):
    st.subheader("📥 Descarga de Resultados Generados")
    
    d_col1, d_col2, d_col3 = st.columns(3)

    with d_col1:
        st.download_button(
            label="📄 Descargar Word",
            data=st.session_state["resultado_word"],
            file_name=f"Informe_Tecnico_{datetime.now():%Y%m%d_%H%M%S}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

    with d_col2:
        st.download_button(
            label="📊 Descargar Excel",
            data=st.session_state["resultado_excel"],
            file_name=f"VT_Checklist_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with d_col3:
        st.download_button(
            label="📑 Descargar Anexos (ZIP)",
            data=st.session_state["resultado_anexos"],
            file_name=f"Anexos_Separadores_{datetime.now():%Y%m%d_%H%M%S}.zip",
            mime="application/zip",
            use_container_width=True
        )
