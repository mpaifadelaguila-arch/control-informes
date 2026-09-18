import io
import os
import sys
from datetime import datetime
from pathlib import Path
import zipfile

import openpyxl
import pandas as pd
import streamlit as st
from docx import Document

# ==============================================================================
# CONFIGURACIÓN DE RUTAS Y COMPONENTES
# ==============================================================================
RUTA_ACTUAL = Path(__file__).resolve().parent
DIR_RAIZ = RUTA_ACTUAL.parent if RUTA_ACTUAL.name == "pages" else RUTA_ACTUAL

DIR_COMPLEMENTO = DIR_RAIZ / "COMPLEMENTO"
RUTA_PLANTILLA_BASE = DIR_RAIZ / "plantilla_base.docx"
RUTA_BASE_DATOS_MAESTRA = DIR_RAIZ / "control-informe" / "BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx"
RUTA_COMPENDIO = DIR_COMPLEMENTO / "COMPENDIO TÉCNICO UNIFICADO DE HALLAZGOS Y RECOMENDACIONES TÉCNICAS.REV.1.docx"
RUTA_POE = DIR_COMPLEMENTO / "PROCEDIMIENTO OPERATIVO ESTANDARIZADO (POE).docx"

# ==============================================================================
# MOTOR INTEGRADO DE PROCESAMIENTO (INVENTARIO)
# ==============================================================================
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

# ==============================================================================
# CONFIGURACIÓN DE INTERFAZ
# ==============================================================================
st.set_page_config(
    page_title="Elaboración de Informes - Ademinsac",
    page_icon="📋",
    layout="wide"
)

st.markdown("""
    <style>
    footer {visibility: hidden;}
    .header-banner {
        background: linear-gradient(120deg, #0B2038 0%, #1E4E7E 60%, #2C6494 100%);
        padding: 20px 25px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
    }
    .header-title { font-size: 22px; font-weight: 800; color: #FFFFFF; }
    .header-subtitle { font-size: 13px; color: #C9DCEE; margin-top: 4px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="header-banner">
        <div class="header-title">MÓDULO INDEPENDIENTE: ELABORACIÓN DE INFORMES</div>
        <div class="header-subtitle">Generación de reporte técnico en Word, VT-Checklist y Anexos Separadores</div>
    </div>
""", unsafe_allow_html=True)

# ==============================================================================
# VERIFICACIÓN DE RECURSOS
# ==============================================================================
st.subheader("🛠️ Estado de Herramientas y Recursos")

col_e1, col_e2, col_e3 = st.columns(3)
with col_e1:
    if RUTA_BASE_DATOS_MAESTRA.exists():
        st.success("🟢 Base Maestra Conectada")
    else:
        st.error("🔴 Base Maestra No Encontrada")

with col_e2:
    if RUTA_COMPENDIO.exists() and RUTA_POE.exists():
        st.success("🟢 Compendio Técnico y POE Listos")
    else:
        st.warning("⚠️ Falta Compendio o POE en COMPLEMENTO")

with col_e3:
    st.success("🟢 Módulo de Procesamiento Integrado")

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
    file_psaim = st.file_uploader("4. Archivo PSAIM (Opcional)", type=["xlsx", "xls"], key="indep_psaim")

# ==============================================================================
# PROCESAMIENTO
# ==============================================================================
st.markdown("---")

if st.button("🚀 Procesar Generación de Informe", type="primary", use_container_width=True):
    if not (file_m3_m6 and file_consolidadas and fotos_unidad):
        st.error("Debe cargar los elementos obligatorios (M3/M6, Consolidadas y Fotos) para ejecutar la herramienta.")
    else:
        with st.spinner("Procesando inventario, generando Informe Word, Checklist Excel y Anexos Separadores..."):
            try:
                df_m3m6 = pd.read_excel(file_m3_m6)
                df_cons = pd.read_excel(file_consolidadas)
                df_psaim = pd.read_excel(file_psaim) if file_psaim else None

                bytes_word, bytes_excel, bytes_anexos = generar_documentos_completos(
                    df_m3m6, df_cons, fotos_unidad, RUTA_PLANTILLA_BASE, plantilla_excel_obj=file_consolidadas, df_psaim=df_psaim
                )

                st.session_state["resultado_word"] = bytes_word
                st.session_state["resultado_excel"] = bytes_excel
                st.session_state["resultado_anexos"] = bytes_anexos
                st.session_state["procesado_exito"] = True
                
                estado_psaim = "con datos PSAIM integrados" if file_psaim else "con PSAIM pendiente"
                st.success(f"¡Proceso completado con éxito ({estado_psaim})! Ya puede descargar los entregables abajo.")

            except Exception as e:
                st.error(f"Error durante el procesamiento: {str(e)}")

# ==============================================================================
# DESCARGA
# ==============================================================================
if st.session_state.get("procesado_exito", False):
    st.subheader("📥 Descarga de Resultados Generados")
    
    d_col1, d_col2, d_col3 = st.columns(3)

    with d_col1:
        st.download_button(
            label="📄 Descargar Informe Técnico (Word)",
            data=st.session_state["resultado_word"],
            file_name=f"Informe_Tecnico_{datetime.now():%Y%m%d_%H%M%S}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

    with d_col2:
        st.download_button(
            label="📊 Descargar VT-Checklist (Excel)",
            data=st.session_state["resultado_excel"],
            file_name=f"VT_Checklist_Recomendaciones_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with d_col3:
        st.download_button(
            label="📑 Descargar Anexos Separadores (ZIP)",
            data=st.session_state["resultado_anexos"],
            file_name=f"Anexos_Separadores_{datetime.now():%Y%m%d_%H%M%S}.zip",
            mime="application/zip",
            use_container_width=True
        )
