import io
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

# ==============================================================================
# CONFIGURACIÓN DE RUTAS Y COMPONENTES
# ==============================================================================
RUTA_ACTUAL = Path(__file__).resolve().parent
DIR_RAIZ = RUTA_ACTUAL.parent if RUTA_ACTUAL.name == "_scripts" else RUTA_ACTUAL

DIR_COMPLEMENTO = DIR_RAIZ / "COMPLEMENTO"
DIR_SCRIPTS = DIR_RAIZ / "_scripts"

RUTA_BASE_DATOS_MAESTRA = DIR_RAIZ / "control-informe" / "BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx"
RUTA_COMPENDIO = DIR_COMPLEMENTO / "COMPENDIO TÉCNICO UNIFICADO DE HALLAZGOS Y RECOMENDACIONES TÉCNICAS.REV.1.docx"
RUTA_POE = DIR_COMPLEMENTO / "PROCEDIMIENTO OPERATIVO ESTANDARIZADO (POE).docx"

if str(DIR_SCRIPTS) not in sys.path:
    sys.path.append(str(DIR_SCRIPTS))

try:
    import inventario
except ImportError:
    inventario = None

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
        <div class="header-subtitle">Generación de reportes técnicos utilizando compendios, plantillas y herramientas de inventario</div>
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
# CARGA DE ARCHIVOS DEL USUARIO
# ==============================================================================
st.subheader("📁 Carga de Archivos Requeridos")

col1, col2, col3 = st.columns(3)
with col1:
    file_m3_m6 = st.file_uploader("1. Archivo M3 y M6 (Excel)", type=["xlsx", "xls"], key="indep_m3m6")
with col2:
    file_consolidadas = st.file_uploader("2. Archivo Consolidadas (Excel)", type=["xlsx", "xls"], key="indep_consolidadas")
with col3:
    fotos_unidad = st.file_uploader("3. Fotos de la Unidad (JPG/PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="indep_fotos")

def generar_excel_formateado(df, nombre_hoja="REPORTE"):
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=nombre_hoja[:31])
        ws = writer.book[nombre_hoja[:31]]
        ws.freeze_panes = "A2"
        
        header_fill = PatternFill("solid", fgColor="0E2A47")
        for cell in ws[1]:
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)
            
    salida.seek(0)
    return salida.getvalue()

# ==============================================================================
# PROCESAMIENTO Y GENERACIÓN
# ==============================================================================
st.markdown("---")

if st.button("🚀 Procesar Generación de Informe", type="primary", use_container_width=True):
    if not (file_m3_m6 and file_consolidadas and fotos_unidad):
        st.error("Debe cargar los 3 elementos obligatorios (M3/M6, Consolidadas y Fotos) para ejecutar la herramienta.")
    else:
        with st.spinner("Procesando datos con el motor de inventario y referencias técnicas..."):
            try:
                df_m3m6 = pd.read_excel(file_m3_m6)
                df_cons = pd.read_excel(file_consolidadas)

                # Ejecución mediante el módulo de inventario e integración de datos
                if inventario and hasattr(inventario, "procesar_informes"):
                    res_final, res_ejecucion = inventario.procesar_informes(
                        df_m3m6, df_cons, fotos_unidad
                    )
                    bytes_final = generar_excel_formateado(res_final, "INFORME_FINAL")
                    bytes_ejecucion = generar_excel_formateado(res_ejecucion, "RESUMEN_EJECUCION")
                else:
                    # Lógica de respaldo directo si el módulo no expone la función
                    bytes_final = generar_excel_formateado(df_m3m6, "INFORME_PROCESADO")
                    bytes_ejecucion = generar_excel_formateado(df_cons, "RESUMEN_PROCESADO")

                st.session_state["resultado_informe"] = bytes_final
                st.session_state["resultado_ejecucion"] = bytes_ejecucion
                st.session_state["procesado_exito"] = True
                st.success("¡Procesamiento completado con éxito!")

            except Exception as e:
                st.error(f"Error durante el procesamiento técnico: {str(e)}")

# ==============================================================================
# DESCARGA DE RESULTADOS
# ==============================================================================
if st.session_state.get("procesado_exito", False):
    st.subheader("📥 Descarga de Resultados Generados")
    d_col1, d_col2 = st.columns(2)

    with d_col1:
        st.download_button(
            label="📄 Descargar Informe Final Generado (Excel)",
            data=st.session_state["resultado_informe"],
            file_name=f"Informe_Tecnico_Final_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            icon=":material/download:"
        )

    with d_col2:
        st.download_button(
            label="📊 Descargar Resumen de Ejecución (Excel)",
            data=st.session_state["resultado_ejecucion"],
            file_name=f"Resumen_Ejecucion_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            icon=":material/download:"
        )
