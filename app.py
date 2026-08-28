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

    .stApp { background-color: #F8FAFC; }

    .header-banner {
        background: linear-gradient(135deg, #0E2A47 0%, #1A3E68 100%);
        padding: 24px 32px;
        border-radius: 12px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(14, 42, 71, 0.15);
        border-left: 6px solid #D4AF37;
    }
    .header-title { font-size: 26px; font-weight: 700; letter-spacing: 0.5px; margin: 0; color: #FFFFFF; }
    .header-subtitle { font-size: 14px; color: #CBD5E1; margin-top: 4px; font-weight: 400; }

    .kpi-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px 6px;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s, box-shadow 0.2s;
        min-height: 95px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
    }
    .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); }
    .kpi-title { font-size: 9.5px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.2px; margin-bottom: 4px; line-height: 1.2; }
    .kpi-value { font-size: 22px; font-weight: 800; color: #0E2A47; }

    .b-blue { border-top: 4px solid #0E2A47; }
    .b-orange { border-top: 4px solid #F59E0B; }
    .b-green { border-top: 4px solid #10B981; }
    .b-purple { border-top: 4px solid #8B5CF6; }
    .b-red { border-top: 4px solid #EF4444; }
    .b-teal { border-top: 4px solid #14B8A6; }
    .b-indigo { border-top: 4px solid #6366F1; }
    .b-cyan { border-top: 4px solid #06B6D4; }
    .b-gold { border-top: 4px solid #D4AF37; }
    .b-pink { border-top: 4px solid #EC4899; }

    .stTabs [data-baseweb="tab-list"] { gap: 4px; background-color: #F1F5F9; padding: 6px; border-radius: 8px; }
    .stTabs [data-baseweb="tab"] { height: 38px; border-radius: 6px; font-size: 11.5px; font-weight: 600; color: #475569; padding: 0 10px; }
    .stTabs [aria-selected="true"] { background-color: #0E2A47 !important; color: #FFFFFF !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .stDataFrame, div[data-testid="stDataEditor"] { background-color: #FFFFFF !important; border-radius: 8px; border: 1px solid #E2E8F0; padding: 4px; }
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

def procesar_cambios_tabla():
    """Lógica para limpiar OBSERVACIÓN automáticamente al cambiar ESTADO - VALORIZACIÓN a 'SI'"""
    editor_state = st.session_state.get("editor_tabla_general_select", {})
    edited_rows = editor_state.get("edited_rows", {})
    
    if edited_rows:
        for row_idx, changes in edited_rows.items():
            if "ESTADO - VALORIZACIÓN" in changes:
                nuevo_val = str(changes["ESTADO - VALORIZACIÓN"]).strip().upper()
                if nuevo_val == "SI":
                    changes["OBSERVACIÓN"] = ""

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
            # ==========================================
# CÁLCULO MÚLTIPLE DE KPIS
# ==========================================
total_informes = len(df)
inf_finalizados = len(df[df["ESTADO - ELABORACIÓN DE INFORME"].astype(str).str.strip().str.upper() == "FINALIZADO"])
inf_pendientes = total_informes - inf_finalizados
inf_observados = len(df[df["OBSERVACIÓN"].astype(str).str.strip() != ""])

inf_cod_prov = len(df[df["CODIGO DE INFORME"].apply(es_codigo_provisional)])
inf_corr_psaim = len(df[df["OBSERVACIÓN"].apply(es_correccion_psaim)])
inf_pend_insp = len(df[df.apply(es_pendiente_inspeccion_fn, axis=1)])

inf_valorizados = len(df[df["ESTADO - VALORIZACIÓN"].astype(str).str.strip().str.upper() == "SI"])
inf_pend_valoriz = total_informes - inf_valorizados

# ==========================================
# RENDERIZADO DE MÉTREDOS / KPIS DENTRO DE CARDS
# ==========================================
st.markdown(f"""
    <div style="display: grid; grid-template-columns: repeat(10, 1fr); gap: 6px; margin-bottom: 20px;">
        <div class="kpi-card b-blue"><div class="kpi-title">TOTAL INFORMES</div><div class="kpi-value">{total_informes}</div></div>
        <div class="kpi-card b-orange"><div class="kpi-title">INFORMES PENDIENTES</div><div class="kpi-value">{inf_pendientes}</div></div>
        <div class="kpi-card b-green"><div class="kpi-title">INFORMES FINALIZADOS</div><div class="kpi-value">{inf_finalizados}</div></div>
        <div class="kpi-card b-purple"><div class="kpi-title">CÓDIGO PROVISIONAL</div><div class="kpi-value">{inf_cod_prov}</div></div>
        <div class="kpi-card b-red"><div class="kpi-title">OBSERVADOS EN REVISIÓN</div><div class="kpi-value">{inf_observados}</div></div>
        <div class="kpi-card b-teal"><div class="kpi-title">CORRECCIÓN EN PSAIM</div><div class="kpi-value">{inf_corr_psaim}</div></div>
        <div class="kpi-card b-indigo"><div class="kpi-title">PENDIENTE INSPECCIÓN</div><div class="kpi-value">{inf_pend_insp}</div></div>
        <div class="kpi-card b-cyan"><div class="kpi-title">P. PEND. VALORIZACIÓN</div><div class="kpi-value">{inf_pend_valoriz}</div></div>
        <div class="kpi-card b-gold"><div class="kpi-title">VALORIZADO (SI)</div><div class="kpi-value">{inf_valorizados}</div></div>
        <div class="kpi-card b-pink"><div class="kpi-title">VALORIZACIÓN PENDIENTE</div><div class="kpi-value">{inf_pend_valoriz}</div></div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# ESTRUCTURA DE PESTAÑAS PRINCIPALES
# ==========================================
tabs = st.tabs([
    "📋 Tabla General",
    "⏳ Inf. Pendientes",
    "🏷️ Códigos Provisionales",
    "📝 Observados en Revisión",
    "🛠️ Corrección en PSAIM",
    "🔍 Pendientes de Inspección",
    "💲 Pendientes de Valorización",
    "✅ Valorizados (SI)",
    "📩 Solicitudes de Cambios",
    "⚙️ Panel de Administración"
])

# ------------------------------------------
# 1. TABLA GENERAL (EDICIÓN INTERACTIVA)
# ------------------------------------------
with tabs[0]:
    col_filtro_m, col_filtro_r, col_busqueda = st.columns([1.5, 1.5, 3])
    
    meses = ["Todos"] + sorted([m for m in df["MES"].dropna().astype(str).str.strip().str.upper().unique() if m], key=lambda x: ORDEN_MESES.index(x) if x in ORDEN_MESES else 99)
    resps = ["Todos"] + sorted([r for r in df["RESPONSABLE"].dropna().astype(str).str.strip().str.upper().unique() if r])
    
    m_sel = col_filtro_m.selectbox("Filtrar por Mes:", meses, key="f_mes_gen")
    r_sel = col_filtro_r.selectbox("Filtrar por Responsable:", resps, key="f_resp_gen")
    q_busqueda = col_busqueda.text_input("🔍 Buscar por Línea, Código de Informe, Grupo o SAP:", "", key="b_gen")

    df_dis = df[COLUMNAS_EXCEL].copy()

    for col_int in ["ITEM POR MES", "IT2", "SAP"]:
        df_dis[col_int] = df_dis[col_int].apply(formatear_entero_limpio)

    if m_sel != "Todos": df_dis = df_dis[df_dis["MES"].astype(str).str.strip().str.upper() == m_sel]
    if r_sel != "Todos": df_dis = df_dis[df_dis["RESPONSABLE"].astype(str).str.strip().str.upper() == r_sel]
    if q_busqueda.strip():
        q_norm = texto_normalizado(q_busqueda)
        df_dis = df_dis[df_dis.apply(lambda r: q_norm in texto_normalizado(r["LINEAS"]) or q_norm in texto_normalizado(r["CODIGO DE INFORME"]) or q_norm in texto_normalizado(r["GRUPO DE TUBERÍAS"]) or q_norm in texto_normalizado(r["SAP"]), axis=1)]

    df_dis["ESTADO - VALORIZACIÓN"] = df_dis["ESTADO - VALORIZACIÓN"].apply(
        lambda x: "SI" if texto_normalizado(x) == "SI" else "Pendiente - valorización"
    )

    df_dis = preparar_tabla_con_indice_1(df_dis)

    config_cols = {
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
        "RESPONSABLE": st.column_config.SelectboxColumn("RESPONSABLE", options=PERSONAL_LISTA, width="medium"),
        "OBSERVACIÓN": st.column_config.TextColumn("OBSERVACIÓN", width="large"),
        "ESTADO - VALORIZACIÓN": st.column_config.SelectboxColumn(
            "ESTADO - VALORIZACIÓN",
            options=["Pendiente - valorización", "SI"],
            required=True,
            width="medium"
        )
    }

    ed_df = st.data_editor(
        df_dis,
        column_config=config_cols,
        hide_index=False,
        use_container_width=True,
        key="editor_tabla_general_select",
        on_change=procesar_cambios_tabla
    )

    if st.button("💾 Guardar Cambios Realizados", key="btn_save_main"):
        for idx in ed_df.index:
            idx_orig = idx - 1
            for col in COLUMNAS_EXCEL:
                st.session_state.df_data.at[idx_orig, col] = ed_df.at[idx, col]
            
            val_valoriz = str(ed_df.at[idx, "ESTADO - VALORIZACIÓN"]).strip().upper()
            if val_valoriz == "SI":
                st.session_state.df_data.at[idx_orig, "OBSERVACIÓN"] = ""

        st.session_state.df_data = limpiar_estado_y_responsable(st.session_state.df_data[COLUMNAS_EXCEL])
        guardar_datos(st.session_state.df_data)
        st.success("¡Base de datos actualizada con éxito!")
        st.rerun()

# ------------------------------------------
# 2. INFORMES PENDIENTES
# ------------------------------------------
with tabs[1]:
    st.markdown("##### ⏳ Informes Pendientes de Elaboración")
    df_p = df[df["ESTADO - ELABORACIÓN DE INFORME"].astype(str).str.strip().str.upper() != "FINALIZADO"].copy()
    for col in ["ITEM POR MES", "IT2", "SAP"]: df_p[col] = df_p[col].apply(formatear_entero_limpio)
    st.dataframe(preparar_tabla_con_indice_1(df_p), use_container_width=True)

# ------------------------------------------
# 3. CÓDIGOS PROVISIONALES
# ------------------------------------------
with tabs[2]:
    st.markdown("##### 🏷️ Informes con Código Provisional")
    df_cp = df[df["CODIGO DE INFORME"].apply(es_codigo_provisional)].copy()
    for col in ["ITEM POR MES", "IT2", "SAP"]: df_cp[col] = df_cp[col].apply(formatear_entero_limpio)
    st.dataframe(preparar_tabla_con_indice_1(df_cp), use_container_width=True)

# ------------------------------------------
# 4. OBSERVADOS EN REVISIÓN
# ------------------------------------------
with tabs[3]:
    st.markdown("##### 📝 Informes Observados en Revisión")
    df_obs = df[df["OBSERVACIÓN"].astype(str).str.strip() != ""].copy()
    for col in ["ITEM POR MES", "IT2", "SAP"]: df_obs[col] = df_obs[col].apply(formatear_entero_limpio)
    st.dataframe(preparar_tabla_con_indice_1(df_obs), use_container_width=True)

# ------------------------------------------
# 5. CORRECCIÓN EN PSAIM
# ------------------------------------------
with tabs[4]:
    st.markdown("##### 🛠️ Informes para Corrección en PSAIM")
    df_ps = df[df["OBSERVACIÓN"].apply(es_correccion_psaim)].copy()
    for col in ["ITEM POR MES", "IT2", "SAP"]: df_ps[col] = df_ps[col].apply(formatear_entero_limpio)
    st.dataframe(preparar_tabla_con_indice_1(df_ps), use_container_width=True)

# ------------------------------------------
# 6. PENDIENTES DE INSPECCIÓN
# ------------------------------------------
with tabs[5]:
    st.markdown("##### 🔍 Informes Pendientes de Inspección Campo")
    df_pi = df[df.apply(es_pendiente_inspeccion_fn, axis=1)].copy()
    for col in ["ITEM POR MES", "IT2", "SAP"]: df_pi[col] = df_pi[col].apply(formatear_entero_limpio)
    st.dataframe(preparar_tabla_con_indice_1(df_pi), use_container_width=True)

# ------------------------------------------
# 7. PENDIENTES DE VALORIZACIÓN
# ------------------------------------------
with tabs[6]:
    st.markdown("##### 💲 Informes Pendientes de Valorización")
    df_pv = df[df["ESTADO - VALORIZACIÓN"].astype(str).str.strip().str.upper() != "SI"].copy()
    for col in ["ITEM POR MES", "IT2", "SAP"]: df_pv[col] = df_pv[col].apply(formatear_entero_limpio)
    st.dataframe(preparar_tabla_con_indice_1(df_pv), use_container_width=True)

# ------------------------------------------
# 8. VALORIZADOS (SI)
# ------------------------------------------
with tabs[7]:
    st.markdown("##### ✅ Informes Completamente Valorizados")
    df_val = df[df["ESTADO - VALORIZACIÓN"].astype(str).str.strip().str.upper() == "SI"].copy()
    for col in ["ITEM POR MES", "IT2", "SAP"]: df_val[col] = df_val[col].apply(formatear_entero_limpio)
    st.dataframe(preparar_tabla_con_indice_1(df_val), use_container_width=True)

# ------------------------------------------
# 9. SOLICITUDES DE CAMBIOS
# ------------------------------------------
with tabs[8]:
    st.markdown("##### 📩 Enviar Solicitud de Cambio al Administrador")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        sol_tipo = st.selectbox("Tipo de Solicitud:", ["REGISTRO DE NUEVO INFORME", "MODIFICACIÓN DE INFORME EXISTENTE", "ELIMINACIÓN DE INFORME"])
        sol_codigo = st.text_input("Código de Informe:")
        sol_grupo = st.text_input("Grupo de Tuberías:")
    with col_s2:
        sol_solicitante = st.selectbox("Solicitado Por:", PERSONAL_LISTA)
        sol_motivo = st.text_area("Detalle / Justificación del cambio:")
        
        if st.button("📨 Enviar Solicitud"):
            if sol_codigo.strip() and sol_grupo.strip():
                ok_s, msg_s = registrar_solicitud(sol_tipo, sol_codigo, sol_grupo, f"{sol_solicitante} - {sol_motivo}")
                if ok_s: st.success(msg_s)
                else: st.warning(msg_s)
            else:
                st.error("Por favor complete los campos obligatorios.")

# ------------------------------------------
# 10. PANEL DE ADMINISTRACIÓN
# ------------------------------------------
with tabs[9]:
    st.markdown("##### ⚙️ Panel de Gestión de Solicitudes Pendientes")
    solicitudes_list = cargar_solicitudes()
    
    if solicitudes_list:
        df_sol = pd.DataFrame(solicitudes_list)
        st.dataframe(df_sol, use_container_width=True)
        
        col_adm1, col_adm2 = st.columns(2)
        sol_id_sel = col_adm1.number_input("ID de Solicitud para Gestionar:", min_value=1, step=1)
        
        if col_adm2.button("✅ Aprobar / Finalizar Solicitud"):
            for s in solicitudes_list:
                if s["id"] == sol_id_sel:
                    s["estado"] = "APROBADO"
            guardar_solicitudes(solicitudes_list)
            st.success(f"Solicitud #{sol_id_sel} marcada como APROBADA.")
            st.rerun()
    else:
        st.info("No hay solicitudes registradas actualmente.")
