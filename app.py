import io
import json
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="CONTROL INTERNO DE INFORMES - ADEMINSAC",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- ESTILOS CSS PROFESIONALES Y PALETA CORPORATIVA ---
st.markdown(
    """
    <style>
    footer {visibility: hidden;}
    .stAppDeployButton {display:none !important;}
    header {visibility: hidden !important;}

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

    /* ---------- HEADER ---------- */
    .header-banner {
        background: linear-gradient(120deg, #0B2038 0%, #1E4E7E 60%, #2C6494 100%);
        padding: 24px 32px;
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
    .header-title { font-size: 26px; font-weight: 800; letter-spacing: 0.3px; margin: 0; color: #FFFFFF; }
    .header-subtitle { font-size: 14px; color: #C9DCEE; margin-top: 5px; font-weight: 500; }

    /* ---------- CONTENEDORES DE SECCIÓN (st.container(key=...)) ---------- */
    .st-key-panel_control, .st-key-sistema_control {
        background: #FFFFFF !important;
        border: 1px solid #DBE5EF;
        border-radius: 16px;
        padding: 20px 22px 22px;
        margin-bottom: 20px;
        box-shadow: 0 4px 14px rgba(15, 42, 70, 0.05);
    }
    .section-title {
        font-size: 1.02rem;
        font-weight: 800;
        color: #122F4C;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid #E7EDF3;
    }

    /* ---------- FILA DE BLOQUES KPI (horizontal, 5 columnas) ---------- */
    .kpi-row {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        align-items: stretch;
        gap: 12px;
    }
    @media (max-width: 1100px) {
        .kpi-row { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    }
    @media (max-width: 700px) {
        .kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    .kpi-block-card {
        background: #F4F8FC;
        border: 1px solid #E1E9F1;
        border-radius: 14px;
        padding: 12px 14px 14px;
        min-width: 0;
        display: flex;
        flex-direction: column;
        height: 100%;
        box-sizing: border-box;
    }
    .kpi-block-title {
        font-size: .68rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .5px;
        color: #5D7086;
        margin-bottom: 10px;
        white-space: nowrap;
    }
    .kpi-items { display: grid; gap: 8px; flex: 1; align-content: start; }
    .kpi-item {
        background: #FFFFFF;
        border: 1px solid #E6EDF4;
        border-left: 3.5px solid var(--tone);
        border-radius: 0 9px 9px 0;
        padding: 7px 11px;
        min-width: 0;
    }
    .kpi-item-label {
        font-size: .63rem;
        font-weight: 750;
        text-transform: uppercase;
        color: #5D7086;
        letter-spacing: .2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .kpi-item-value { font-size: 1.35rem; font-weight: 800; color: #102E4C; line-height: 1.15; }

    /* ---------- PESTAÑAS DISTRIBUIDAS EN TODO EL ANCHO ---------- */
    .st-key-sistema_control .stTabs [data-baseweb="tab-list"],
    .st-key-sistema_control .stTabs [role="tablist"] {
        display: flex !important;
        width: 100% !important;
        gap: 5px !important;
        flex-wrap: wrap;
        background-color: #EEF3F9;
        padding: 6px;
        border-radius: 10px;
    }
    .st-key-sistema_control .stTabs [data-baseweb="tab"],
    .st-key-sistema_control .stTabs button[role="tab"] {
        flex: 1 1 auto !important;
        min-width: 110px;
        justify-content: center !important;
        height: 38px;
        border-radius: 7px;
        font-size: 11.5px;
        font-weight: 650;
        color: #475569;
        padding: 0 8px !important;
        background: #FFFFFF;
        border: 1px solid #DFE7EF;
        text-align: center;
        white-space: nowrap;
    }
    .st-key-sistema_control .stTabs [aria-selected="true"] {
        background-color: #0E2A47 !important;
        color: #FFFFFF !important;
        border-color: #0E2A47 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .stDataFrame, div[data-testid="stDataEditor"] {
        background-color: #FFFFFF !important;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        padding: 4px;
    }
    div[data-testid="stExpander"] { background:#fff; border-color:#dbe5ef; border-radius:12px; }
    </style>
""",
    unsafe_allow_html=True,
)

DB_FILE = "database_informes.json"
SOLICITUDES_FILE = "database_solicitudes.json"

COLUMNAS_EXCEL = [
    "ITEM POR MES", "IT2", "UNIDAD", "MES", "LINEAS", "CODIGO DE INFORME",
    "GRUPO DE TUBERÍAS", "SAP", "ALCANCE DEL SERVICIO",
    "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "OBSERVACIÓN", "ESTADO - VALORIZACIÓN"
]

ORDEN_MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SETIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]

ESPECIALISTAS_LISTA = ["Jesús Rehkoff Díaz", "M. Paifa", "Julio Ponce", "Omar", "Christopher", "Timana", "Ingrid"]
REVISORES_PSAIM_LISTA = ["Franmary Gutierrez", "Alejandro Macury", "M. Paifa", "Julio Ponce", "Omar", "Christopher", "Timana", "Ingrid"]
PERSONAL_LISTA_BASE = ["M. Paifa", "Julio Ponce", "Omar", "Christopher", "Timana", "Ingrid", "Juan José", "Dante", "Jesús Rehkoff Díaz", "Franmary Gutierrez", "Alejandro Macury", "Otro Inspector"]

def formatear_entero_limpio(valor):
    """Limpia cadenas o números eliminando la terminación decimal .0 provocada por Pandas."""
    if pd.isna(valor) or valor is None:
        return ""
    val_str = str(valor).strip()
    if val_str.endswith(".0"):
        return val_str[:-2]
    return val_str

def texto_normalizado(texto):
    if pd.isna(texto): return ""
    t = str(texto).strip().upper()
    replacements = {"Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ü": "U", "Ñ": "N"}
    for orig, repl in replacements.items(): t = t.replace(orig, repl)
    return t

def limpiar_estado_y_responsable(df_input):
    df_clean = df_input.copy()

    # Garantizar que las columnas numéricas sean tratadas como tipo objeto/texto antes de asignar valores
    for col in ["ITEM POR MES", "IT2", "SAP"]:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(object)

    for idx, row in df_clean.iterrows():
        val_estado = str(row["ESTADO - ELABORACIÓN DE INFORME"]).strip()
        val_resp = str(row["RESPONSABLE"]).strip()
        if "-" in val_estado:
            partes = val_estado.split("-", 1)
            df_clean.at[idx, "ESTADO - ELABORACIÓN DE INFORME"] = partes[0].strip()
            if val_resp in ["", "nan", "None"]:
                df_clean.at[idx, "RESPONSABLE"] = partes[1].strip()

        # Limpieza de valores numéricos para remover .0 sin conflicto de tipos
        df_clean.at[idx, "ITEM POR MES"] = formatear_entero_limpio(row["ITEM POR MES"])
        df_clean.at[idx, "IT2"] = formatear_entero_limpio(row["IT2"])
        df_clean.at[idx, "SAP"] = formatear_entero_limpio(row["SAP"])

    return df_clean

def es_codigo_provisional(codigo):
    t = texto_normalizado(codigo)
    return t in ["", "-"] or any(p in t for p in ["PENDIENTE ASIGNAR", "PENDIENTE DE ASIGNAR", "POR ASIGNAR"])

def es_correccion_psaim(observacion):
    t = texto_normalizado(observacion)
    return "PSAIM" in t and any(word in t for word in ["CORRECCION", "CORREGIR", "CORREGIDO", "CORREGIDA"])

def es_pendiente_inspeccion_fn(row):
    estado = texto_normalizado(row.get("ESTADO - ELABORACIÓN DE INFORME", ""))
    alcance = texto_normalizado(row.get("ALCANCE DEL SERVICIO", ""))
    obs = texto_normalizado(row.get("OBSERVACIÓN", ""))
    return ("PENDIENTE COMPLETAR INSPECCION" in estado or "PENDIENTE INSPECCION" in estado or
            "PENDIENTE INSPECCION" in alcance or "FALTA CARPETA" in alcance or
            "COMPLETAR INSPECCION" in obs or "COMPLETAR INSPECCIÓN" in obs)

def preparar_tabla_con_indice_1(df_input):
    if df_input.empty:
        return df_input
    df_res = df_input.reset_index(drop=True)
    df_res.index = range(1, len(df_res) + 1)
    return df_res

def cargar_datos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            df = pd.DataFrame(json.load(f))
            for col in COLUMNAS_EXCEL:
                if col not in df.columns: df[col] = ""
            return limpiar_estado_y_responsable(df)[COLUMNAS_EXCEL]
    else:
        df = pd.DataFrame(columns=COLUMNAS_EXCEL)
        guardar_datos(df)
        return df

def guardar_datos(df):
    df.to_json(DB_FILE, orient="records", force_ascii=False, indent=4)

def cargar_solicitudes():
    if os.path.exists(SOLICITUDES_FILE):
        with open(SOLICITUDES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_solicitudes(solicitudes):
    with open(SOLICITUDES_FILE, "w", encoding="utf-8") as f:
        json.dump(solicitudes, f, ensure_ascii=False, indent=4)

def registrar_solicitud(tipo, codigo, grupo, solicitante):
    solicitudes = cargar_solicitudes()
    for s in solicitudes:
        if s["codigo"] == codigo and s["grupo"] == grupo and s["tipo"] == tipo and s["estado"] == "PENDIENTE":
            return False, "Ya existe una solicitud pendiente de aprobación para este informe."
    solicitudes.append({"id": len(solicitudes) + 1, "tipo": tipo, "codigo": codigo, "grupo": grupo, "solicitante": solicitante, "estado": "PENDIENTE"})
    guardar_solicitudes(solicitudes)
    return True, "Solicitud enviada con éxito al Administrador."

if "df_data" not in st.session_state:
    st.session_state.df_data = cargar_datos()

df = st.session_state.df_data

resp_unicos = [str(r).strip() for r in df["RESPONSABLE"].unique() if pd.notna(r) and str(r).strip() not in ["", "nan", "None"]]
PERSONAL_LISTA = sorted(list(set(PERSONAL_LISTA_BASE + resp_unicos)))

st.markdown("""
    <div class="header-banner">
        <div class="header-title">CONTROL INTERNO DE INFORMES - ADEMINSAC</div>
        <div class="header-subtitle">Sistema de Monitoreo de Inspección Técnicas y Valorización | Refinería La Pampilla</div>
    </div>
""", unsafe_allow_html=True)

with st.expander("⚙️ **Gestión de Datos: Cargar / Restaurar Excel & Descargar Respaldo**", expanded=False):
    col_carg, col_desc = st.columns(2)
    with col_carg:
        st.markdown("##### 📤 Cargar Base de Datos desde Excel")
        archivo_excel = st.file_uploader("Seleccionar archivo Excel:", type=["xlsx", "xlsm"], key="uploader_main")
        if archivo_excel and st.button("🔄 Reemplazar Base de Datos"):
            try:
                excel_file = pd.ExcelFile(archivo_excel)
                hoja = "CONTROL" if "CONTROL" in excel_file.sheet_names else excel_file.sheet_names[0]
                df_cargado = pd.read_excel(excel_file, sheet_name=hoja)
                mapeo = {c: r for c in df_cargado.columns for r in COLUMNAS_EXCEL if str(c).strip().upper() == r.upper()}
                df_cargado = df_cargado.rename(columns=mapeo)
                for col in COLUMNAS_EXCEL:
                    if col not in df_cargado.columns: df_cargado[col] = ""
                st.session_state.df_data = limpiar_estado_y_responsable(df_cargado)[COLUMNAS_EXCEL]
                guardar_datos(st.session_state.df_data)
                st.success("¡Base de datos cargada correctamente!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    with col_desc:
        st.markdown("##### 📥 Descargar Respaldo Actual")
        if not df.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="CONTROL")
            buffer.seek(0)
            st.download_button("💾 Descargar Copia en Excel (.xlsx)", buffer, "Respaldo_Control_Informes.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if not df.empty:
    df_activos = df[df["OBSERVACIÓN"].apply(texto_normalizado) != "RETIRADO"].copy()
    df_activos["CLAVE_GLOBAL"] = df_activos.apply(lambda r: f"{str(r['MES']).strip()}|SIN-CODIGO-GRUPO|{texto_normalizado(r['GRUPO DE TUBERÍAS'])}" if es_codigo_provisional(r["CODIGO DE INFORME"]) else f"{str(r['MES']).strip()}|{str(r['CODIGO DE INFORME']).strip()}", axis=1)

    mask_psaim = df_activos["OBSERVACIÓN"].apply(es_correccion_psaim)
    mask_pend_insp = df_activos.apply(es_pendiente_inspeccion_fn, axis=1)
    mask_pend_elab = df_activos["ESTADO - ELABORACIÓN DE INFORME"].apply(texto_normalizado).str.contains("PENDIENTE ELABORACION")

    df_psaim_det = df_activos[mask_psaim]
    df_pend_inspeccion = df_activos[mask_pend_insp]
    df_pend_asignacion = df_activos[mask_pend_elab]
    df_en_proceso = df_activos[df_activos["ESTADO - ELABORACIÓN DE INFORME"].apply(texto_normalizado).str.contains("EN PROCESO") & ~mask_pend_insp]

    dict_unicos, dict_psaim_unicos = {}, set()
    dict_t3_val, dict_t3_pen, dict_t3_ademinsac, dict_t3_fiabilidad, dict_t3_psaim = {}, {}, {}, {}, {}
    dict_t4, dict_t5 = {}, {}
    cnt_revision_fiabilidad, cnt_pend_revision_especialista, cnt_revision_por_especialista = 0, 0, 0

    for _, row in df_activos.iterrows():
        mes, cod, grupo = str(row["MES"]).strip(), str(row["CODIGO DE INFORME"]).strip(), str(row["GRUPO DE TUBERÍAS"]).strip()
        obs = str(row["OBSERVACIÓN"]).strip() if pd.notna(row["OBSERVACIÓN"]) else ""
        estado_val, clave_global = texto_normalizado(row["ESTADO - VALORIZACIÓN"]), row["CLAVE_GLOBAL"]

        if mes and grupo:
            if not es_codigo_provisional(cod) and es_correccion_psaim(obs):
                if f"{mes}|{cod}" not in dict_psaim_unicos:
                    dict_psaim_unicos.add(f"{mes}|{cod}")
                    dict_t3_psaim[mes] = dict_t3_psaim.get(mes, 0) + 1

            if clave_global not in dict_unicos:
                dict_unicos[clave_global] = True
                dict_t3_val.setdefault(mes, 0); dict_t3_pen.setdefault(mes, 0)
                dict_t3_ademinsac.setdefault(mes, 0); dict_t3_fiabilidad.setdefault(mes, 0)
                obs_norm = texto_normalizado(obs)

                if estado_val == "SI":
                    dict_t3_val[mes] += 1
                else:
                    dict_t3_pen[mes] += 1
                    if "ENTREGADO PARA SU REVISION" in obs_norm and "FIABILIDAD" in obs_norm: cnt_revision_fiabilidad += 1
                    if "PENDIENTE REVISION POR EL ESPECIALISTA" in obs_norm: cnt_pend_revision_especialista += 1
                    if ("REV. POR EL ESPECIALISTA" in obs_norm or "REVISION POR EL ESPECIALISTA" in obs_norm) and "PENDIENTE" not in obs_norm: cnt_revision_por_especialista += 1
                    if "ADEMINSAC" in obs_norm: dict_t3_ademinsac[mes] += 1
                    else: dict_t3_fiabilidad[mes] += 1

                    obs_key = "(En blanco)" if obs == "" else obs
                    dict_t4[f"{mes}|{obs_key}"] = dict_t4.get(f"{mes}|{obs_key}", 0) + 1
                    dict_t5[obs_key] = dict_t5.get(obs_key, 0) + 1

    # -----------------------------------------------------------------
    # VALORES DE LOS 10 KPI (idénticos a los que ya calculabas)
    # -----------------------------------------------------------------
    kpi_informes_totales = len(dict_unicos)
    kpi_pendientes_total = sum(dict_t3_pen.values())
    kpi_valorizados = sum(dict_t3_val.values())
    kpi_pend_asignar = df_pend_asignacion["CLAVE_GLOBAL"].nunique()
    kpi_en_proceso = df_en_proceso["CLAVE_GLOBAL"].nunique()
    kpi_pend_inspeccion = df_pend_inspeccion["CLAVE_GLOBAL"].nunique()
    kpi_rev_fiabilidad = cnt_revision_fiabilidad
    kpi_pend_rev_especialista = cnt_pend_revision_especialista
    kpi_rev_por_especialista = cnt_revision_por_especialista
    kpi_correccion_psaim = sum(dict_t3_psaim.values())

    # -----------------------------------------------------------------
    # PANEL DE CONTROL — 5 bloques distribuidos en una sola fila horizontal
    # (usamos st.container(key=...) para tener un contenedor real y
    # estable en el DOM; con esto el CSS de arriba puede darle el
    # aspecto de tarjeta con borde, sombra y separación clara)
    # -----------------------------------------------------------------
    def item_kpi(titulo, valor, color):
        return (
            f"<div class='kpi-item' style='--tone:{color}'>"
            f"<div class='kpi-item-label'>{titulo}</div>"
            f"<div class='kpi-item-value'>{valor}</div>"
            f"</div>"
        )

    def bloque_kpi(titulo_bloque, emoji, items):
        filas = "".join(item_kpi(*i) for i in items)
        return (
            f"<div class='kpi-block-card'>"
            f"<div class='kpi-block-title'>{emoji} {titulo_bloque}</div>"
            f"<div class='kpi-items'>{filas}</div></div>"
        )

    panel_control = st.container(key="panel_control")
    panel_control.markdown(
        "<div class='section-title'>📊 Panel de control de informes</div>",
        unsafe_allow_html=True,
    )

    bloques_html = "".join(
        [
            bloque_kpi(
                "Bloque general",
                "📊",
                [
                    ("Informes totales", kpi_informes_totales, "#173F67"),
                    ("Valorizados (SI)", kpi_valorizados, "#159A68"),
                    ("Pendientes total", kpi_pendientes_total, "#E38921"),
                ],
            ),
            bloque_kpi(
                "Bloque gabinete",
                "📁",
                [
                    ("En proceso", kpi_en_proceso, "#7B61C9"),
                    ("Pend. asignar", kpi_pend_asignar, "#D54D9D"),
                    ("Correc. PSAIM", kpi_correccion_psaim, "#C89716"),
                ],
            ),
            bloque_kpi(
                "Bloque especialista",
                "👤",
                [
                    ("Rev. por especialista", kpi_rev_por_especialista, "#168EAE"),
                    ("Pend. rev. especialista", kpi_pend_rev_especialista, "#5564D8"),
                ],
            ),
            bloque_kpi(
                "Bloque campo",
                "📝",
                [
                    ("Pend. inspección", kpi_pend_inspeccion, "#D8534F"),
                ],
            ),
            bloque_kpi(
                "Bloque cliente",
                "🏢",
                [
                    ("Rev. fiabilidad", kpi_rev_fiabilidad, "#159D99"),
                ],
            ),
        ]
    )
    panel_control.markdown(
        f"<div class='kpi-row'>{bloques_html}</div>", unsafe_allow_html=True
    )

    solic_activas = [s for s in cargar_solicitudes() if s["estado"] == "PENDIENTE"]

    # -----------------------------------------------------------------
    # SISTEMA DE CONTROL Y RESÚMENES — segunda tarjeta contenedora,
    # con pestañas distribuidas parejo en todo el ancho
    # -----------------------------------------------------------------
    sistema_control = st.container(key="sistema_control")
    sistema_control.markdown(
        "<div class='section-title'>🗂️ Sistema de control y resúmenes</div>",
        unsafe_allow_html=True,
    )

    t_admin, t_gen, t_pasig, t_proc, t_pinsp, t_rfiab, t_pesp, t_resp, t_psaim, t_t3, t_t4, t_t5 = sistema_control.tabs([
        f"🔔 Admin ({len(solic_activas)})" if solic_activas else "🔔 Admin",
        "📋 Tabla General", "📋 Pend. Asignar", "🔄 En Proceso", "⏳ Pend. Inspección",
        "🔍 Rev. Fiabilidad", "👨‍🔬 Pend. Rev. Especialista", "🔬 Rev. por Especialista",
        "🛠️ Correc. PSAIM", "📅 Resumen Mes (T3)", "📊 Pend. Mes/Obs (T4)", "📌 Resumen Obs (T5)"
    ])

    with t_admin:
        st.markdown("#### **BANDEJA DE APROBACIÓN (ADMINISTRADOR)**")
        if solic_activas:
            for sol in solic_activas:
                c_inf, c_app, c_rej = st.columns([4, 1, 1])
                c_inf.markdown(f"📌 **[{sol['tipo']}]** Código: **{sol['codigo']}** | Grupo: **{sol['grupo']}** | Solicitante: **{sol['solicitante']}**")

                if c_app.button("✅ Aprobar", key=f"app_{sol['id']}"):
                    mask = (df["CODIGO DE INFORME"] == sol["codigo"]) & (df["GRUPO DE TUBERÍAS"] == sol["grupo"])
                    if sol["tipo"] == "INFORME COMPLETADO (GABINETE)": df.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "FINALIZADO"
                    elif sol["tipo"] == "CORRECCIÓN PSAIM": df.loc[mask, "OBSERVACIÓN"] = "PSAIM CORREGIDO"; df.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "EN PROCESO"
                    elif sol["tipo"] == "REVISIÓN ESPECIALISTA": df.loc[mask, "OBSERVACIÓN"] = "INFORME REVISADO POR ESPECIALISTA"

                    solicitudes = cargar_solicitudes()
                    for s in solicitudes:
                        if s["id"] == sol["id"]: s["estado"] = "APROBADO"
                    guardar_solicitudes(solicitudes)
                    guardar_datos(df)
                    st.success("Aprobado correctamente.")
                    st.rerun()

                if c_rej.button("❌ Rechazar", key=f"rej_{sol['id']}"):
                    solicitudes = cargar_solicitudes()
                    for s in solicitudes:
                        if s["id"] == sol["id"]: s["estado"] = "RECHAZADO"
                    guardar_solicitudes(solicitudes)
                    st.warning("Rechazado correctamente.")
                    st.rerun()

                st.divider()
        else: st.success("✨ No hay solicitudes pendientes.")

    with t_gen:
        c_m, c_b = st.columns([1, 3])
        meses_disp = ["Todos"] + sorted([m for m in df["MES"].dropna().astype(str).str.strip().str.upper().unique() if m], key=lambda x: ORDEN_MESES.index(x) if x in ORDEN_MESES else 99)
        m_sel = c_m.selectbox("Filtrar Mes:", meses_disp)
        txt_b = c_b.text_input("🔍 Buscador:")

        # Conservar el índice original para evitar desajustes durante los filtros
        df_dis = df[COLUMNAS_EXCEL].copy()

        # Convierte todos los campos a texto limpio formateado
        for column in df_dis.columns:
            df_dis[column] = df_dis[column].apply(formatear_entero_limpio)

        if m_sel != "Todos":
            df_dis = df_dis[df_dis["MES"].astype(str).str.strip().str.upper() == m_sel]
        if txt_b.strip():
            q = texto_normalizado(txt_b)
            df_dis = df_dis[df_dis.apply(lambda r: q in texto_normalizado(r["LINEAS"]) or q in texto_normalizado(r["SAP"]) or q in texto_normalizado(r["CODIGO DE INFORME"]) or q in texto_normalizado(r["GRUPO DE TUBERÍAS"]), axis=1)]

        df_dis["ESTADO - VALORIZACIÓN"] = df_dis["ESTADO - VALORIZACIÓN"].apply(
            lambda x: "SI" if texto_normalizado(x) == "SI" else "Pendiente - valorización"
        )

        # Configuración de columnas con tipos 100% seguros
        config_columnas = {
            "ITEM POR MES": st.column_config.TextColumn("ITEM POR MES", width="small"),
            "IT2": st.column_config.TextColumn("IT2", width="small"),
            "UNIDAD": st.column_config.TextColumn("UNIDAD", width="small"),
            "MES": st.column_config.TextColumn("MES", width="small"),
            "LINEAS": st.column_config.TextColumn("LINEAS", width="large"),
            "CODIGO DE INFORME": st.column_config.TextColumn("CODIGO DE INFORME", width="medium"),
            "GRUPO DE TUBERÍAS": st.column_config.TextColumn("GRUPO DE TUBERÍAS", width="medium"),
            "SAP": st.column_config.TextColumn("SAP", width="small"),
            "ALCANCE DEL SERVICIO": st.column_config.TextColumn("ALCANCE DEL SERVICIO", width="large"),
            "ESTADO - ELABORACIÓN DE INFORME": st.column_config.TextColumn("ESTADO - ELABORACIÓN DE INFORME", width="medium"),
            "RESPONSABLE": st.column_config.TextColumn("RESPONSABLE", width="medium"),
            "OBSERVACIÓN": st.column_config.TextColumn("OBSERVACIÓN", width="large"),
            "ESTADO - VALORIZACIÓN": st.column_config.SelectboxColumn(
                "ESTADO - VALORIZACIÓN",
                help="Seleccione el estado de valorización",
                options=["Pendiente - valorización", "SI"],
                required=True,
                width="medium"
            )
        }

        # Función para aplicar estilos condicionales por fila
        def resaltar_filas(row):
            val_estado = str(row.get("ESTADO - VALORIZACIÓN", "")).strip().upper()
            val_alcance = texto_normalizado(row.get("ALCANCE DEL SERVICIO", ""))

            # 1. Verde claro si ESTADO - VALORIZACIÓN indica SI
            if val_estado == "SI":
                return ["background-color: #D1FAE5; color: #065F46;"] * len(row)

            # 2. Amarillo claro para estados específicos de ALCANCE DEL SERVICIO
            if val_alcance in [
                "VT-CIRCUITOS - PENDIENTE INSPECCION",
                "VT-CIRCUITOS - FALTA CARPETA",
                "LINEAS - PENDIENTE INSPECCION"
            ]:
                return ["background-color: #FEF08A; color: #713F12;"] * len(row)

            # 3. Celeste claro para inspección complementaria
            if val_alcance == "VT-CIRCUITOS - INSPECCION COMPLEMENTARIA":
                return ["background-color: #BAE6FD; color: #0C4A6E;"] * len(row)

            return [""] * len(row)

        df_styled = df_dis.style.apply(resaltar_filas, axis=1)

        # Usar st.dataframe para visualizar los colores de forma directa manteniendo st.data_editor si se activa edición
        ed_df = st.data_editor(
            df_styled,
            column_config=config_columnas,
            hide_index=True,
            use_container_width=True,
            key="editor_tabla_general_select"
        )

        if st.button("💾 Guardar Cambios", key="btn_guardar_gen"):
            # Mapeo exacto por índice original para evitar duplicaciones al guardar grupos filtrados
            for real_idx, row in ed_df.iterrows():
                for col in COLUMNAS_EXCEL:
                    st.session_state.df_data.at[real_idx, col] = row[col]

                # Limpieza automatizada de la observación si cambia a SI
                if str(row["ESTADO - VALORIZACIÓN"]).strip().upper() == "SI":
                    st.session_state.df_data.at[real_idx, "OBSERVACIÓN"] = ""

            st.session_state.df_data = limpiar_estado_y_responsable(st.session_state.df_data[COLUMNAS_EXCEL])
            guardar_datos(st.session_state.df_data)
            st.success("Cambios guardados con éxito en la base de datos.")
            st.rerun()

    with t_pasig:
        if not df_pend_asignacion.empty:
            # dropna=False permite mantener los registros agrupados aunque CODIGO DE INFORME o RESPONSABLE sean nulos/vacíos
            res_pasig = df_pend_asignacion.groupby(
                ["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"],
                as_index=False,
                dropna=False
            ).agg({"LINEAS": "count"})

            # Reemplazar NaN resultantes del groupby por cadenas vacías para visualización limpia
            res_pasig = res_pasig.fillna("")
            st.dataframe(preparar_tabla_con_indice_1(res_pasig), use_container_width=True)
        else:
            st.info("No hay informes pendientes de asignación.")

    with t_proc:
        if not df_en_proceso.empty:
            tg = df_en_proceso.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False, dropna=False).agg({"LINEAS": "count"}).fillna("")
            st.dataframe(preparar_tabla_con_indice_1(tg), use_container_width=True)
            c1, c2, c3 = st.columns([2, 2, 1])
            cod_s = c1.selectbox("Código:", tg["CODIGO DE INFORME"].unique(), key="spc")
            resp_s = c2.selectbox("Inspector:", PERSONAL_LISTA, key="spr")
            if c3.button("🟢 Enviar al 100%", key="b_proc"):
                ok, m = registrar_solicitud("INFORME COMPLETADO (GABINETE)", cod_s, tg[tg["CODIGO DE INFORME"] == cod_s]["GRUPO DE TUBERÍAS"].values[0], resp_s)
                st.success(m) if ok else st.warning(m)

    with t_pinsp:
        if not df_pend_inspeccion.empty:
            res_pinsp = df_pend_inspeccion.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False, dropna=False).agg({"LINEAS": "count"}).fillna("")
            st.dataframe(preparar_tabla_con_indice_1(res_pinsp), use_container_width=True)

    with t_rfiab:
        df_f = df_activos[df_activos["OBSERVACIÓN"].apply(lambda x: "ENTREGADO PARA SU REVISION" in texto_normalizado(x) and "FIABILIDAD" in texto_normalizado(x))]
        if not df_f.empty:
            res_fiab = df_f.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False, dropna=False).agg({"LINEAS": "count"}).fillna("")
            st.dataframe(preparar_tabla_con_indice_1(res_fiab), use_container_width=True)

    with t_pesp:
        df_e = df_activos[df_activos["OBSERVACIÓN"].apply(lambda x: "PENDIENTE REVISION POR EL ESPECIALISTA" in texto_normalizado(x))]
        if not df_e.empty:
            tg_e = df_e.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False, dropna=False).agg({"LINEAS": "count"}).fillna("")
            st.dataframe(preparar_tabla_con_indice_1(tg_e), use_container_width=True)
            c1, c2, c3 = st.columns([2, 2, 1])
            cod_pe = c1.selectbox("Código:", tg_e["CODIGO DE INFORME"].unique(), key="pesp_c")
            resp_pe = c2.selectbox("Especialista:", ESPECIALISTAS_LISTA, key="pesp_r")
            if c3.button("🟢 Enviar a Revisión", key="b_pesp"):
                grupo_sel = tg_e[tg_e["CODIGO DE INFORME"] == cod_pe]["GRUPO DE TUBERÍAS"].values[0]
                ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_pe, grupo_sel, resp_pe)
                st.success(m) if ok else st.warning(m)

    with t_resp:
        df_re = df_activos[df_activos["OBSERVACIÓN"].apply(lambda x: ("REV. POR EL ESPECIALISTA" in texto_normalizado(x) or "REVISION POR EL ESPECIALISTA" in texto_normalizado(x)) and "PENDIENTE" not in texto_normalizado(x))]
        if not df_re.empty:
            tg_re = df_re.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False, dropna=False).agg({"LINEAS": "count"}).fillna("")
            st.dataframe(preparar_tabla_con_indice_1(tg_re), use_container_width=True)
            c1, c2, c3 = st.columns([2, 2, 1])
            cod_se = c1.selectbox("Código:", tg_re["CODIGO DE INFORME"].unique(), key="sec")
            resp_se = c2.selectbox("Especialista:", ESPECIALISTAS_LISTA, key="ser")
            if c3.button("🟢 Liberar Especialista", key="b_esp"):
                ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_se, tg_re[tg_re["CODIGO DE INFORME"] == cod_se]["GRUPO DE TUBERÍAS"].values[0], resp_se)
                st.success(m) if ok else st.warning(m)

    with t_psaim:
        if not df_psaim_det.empty:
            df_psaim_lineas = df_psaim_det[
                df_psaim_det["ALCANCE DEL SERVICIO"].apply(texto_normalizado) == "LINEAS"
            ].copy()

            if not df_psaim_lineas.empty:
                cols_psaim = [
                    "MES",
                    "ESTADO - ELABORACIÓN DE INFORME",
                    "RESPONSABLE",
                    "ITEM POR MES",
                    "IT2",
                    "LINEAS",
                    "GRUPO DE TUBERÍAS",
                    "CODIGO DE INFORME",
                    "OBSERVACIÓN"
                ]

                cols_disponibles = [c for c in cols_psaim if c in df_psaim_lineas.columns]
                df_psaim_vista = df_psaim_lineas[cols_disponibles]

                st.dataframe(preparar_tabla_con_indice_1(df_psaim_vista), use_container_width=True)

                c1, c2, c3 = st.columns([2, 2, 1])
                codigos_unicos = [c for c in df_psaim_vista["CODIGO DE INFORME"].dropna().unique() if str(c).strip()]

                if codigos_unicos:
                    cod_sp = c1.selectbox("Código:", codigos_unicos, key="spc_p")
                    resp_sp = c2.selectbox("Revisor PSAIM:", REVISORES_PSAIM_LISTA, key="spr_p")

                    if c3.button("🟢 PSAIM Corregido", key="b_psaim"):
                        grupo_asociado = df_psaim_vista[df_psaim_vista["CODIGO DE INFORME"] == cod_sp]["GRUPO DE TUBERÍAS"].values[0]
                        ok, m = registrar_solicitud("CORRECCIÓN PSAIM", cod_sp, grupo_asociado, resp_sp)
                        if ok:
                            st.success(m)
                        else:
                            st.warning(m)
            else:
                st.info("No hay registros pendientes de corrección PSAIM con alcance 'LINEAS'.")
        else:
            st.info("No hay informes pendientes de corrección PSAIM.")

    with t_t3:
        m_u = list(set(list(dict_t3_val.keys()) + list(dict_t3_pen.keys())))
        f_t3 = [{"MES": m, "GRUPOS": df_activos[df_activos["MES"].astype(str).str.strip() == m]["GRUPO DE TUBERÍAS"].nunique(), "VALORIZADOS": dict_t3_val.get(m, 0), "PENDIENTE VALORIZAR": dict_t3_pen.get(m, 0), "SUMA TOTAL": dict_t3_val.get(m, 0) + dict_t3_pen.get(m, 0), "PENDIENTE ADEMINSAC": dict_t3_ademinsac.get(m, 0), "PENDIENTE FIABILIDAD": dict_t3_fiabilidad.get(m, 0), "CORRECCION PSAIM": dict_t3_psaim.get(m, 0)} for m in m_u]
        df_t3 = pd.DataFrame(f_t3)
        if not df_t3.empty:
            df_t3["MES_CAT"] = pd.Categorical(df_t3["MES"].str.upper(), categories=ORDEN_MESES, ordered=True)
            st.dataframe(preparar_tabla_con_indice_1(df_t3.sort_values("MES_CAT").drop(columns=["MES_CAT"])), use_container_width=True)

    with t_t4:
        df_t4 = pd.DataFrame([{"MES": k.split("|", 1)[0], "OBSERVACIÓN PENDIENTE": k.split("|", 1)[1], "CANTIDAD": v} for k, v in dict_t4.items()])
        if not df_t4.empty:
            df_t4["MES_CAT"] = pd.Categorical(df_t4["MES"].str.upper(), categories=ORDEN_MESES, ordered=True)
            st.dataframe(preparar_tabla_con_indice_1(df_t4.sort_values(["MES_CAT", "CANTIDAD"], ascending=[True, False]).drop(columns=["MES_CAT"])), use_container_width=True)

    with t_t5:
        df_t5 = pd.DataFrame([{"OBSERVACIÓN PENDIENTE": k, "CANTIDAD TOTAL": v, "RESPONSABLE": ("ADEMINSAC" if "ADEMINSAC" in texto_normalizado(k) else "FIABILIDAD")} for k, v in dict_t5.items()])
        if not df_t5.empty:
            st.dataframe(preparar_tabla_con_indice_1(df_t5.sort_values("CANTIDAD TOTAL", ascending=False)), use_container_width=True)
else:
    st.info("Haga clic en la sección superior '⚙️ Gestión de Datos' para cargar un archivo Excel o iniciar la base de datos.")
