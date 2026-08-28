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

# Listas de personal diferenciadas según rol
ESPECIALISTAS_LISTA = ["Jesús Rehkoff Díaz", "M. Paifa", "Julio Ponce", "Omar", "Christopher", "Timana", "Ingrid"]
REVISORES_PSAIM_LISTA = ["Franmary Gutierrez", "Alejandro Macury", "M. Paifa", "Julio Ponce", "Omar", "Christopher", "Timana", "Ingrid"]
PERSONAL_LISTA_BASE = ["M. Paifa", "Julio Ponce", "Omar", "Christopher", "Timana", "Ingrid", "Juan José", "Dante", "Jesús Rehkoff Díaz", "Franmary Gutierrez", "Alejandro Macury", "Otro Inspector"]

def texto_normalizado(texto):
    if pd.isna(texto): return ""
    t = str(texto).strip().upper()
    replacements = {"Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ü": "U", "Ñ": "N"}
    for orig, repl in replacements.items(): t = t.replace(orig, repl)
    return t

def limpiar_estado_y_responsable(df_input):
    df_clean = df_input.copy()
    for idx, row in df_clean.iterrows():
        val_estado = str(row["ESTADO - ELABORACIÓN DE INFORME"]).strip()
        val_resp = str(row["RESPONSABLE"]).strip()
        if "-" in val_estado:
            partes = val_estado.split("-", 1)
            df_clean.at[idx, "ESTADO - ELABORACIÓN DE INFORME"] = partes[0].strip()
            if val_resp in ["", "nan", "None"]:
                df_clean.at[idx, "RESPONSABLE"] = partes[1].strip()
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

# Construcción dinámica de la lista general de personal
resp_unicos = [str(r).strip() for r in df["RESPONSABLE"].unique() if pd.notna(r) and str(r).strip() not in ["", "nan", "None"]]
PERSONAL_LISTA = sorted(list(set(PERSONAL_LISTA_BASE + resp_unicos)))

st.markdown("""
    <div class="header-banner">
        <div class="header-title">CONTROL INTERNO DE INFORMES - ADEMINSAC</div>
        <div class="header-subtitle">Sistema de Monitoreo de Inspección Técnicas y Valorización | Refinería La Pampilla</div>
    </div>
""", unsafe_allow_html=True)
# --- CÁLCULO DE VISTAS Y FILTROS ---
def get_vistas(df_in):
    v_prov = df_in[df_in["CODIGO DE INFORME"].apply(es_codigo_provisional)]
    
    # Filtro Pendiente Inspección
    v_insp = df_in[df_in.apply(es_pendiente_inspeccion_fn, axis=1)]
    
    # Resto de registros asignados
    df_rest = df_in.drop(v_prov.index).drop(v_insp.index, errors='ignore')
    
    v_fiab = df_rest[df_rest["OBSERVACIÓN"].apply(lambda x: "REVISE" in texto_normalizado(x) or "FIABILIDAD" in texto_normalizado(x))]
    v_esp_pend = df_rest[df_rest["OBSERVACIÓN"].apply(lambda x: "PEND" in texto_normalizado(x) and "ESPECIALISTA" in texto_normalizado(x))]
    v_esp_rev = df_rest[df_rest["OBSERVACIÓN"].apply(lambda x: "INFORME REVISADO POR ESPECIALISTA" in texto_normalizado(x))]
    v_psaim = df_rest[df_rest["OBSERVACIÓN"].apply(es_correccion_psaim)]
    
    v_proc = df_rest.drop(v_fiab.index, errors='ignore').drop(v_esp_pend.index, errors='ignore').drop(v_esp_rev.index, errors='ignore').drop(v_psaim.index, errors='ignore')
    v_proc = v_proc[v_proc["ESTADO - ELABORACIÓN DE INFORME"].apply(lambda x: "FINALIZADO" not in texto_normalizado(x))]
    
    return v_prov, v_proc, v_insp, v_fiab, v_esp_pend, v_esp_rev, v_psaim

v_prov, v_proc, v_insp, v_fiab, v_esp_pend, v_esp_rev, v_psaim = get_vistas(df)
solic_todas = cargar_solicitudes()
solic_activas = [s for s in solic_todas if s.get("estado") == "PENDIENTE"]

# KPI Metrics Bar
k1, k2, k3, k4, k5, k6, k7, k8, k9 = st.columns(9)
k1.markdown(f'<div class="kpi-card b-blue"><div class="kpi-title">TOTAL INFORMES</div><div class="kpi-value">{len(df)}</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="kpi-card b-gold"><div class="kpi-title">PEND. ASIGNAR</div><div class="kpi-value">{len(v_prov)}</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="kpi-card b-orange"><div class="kpi-title">EN PROCESO</div><div class="kpi-value">{len(v_proc)}</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="kpi-card b-purple"><div class="kpi-title">PEND. INSPECCIÓN</div><div class="kpi-value">{len(v_insp)}</div></div>', unsafe_allow_html=True)
k5.markdown(f'<div class="kpi-card b-cyan"><div class="kpi-title">REV. FIABILIDAD</div><div class="kpi-value">{len(v_fiab)}</div></div>', unsafe_allow_html=True)
k6.markdown(f'<div class="kpi-card b-indigo"><div class="kpi-title">PEND. REV. ESP.</div><div class="kpi-value">{len(v_esp_pend)}</div></div>', unsafe_allow_html=True)
k7.markdown(f'<div class="kpi-card b-teal"><div class="kpi-title">REV. ESPECIALISTA</div><div class="kpi-value">{len(v_esp_rev)}</div></div>', unsafe_allow_html=True)
k8.markdown(f'<div class="kpi-card b-red"><div class="kpi-title">CORREC. PSAIM</div><div class="kpi-value">{len(v_psaim)}</div></div>', unsafe_allow_html=True)
k9.markdown(f'<div class="kpi-card b-pink"><div class="kpi-title">SOLICITUDES</div><div class="kpi-value">{len(solic_activas)}</div></div>', unsafe_allow_html=True)

st.write("")

# Pestanas
t_admin, t_gen, t_asign, t_proc, t_insp, t_fiab, t_esp_pend, t_esp_rev, t_psaim, t_res_mes, t_res_obs_t4, t_res_obs_t5 = st.tabs([
    f"🔔 Admin ({len(solic_activas)})",
    "📋 Tabla General",
    f"📋 Pend. Asignar ({len(v_prov)})",
    f"🔄 En Proceso ({len(v_proc)})",
    f"⌛ Pend. Inspección ({len(v_insp)})",
    f"🔍 Rev. Fiabilidad ({len(v_fiab)})",
    f"💡 Pend. Rev. Especialista ({len(v_esp_pend)})",
    f"🔬 Rev. por Especialista ({len(v_esp_rev)})",
    f"🛠️ Correc. PSAIM ({len(v_psaim)})",
    "📅 Resumen Mes (T3)",
    "📊 Pend. Mes/Obs (T4)",
    "📌 Resumen Obs (T5)"
])

# --- PESTAÑA ADMIN (CORREGIDA) ---
with t_admin:
    st.markdown("#### **BANDEJA DE APROBACIÓN (ADMINISTRADOR)**")
    if solic_activas:
        for sol in solic_activas:
            c_inf, c_app, c_rej = st.columns([4, 1, 1])
            c_inf.markdown(f"📌 **[{sol['tipo']}]** Código: **{sol['codigo']}** | Grupo: **{sol['grupo']}** | Solicitante: **{sol['solicitante']}**")
            
            # Botón Aprobar
            if c_app.button("✅ Aprobar", key=f"app_{sol['id']}"):
                mask = (df["CODIGO DE INFORME"] == sol["codigo"]) & (df["GRUPO DE TUBERÍAS"] == sol["grupo"])
                if sol["tipo"] == "INFORME COMPLETADO (GABINETE)": 
                    df.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "FINALIZADO"
                elif sol["tipo"] == "CORRECCIÓN PSAIM": 
                    df.loc[mask, "OBSERVACIÓN"] = "PSAIM CORREGIDO"
                    df.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "EN PROCESO"
                elif sol["tipo"] == "REVISIÓN ESPECIALISTA": 
                    df.loc[mask, "OBSERVACIÓN"] = "INFORME REVISADO POR ESPECIALISTA"
                
                # Actualizar base de solicitudes
                todas_solicitudes = cargar_solicitudes()
                for s in todas_solicitudes:
                    if s["id"] == sol["id"]:
                        s["estado"] = "APROBADO"
                guardar_solicitudes(todas_solicitudes)
                guardar_datos(df)
                st.session_state.df_data = df
                st.success("Solicitud aprobada correctamente.")
                st.rerun()
            
            # Botón Rechazar (Corregido con actualización JSON y recarga st.rerun)
            if c_rej.button("❌ Rechazar", key=f"rej_{sol['id']}"):
                todas_solicitudes = cargar_solicitudes()
                for s in todas_solicitudes:
                    if s["id"] == sol["id"]:
                        s["estado"] = "RECHAZADO"
                guardar_solicitudes(todas_solicitudes)
                st.warning("Solicitud rechazada.")
                st.rerun()
            
            st.divider()
    else: 
        st.success("✨ No hay solicitudes pendientes.")

# --- PESTAÑA TABLA GENERAL ---
with t_gen:
    st.markdown("#### **BASE GENERAL DE INFORMES**")
    f_mes = st.multiselect("Filtrar por Mes", options=sorted(list(set(df["MES"].dropna().unique()))))
    f_resp = st.multiselect("Filtrar por Responsable", options=PERSONAL_LISTA)
    df_ver = df.copy()
    if f_mes: df_ver = df_ver[df_ver["MES"].isin(f_mes)]
    if f_resp: df_ver = df_ver[df_ver["RESPONSABLE"].isin(f_resp)]
    
    df_edit = st.data_editor(
        df_ver,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "RESPONSABLE": st.column_config.SelectboxColumn("RESPONSABLE", options=PERSONAL_LISTA),
            "ESTADO - ELABORACIÓN DE INFORME": st.column_config.SelectboxColumn("ESTADO", options=["EN PROCESO", "PENDIENTE COMPLETAR INSPECCION", "FINALIZADO"]),
            "ESTADO - VALORIZACIÓN": st.column_config.SelectboxColumn("VALORIZACIÓN", options=["PENDIENTE", "VALORIZADO", "NO APLICA"])
        },
        key="editor_general"
    )
    if st.button("💾 Guardar Cambios Generales"):
        guardar_datos(df_edit)
        st.session_state.df_data = df_edit
        st.success("Cambios guardados con éxito.")
        st.rerun()

# --- PESTAÑA PENDIENTE ASIGNAR ---
with t_asign:
    st.markdown("#### **INFORMES PENDIENTES DE ASIGNACIÓN CÓDIGO/RESPONSABLE**")
    st.dataframe(v_prov, use_container_width=True)

# --- PESTAÑA EN PROCESO ---
with t_proc:
    st.markdown("#### **INFORMES EN PROCESO DE ELABORACIÓN**")
    st.dataframe(v_proc, use_container_width=True)
    st.divider()
    st.markdown("##### 📤 Solicitud de Finalización")
    c1, c2, c3 = st.columns([2, 2, 1])
    code_sel = c1.selectbox("Seleccionar Código", options=v_proc["CODIGO DE INFORME"].unique(), key="s_proc_c")
    solic_by = c2.selectbox("Solicitante", options=PERSONAL_LISTA, key="s_proc_r")
    if c3.button("Solicitar Aprobación", key="btn_sol_proc"):
        row_sel = v_proc[v_proc["CODIGO DE INFORME"] == code_sel].iloc[0]
        ok, msg = registrar_solicitud("INFORME COMPLETADO (GABINETE)", code_sel, row_sel["GRUPO DE TUBERÍAS"], solic_by)
        if ok: st.success(msg)
        else: st.warning(msg)

# --- PESTAÑA PENDIENTE INSPECCIÓN ---
with t_insp:
    st.markdown("#### **INFORMES CON INSPECCIÓN EN CAMPO PENDIENTE**")
    st.dataframe(v_insp, use_container_width=True)

# --- PESTAÑA REVISIÓN FIABILIDAD ---
with t_fiab:
    st.markdown("#### **OBSERVACIONES DE FIABILIDAD**")
    st.dataframe(v_fiab, use_container_width=True)

# --- PESTAÑA PENDIENTE REV. ESPECIALISTA ---
with t_esp_pend:
    st.markdown("#### **INFORMES PENDIENTES DE REVISIÓN POR ESPECIALISTA**")
    st.dataframe(v_esp_pend, use_container_width=True)
    st.divider()
    c1, c2, c3 = st.columns([2, 2, 1])
    code_sel_esp = c1.selectbox("Seleccionar Código para Especialista", options=v_esp_pend["CODIGO DE INFORME"].unique(), key="s_esp_c")
    solic_by_esp = c2.selectbox("Especialista Asignado", options=ESPECIALISTAS_LISTA, key="s_esp_r")
    if c3.button("Enviar a Revisión Especialista", key="btn_sol_esp"):
        row_sel = v_esp_pend[v_esp_pend["CODIGO DE INFORME"] == code_sel_esp].iloc[0]
        ok, msg = registrar_solicitud("REVISIÓN ESPECIALISTA", code_sel_esp, row_sel["GRUPO DE TUBERÍAS"], solic_by_esp)
        if ok: st.success(msg)
        else: st.warning(msg)

# --- PESTAÑA REVISIÓN POR ESPECIALISTA ---
with t_esp_rev:
    st.markdown("#### **INFORMES REVISADOS POR ESPECIALISTA**")
    st.dataframe(v_esp_rev, use_container_width=True)

# --- PESTAÑA CORRECCIÓN PSAIM ---
with t_psaim:
    st.markdown("#### **CORRECCIONES REQUERIDAS POR PSAIM**")
    st.dataframe(v_psaim, use_container_width=True)
    st.divider()
    c1, c2, c3 = st.columns([2, 2, 1])
    code_sel_p = c1.selectbox("Seleccionar Código PSAIM", options=v_psaim["CODIGO DE INFORME"].unique(), key="s_p_c")
    solic_by_p = c2.selectbox("Revisor PSAIM", options=REVISORES_PSAIM_LISTA, key="s_p_r")
    if c3.button("Marcar Corregido (PSAIM)", key="btn_sol_psaim"):
        row_sel = v_psaim[v_psaim["CODIGO DE INFORME"] == code_sel_p].iloc[0]
        ok, msg = registrar_solicitud("CORRECCIÓN PSAIM", code_sel_p, row_sel["GRUPO DE TUBERÍAS"], solic_by_p)
        if ok: st.success(msg)
        else: st.warning(msg)

# --- PESTAÑA RESUMEN MES (T3) ---
with t_res_mes:
    st.markdown("#### **TABLA RESUMEN POR MES (CANTIDADES)**")
    df_t3 = df.groupby("MES").size().reindex(ORDEN_MESES).fillna(0).reset_index(name="CANTIDAD DE INFORMES")
    st.dataframe(df_t3, use_container_width=True)

# --- PESTAÑA PEND. MES/OBS (T4) ---
with t_res_obs_t4:
    st.markdown("#### **RESUMEN PENDIENTES POR MES Y OBSERVACIÓN**")
    df_t4 = df.pivot_table(index="MES", columns="OBSERVACIÓN", values="CODIGO DE INFORME", aggfunc="count", fill_value=0)
    st.dataframe(df_t4, use_container_width=True)

# --- PESTAÑA RESUMEN OBS (T5) ---
with t_res_obs_t5:
    st.markdown("#### **RESUMEN GLOBAL POR OBSERVACIÓN**")
    df_t5 = df.groupby("OBSERVACIÓN").size().reset_index(name="TOTAL").sort_values(by="TOTAL", ascending=False)
    st.dataframe(df_t5, use_container_width=True)
