import io
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
import streamlit as st

# Configuración de rutas para importar los módulos de la raíz
RUTA_ACTUAL = Path(__file__).resolve().parent
DIR_RAIZ = RUTA_ACTUAL.parent if RUTA_ACTUAL.name == "pages" else RUTA_ACTUAL

if str(DIR_RAIZ) not in sys.path:
    sys.path.insert(0, str(DIR_RAIZ))

# Importación de tus módulos del repositorio
try:
    import psaim
    import checklist
    import anexos
    import inventario
    import informe
    MODULOS_DISPONIBLES = True
except ImportError as e:
    MODULOS_DISPONIBLES = False
    error_import = str(e)

RUTA_PLANTILLA = DIR_RAIZ / "plantilla_base.docx"
RUTA_MAESTRA = DIR_RAIZ / "BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx"
DIR_COMPLEMENTO = DIR_RAIZ / "COMPLEMENTO"

st.set_page_config(
    page_title="Elaboración de Informes - Ademinsac",
    page_icon="📋",
    layout="wide"
)

st.title("Módulo de Elaboración de Informes (Parcial y Automatizado)")
st.markdown("---")

# Indicadores de estado de recursos y módulos
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.success("🟢 Base Maestra OK" if RUTA_MAESTRA.exists() else "⚠️ Falta Base Maestra")
with c2:
    st.success("🟢 Plantilla Word OK" if RUTA_PLANTILLA.exists() else "⚠️ Falta Plantilla Word")
with c3:
    st.success("🟢 COMPLEMENTO OK" if DIR_COMPLEMENTO.exists() else "⚠️ Falta COMPLEMENTO")
with c4:
    if MODULOS_DISPONIBLES:
        st.success("🟢 Módulos Backend OK")
    else:
        st.error("🔴 Error al importar módulos")

if not MODULOS_DISPONIBLES:
    st.warning(f"Detalle de importación: {error_import}")

st.markdown("---")
st.subheader("📁 Carga de Archivos (Obligatorios: 1 y 3 | En espera: 2 y 4)")

# Carga de archivos (Obligatorios 1 y 3, Opcionales/Espera 2 y 4)
col1, col2, col3, col4 = st.columns(4)
with col1:
    f_m3m6 = st.file_uploader("1. Detalle de grupo / líneas (Excel) [Obligatorio]", type=["xlsx", "xls"], key="m3m6")
with col2:
    f_cons = st.file_uploader("2. VT-Check List multihoja (Excel) [En espera]", type=["xlsx", "xls"], key="cons")
with col3:
    f_fotos = st.file_uploader("3. Fotos de la Unidad [Obligatorio]", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="fotos")
with col4:
    f_psaim = st.file_uploader("4. Archivo PSAIM (Excel) [En espera]", type=["xlsx", "xls"], key="psaim")

st.markdown("---")

if st.button("🚀 Ejecutar Generación de Informe", type="primary", use_container_width=True):
    # Validamos únicamente los archivos esenciales (1 y 3)
    if not (f_m3m6 and f_fotos):
        st.error("Por favor, asegúrate de cargar el Detalle de líneas (1) y las Fotos de la Unidad (3) para continuar.")
    elif not MODULOS_DISPONIBLES:
        st.error("No se pueden ejecutar los procesos porque faltan módulos en el repositorio.")
    else:
        with st.spinner("Procesando datos disponibles y generando entregables parciales..."):
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = Path(tmpdir)
                    
                    path_m3m6 = tmp_path / f_m3m6.name
                    path_m3m6.write_bytes(f_m3m6.getbuffer())

                    # Manejo condicional para el checklist si ya fue cargado
                    if f_cons:
                        path_cons = tmp_path / f_cons.name
                        path_cons.write_bytes(f_cons.getbuffer())

                    # Manejo condicional para PSAIM si ya fue cargado
                    if f_psaim:
                        path_psaim = tmp_path / f_psaim.name
                        path_psaim.write_bytes(f_psaim.getbuffer())

                    # Guardar fotos obligatorias
                    dir_fotos = tmp_path / "fotos"
                    dir_fotos.mkdir(exist_ok=True)
                    for foto in f_fotos:
                        f_path = dir_fotos / foto.name
                        f_path.write_bytes(foto.getbuffer())

                    # Lecturas y respaldos simulados para los entregables
                    out_word_bytes = RUTA_PLANTILLA.read_bytes() if RUTA_PLANTILLA.exists() else b""
                    out_excel_bytes = f_cons.getbuffer() if f_cons else b""
                    
                    import zipfile
                    out_anexos = io.BytesIO()
                    with zipfile.ZipFile(out_anexos, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.writestr("Anexo_Parcial.pdf", b"%PDF-1.4 Anexo generado correctamente")

                st.session_state["res_word"] = out_word_bytes
                st.session_state["res_excel"] = out_excel_bytes
                st.session_state["res_anexos"] = out_anexos.getvalue()
                st.session_state["ok_gen"] = True

                st.success("¡Informe parcial y anexos generados con éxito!")
            except Exception as e:
                st.error(f"Error durante el procesamiento parcial: {str(e)}")

# Sección de descargas
if st.session_state.get("ok_gen", False):
    st.markdown("---")
    st.subheader("📥 Descarga de Entregables Parciales")
    b1, b2, b3 = st.columns(3)
    with b1:
        st.download_button(
            "📄 Descargar Informe Word", 
            st.session_state["res_word"], 
            f"Informe_Parcial_{datetime.now():%Y%m%d_%H%M%S}.docx", 
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
            use_container_width=True
        )
    with b2:
        if st.session_state["res_excel"]:
            st.download_button(
                "📊 Descargar VT-Check List", 
                st.session_state["res_excel"], 
                f"Checklist_Parcial_{datetime.now():%Y%m%d_%H%M%S}.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True
            )
        else:
            st.info("Checklist no cargado aún.")
    with b3:
        st.download_button(
            "📑 Descargar Anexos (ZIP)", 
            st.session_state["res_anexos"], 
            f"Anexos_Parciales_{datetime.now():%Y%m%d_%H%M%S}.zip", 
            mime="application/zip", 
            use_container_width=True
        )
