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

    /* TARJETAS DE SECCIÓN */
    .st-key-tarjeta_estado, .st-key-tarjeta_carga, .st-key-tarjeta_iso,
    .st-key-tarjeta_resultados {
        background: #FFFFFF !important;
        border: 1px solid #DBE5EF;
        border-radius: 16px;
        padding: 20px 24px 24px;
        margin-bottom: 18px;
        box-shadow: 0 4px 14px rgba(15, 42, 70, 0.05);
    }
    .section-title-row {
        display: flex; align-items: center; justify-content: space-between;
        border-bottom: 1px solid #E7EDF3; padding-bottom: 12px; margin-bottom: 16px;
    }
    .section-title { display: flex; align-items: center; gap: 9px; font-size: 16px; font-weight: 800; color: #122F4C; }
    .badge-oblig {
        font-size: 11px; font-weight: 800; color: #8a6d1f; background: #FBF0D9;
        border: 1px solid #EFD9A0; border-radius: 999px; padding: 4px 12px; white-space: nowrap;
    }
    .badge-opt {
        font-size: 11px; font-weight: 800; color: #64748B; background: #F1F5F9;
        border-radius: 999px; padding: 4px 12px; white-space: nowrap;
    }

    /* FILA DE ESTADO DEL SISTEMA */
    .status-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
    @media (max-width: 1100px) { .status-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
    .status-pill { display: flex; align-items: center; gap: 10px; border-radius: 12px; padding: 11px 13px; }
    .status-pill.ok { background: #F0FAF4; border: 1px solid #CDEDD9; }
    .status-pill.bad { background: #FDF1F0; border: 1px solid #F3C9C6; }
    .status-icon {
        width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center;
        justify-content: center; flex-shrink: 0; color: #fff; font-size: 12px; font-weight: 900;
        line-height: 1;
    }
    .status-icon.ok { background: #159A68; }
    .status-icon.bad { background: #D8534F; }
    .status-label { font-size: 12.5px; font-weight: 700; color: #0F2E22; overflow-wrap: anywhere; }
    .status-pill.bad .status-label { color: #6B1E1A; }

    /* Columnas nativas de Streamlit: por defecto no se achican por debajo   */
    /* del contenido interno, lo que descuadra el ancho entre tarjetas con  */
    /* textos de distinto largo -- se fuerza el reparto parejo.             */
    [data-testid="stColumn"] { min-width: 0 !important; }
    [data-testid="stHorizontalBlock"] { align-items: stretch !important; }

    /* ETIQUETAS DE CARGA DE ARCHIVOS */
    .upload-label-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; margin-top: 6px; margin-bottom: 4px; }
    .upload-label-title { font-size: 13px; font-weight: 750; color: #1E293B; overflow-wrap: anywhere; }
    .upload-label-sub { font-size: 11px; color: #8592A3; margin-bottom: 6px; }
    [data-testid="stFileUploaderDropzone"] {
        border: 1.5px dashed #C7D4E1 !important;
        border-radius: 14px !important;
        background: #FBFDFF !important;
        transition: border-color .15s ease, box-shadow .15s ease;
    }
    [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #D4AF37 !important;
        box-shadow: 0 6px 18px rgba(15, 42, 70, .10);
    }

    /* FILAS DE ASIGNACIÓN DE ISOMÉTRICOS */
    .iso-row-name { display: flex; align-items: center; gap: 10px; font-size: 12.5px; font-weight: 650; color: #475569; padding-top: 8px; }

    /* BOTÓN PRINCIPAL */
    .stButton > button[kind="primary"] {
        background: linear-gradient(120deg, #0B2038, #1E4E7E 70%) !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 12px 22px !important;
        font-weight: 800 !important;
        letter-spacing: .3px;
        box-shadow: 0 12px 26px rgba(11, 32, 56, .22);
        transition: filter .15s ease, transform .15s ease;
    }
    .stButton > button[kind="primary"]:hover { filter: brightness(1.08); transform: translateY(-1px); }

    /* TARJETA DE DESCARGA DESTACADA (Informe Compilado) */
    .st-key-dl_compilado {
        background: linear-gradient(120deg, #0B2038, #1E4E7E 85%) !important;
        border-radius: 14px; padding: 16px 18px 18px; margin-bottom: 14px;
    }
    .dl-compilado-title { font-size: 14.5px; font-weight: 800; color: #FFFFFF; }
    .dl-compilado-sub { font-size: 11.5px; color: #C9DCEE; margin: 2px 0 10px; }
    .st-key-dl_compilado .stDownloadButton button {
        background: #F4D785 !important; color: #0B2038 !important; border: none !important;
        font-weight: 800 !important; border-radius: 10px !important;
    }
    .st-key-dl_compilado .stDownloadButton button:hover { filter: brightness(1.05); }

    /* TARJETAS DE DESCARGA SECUNDARIAS */
    .st-key-dl_word, .st-key-dl_excel, .st-key-dl_anexos {
        background: #F8FAFC !important; border: 1px solid #E7EDF3; border-radius: 12px; padding: 8px;
    }
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

_ICON_CHECK = "✓"
_ICON_WARN = "!"


def _status_pill(ok, label):
    tono = "ok" if ok else "bad"
    icono = _ICON_CHECK if ok else _ICON_WARN
    return (
        f'<div class="status-pill {tono}">'
        f'<div class="status-icon {tono}">{icono}</div>'
        f'<span class="status-label">{label}</span></div>'
    )


estado_html = "".join([
    _status_pill(RUTA_MAESTRA.exists(), "Base Maestra"),
    _status_pill(RUTA_CATALOGO.exists(), "Catálogo Hallazgos"),
    _status_pill(RUTA_PLANTILLA.exists(), "Plantilla Word"),
    _status_pill(DIR_COMPLEMENTO.exists(), "Complemento"),
    _status_pill(MODULOS_DISPONIBLES, "Módulos Backend"),
])

tarjeta_estado = st.container(key="tarjeta_estado")
tarjeta_estado.html(f"""
    <div class="section-title-row" style="margin-bottom:14px;">
        <div class="section-title">Estado del sistema</div>
    </div>
    <div class="status-grid">{estado_html}</div>
""")

if not MODULOS_DISPONIBLES:
    st.warning(f"Detalle de importación: {error_import}")

tarjeta_carga = st.container(key="tarjeta_carga")
tarjeta_carga.html("""
    <div class="section-title-row">
        <div class="section-title">📁 Carga de archivos</div>
        <span class="badge-oblig">Obligatorios: 1 y 3</span>
    </div>
""")

col1, col2, col3, col4 = tarjeta_carga.columns(4)
with col1:
    st.html('<div class="upload-label-row"><span class="upload-label-title">1. Detalle de grupo / líneas</span><span class="badge-oblig">Obligatorio</span></div><div class="upload-label-sub">Excel (.xlsx, .xls)</div>')
    f_m3m6 = st.file_uploader("1. Detalle de grupo / líneas", type=["xlsx", "xls"], key="m3m6", label_visibility="collapsed")
with col2:
    st.html('<div class="upload-label-row"><span class="upload-label-title">2. VT-CHECK LIST</span><span class="badge-opt">Opcional</span></div><div class="upload-label-sub">Excel (.xlsx, .xls)</div>')
    f_cons = st.file_uploader("2. VT-CHECK LIST", type=["xlsx", "xls"], key="cons", label_visibility="collapsed")
with col3:
    st.html('<div class="upload-label-row"><span class="upload-label-title">3. Fotos de la Unidad</span><span class="badge-oblig">Obligatorio</span></div><div class="upload-label-sub">JPG, PNG · múltiples</div>')
    f_fotos = st.file_uploader("3. Fotos de la Unidad", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="fotos", label_visibility="collapsed")
with col4:
    st.html('<div class="upload-label-row"><span class="upload-label-title">4. Archivo PSAIM</span><span class="badge-opt">Opcional</span></div><div class="upload-label-sub">Excel · una hoja por línea</div>')
    f_psaim = st.file_uploader("4. Archivo PSAIM", type=["xlsx", "xls"], key="psaim", label_visibility="collapsed")

col5, col6 = tarjeta_carga.columns(2)
with col5:
    st.html('<div class="upload-label-row"><span class="upload-label-title">5. P&amp;ID del grupo</span><span class="badge-opt">Opcional</span></div><div class="upload-label-sub">PDF</div>')
    f_pid = st.file_uploader("5. P&ID del grupo", type=["pdf"], key="pid", label_visibility="collapsed")
with col6:
    st.html('<div class="upload-label-row"><span class="upload-label-title">6. Isométricos por línea</span><span class="badge-opt">Opcional</span></div><div class="upload-label-sub">PDF · uno por archivo</div>')
    f_isometricos = st.file_uploader(
        "6. Isométricos por línea",
        type=["pdf"], accept_multiple_files=True, key="isometricos", label_visibility="collapsed"
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
        tarjeta_iso = st.container(key="tarjeta_iso")
        tarjeta_iso.html("""
            <div class="section-title-row" style="margin-bottom:6px;">
                <div class="section-title">🔗 Asignación de isométricos a cada línea</div>
            </div>
        """)

        def _normaliza(s):
            return "".join(c for c in str(s).upper() if c.isalnum())

        tags_norm = {_normaliza(t): t for t in tags_detectados}
        for f_iso in f_isometricos:
            nombre_norm = _normaliza(f_iso.name)
            sugerido = next((t for tn, t in tags_norm.items() if tn and tn in nombre_norm), None)
            opciones = ["-- Sin asignar --"] + tags_detectados
            idx_default = opciones.index(sugerido) if sugerido in opciones else 0
            col_nombre, col_select = tarjeta_iso.columns([2, 1], vertical_alignment="center")
            with col_nombre:
                st.html(f'<div class="iso-row-name">{f_iso.name}</div>')
            with col_select:
                seleccion = st.selectbox(
                    f"Línea para «{f_iso.name}»", opciones, index=idx_default,
                    key=f"iso_tag_{f_iso.name}", label_visibility="collapsed",
                )
            if seleccion != "-- Sin asignar --":
                isometricos_por_tag[seleccion] = f_iso

if st.button("Ejecutar Generación de Informe Real", type="primary", use_container_width=True, icon=":material/play_arrow:"):
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
                        checklists_vt_pdf = reportes_pdf.generar_pdf_checklist_vt_por_tag(
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
    tarjeta_resultados = st.container(key="tarjeta_resultados")
    tarjeta_resultados.html("""
        <div class="section-title-row">
            <div class="section-title">📥 Resultados de la generación</div>
        </div>
    """)

    nombre_grupo_archivo = st.session_state.get("nombre_grupo_archivo", "Grupo")
    nombre_compilado_archivo = st.session_state.get("nombre_compilado_archivo", nombre_grupo_archivo)
    compilado_data = st.session_state.get("res_compilado")
    if compilado_data:
        dl_compilado = tarjeta_resultados.container(key="dl_compilado")
        dl_compilado.html(f"""
            <div class="dl-compilado-title">📦 Informe Compilado al 100%</div>
            <div class="dl-compilado-sub">{nombre_compilado_archivo}.pdf · Word + todos los anexos en un solo PDF</div>
        """)
        dl_compilado.download_button(
            "Descargar Informe Compilado (100%)",
            data=compilado_data,
            file_name=f"{nombre_compilado_archivo}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    else:
        tarjeta_resultados.warning(
            "No se pudo generar el Informe Compilado en PDF (LibreOffice no está "
            "disponible en el servidor). Los entregables individuales sí están "
            "listos para descarga abajo."
        )

    tiene_excel = st.session_state.get("res_excel") is not None and len(st.session_state.get("res_excel", b"")) > 0
    cols = tarjeta_resultados.columns(3 if tiene_excel else 2)

    with cols[0]:
        word_data = st.session_state.get("res_word", b"")
        if word_data:
            dl_word = st.container(key="dl_word")
            dl_word.download_button(
                "📄 Informe Word Real",
                data=word_data,
                file_name=f"Informe_{nombre_grupo_archivo}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

    if tiene_excel:
        with cols[1]:
            excel_data = st.session_state.get("res_excel")
            dl_excel = st.container(key="dl_excel")
            dl_excel.download_button(
                "📊 VT-CHECK LIST Parchado",
                data=excel_data,
                file_name=f"VT-CHECK_LIST_{nombre_grupo_archivo}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with cols[2]:
            anexos_data = st.session_state.get("res_anexos", b"")
            dl_anexos = st.container(key="dl_anexos")
            dl_anexos.download_button(
                "📑 Anexos ZIP",
                data=anexos_data,
                file_name=f"Anexos_{nombre_grupo_archivo}.zip",
                mime="application/zip",
                use_container_width=True
            )
    else:
        with cols[1]:
            anexos_data = st.session_state.get("res_anexos", b"")
            dl_anexos = st.container(key="dl_anexos")
            dl_anexos.download_button(
                "📑 Anexos ZIP",
                data=anexos_data,
                file_name=f"Anexos_{nombre_grupo_archivo}.zip",
                mime="application/zip",
                use_container_width=True
            )
