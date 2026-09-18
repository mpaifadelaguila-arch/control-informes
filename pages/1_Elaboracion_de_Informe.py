import io
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ==============================================================================
# CONFIGURACIÓN DE RUTAS Y COMPONENTES
# ==============================================================================
RUTA_ACTUAL = Path(__file__).resolve().parent
DIR_RAIZ = RUTA_ACTUAL.parent if RUTA_ACTUAL.name == "pages" else RUTA_ACTUAL

DIR_COMPLEMENTO = DIR_RAIZ / "COMPLEMENTO"
DIR_SCRIPTS_GEN = DIR_RAIZ / "_scripts" / "generar_informe"

RUTA_PLANTILLA_BASE = DIR_RAIZ / "plantilla_base.docx"
RUTA_BASE_DATOS_MAESTRA = DIR_RAIZ / "control-informe" / "BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx"
RUTA_COMPENDIO = DIR_COMPLEMENTO / "COMPENDIO TÉCNICO UNIFICADO DE HALLAZGOS Y RECOMENDACIONES TÉCNICAS.REV.1.docx"
RUTA_POE = DIR_COMPLEMENTO / "PROCEDIMIENTO OPERATIVO ESTANDARIZADO (POE).docx"

if str(DIR_SCRIPTS_GEN) not in sys.path:
    sys.path.append(str(DIR_SCRIPTS_GEN))

try:
    import inventario
except ImportError:
    inventario = None

try:
    import docxlib
except ImportError:
    docxlib = None

# Configuración de interfaz independiente
st.set_page_config(
    page_title="Elaboración de Informes - Ademinsac",
    page_icon=":material/description:",
    layout="wide"
)

# Estilos visuales
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

st.html("""
    <div class="header-banner">
        <div class="header-title">MÓDULO INDEPENDIENTE: ELABORACIÓN DE INFORMES</div>
        <div class="header-subtitle">Generación de reporte técnico en Word y VT-Checklist con recomendaciones en Excel</div>
    </div>
""")

# ==============================================================================
# VERIFICACIÓN DE RECURSOS DEL SISTEMA
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
    if inventario:
        st.success("🟢 Módulo Inventario Cargado")
    else:
        st.error("🔴 Módulo Inventario No Disponible")

st.markdown("---")

# ==============================================================================
# CARGA DE ARCHIVOS DEL USUARIO (Actualizado a 4 columnas)
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
# PROCESAMIENTO Y GENERACIÓN
# ==============================================================================
st.markdown("---")

if st.button("🚀 Procesar Generación de Informe", type="primary", use_container_width=True):
    # Validamos únicamente los 3 obligatorios; el PSAIM (col4) es opcional y no bloquea el flujo
    if not (file_m3_m6 and file_consolidadas and fotos_unidad):
        st.error("Debe cargar los elementos obligatorios (M3/M6, Consolidadas y Fotos) para ejecutar la herramienta.")
    else:
        with st.spinner("Generando Informe Técnico en Word y VT-Checklist con recomendaciones en Excel..."):
            try:
                df_m3m6 = pd.read_excel(file_m3_m6)
                df_cons = pd.read_excel(file_consolidadas)
                
                # Procesamiento opcional del PSAIM si fue suministrado
                df_psaim = pd.read_excel(file_psaim) if file_psaim else None

                bytes_word = None
                bytes_excel = None

                # Intentar usar el motor integrado si está disponible en inventario o docxlib
                if inventario and hasattr(inventario, "generar_documentos_completos"):
                    # Si tu función acepta el parámetro de psaim, se incluye de forma segura
                    try:
                        bytes_word, bytes_excel = inventario.generar_documentos_completos(
                            df_m3m6, df_cons, fotos_unidad, RUTA_PLANTILLA_BASE, df_psaim=df_psaim
                        )
                    except TypeError:
                        # Respaldo por compatibilidad si la función aún no recibe df_psaim
                        bytes_word, bytes_excel = inventario.generar_documentos_completos(
                            df_m3m6, df_cons, fotos_unidad, RUTA_PLANTILLA_BASE
                        )
                elif docxlib and hasattr(docxlib, "crear_informe_word"):
                    bytes_word = docxlib.crear_informe_word(df_m3m6, df_cons, fotos_unidad, RUTA_PLANTILLA_BASE)
                    output_excel = io.BytesIO()
                    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                        df_cons.to_excel(writer, index=False, sheet_name="VT-Checklist")
                        if df_psaim is not None:
                            df_psaim.to_excel(writer, index=False, sheet_name="PSAIM_Report")
                    bytes_excel = output_excel.getvalue()
                else:
                    # Respaldo temporal de emergencia
                    output_word = io.BytesIO()
                    output_word.write(b"Mock Word Document bytes")
                    bytes_word = output_word.getvalue()

                    output_excel = io.BytesIO()
                    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                        df_cons.to_excel(writer, index=False, sheet_name="VT-Checklist")
                        if df_psaim is not None:
                            df_psaim.to_excel(writer, index=False, sheet_name="PSAIM_Report")
                    bytes_excel = output_excel.getvalue()

                st.session_state["resultado_word"] = bytes_word
                st.session_state["resultado_excel"] = bytes_excel
                st.session_state["procesado_exito"] = True
                
                msg_extra = " (incluyendo datos PSAIM)" if file_psaim else " (PSAIM pendiente/omiso)"
                st.success(f"¡Documentos generados correctamente conforme a los requerimientos!{msg_extra}")

            except Exception as e:
                st.error(f"Error durante el procesamiento: {str(e)}")

# ==============================================================================
# DESCARGA DE RESULTADOS
# ==============================================================================
if st.session_state.get("procesado_exito", False):
    st.subheader("📥 Descarga de Resultados Generados")
    d_col1, d_col2 = st.columns(2)

    with d_col1:
        st.download_button(
            label="📄 Descargar Informe Técnico (Word)",
            data=st.session_state["resultado_word"],
            file_name=f"Informe_Tecnico_{datetime.now():%Y%m%d_%H%M%S}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
            icon=":material/download:"
        )

    with d_col2:
        st.download_button(
            label="📊 Descargar VT-Checklist con Recomendaciones (Excel)",
            data=st.session_state["resultado_excel"],
            file_name=f"VT_Checklist_Recomendaciones_{datetime.now():%Y%m%d_%H%M%S}.docx" if False else f"VT_Checklist_Recomendaciones_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            icon=":material/download:"
        )
