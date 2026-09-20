import io
import os
import sys
import tempfile
import zipfile
from pathlib import Path
import streamlit as st

# ==============================================================================
# CONFIGURACIÓN DE RUTAS Y CONFIGURACIÓN DE PÁGINA
# ==============================================================================
RUTA_ACTUAL = Path(__file__).resolve().parent
DIR_RAIZ = RUTA_ACTUAL.parent if RUTA_ACTUAL.name == "pages" else RUTA_ACTUAL

if str(DIR_RAIZ) not in sys.path:
    sys.path.insert(0, str(DIR_RAIZ))

try:
    import psaim
    import checklist
    import anexos
    import inventario
    import recomendaciones
    import reportes_pdf
    from generar_informe import ejecutar_proceso_grupo
    MODULOS_DISPONIBLES = True
except ImportError as e:
    MODULOS_DISPONIBLES = False
    error_import = str(e)

RUTA_PLANTILLA = DIR_RAIZ / "plantilla_base.docx"
RUTA_MAESTRA = DIR_RAIZ / "BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx"
RUTA_CATALOGO = DIR_RAIZ / "Catalogo_Hallazgos_Recomendaciones.xlsx"
DIR_COMPLEMENTO = DIR_RAIZ / "COMPLEMENTO"

st.set_page_config(
    page_title="Elaboración de Informes - Ademinsac",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    footer {visibility: hidden;}
    :root {
        --primary-navy: #0E2A47;
        --secondary-navy: #1A3E68;
        --gold-accent: #D4AF37;
        --bg-card: #FFFFFF;
        --border-color: #E2E8F0;
        --text-main: #1E293B;
        --text-sub: #64748B;
    }
    .stApp { background-color: #EEF2F7; }
    .block-container { padding-top: 1.6rem !important; }
    .header-banner {
        background: linear-gradient(120deg, #0B2038 0%, #1E4E7E 60%, #2C6494 100%);
        padding: 22px 30px;
        border-radius: 14px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 12px 28px rgba(11, 32, 56, 0.18);
        position: relative;
        overflow: hidden;
    }
    .header-banner::after {
        content: "";
        position: absolute; top: 0; right: 0; bottom: 0; width: 6px;
        background: linear-gradient(180deg, #E7BE30, #C99A1E);
    }
    .header-title { font-size: 24px; font-weight: 800; letter-spacing: 0.3px; margin: 0; color: #FFFFFF; }
    .header-subtitle { font-size: 13.5px; color: #C9DCEE; margin-top: 4px; font-weight: 500; }
    </style>
""",
    unsafe_allow_html=True,
)

st.html("""
    <div class="header-banner">
        <div class="header-title">MÓDULO DE ELABORACIÓN DE INFORMES</div>
        <div class="header-subtitle">Generación y procesamiento automático de expedientes técnicos | Refinería La Pampilla</div>
    </div>
""")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.success("🟢 Base Maestra OK" if RUTA_MAESTRA.exists() else "⚠️ Falta Base Maestra")
with c2:
    st.success("🟢 Catálogo Hallazgos OK" if RUTA_CATALOGO.exists() else "⚠️ Falta Catálogo Hallazgos")
with c3:
    st.success("🟢 Plantilla Word OK" if RUTA_PLANTILLA.exists() else "⚠️ Falta Plantilla Word")
with c4:
    st.success("🟢 COMPLEMENTO OK" if DIR_COMPLEMENTO.exists() else "⚠️ Falta COMPLEMENTO")
with c5:
    if MODULOS_DISPONIBLES:
        st.success("🟢 Módulos Backend OK")
    else:
        st.error("🔴 Error al importar módulos")

if not MODULOS_DISPONIBLES:
    st.warning(f"Detalle de importación: {error_import}")

st.markdown("---")
st.subheader("📁 Carga de Archivos (Obligatorios: 1 y 3)")

col1, col2, col3, col4 = st.columns(4)
with col1:
    f_m3m6 = st.file_uploader("1. Detalle de grupo / líneas (Excel) [Obligatorio]", type=["xlsx", "xls"], key="m3m6")
with col2:
    f_cons = st.file_uploader("2. VT-CHECK LIST (Excel) [Opcional]", type=["xlsx", "xls"], key="cons")
with col3:
    f_fotos = st.file_uploader("3. Fotos de la Unidad [Obligatorio]", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="fotos")
with col4:
    f_psaim = st.file_uploader("4. Archivo PSAIM (Excel, una hoja por línea) [Opcional]", type=["xlsx", "xls"], key="psaim")

col5, col6 = st.columns(2)
with col5:
    f_pid = st.file_uploader("5. P&ID del grupo (PDF) [Opcional]", type=["pdf"], key="pid")
with col6:
    f_isometricos = st.file_uploader(
        "6. Isométricos por línea (PDF, uno por archivo) [Opcional]",
        type=["pdf"], accept_multiple_files=True, key="isometricos"
    )

# --- Detección de tags y asignación de isométricos a cada línea -------------
tags_detectados = []
if f_m3m6 is not None and MODULOS_DISPONIBLES:
    try:
        lineas_preview = inventario.cargar_alcance(io.BytesIO(f_m3m6.getbuffer()))
        tags_detectados = [ln["tag"] for ln in lineas_preview]
    except Exception as e:
        st.warning(f"No se pudieron leer las líneas del Detalle de grupo todavía: {e}")

isometricos_por_tag = {}
if f_isometricos:
    if not tags_detectados:
        st.info("Carga primero el Detalle de grupo/líneas (1) para poder asignar cada isométrico a su línea.")
    else:
        st.markdown("**Asignación de isométricos a cada línea:**")

        def _normaliza(s):
            return "".join(c for c in str(s).upper() if c.isalnum())

        tags_norm = {_normaliza(t): t for t in tags_detectados}
        for f_iso in f_isometricos:
            nombre_norm = _normaliza(f_iso.name)
            sugerido = next((t for tn, t in tags_norm.items() if tn and tn in nombre_norm), None)
            opciones = ["-- Sin asignar --"] + tags_detectados
            idx_default = opciones.index(sugerido) if sugerido in opciones else 0
            seleccion = st.selectbox(
                f"Línea para «{f_iso.name}»", opciones, index=idx_default, key=f"iso_tag_{f_iso.name}"
            )
            if seleccion != "-- Sin asignar --":
                isometricos_por_tag[seleccion] = f_iso

st.markdown("---")

if st.button("🚀 Ejecutar Generación de Informe Real", type="primary", use_container_width=True, icon=":material/play_arrow:"):
    if not (f_m3m6 and f_fotos):
        st.error("Por favor, asegúrate de cargar el Detalle de líneas (1) y las Fotos de la Unidad (3) para continuar.")
    elif not MODULOS_DISPONIBLES:
        st.error("No se pueden ejecutar los procesos porque faltan módulos en el repositorio.")
    else:
        with st.spinner("Procesando datos reales, imágenes y motores backend..."):
            try:
                # Se recarga el catálogo de hallazgos/recomendaciones desde su
                # Excel en cada generación, para que una edición reciente del
                # archivo (agregar o corregir un caso) surta efecto sin tener
                # que reiniciar la app -- igual que BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx.
                recomendaciones.recargar_catalogo(RUTA_CATALOGO)
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = Path(tmpdir)

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

                    path_pid = None
                    if f_pid is not None:
                        path_pid = tmp_path / f_pid.name
                        path_pid.write_bytes(f_pid.getbuffer())

                    dir_iso = tmp_path / "isometricos"
                    dir_iso.mkdir(exist_ok=True)
                    rutas_iso_por_tag = {}
                    for tag, f_iso in isometricos_por_tag.items():
                        p_iso = dir_iso / f_iso.name
                        p_iso.write_bytes(f_iso.getbuffer())
                        rutas_iso_por_tag[tag] = str(p_iso)

                    dir_fotos = tmp_path / "fotos"
                    dir_fotos.mkdir(exist_ok=True)

                    ruta_primera_foto = None
                    for i, foto in enumerate(f_fotos):
                        f_path = dir_fotos / foto.name
                        f_path.write_bytes(foto.getbuffer())
                        if i == 0:
                            ruta_primera_foto = f_path

                    grupo_input = Path(f_m3m6.name).stem.replace("(", "").replace(")", "").strip()

                    # --- LLAMADA DIRECTA A LOS MOTORES REALES ---
                    resultado = ejecutar_proceso_grupo(
                        grupo_buscado=grupo_input,
                        ruta_maestro=path_m3m6,
                        ruta_base_lineas=RUTA_MAESTRA,
                        ruta_plantilla_word=RUTA_PLANTILLA,
                        dir_salida=str(tmp_path),
                        ruta_foto=ruta_primera_foto,
                        ruta_checklist=path_cons,
                        ruta_psaim=path_psaim,
                    )

                    out_word_path = Path(resultado["ruta_word"])
                    out_excel_path = Path(resultado["ruta_checklist"]) if resultado["ruta_checklist"] else None
                    if not out_word_path.exists():
                        raise FileNotFoundError("El motor backend no generó el archivo Word en el directorio de salida.")

                    # --- ANEXOS REALES: P&ID + isométricos + checklist VT en PDF + PSAIM en PDF ---
                    dir_anexos = tmp_path / "anexos_pdf"
                    dir_anexos.mkdir(exist_ok=True)

                    checklists_vt_pdf = {}
                    if out_excel_path and out_excel_path.exists():
                        checklists_vt_pdf = reportes_pdf.generar_pdf_checklist_por_tag(
                            str(out_excel_path), str(dir_anexos)
                        )

                    psaim_pdf_por_tag = {}
                    if resultado.get("psaim_por_tag"):
                        inv = inventario.cargar_inventario(RUTA_MAESTRA)
                        inv_norm = {k.strip().upper(): v for k, v in inv.items()}
                        filas_tecnicas = []
                        for ln in resultado["lineas_alcance"]:
                            tag = ln["tag"]
                            datos, _ = inventario.cruzar_linea(tag, inv_norm.get(tag.strip().upper()))
                            filas_tecnicas.append({"tag": tag, **datos})
                        psaim_pdf_por_tag = reportes_pdf.generar_pdf_psaim_por_tag(
                            resultado["psaim_por_tag"], filas_tecnicas, str(dir_anexos)
                        )

                    config_anexos = {
                        "lineas": resultado["lineas_alcance"],
                        "anexos": {
                            "pid_pdf": str(path_pid) if path_pid else None,
                            "isometricos": rutas_iso_por_tag,
                            "checklists_vt_pdf": checklists_vt_pdf,
                            "psaim_pdf": psaim_pdf_por_tag,
                        },
                    }
                    dir_anexos_finales = tmp_path / "anexos_finales"
                    anexos_generados, avisos_anexos = anexos.construir_anexos(
                        config_anexos, str(dir_anexos_finales)
                    )

                    # --- Informe Compilado al 100%: Informe Word (convertido
                    # a PDF) + todos los anexos, fusionados en un solo PDF,
                    # nombrado con el Código de Informe (p.ej.
                    # "ADEMINSAC-FIAB-RLP-1133-2026"). ---
                    codigo_informe = resultado.get("codigo_informe") or grupo_input
                    dir_compilado = tmp_path / "informe_compilado"
                    ruta_compilado, aviso_compilado = anexos.construir_informe_compilado(
                        str(out_word_path), anexos_generados, str(dir_compilado), codigo_informe
                    )
                    compilado_bytes = (
                        Path(ruta_compilado).read_bytes() if ruta_compilado else None
                    )

                    # --- Empaquetado en ZIP: anexos reales + fotos de campo ---
                    out_zip_path = tmp_path / f"Anexos_Comprimidos_{grupo_input}.zip"
                    with zipfile.ZipFile(out_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                        for ruta_anexo in anexos_generados:
                            zipf.write(ruta_anexo, arcname=os.path.basename(ruta_anexo))
                        for foto in f_fotos:
                            zipf.write(dir_fotos / foto.name, arcname=f"fotos/{foto.name}")

                    word_bytes = out_word_path.read_bytes()
                    excel_bytes = out_excel_path.read_bytes() if out_excel_path and out_excel_path.exists() else None
                    anexos_bytes = out_zip_path.read_bytes()

                # Nombre de grupo real (columna "GRUPO DE TUBERÍAS" del
                # detalle), saneado para nombre de archivo de descarga.
                nombre_grupo_real = next(
                    (str(ln["grupo"]).strip() for ln in resultado["lineas_alcance"] if ln.get("grupo")),
                    grupo_input,
                )
                nombre_grupo_archivo = anexos.nombre_archivo_seguro(nombre_grupo_real)

                # Guardado persistente en session_state
                st.session_state["res_word"] = word_bytes
                st.session_state["res_excel"] = excel_bytes
                st.session_state["res_anexos"] = anexos_bytes
                st.session_state["res_compilado"] = compilado_bytes
                st.session_state["nombre_grupo_archivo"] = nombre_grupo_archivo
                st.session_state["nombre_compilado_archivo"] = anexos.nombre_archivo_seguro(codigo_informe)
                st.session_state["ok_gen"] = True

                avisos = list(resultado.get("avisos", [])) + list(avisos_anexos)
                if aviso_compilado:
                    avisos.append(aviso_compilado)
                st.success("¡Informe técnico, checklist y anexos generados y capturados con éxito!")

                pendientes = [a for a in avisos if a.startswith("Hoja") and "PENDIENTE" in a]
                otros = [a for a in avisos if a not in pendientes]

                if pendientes:
                    st.error(
                        f"⚠️ {len(pendientes)} hallazgo(s) requieren redacción manual del "
                        "especialista (ninguna regla automática calzó con confianza; el "
                        "hallazgo de campo se conservó intacto en el checklist)."
                    )
                    with st.expander("Ver detalle de pendientes de redacción manual", expanded=True):
                        for a in pendientes:
                            st.write(f"- {a}")

                if otros:
                    with st.expander(f"Ver detalle técnico ({len(otros)} avisos)", expanded=False):
                        for a in otros:
                            st.write(f"- {a}")

            except Exception as e:
                st.error("Error crítico en la ejecución de los motores backend:")
                st.exception(e)
                st.session_state["ok_gen"] = False

if st.session_state.get("ok_gen", False):
    st.markdown("---")
    st.subheader("📥 Descarga de Entregables Generados por el Sistema")

    nombre_grupo_archivo = st.session_state.get("nombre_grupo_archivo", "Grupo")
    nombre_compilado_archivo = st.session_state.get("nombre_compilado_archivo", nombre_grupo_archivo)
    compilado_data = st.session_state.get("res_compilado")
    if compilado_data:
        st.download_button(
            "📦 Descargar Informe Compilado (100%)",
            data=compilado_data,
            file_name=f"{nombre_compilado_archivo}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    else:
        st.warning(
            "No se pudo generar el Informe Compilado en PDF (LibreOffice no está "
            "disponible en el servidor). Los entregables individuales sí están "
            "listos para descarga abajo."
        )

    tiene_excel = st.session_state.get("res_excel") is not None and len(st.session_state.get("res_excel", b"")) > 0
    cols = st.columns(3 if tiene_excel else 2)

    with cols[0]:
        word_data = st.session_state.get("res_word", b"")
        if word_data:
            st.download_button(
                "📄 Descargar Informe Word Real",
                data=word_data,
                file_name=f"Informe_{nombre_grupo_archivo}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

    if tiene_excel:
        with cols[1]:
            excel_data = st.session_state.get("res_excel")
            st.download_button(
                "📊 Descargar VT-CHECK LIST Parchado",
                data=excel_data,
                file_name=f"VT-CHECK_LIST_{nombre_grupo_archivo}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with cols[2]:
            anexos_data = st.session_state.get("res_anexos", b"")
            st.download_button(
                "📑 Descargar Anexos ZIP",
                data=anexos_data,
                file_name=f"Anexos_{nombre_grupo_archivo}.zip",
                mime="application/zip",
                use_container_width=True
            )
    else:
        with cols[1]:
            anexos_data = st.session_state.get("res_anexos", b"")
            st.download_button(
                "📑 Descargar Anexos ZIP",
                data=anexos_data,
                file_name=f"Anexos_{nombre_grupo_archivo}.zip",
                mime="application/zip",
                use_container_width=True
            )
