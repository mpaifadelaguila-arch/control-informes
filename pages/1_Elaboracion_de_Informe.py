import io
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from docx import Document

# Configuración básica de rutas
RUTA_ACTUAL = Path(__file__).resolve().parent
DIR_RAIZ = RUTA_ACTUAL.parent if RUTA_ACTUAL.name == "pages" else RUTA_ACTUAL

st.set_page_config(
    page_title="Elaboración de Informes - Ademinsac",
    page_icon="📋",
    layout="wide"
)

st.title("Módulo de Elaboración de Informes")
st.success("¡La página cargó correctamente sin errores de sintaxis!")

st.markdown("---")
st.subheader("📁 Carga de Archivos Requeridos")

col1, col2, col3 = st.columns(3)
with col1:
    file_m3_m6 = st.file_uploader("1. Archivo M3 y M6 (Excel)", type=["xlsx", "xls"], key="indep_m3m6")
with col2:
    file_consolidadas = st.file_uploader("2. Archivo Consolidadas (Excel)", type=["xlsx", "xls"], key="indep_consolidadas")
with col3:
    fotos_unidad = st.file_uploader("3. Fotos de la Unidad (JPG/PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="indep_fotos")

st.markdown("---")

if st.button("🚀 Procesar Generación", type="primary", use_container_width=True):
    if not (file_m3_m6 and file_consolidadas and fotos_unidad):
        st.error("Por favor, carga los archivos obligatorios para continuar.")
    else:
        st.success("¡Archivos recibidos correctamente! Listo para generar los entregables.")
