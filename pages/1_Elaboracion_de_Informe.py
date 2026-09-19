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
    from generar_informe import ejecutar_proceso_grupo
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

st.title("Módulo de Elaboración de Informes (Ejecución Real con Motores)")
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

col1, col2, col3, col4 = st.columns(4)
with col1:
    f_m3m6 = st.file_uploader("1. Detalle de grupo / líneas (Excel) [Obligatorio]", type=["xlsx", "xls"], key="m3m6")
with col2:
    f_cons = st.file_uploader("2. VT-Check List multihoja (Excel) [En espera / Opcional]", type=["xlsx", "xls"], key="cons")
with col3:
    f_fotos = st.file_uploader("3. Fotos de la Unidad [Obligatorio]", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="fotos")
with col4:
    f_psaim = st.file_uploader("4. Archivo PSAIM (Excel) [En espera]", type=["xlsx", "xls"], key="psaim")

st.markdown("---")

if st.button("🚀 Ejecutar Generación de Informe Real", type="primary", use_container_width=True):
    if not (f_m3m6 and f_fotos):
        st.error("Por favor, asegúrate de cargar el Detalle de líneas (1) y las Fotos de la Unidad (3) para continuar.")
    elif not MODULOS_DISPONIBLES:
        st.error("No se pueden ejecutar los procesos porque faltan módulos en el repositorio.")
    else:
        with st.spinner("Procesando datos reales, imágenes y motores backend..."):
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = Path(tmpdir)
                    
                    # 1. Guardar archivos cargados en el directorio temporal
                    path_m3m6 = tmp_path / f_m3m6.name
                    path_m3m6.write_bytes(f_m3m6.getbuffer())

                    path_cons = None
                    if f_cons is not None:
                        path_cons = tmp_path / f_cons.name
                        path_cons.write_bytes(f_cons.getbuffer())

                    path_psaim = None
                    if f_psaim is not None:
                        path_psaim = tmp_path / f_psaim.name
                        path_psaim.write_bytes(f_psaim.getbuffer())

                    dir_fotos = tmp_path / "fotos"
                    dir_fotos.mkdir(exist_ok=True)
                    
                    ruta_primera_foto = None
                    for i, foto in enumerate(f_fotos):
                        f_path = dir_fotos / foto.name
                        f_path.write_bytes(foto.getbuffer())
                        if i == 0:
                            ruta_primera_foto = f_path

                    # Extraer el nombre del grupo (ej. "22-GLP-GT-023")
                    grupo_input = Path(f_m3m6.name).stem.replace("(", "").replace(")", "").strip()
                    
                    # --- LLAMADA DIRECTA A LOS MOTORES REALES ---
                    ejecutar_proceso_grupo(
                        grupo_buscado=grupo_input,
                        ruta_maestro=path_m3m6,
                        ruta_base_lineas=RUTA_MAESTRA,
                        ruta_plantilla_word=RUTA_PLANTILLA,
                        dir_salida=str(tmp_path),
                        ruta_foto=ruta_primera_foto
                    )

                    # Rutas de salida generadas por el backend
                    out_word_path = tmp_path / f"Informe_{grupo_input}.docx"
                    out_excel_path = tmp_path / f"Checklist_VT_{grupo_input}.xlsx"
                    out_zip_path = tmp_path / f"Anexos_Comprimidos_{grupo_input}.zip"

                    # D. Generación del ZIP de Anexos
                    import zipfile
                    with zipfile.ZipFile(out_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        zipf.write(path_m3m6, arcname=f"Detalle_Grupo_{f_m3m6.name}")
                        if path_cons:
                            zipf.write(path_cons, arcname=f"VT_Checklist_Original_{path_cons.name}")
                        for foto in f_fotos:
                            zipf.write(dir_fotos / foto.name, arcname=f"fotos/{foto.name}")

                    # Lectura obligatoria de los binarios generados
                    if not out_word_path.exists():
                        raise FileNotFoundError(f"El motor no generó el archivo Word para el grupo {grupo_input}.")
                    
                    word_bytes = out_word_path.read_bytes()
                    excel_bytes = out_excel_path.read_bytes() if out_excel_path.exists() else (path_cons.read_bytes() if path_cons else None)
                    anexos_bytes = out_zip_path.read_bytes()

                # Guardar en session_state de manera persistente
                st.session_state["res_word"] = word_bytes
                st.session_state["res_excel"] = excel_bytes
                st.session_state["res_anexos"] = anexos_bytes
                st.session_state["ok_gen"] = True

                st.success("¡Informes, VT parchado y anexos generados con éxito por los motores!")
            
            except Exception as e:
                st.error("Error crítico en la ejecución de los motores backend:")
                st.exception(e)
                st.session_state["ok_gen"] = False

# Sección de descargas conectada a los resultados reales
if st.session_state.get("ok_gen", False):
    st.markdown("---")
    st.subheader("📥 Descarga de Entregables Generados por el Sistema")
    
    tiene_excel = st.session_state.get("res_excel") is not None and len(st.session_state.get("res_excel", b"")) > 0
    cols = st.columns(3 if tiene_excel else 2)
    
    with cols[0]:
        word_data = st.session_state.get("res_word", b"")
        if word_data:
            st.download_button(
                "📄 Descargar Informe Word Real", 
                data=word_data, 
                file_name=f"Informe_Tecnico_{datetime.now():%Y%m%d_%H%M%S}.docx", 
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                use_container_width=True
            )
        
    if tiene_excel:
        with cols[1]:
            excel_data = st.session_state.get("res_excel")
            st.download_button(
                "📊 Descargar VT-Check List Parchado", 
                data=excel_data, 
                file_name=f"Checklist_Parchado_{datetime.now():%Y%m%d_%H%M%S}.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True
            )
        with cols[2]:
            anexos_data = st.session_state.get("res_anexos", b"")
            st.download_button(
                "📑 Descargar Anexos ZIP", 
                data=anexos_data, 
                file_name=f"Anexos_Comprimidos_{datetime.now():%Y%m%d_%H%M%S}.zip", 
                mime="application/zip", 
                use_container_width=True
            )
    else:
        with cols[1]:
            anexos_data = st.session_state.get("res_anexos", b"")
            st.download_button(
                "📑 Descargar Anexos ZIP", 
                data=anexos_data, 
                file_name=f"Anexos_Comprimidos_{datetime.now():%Y%m%d_%H%M%S}.zip", 
                mime="application/zip", 
                use_container_width=True
            )
