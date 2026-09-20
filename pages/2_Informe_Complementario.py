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
    import checklist
    import anexos
    import inventario
    import recomendaciones
    import reportes_pdf
    from generar_informe import ejecutar_proceso_grupo_complementario
    MODULOS_DISPONIBLES = True
except ImportError as e:
    MODULOS_DISPONIBLES = False
    error_import = str(e)

RUTA_PLANTILLA = DIR_RAIZ / "plantilla_complementario.docx"
RUTA_MAESTRA = DIR_RAIZ / "BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx"
RUTA_CATALOGO = DIR_RAIZ / "Catalogo_Hallazgos_Recomendaciones.xlsx"

st.set_page_config(
    page_title="Informe Complementario - Ademinsac",
    page_icon="📎",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    footer {visibility: hidden;}
    .stApp { background-color: #EEF2F7; }
    .block-container { padding-top: 1.6rem !important; }
    .header-banner {
        background: linear-gradient(120deg, #3E2A0B 0%, #7E5E1E 60%, #94742C 100%);
        padding: 22px 30px;
        border-radius: 14px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 12px 28px rgba(56, 32, 11, 0.18);
        position: relative;
        overflow: hidden;
    }
    .header-banner::after {
        content: "";
        position: absolute; top: 0; right: 0; bottom: 0; width: 6px;
        background: linear-gradient(180deg, #0B2038, #1E4E7E);
    }
    .header-title { font-size: 24px; font-weight: 800; letter-spacing: 0.3px; margin: 0; color: #FFFFFF; }
    .header-subtitle { font-size: 13.5px; color: #F0E3C9; margin-top: 4px; font-weight: 500; }
    </style>
""",
    unsafe_allow_html=True,
)

st.html("""
    <div class="header-banner">
        <div class="header-title">📎 INFORME COMPLEMENTARIO / ANEXO ADICIONAL</div>
        <div class="header-subtitle">Para líneas de un grupo ya cerrado que se inspeccionan tiempo después — solo inspección visual (VT), sin PSAIM</div>
    </div>
""")

st.info(
    "Este módulo es **independiente** del informe principal: usa su propia plantilla "
    "y no afecta en nada la generación del informe normal. Úsalo cuando, de un grupo "
    "de tuberías ya entregado, quedaron líneas sin inspeccionar en su momento y ahora "
    "se inspeccionan e informan como anexo al informe principal."
)

c1, c2, c3 = st.columns(3)
with c1:
    st.success("🟢 Base Maestra OK" if RUTA_MAESTRA.exists() else "⚠️ Falta Base Maestra")
with c2:
    st.success("🟢 Plantilla Complementaria OK" if RUTA_PLANTILLA.exists() else "⚠️ Falta plantilla_complementario.docx")
with c3:
    if MODULOS_DISPONIBLES:
        st.success("🟢 Módulos Backend OK")
    else:
        st.error("🔴 Error al importar módulos")

if not MODULOS_DISPONIBLES:
    st.warning(f"Detalle de importación: {error_import}")

st.markdown("---")
st.subheader("📝 Datos del Anexo Complementario")

col_a, col_b = st.columns(2)
with col_a:
    codigo_informe_principal = st.text_input(
        "Código del informe principal",
        placeholder="Ej: ADEMINSAC-FIAB-RLP-1820-2025",
        help="El código del informe original ya cerrado, al que este documento complementa.",
    )
with col_b:
    st.text_input(
        "Código de este informe complementario",
        value="(se toma de la columna CODIGO DE INFORME del detalle de grupo)",
        disabled=True,
        help='Debe incluir el número de anexo antes del año, ej: ADEMINSAC-FIAB-RLP-1820-1-2025.',
    )

sumario_texto = st.text_area(
    "1.0 Sumario de Inspección (texto libre)",
    height=140,
    placeholder=(
        "Como resultado de la aplicación de las técnicas de inspección no destructiva y de la "
        "evaluación de integridad contempladas dentro del alcance del servicio (inspección visual "
        "externa), se determinó que las Líneas N° ... presentan ..."
    ),
    help="Redacción específica de qué líneas presentan qué hallazgos -- se escribe a mano porque "
         "es demasiado particular para generarla de forma confiable de manera automática.",
)

st.markdown("---")
st.subheader("📁 Carga de Archivos (Obligatorios: 1)")

col1, col2, col3 = st.columns(3)
with col1:
    f_m3m6 = st.file_uploader(
        "1. Detalle de líneas (Excel, con columna N° ORIGINAL) [Obligatorio]",
        type=["xlsx", "xls"], key="c_m3m6",
    )
with col2:
    f_cons = st.file_uploader("2. VT-CHECK LIST (Excel) [Opcional]", type=["xlsx", "xls"], key="c_cons")
with col3:
    f_fotos = st.file_uploader(
        "3. Fotos de la Unidad [Opcional]", type=["jpg", "jpeg", "png"],
        accept_multiple_files=True, key="c_fotos",
    )

col4, col5 = st.columns(2)
with col4:
    f_pid = st.file_uploader("4. P&ID del grupo (PDF) [Opcional]", type=["pdf"], key="c_pid")
with col5:
    f_isometricos = st.file_uploader(
        "5. Isométricos por línea (PDF, uno por archivo) [Opcional]",
        type=["pdf"], accept_multiple_files=True, key="c_isometricos"
    )

tags_detectados = []
if f_m3m6 is not None and MODULOS_DISPONIBLES:
    try:
        lineas_preview = inventario.cargar_alcance(io.BytesIO(f_m3m6.getbuffer()))
        tags_detectados = [ln["tag"] for ln in lineas_preview]
        if not any(ln.get("numero_original") for ln in lineas_preview):
            st.warning(
                "El detalle de líneas no trae la columna \"N° ORIGINAL\" (o está vacía): "
                "la tabla N°/SAP/Línea del informe quedará numerada 1, 2, 3... en vez de "
                "conservar el N° del informe principal."
            )
    except Exception as e:
        st.warning(f"No se pudieron leer las líneas del detalle todavía: {e}")

isometricos_por_tag = {}
if f_isometricos:
    if not tags_detectados:
        st.info("Carga primero el Detalle de líneas (1) para poder asignar cada isométrico a su línea.")
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
                f"Línea para «{f_iso.name}»", opciones, index=idx_default, key=f"c_iso_tag_{f_iso.name}"
            )
            if seleccion != "-- Sin asignar --":
                isometricos_por_tag[seleccion] = f_iso

st.markdown("---")

if st.button("🚀 Ejecutar Generación de Informe Complementario", type="primary", use_container_width=True, icon=":material/play_arrow:"):
    if not f_m3m6:
        st.error("Por favor, carga el Detalle de líneas (1) para continuar.")
    elif not sumario_texto or not sumario_texto.strip():
        st.error("Por favor, escribe el texto del Sumario de Inspección (1.0).")
    elif not MODULOS_DISPONIBLES:
        st.error("No se pueden ejecutar los procesos porque faltan módulos en el repositorio.")
    else:
        with st.spinner("Procesando datos reales del anexo complementario..."):
            try:
                recomendaciones.recargar_catalogo(RUTA_CATALOGO)
                with tempfile.TemporaryDirectory() as tmpdir:
                    tmp_path = Path(tmpdir)

                    path_m3m6 = tmp_path / f_m3m6.name
                    path_m3m6.write_bytes(f_m3m6.getbuffer())

                    path_cons = None
                    if f_cons is not None:
                        path_cons = tmp_path / f_cons.name
                        path_cons.write_bytes(f_cons.getbuffer())

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
                    for i, foto in enumerate(f_fotos or []):
                        f_path = dir_fotos / foto.name
                        f_path.write_bytes(foto.getbuffer())
                        if i == 0:
                            ruta_primera_foto = f_path

                    grupo_input = Path(f_m3m6.name).stem.replace("(", "").replace(")", "").strip()

                    resultado = ejecutar_proceso_grupo_complementario(
                        grupo_buscado=grupo_input,
                        ruta_maestro=path_m3m6,
                        ruta_base_lineas=RUTA_MAESTRA,
                        ruta_plantilla_word=RUTA_PLANTILLA,
                        dir_salida=str(tmp_path),
                        ruta_foto=ruta_primera_foto,
                        ruta_checklist=path_cons,
                        codigo_informe_principal=codigo_informe_principal,
                        sumario_texto=sumario_texto,
                    )

                    out_word_path = Path(resultado["ruta_word"])
                    out_excel_path = Path(resultado["ruta_checklist"]) if resultado["ruta_checklist"] else None
                    if not out_word_path.exists():
                        raise FileNotFoundError("El motor backend no generó el archivo Word en el directorio de salida.")

                    dir_anexos = tmp_path / "anexos_pdf"
                    dir_anexos.mkdir(exist_ok=True)

                    checklists_vt_pdf = {}
                    if out_excel_path and out_excel_path.exists():
                        checklists_vt_pdf = reportes_pdf.generar_pdf_checklist_por_tag(
                            str(out_excel_path), str(dir_anexos)
                        )

                    config_anexos = {
                        "lineas": resultado["lineas_alcance"],
                        "anexos": {
                            "pid_pdf": str(path_pid) if path_pid else None,
                            "isometricos": rutas_iso_por_tag,
                            "checklists_vt_pdf": checklists_vt_pdf,
                        },
                    }
                    dir_anexos_finales = tmp_path / "anexos_finales"
                    # incluir_anexo_c=False: un informe complementario nunca lleva
                    # Anexo C (Ultrasonido/PSAIM) -- es siempre solo inspección visual.
                    anexos_generados, avisos_anexos = anexos.construir_anexos(
                        config_anexos, str(dir_anexos_finales), incluir_anexo_c=False
                    )

                    codigo_informe = resultado.get("codigo_informe") or grupo_input
                    dir_compilado = tmp_path / "informe_compilado"
                    ruta_compilado, aviso_compilado = anexos.construir_informe_compilado(
                        str(out_word_path), anexos_generados, str(dir_compilado), codigo_informe
                    )
                    compilado_bytes = Path(ruta_compilado).read_bytes() if ruta_compilado else None

                    out_zip_path = tmp_path / f"Anexos_Complementario_{grupo_input}.zip"
                    with zipfile.ZipFile(out_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                        for ruta_anexo in anexos_generados:
                            zipf.write(ruta_anexo, arcname=os.path.basename(ruta_anexo))
                        for foto in (f_fotos or []):
                            zipf.write(dir_fotos / foto.name, arcname=f"fotos/{foto.name}")

                    word_bytes = out_word_path.read_bytes()
                    excel_bytes = out_excel_path.read_bytes() if out_excel_path and out_excel_path.exists() else None
                    anexos_bytes = out_zip_path.read_bytes()

                st.session_state["c_res_word"] = word_bytes
                st.session_state["c_res_excel"] = excel_bytes
                st.session_state["c_res_anexos"] = anexos_bytes
                st.session_state["c_res_compilado"] = compilado_bytes
                st.session_state["c_nombre_archivo"] = anexos.nombre_archivo_seguro(codigo_informe)
                st.session_state["c_ok_gen"] = True

                avisos = list(resultado.get("avisos", [])) + list(avisos_anexos)
                if aviso_compilado:
                    avisos.append(aviso_compilado)
                st.success("¡Informe complementario, checklist y anexos generados con éxito!")

                if avisos:
                    with st.expander(f"Ver avisos ({len(avisos)})", expanded=False):
                        for a in avisos:
                            st.write(f"- {a}")

            except Exception as e:
                st.error("Error crítico en la ejecución de los motores backend:")
                st.exception(e)
                st.session_state["c_ok_gen"] = False

if st.session_state.get("c_ok_gen", False):
    st.markdown("---")
    st.subheader("📥 Descarga de Entregables")

    nombre_archivo = st.session_state.get("c_nombre_archivo", "Informe_Complementario")
    compilado_data = st.session_state.get("c_res_compilado")
    if compilado_data:
        st.download_button(
            "📦 Descargar Informe Compilado (100%)",
            data=compilado_data,
            file_name=f"{nombre_archivo}.pdf",
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

    tiene_excel = st.session_state.get("c_res_excel") is not None and len(st.session_state.get("c_res_excel", b"")) > 0
    cols = st.columns(3 if tiene_excel else 2)

    with cols[0]:
        word_data = st.session_state.get("c_res_word", b"")
        if word_data:
            st.download_button(
                "📄 Descargar Informe Word",
                data=word_data,
                file_name=f"{nombre_archivo}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

    if tiene_excel:
        with cols[1]:
            st.download_button(
                "📊 Descargar VT-CHECK LIST Parchado",
                data=st.session_state.get("c_res_excel"),
                file_name=f"VT-CHECK_LIST_{nombre_archivo}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with cols[2]:
            st.download_button(
                "📑 Descargar Anexos ZIP",
                data=st.session_state.get("c_res_anexos", b""),
                file_name=f"Anexos_{nombre_archivo}.zip",
                mime="application/zip",
                use_container_width=True
            )
    else:
        with cols[1]:
            st.download_button(
                "📑 Descargar Anexos ZIP",
                data=st.session_state.get("c_res_anexos", b""),
                file_name=f"Anexos_{nombre_archivo}.zip",
                mime="application/zip",
                use_container_width=True
            )
