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
# --- SECCIÓN DE GESTIÓN Y CARGA DE EXCEL ---
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
    df_pend_asignacion = df_activos[df_activos["CODIGO DE INFORME"].apply(es_codigo_provisional)]
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

    # --- KPI TARJETAS ---
    k1, k2, k3, k4, k5, k6, k7, k8, k9, k10 = st.columns(10)
    kpis = [
        (k1, "INFORMES TOTALES", len(dict_unicos), "b-blue"),
        (k2, "PENDIENTES TOTAL", sum(dict_t3_pen.values()), "b-orange"),
        (k3, "VALORIZADOS (SI)", sum(dict_t3_val.values()), "b-green"),
        (k4, "PEND. ASIGNAR INFORME", len(df_pend_asignacion), "b-pink"),
        (k5, "EN PROCESO", len(df_en_proceso), "b-purple"),
        (k6, "PEND. INSPECCIÓN", len(df_pend_inspeccion), "b-red"),
        (k7, "REV. FIABILIDAD", cnt_revision_fiabilidad, "b-teal"),
        (k8, "PEND. REV. ESPECIALISTA", cnt_pend_revision_especialista, "b-indigo"),
        (k9, "REV. POR ESPECIALISTA", cnt_revision_por_especialista, "b-cyan"),
        (k10, "CORRECCIÓN PSAIM", len(df_psaim_det), "b-gold")
    ]
    for col, titulo, valor, clase in kpis:
        col.markdown(f'<div class="kpi-card {clase}"><div class="kpi-title">{titulo}</div><div class="kpi-value">{valor}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    solic_activas = [s for s in cargar_solicitudes() if s["estado"] == "PENDIENTE"]
    
    # --- PESTAÑAS Y CANTIDADES EN TÍTULOS ---
    cnt_pasig = len(df_pend_asignacion)
    cnt_proc = len(df_en_proceso)
    cnt_pinsp = len(df_pend_inspeccion)
    df_rfiab_det = df_activos[df_activos["OBSERVACIÓN"].apply(lambda x: "ENTREGADO PARA SU REVISION" in texto_normalizado(x) and "FIABILIDAD" in texto_normalizado(x))]
    df_pesp_det = df_activos[df_activos["OBSERVACIÓN"].apply(lambda x: "PENDIENTE REVISION POR EL ESPECIALISTA" in texto_normalizado(x))]
    df_resp_det = df_activos[df_activos["OBSERVACIÓN"].apply(lambda x: ("REV. POR EL ESPECIALISTA" in texto_normalizado(x) or "REVISION POR EL ESPECIALISTA" in texto_normalizado(x)) and "PENDIENTE" not in texto_normalizado(x))]

    t_admin, t_gen, t_pasig, t_proc, t_pinsp, t_rfiab, t_pesp, t_resp, t_psaim, t_t3, t_t4, t_t5 = st.tabs([
        f"🔔 Admin ({len(solic_activas)})" if solic_activas else "🔔 Admin",
        "📋 Tabla General",
        f"📋 Pend. Asignar ({cnt_pasig})",
        f"🔄 En Proceso ({cnt_proc})",
        f"⏳ Pend. Inspección ({cnt_pinsp})",
        f"🔍 Rev. Fiabilidad ({len(df_rfiab_det)})",
        f"💡 Pend. Rev. Especialista ({len(df_pesp_det)})",
        f"🔬 Rev. por Especialista ({len(df_resp_det)})",
        f"🛠️ Correc. PSAIM ({len(df_psaim_det)})",
        "📅 Resumen Mes (T3)",
        "📊 Pend. Mes/Obs (T4)",
        "📌 Resumen Obs (T5)"
    ])

    # --- 🔔 ADMIN (BANDEJA CORREGIDA DE RECHAZO) ---
    with t_admin:
        st.markdown("#### **BANDEJA DE APROBACIÓN (ADMINISTRADOR)**")
        if solic_activas:
            for sol in solic_activas:
                c_inf, c_app, c_rej = st.columns([4, 1, 1])
                c_inf.markdown(f"📌 **[{sol['tipo']}]** Código: **{sol['codigo']}** | Grupo: **{sol['grupo']}** | Solicitante: **{sol['solicitante']}**")
                
                # APROBAR
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

                # RECHAZAR (CORREGIDO CON RERUN INMEDIATO)
                if c_rej.button("❌ Rechazar", key=f"rej_{sol['id']}"):
                    solicitudes = cargar_solicitudes()
                    for s in solicitudes:
                        if s["id"] == sol["id"]: s["estado"] = "RECHAZADO"
                    guardar_solicitudes(solicitudes)
                    st.warning("Solicitud rechazada.")
                    st.rerun()

                st.divider()
        else: st.success("✨ No hay solicitudes pendientes.")

    # --- 📋 TABLA GENERAL ---
    with t_gen:
        c_m, c_b = st.columns([1, 3])
        meses_disp = ["Todos"] + sorted([m for m in df["MES"].dropna().astype(str).str.strip().str.upper().unique() if m], key=lambda x: ORDEN_MESES.index(x) if x in ORDEN_MESES else 99)
        m_sel = c_m.selectbox("Filtrar Mes:", meses_disp)
        txt_b = c_b.text_input("🔍 Buscador:")
        df_dis = df[COLUMNAS_EXCEL].copy()
        if m_sel != "Todos": df_dis = df_dis[df_dis["MES"].astype(str).str.strip().str.upper() == m_sel]
        if txt_b.strip():
            q = texto_normalizado(txt_b)
            df_dis = df_dis[df_dis.apply(lambda r: q in texto_normalizado(r["LINEAS"]) or q in texto_normalizado(r["SAP"]) or q in texto_normalizado(r["CODIGO DE INFORME"]) or q in texto_normalizado(r["GRUPO DE TUBERÍAS"]), axis=1)]
        ed_df = st.data_editor(df_dis, num_rows="dynamic", use_container_width=True, key="ed_gen")
        if st.button("💾 Guardar Cambios Generales"):
            df.update(ed_df)
            st.session_state.df_data = limpiar_estado_y_responsable(df[COLUMNAS_EXCEL])
            guardar_datos(st.session_state.df_data)
            st.success("Guardado"); st.rerun()

    # --- 📋 PENDIENTE ASIGNAR ---
    with t_pasig:
        st.markdown("#### **INFORMES PENDIENTES DE ASIGNACIÓN**")
        st.dataframe(df_pend_asignacion[COLUMNAS_EXCEL], use_container_width=True)

    # --- 🔄 EN PROCESO ---
    with t_proc:
        st.markdown("#### **INFORMES EN PROCESO DE ELABORACIÓN**")
        st.dataframe(df_en_proceso[COLUMNAS_EXCEL], use_container_width=True)
        st.divider()
        c1, c2, c3 = st.columns([2, 2, 1])
        codigos_proc = df_en_proceso["CODIGO DE INFORME"].dropna().unique()
        if len(codigos_proc) > 0:
            cod_s = c1.selectbox("Seleccionar Código:", codigos_proc, key="spc")
            resp_s = c2.selectbox("Seleccionar Inspector:", PERSONAL_LISTA, key="spr")
            if c3.button("🟢 Solicitar Completado", key="b_proc"):
                grupo_s = df_en_proceso[df_en_proceso["CODIGO DE INFORME"] == cod_s]["GRUPO DE TUBERÍAS"].values[0]
                ok, m = registrar_solicitud("INFORME COMPLETADO (GABINETE)", cod_s, grupo_s, resp_s)
                st.success(m) if ok else st.warning(m)

    # --- ⏳ PENDIENTE INSPECCIÓN ---
    with t_pinsp:
        st.markdown("#### **INFORMES CON INSPECCIÓN EN CAMPO PENDIENTE**")
        st.dataframe(df_pend_inspeccion[COLUMNAS_EXCEL], use_container_width=True)

    # --- 🔍 REV. FIABILIDAD ---
    with t_rfiab:
        st.markdown("#### **OBSERVACIONES DE FIABILIDAD**")
        st.dataframe(df_rfiab_det[COLUMNAS_EXCEL], use_container_width=True)

    # --- 💡 PEND. REV. ESPECIALISTA ---
    with t_pesp:
        st.markdown("#### **INFORMES PENDIENTES DE REVISIÓN POR ESPECIALISTA**")
        st.dataframe(df_pesp_det[COLUMNAS_EXCEL], use_container_width=True)
        st.divider()
        c1, c2, c3 = st.columns([2, 2, 1])
        codigos_pesp = df_pesp_det["CODIGO DE INFORME"].dropna().unique()
        if len(codigos_pesp) > 0:
            cod_pe = c1.selectbox("Seleccionar Código:", codigos_pesp, key="pesp_c")
            resp_pe = c2.selectbox("Seleccionar Especialista:", ESPECIALISTAS_LISTA, key="pesp_r")
            if c3.button("🟢 Enviar a Revisión", key="b_pesp"):
                grupo_sel = df_pesp_det[df_pesp_det["CODIGO DE INFORME"] == cod_pe]["GRUPO DE TUBERÍAS"].values[0]
                ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_pe, grupo_sel, resp_pe)
                st.success(m) if ok else st.warning(m)

    # --- 🔬 REV. POR ESPECIALISTA ---
    with t_resp:
        st.markdown("#### **INFORMES REVISADOS POR ESPECIALISTA**")
        st.dataframe(df_resp_det[COLUMNAS_EXCEL], use_container_width=True)
        st.divider()
        c1, c2, c3 = st.columns([2, 2, 1])
        codigos_resp = df_resp_det["CODIGO DE INFORME"].dropna().unique()
        if len(codigos_resp) > 0:
            cod_se = c1.selectbox("Seleccionar Código:", codigos_resp, key="sec")
            resp_se = c2.selectbox("Seleccionar Especialista:", ESPECIALISTAS_LISTA, key="ser")
            if c3.button("🟢 Liberar Especialista", key="b_esp"):
                grupo_sel = df_resp_det[df_resp_det["CODIGO DE INFORME"] == cod_se]["GRUPO DE TUBERÍAS"].values[0]
                ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_se, grupo_sel, resp_se)
                st.success(m) if ok else st.warning(m)

    # --- 🛠️ CORREC. PSAIM ---
    with t_psaim:
        st.markdown("#### **CORRECCIONES REQUERIDAS POR PSAIM**")
        st.dataframe(df_psaim_det[COLUMNAS_EXCEL], use_container_width=True)
        st.divider()
        c1, c2, c3 = st.columns([2, 2, 1])
        codigos_psaim = df_psaim_det["CODIGO DE INFORME"].dropna().unique()
        if len(codigos_psaim) > 0:
            cod_sp = c1.selectbox("Seleccionar Código PSAIM:", codigos_psaim, key="spc_p")
            resp_sp = c2.selectbox("Revisor PSAIM:", REVISORES_PSAIM_LISTA, key="spr_p")
            if c3.button("🟢 Marcar Corregido (PSAIM)", key="b_psaim"):
                grupo_sel = df_psaim_det[df_psaim_det["CODIGO DE INFORME"] == cod_sp]["GRUPO DE TUBERÍAS"].values[0]
                ok, m = registrar_solicitud("CORRECCIÓN PSAIM", cod_sp, grupo_sel, resp_sp)
                st.success(m) if ok else st.warning(m)

    # --- 📅 RESUMEN MES (T3) ---
    with t_t3:
        m_u = list(set(list(dict_t3_val.keys()) + list(dict_t3_pen.keys())))
        f_t3 = [{"MES": m, "GRUPOS": df_activos[df_activos["MES"].astype(str).str.strip() == m]["GRUPO DE TUBERÍAS"].nunique(), "VALORIZADOS": dict_t3_val.get(m, 0), "PENDIENTE VALORIZAR": dict_t3_pen.get(m, 0), "SUMA TOTAL": dict_t3_val.get(m, 0) + dict_t3_pen.get(m, 0), "PENDIENTE ADEMINSAC": dict_t3_ademinsac.get(m, 0), "PENDIENTE FIABILIDAD": dict_t3_fiabilidad.get(m, 0), "CORRECCION PSAIM": dict_t3_psaim.get(m, 0)} for m in m_u]
        df_t3 = pd.DataFrame(f_t3)
        if not df_t3.empty:
            df_t3["MES_CAT"] = pd.Categorical(df_t3["MES"].str.upper(), categories=ORDEN_MESES, ordered=True)
            st.dataframe(df_t3.sort_values("MES_CAT").drop(columns=["MES_CAT"]), use_container_width=True)

    # --- 📊 PEND. MES/OBS (T4) ---
    with t_t4:
        df_t4 = pd.DataFrame([{"MES": k.split("|", 1)[0], "OBSERVACIÓN PENDIENTE": k.split("|", 1)[1], "CANTIDAD": v} for k, v in dict_t4.items()])
        if not df_t4.empty:
            df_t4["MES_CAT"] = pd.Categorical(df_t4["MES"].str.upper(), categories=ORDEN_MESES, ordered=True)
            st.dataframe(df_t4.sort_values(["MES_CAT", "CANTIDAD"], ascending=[True, False]).drop(columns=["MES_CAT"]), use_container_width=True)

    # --- 📌 RESUMEN OBS (T5) ---
    with t_t5:
        df_t5 = pd.DataFrame([{"OBSERVACIÓN PENDIENTE": k, "CANTIDAD TOTAL": v, "RESPONSABLE": ("ADEMINSAC" if "ADEMINSAC" in texto_normalizado(k) else "FIABILIDAD")} for k, v in dict_t5.items()])
        if not df_t5.empty: st.dataframe(df_t5.sort_values("CANTIDAD TOTAL", ascending=False), use_container_width=True)

else:
    st.info("Haga clic en la sección superior '⚙️ Gestión de Datos' para cargar un archivo Excel o iniciar la base de datos.")
