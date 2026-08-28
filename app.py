import streamlit as st
import pandas as pd
import io

# Configuración de la página
st.set_page_config(page_title="Control Interno de Informes de Inspección", layout="wide", initial_sidebar_state="collapsed")

# OCULTAR ÚNICAMENTE MUESTRAS INDESEADAS (SIDEBAR Y FOOTER) SIN OCULTAR EL TÍTULO
st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        .block-container { padding-top: 1rem; padding-bottom: 2rem; }
        .main-title {
            text-align: center;
            font-size: 26px;
            font-weight: 800;
            color: #1E293B;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
    </style>
""", unsafe_allow_html=True)

PERSONAL_LISTA = ["INSPECTOR 1", "INSPECTOR 2", "INSPECTOR 3", "SIN ASIGNAR"]
ESPECIALISTAS_LISTA = ["ESPECIALISTA 1", "ESPECIALISTA 2"]
REVISORES_PSAIM_LISTA = ["REVISOR PSAIM 1", "REVISOR PSAIM 2"]

COLUMN_DEFAULTS = [
    "MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", 
    "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN", 
    "ESTADO - VALORIZACIÓN", "LINEAS"
]

# --- GESTIÓN DE SESIÓN ---
if "df_data" not in st.session_state:
    st.session_state.df_data = pd.DataFrame(columns=COLUMN_DEFAULTS)

if "solicitudes" not in st.session_state:
    st.session_state.solicitudes = []

def procesar_excel_cargado(file):
    try:
        df = pd.read_excel(file)
        for col in COLUMN_DEFAULTS:
            if col not in df.columns:
                df[col] = "" if col != "LINEAS" else 1
            elif col != "LINEAS":
                df[col] = df[col].fillna("").astype(str)
        
        df["LINEAS"] = pd.to_numeric(df["LINEAS"], errors="coerce").fillna(1)
        st.session_state.df_data = df
        return True, "Base de datos cargada correctamente en la aplicación."
    except Exception as e:
        return False, f"Error al leer el archivo Excel: {e}"

def registrar_solicitud(tipo, codigo, grupo, usuario):
    for s in st.session_state.solicitudes:
        if s["codigo"] == codigo and s["grupo"] == grupo and s["estado"] == "PENDIENTE":
            return False, "Ya existe una solicitud pendiente para este informe."
    
    nueva_sol = {
        "id": len(st.session_state.solicitudes) + 1,
        "tipo": tipo,
        "codigo": codigo,
        "grupo": grupo,
        "usuario": usuario,
        "fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "estado": "PENDIENTE"
    }
    st.session_state.solicitudes.append(nueva_sol)
    return True, "Solicitud enviada a Administración con éxito."

# --- TÍTULO PRINCIPAL VISIBLE ---
st.markdown("<div class='main-title'>CONTROL INTERNO DE INFORMES DE INSPECCIÓN</div>", unsafe_allow_html=True)

# CARGA DE EMERGENCIA
if st.session_state.df_data.empty:
    st.warning("⚠️ No hay datos cargados en la sesión. Carga tu archivo Excel para iniciar.")
    uploaded_file = st.file_uploader("📂 Seleccionar y Cargar Archivo Excel (.xlsx / .xlsm):", type=["xlsx", "xlsm"], key="main_upload")
    if uploaded_file is not None:
        ok, msg = procesar_excel_cargado(uploaded_file)
        if ok:
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)

df_data = st.session_state.df_data

# --- CÁLCULO REVISADO DE KPIS Y FILTROS ESTRUCTURALES ---
if not df_data.empty:
    # 1. INFORMES TOTALES: Conteo general sin exclusión
    tot_informes = len(df_data["CODIGO DE INFORME"].unique())

    # 2. PENDIENTES TOTALES: Filtrado de informes que no han sido completamente cerrados ni valorizados
    df_activos = df_data[
        (df_data["ESTADO - VALORIZACIÓN"].str.upper() != "VALORIZADO") &
        (df_data["ESTADO - ELABORACIÓN DE INFORME"].str.upper() != "FINALIZADO")
    ].copy()
    tot_pendientes = len(df_activos["CODIGO DE INFORME"].unique())

    # 3. VALORIZADOS
    tot_valorizados = len(df_data[df_data["ESTADO - VALORIZACIÓN"].str.upper() == "VALORIZADO"]["CODIGO DE INFORME"].unique())

    # 4. Pendiente Asignar
    df_pend_asignacion = df_activos[
        (df_activos["ESTADO - ELABORACIÓN DE INFORME"].str.upper() == "PENDIENTE ELABORACIÓN") &
        ((df_activos["RESPONSABLE"].str.upper() == "SIN ASIGNAR") | (df_activos["RESPONSABLE"].str.strip() == ""))
    ]

    # 5. En Proceso
    df_en_proceso = df_activos[
        (df_activos["ESTADO - ELABORACIÓN DE INFORME"].str.upper() == "EN PROCESO") |
        ((df_activos["ESTADO - ELABORACIÓN DE INFORME"].str.upper() == "PENDIENTE ELABORACIÓN") & 
         (df_activos["RESPONSABLE"].str.upper() != "SIN ASIGNAR") & (df_activos["RESPONSABLE"].str.strip() != ""))
    ]

    # 6. Pendiente Inspección (INCLUYE REGLA ESPECÍFICA "PENDIENTE COMPLETAR INSPECCIÓN")
    df_pend_inspeccion = df_activos[
        (df_activos["ESTADO - ELABORACIÓN DE INFORME"].str.upper().str.contains("PENDIENTE.*INSPECCI", regex=True, na=False)) |
        (df_activos["ESTADO - ELABORACIÓN DE INFORME"].str.upper().str.contains("PENDIENTE COMPLETAR INSPECCI", na=False)) |
        (df_activos["OBSERVACIÓN"].str.upper().str.contains("PENDIENTE COMPLETAR INSPECCIÓN - ADEMINSAC", na=False)) |
        (df_activos["OBSERVACIÓN"].str.upper().str.contains("PENDIENTE INSPECCI", na=False))
    ]

    # 7. Revisión Fiabilidad
    df_fiab_activos = df_activos[
        (df_activos["ESTADO - ELABORACIÓN DE INFORME"].str.upper() == "REVISIÓN FIABILIDAD") |
        (df_activos["OBSERVACIÓN"].str.upper().str.contains("FIABILIDAD", na=False))
    ]

    # 8. Pendiente Revisión por Especialista
    df_pesp_det = df_activos[
        df_activos["OBSERVACIÓN"].str.upper().str.contains("PENDIENTE.*ESPECIALISTA", regex=True, na=False)
    ]

    # 9. Revisión por Especialista
    df_resp_det = df_activos[
        df_activos["OBSERVACIÓN"].str.upper().str.contains("REV.*ESPECIALISTA", regex=True, na=False) &
        ~df_activos["OBSERVACIÓN"].str.upper().str.contains("PENDIENTE", na=False)
    ]

    # 10. Corrección PSAIM
    df_psaim_det = df_activos[
        df_activos["OBSERVACIÓN"].str.upper().str.contains("PSAIM", na=False)
    ]

    kpi_pasig = len(df_pend_asignacion["CODIGO DE INFORME"].unique())
    kpi_proc = len(df_en_proceso["CODIGO DE INFORME"].unique())
    kpi_pinsp = len(df_pend_inspeccion["CODIGO DE INFORME"].unique())
    kpi_rfiab = len(df_fiab_activos["CODIGO DE INFORME"].unique())
    kpi_pesp = len(df_pesp_det["CODIGO DE INFORME"].unique())
    kpi_resp = len(df_resp_det["CODIGO DE INFORME"].unique())
    kpi_psaim = len(df_psaim_det["CODIGO DE INFORME"].unique())
else:
    df_activos = pd.DataFrame(columns=COLUMN_DEFAULTS)
    df_pend_asignacion = df_en_proceso = df_pend_inspeccion = df_fiab_activos = pd.DataFrame(columns=COLUMN_DEFAULTS)
    df_pesp_det = df_resp_det = df_psaim_det = pd.DataFrame(columns=COLUMN_DEFAULTS)
    tot_informes = tot_pendientes = tot_valorizados = 0
    kpi_pasig = kpi_proc = kpi_pinsp = kpi_rfiab = kpi_pesp = kpi_resp = kpi_psaim = 0

# --- REDISEÑO DE COLORES DE KPIS ---
kpi_cols = st.columns(10)

metrics = [
    ("INFORMES TOTALES", tot_informes, "#0F172A", "#F8FAFC"),
    ("PENDIENTES TOTAL", tot_pendientes, "#C2410C", "#FFF7ED"),
    ("VALORIZADOS (SI)", tot_valorizados, "#15803D", "#F0FDF4"),
    ("PEND. ASIGNAR INFORME", kpi_pasig, "#BE185D", "#FDF2F8"),
    ("EN PROCESO", kpi_proc, "#6D28D9", "#F5F3FF"),
    ("PEND. INSPECCIÓN", kpi_pinsp, "#B91C1C", "#FEF2F2"),
    ("REV. FIABILIDAD", kpi_rfiab, "#0F766E", "#F0FDFA"),
    ("PEND. REV. ESPECIALISTA", kpi_pesp, "#4338CA", "#EEF2FF"),
    ("REV. POR ESPECIALISTA", kpi_resp, "#0369A1", "#F0F9FF"),
    ("CORRECCIÓN PSAIM", kpi_psaim, "#A16207", "#FEFCE8"),
]

for col, (label, val, text_color, bg_color) in zip(kpi_cols, metrics):
    with col:
        st.markdown(f"""
            <div style="
                border: 2px solid {text_color};
                border-radius: 8px;
                padding: 10px 4px;
                text-align: center;
                background-color: {bg_color};
                min-height: 85px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <span style="font-size: 8.5px; font-weight: 700; color: {text_color}; text-transform: uppercase; line-height: 1.1; margin-bottom: 4px;">{label}</span>
                <span style="font-size: 22px; font-weight: 800; color: {text_color};">{val}</span>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
# --- PESTAÑAS DE TRABAJO ---
(
    t_admin, t_gen, t_pasig, t_proc, t_pinsp, t_rfiab, 
    t_pesp, t_resp, t_psaim, t_res_m, t_p_m, t_res_o
) = st.tabs([
    "🔔 Administración / Cargar", "📋 Tabla General", "📝 Pend. Asignar", "🔄 En Proceso", 
    "⏳ Pend. Inspección", "🔍 Rev. Fiabilidad", "🧑‍🔬 Pend. Rev. Especialista", 
    "🔬 Rev. por Especialista", "🛠️ Correc. PSAIM", "📅 Resumen Mes (T3)", 
    "📊 Pend. Mes/Obs (T4)", "📌 Resumen Obs (T5)"
])

# --- 1. ADMINISTRACIÓN ---
with t_admin:
    st.subheader("⚙️ Gestión de Carga y Descarga")
    c_up, c_down = st.columns([2, 1])
    
    with c_up:
        st.markdown("##### 📂 Cargar / Actualizar Archivo Excel")
        file_excel = st.file_uploader("Subir dataset:", type=["xlsx", "xlsm"], key="admin_upload")
        if file_excel is not None:
            if st.button("🔄 Procesar y Cargar Base"):
                ok, msg = procesar_excel_cargado(file_excel)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    with c_down:
        st.markdown("##### 💾 Guardar Avances")
        if not st.session_state.df_data.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                st.session_state.df_data.to_excel(writer, index=False, sheet_name="BaseDatos")
            st.download_button(
                label="💾 Descargar Excel Actualizado",
                data=buffer.getvalue(),
                file_name="CONTROL_INFORMES_INSPECCION.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    st.markdown("---")
    st.subheader("🔔 Solicitudes Registradas")
    pendientes = [s for s in st.session_state.solicitudes if s["estado"] == "PENDIENTE"]
    
    if not pendientes:
        st.info("No hay solicitudes pendientes.")
    else:
        for sol in pendientes:
            with st.container():
                c_info, c_acc1, c_acc2 = st.columns([3, 1, 1])
                c_info.markdown(f"**[{sol['tipo']}]** Código: `{sol['codigo']}` | Grupo: `{sol['grupo']}` | Solicitante: **{sol['usuario']}**")
                if c_acc1.button("🟢 Aprobar", key=f"ac_{sol['id']}"):
                    df_mod = st.session_state.df_data
                    mask = (df_mod["CODIGO DE INFORME"].str.strip() == sol["codigo"].strip()) & (df_mod["GRUPO DE TUBERÍAS"].str.strip() == sol["grupo"].strip())
                    
                    if sol["tipo"] == "INFORME COMPLETADO (GABINETE)":
                        df_mod.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "Finalizado"
                        df_mod.loc[mask, "OBSERVACIÓN"] = "Informe (Carta) entregado para su revisión - Fiabilidad"
                        df_mod.loc[mask, "RESPONSABLE"] = sol["usuario"]
                    elif sol["tipo"] == "REVISIÓN ESPECIALISTA":
                        df_mod.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "Finalizado"
                        df_mod.loc[mask, "OBSERVACIÓN"] = f"REV. POR EL ESPECIALISTA ({sol['usuario']})"
                    elif sol["tipo"] == "CORRECCIÓN PSAIM":
                        df_mod.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "Finalizado"
                        df_mod.loc[mask, "OBSERVACIÓN"] = "Informe (Carta) entregado para su revisión - Fiabilidad"
                    
                    st.session_state.df_data = df_mod
                    sol["estado"] = "APROBADO"
                    st.success("Cambio aplicado con éxito.")
                    st.rerun()

                if c_acc2.button("🔴 Rechazar", key=f"rc_{sol['id']}"):
                    sol["estado"] = "RECHAZADO"
                    st.warning("Solicitud descartada.")
                    st.rerun()

# --- 2. TABLA GENERAL CON FILTROS CONTIGUOS ---
with t_gen:
    st.subheader("📋 Tabla General de Informes")
    
    if not df_data.empty:
        col_m, col_b = st.columns([1, 2])
        
        meses_disponibles = sorted([str(m) for m in df_data["MES"].dropna().unique() if str(m).strip() != ""])
        with col_m:
            meses_sel = st.multiselect("📅 Filtrar por Mes:", options=meses_disponibles, default=meses_disponibles, key="filter_mes_tg")
            
        with col_b:
            search_query = st.text_input("🔍 Búsqueda (Código SAP / Informe / Grupo / Todo):", placeholder="Escribe para filtrar y traer todas las líneas del grupo/informe...", key="search_tg_input")
        
        df_gen_disp = df_data.copy()
        
        if meses_sel:
            df_gen_disp = df_gen_disp[df_gen_disp["MES"].astype(str).isin(meses_sel)]
            
        if search_query.strip():
            sq = search_query.strip().lower()
            
            cods_coincidentes = df_gen_disp[df_gen_disp["CODIGO DE INFORME"].astype(str).str.lower().str.contains(sq, na=False)]["CODIGO DE INFORME"].unique()
            grupos_coincidentes = df_gen_disp[df_gen_disp["GRUPO DE TUBERÍAS"].astype(str).str.lower().str.contains(sq, na=False)]["GRUPO DE TUBERÍAS"].unique()
            
            mask_asociada = (
                df_gen_disp["CODIGO DE INFORME"].isin(cods_coincidentes) |
                df_gen_disp["GRUPO DE TUBERÍAS"].isin(grupos_coincidentes) |
                df_gen_disp.astype(str).apply(lambda row: row.str.lower().str.contains(sq, regex=False)).any(axis=1)
            )
            df_gen_disp = df_gen_disp[mask_asociada]

        df_gen_disp.index = pd.RangeIndex(start=1, stop=len(df_gen_disp) + 1, step=1)
        st.dataframe(df_gen_disp, use_container_width=True)
    else:
        st.info("No hay datos cargados en la sesión.")

# --- 3. PENDIENTES DE ASIGNAR ---
with t_pasig:
    st.subheader("📝 Pendientes de Asignar Informe")
    if not df_pend_asignacion.empty:
        search_pasig = st.text_input("🔍 Buscar:", key="search_pasig")
        res_pasig = df_pend_asignacion.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False).agg({"LINEAS": "sum"})
        
        if search_pasig:
            mask_pasig = res_pasig.astype(str).apply(lambda row: row.str.contains(search_pasig, case=False, regex=False)).any(axis=1)
            res_pasig = res_pasig[mask_pasig]

        res_pasig.index = pd.RangeIndex(start=1, stop=len(res_pasig) + 1, step=1)
        st.dataframe(res_pasig, use_container_width=True)
    else:
        st.info("Sin registros.")

# --- 4. EN PROCESO ---
with t_proc:
    st.subheader("🔄 Informes En Proceso")
    if not df_en_proceso.empty:
        search_proc = st.text_input("🔍 Buscar:", key="search_proc")
        tg = df_en_proceso.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False).agg({"LINEAS": "sum"})
        
        tg_disp = tg.copy()
        if search_proc:
            mask_proc = tg_disp.astype(str).apply(lambda row: row.str.contains(search_proc, case=False, regex=False)).any(axis=1)
            tg_disp = tg_disp[mask_proc]

        tg_disp.index = pd.RangeIndex(start=1, stop=len(tg_disp) + 1, step=1)
        st.dataframe(tg_disp, use_container_width=True)
        
        st.markdown("---")
        st.markdown("##### 📌 Control de Envío (100% Gabinete)")
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_s = c1.selectbox("Código de Informe:", tg["CODIGO DE INFORME"].unique(), key="spc")
        resp_s = c2.selectbox("Inspector Responsable:", PERSONAL_LISTA, key="spr")
        if c3.button("🟢 Enviar al 100%", key="b_proc"):
            ok, m = registrar_solicitud("INFORME COMPLETADO (GABINETE)", cod_s, tg[tg["CODIGO DE INFORME"] == cod_s]["GRUPO DE TUBERÍAS"].values[0], resp_s)
            st.success(m) if ok else st.warning(m)
    else:
        st.info("Sin registros.")

# --- 5. PENDIENTE INSPECCIÓN ---
with t_pinsp:
    st.subheader("⏳ Pendientes de Inspección")
    if not df_pend_inspeccion.empty:
        search_pinsp = st.text_input("🔍 Buscar:", key="search_pinsp")
        res_pinsp = df_pend_inspeccion.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "sum"})
        
        if search_pinsp:
            mask_pinsp = res_pinsp.astype(str).apply(lambda row: row.str.contains(search_pinsp, case=False, regex=False)).any(axis=1)
            res_pinsp = res_pinsp[mask_pinsp]

        res_pinsp.index = pd.RangeIndex(start=1, stop=len(res_pinsp) + 1, step=1)
        st.dataframe(res_pinsp, use_container_width=True)
    else:
        st.info("Sin registros.")

# --- 6. REVISIÓN FIABILIDAD ---
with t_rfiab:
    st.subheader("🔍 Revisión Fiabilidad")
    if not df_fiab_activos.empty:
        search_rfiab = st.text_input("🔍 Buscar:", key="search_rfiab")
        res_fiab = df_fiab_activos.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "sum"})
        
        if search_rfiab:
            mask_rfiab = res_fiab.astype(str).apply(lambda row: row.str.contains(search_rfiab, case=False, regex=False)).any(axis=1)
            res_fiab = res_fiab[mask_rfiab]

        res_fiab.index = pd.RangeIndex(start=1, stop=len(res_fiab) + 1, step=1)
        st.dataframe(res_fiab, use_container_width=True)
    else:
        st.info("Sin registros.")

# --- 7. PENDIENTE REVISIÓN ESPECIALISTA ---
with t_pesp:
    st.subheader("🧑‍🔬 Pendiente Revisión por Especialista")
    if not df_pesp_det.empty:
        search_pesp = st.text_input("🔍 Buscar:", key="search_pesp")
        tg_e = df_pesp_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "sum"})
        
        tg_e_disp = tg_e.copy()
        if search_pesp:
            mask_pesp = tg_e_disp.astype(str).apply(lambda row: row.str.contains(search_pesp, case=False, regex=False)).any(axis=1)
            tg_e_disp = tg_e_disp[mask_pesp]

        tg_e_disp.index = pd.RangeIndex(start=1, stop=len(tg_e_disp) + 1, step=1)
        st.dataframe(tg_e_disp, use_container_width=True)
        
        st.markdown("---")
        st.markdown("##### 📌 Control de Envío a Especialista")
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_pe = c1.selectbox("Código de Informe:", tg_e["CODIGO DE INFORME"].unique(), key="pesp_c")
        resp_pe = c2.selectbox("Especialista:", ESPECIALISTAS_LISTA, key="pesp_r")
        if c3.button("🟢 Enviar", key="b_pesp"):
            grupo_sel = tg_e[tg_e["CODIGO DE INFORME"] == cod_pe]["GRUPO DE TUBERÍAS"].values[0]
            ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_pe, grupo_sel, resp_pe)
            st.success(m) if ok else st.warning(m)
    else:
        st.info("Sin registros.")

# --- 8. REVISIÓN POR ESPECIALISTA ---
with t_resp:
    st.subheader("🔬 Revisión por Especialista")
    if not df_resp_det.empty:
        search_resp = st.text_input("🔍 Buscar:", key="search_resp")
        tg_re = df_resp_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "sum"})
        
        tg_re_disp = tg_re.copy()
        if search_resp:
            mask_resp = tg_re_disp.astype(str).apply(lambda row: row.str.contains(search_resp, case=False, regex=False)).any(axis=1)
            tg_re_disp = tg_re_disp[mask_resp]

        tg_re_disp.index = pd.RangeIndex(start=1, stop=len(tg_re_disp) + 1, step=1)
        st.dataframe(tg_re_disp, use_container_width=True)
        
        st.markdown("---")
        st.markdown("##### 📌 Control de Liberación Especialista")
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_se = c1.selectbox("Código de Informe:", tg_re["CODIGO DE INFORME"].unique(), key="sec")
        resp_se = c2.selectbox("Especialista:", ESPECIALISTAS_LISTA, key="ser")
        if c3.button("🟢 Liberar", key="b_esp"):
            ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_se, tg_re[tg_re["CODIGO DE INFORME"] == cod_se]["GRUPO DE TUBERÍAS"].values[0], resp_se)
            st.success(m) if ok else st.warning(m)
    else:
        st.info("Sin registros.")

# --- 9. CORRECCIÓN PSAIM ---
with t_psaim:
    st.subheader("🛠️ Corrección PSAIM")
    if not df_psaim_det.empty:
        search_psaim = st.text_input("🔍 Buscar:", key="search_psaim")
        tg_p = df_psaim_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "sum"})
        
        tg_p_disp = tg_p.copy()
        if search_psaim:
            mask_psaim = tg_p_disp.astype(str).apply(lambda row: row.str.contains(search_psaim, case=False, regex=False)).any(axis=1)
            tg_p_disp = tg_p_disp[mask_psaim]

        tg_p_disp.index = pd.RangeIndex(start=1, stop=len(tg_p_disp) + 1, step=1)
        st.dataframe(tg_p_disp, use_container_width=True)
        
        st.markdown("---")
        st.markdown("##### 📌 Control PSAIM")
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_sp = c1.selectbox("Código de Informe:", tg_p["CODIGO DE INFORME"].unique(), key="spc_p")
        resp_sp = c2.selectbox("Revisor PSAIM:", REVISORES_PSAIM_LISTA, key="spr_p")
        if c3.button("🟢 Conforme", key="b_psaim"):
            ok, m = registrar_solicitud("CORRECCIÓN PSAIM", cod_sp, tg_p[tg_p["CODIGO DE INFORME"] == cod_sp]["GRUPO DE TUBERÍAS"].values[0], resp_sp)
            st.success(m) if ok else st.warning(m)
    else:
        st.info("Sin registros.")

# --- 10. RESÚMENES (T3, T4, T5) ---
with t_res_m:
    st.subheader("📅 Resumen Mes (T3)")
    if not df_activos.empty:
        piv_m = pd.pivot_table(df_activos, index="MES", columns="ESTADO - ELABORACIÓN DE INFORME", values="LINEAS", aggfunc="sum", fill_value=0)
        piv_m.index = pd.RangeIndex(start=1, stop=len(piv_m) + 1, step=1)
        st.dataframe(piv_m, use_container_width=True)

with t_p_m:
    st.subheader("📊 Pend. Mes/Obs (T4)")
    if not df_activos.empty:
        piv_po = pd.pivot_table(df_activos, index="MES", columns="OBSERVACIÓN", values="LINEAS", aggfunc="sum", fill_value=0)
        piv_po.index = pd.RangeIndex(start=1, stop=len(piv_po) + 1, step=1)
        st.dataframe(piv_po, use_container_width=True)

with t_res_o:
    st.subheader("📌 Resumen Obs (T5)")
    if not df_activos.empty:
        piv_o = pd.pivot_table(df_activos, index="OBSERVACIÓN", columns="ESTADO - ELABORACIÓN DE INFORME", values="LINEAS", aggfunc="sum", fill_value=0)
        piv_o.index = pd.RangeIndex(start=1, stop=len(piv_o) + 1, step=1)
        st.dataframe(piv_o, use_container_width=True)
