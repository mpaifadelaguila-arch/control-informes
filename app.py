import streamlit as st
import pandas as pd
import json
import os
import io

st.set_page_config(page_title="Control de Informes de Inspección", layout="wide")

DB_FILE = "base_datos.xlsx"
SOL_FILE = "solicitudes.json"

PERSONAL_LISTA = ["INSPECTOR 1", "INSPECTOR 2", "INSPECTOR 3", "SIN ASIGNAR"]
ESPECIALISTAS_LISTA = ["ESPECIALISTA 1", "ESPECIALISTA 2"]
REVISORES_PSAIM_LISTA = ["REVISOR PSAIM 1", "REVISOR PSAIM 2"]

# --- CARGA Y GUARDADO DE DATOS ---
def cargar_base_datos():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_excel(DB_FILE)
            cols_req = ["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN", "ESTADO - VALORIZACIÓN"]
            for col in cols_req:
                if col not in df.columns:
                    df[col] = ""
                else:
                    df[col] = df[col].fillna("").astype(str)
            if "LINEAS" in df.columns:
                df["LINEAS"] = pd.to_numeric(df["LINEAS"], errors="coerce").fillna(1)
            else:
                df["LINEAS"] = 1
            return df
        except Exception as e:
            st.error(f"Error al cargar la base de datos: {e}")
            return pd.DataFrame()
    else:
        return pd.DataFrame()

def guardar_base_datos(df):
    try:
        df.to_excel(DB_FILE, index=False, engine="openpyxl")
        return True
    except Exception as e:
        st.error(f"Error al guardar la base de datos: {e}")
        return False

def cargar_solicitudes():
    if os.path.exists(SOL_FILE):
        with open(SOL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_solicitudes(sol):
    with open(SOL_FILE, "w", encoding="utf-8") as f:
        json.dump(sol, f, ensure_ascii=False, indent=4)

def registrar_solicitud(tipo, codigo, grupo, usuario):
    solicitudes = cargar_solicitudes()
    for s in solicitudes:
        if s["codigo"] == codigo and s["grupo"] == grupo and s["estado"] == "PENDIENTE":
            return False, "Ya existe una solicitud pendiente para este informe."
    
    nueva_sol = {
        "id": len(solicitudes) + 1,
        "tipo": tipo,
        "codigo": codigo,
        "grupo": grupo,
        "usuario": usuario,
        "fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "estado": "PENDIENTE"
    }
    solicitudes.append(nueva_sol)
    guardar_solicitudes(solicitudes)
    return True, "Solicitud enviada a Administración con éxito."

# --- CARGA INICIAL ---
df_data = cargar_base_datos()

if df_data.empty:
    st.warning("⚠️ No se encontraron datos en la base de datos local.")
    st.stop()

# --- FILTROS DE LÓGICA DE NEGOCIO CORREGIDOS ---
df_activos = df_data[df_data["ESTADO - VALORIZACIÓN"].str.upper() != "VALORIZADO"].copy()

# 1. Pendiente Asignar: Solo ESTADO = 'PENDIENTE ELABORACIÓN' y RESPONSABLE = 'SIN ASIGNAR' (o Vacío)
df_pend_asignacion = df_activos[
    (df_activos["ESTADO - ELABORACIÓN DE INFORME"].str.upper() == "PENDIENTE ELABORACIÓN") &
    ((df_activos["RESPONSABLE"].str.upper() == "SIN ASIGNAR") | (df_activos["RESPONSABLE"].str.strip() == ""))
]

# 2. En Proceso: ESTADO = 'EN PROCESO' o 'PENDIENTE ELABORACIÓN' (con responsable asignado)
df_en_proceso = df_activos[
    (df_activos["ESTADO - ELABORACIÓN DE INFORME"].str.upper() == "EN PROCESO") |
    ((df_activos["ESTADO - ELABORACIÓN DE INFORME"].str.upper() == "PENDIENTE ELABORACIÓN") & 
     (df_activos["RESPONSABLE"].str.upper() != "SIN ASIGNAR") & (df_activos["RESPONSABLE"].str.strip() != ""))
]

# 3. Pendiente Inspección: ESTADO = 'PENDIENTE INSPECCIÓN' o OBSERVACIÓN contenga 'PENDIENTE INSPECCIÓN'
df_pend_inspeccion = df_activos[
    (df_activos["ESTADO - ELABORACIÓN DE INFORME"].str.upper() == "PENDIENTE INSPECCIÓN") |
    (df_activos["OBSERVACIÓN"].str.upper().str.contains("PENDIENTE INSPECCI", na=False))
]

# 4. Revisión Fiabilidad: ESTADO = 'REVISIÓN FIABILIDAD' o OBSERVACIÓN contenga 'FIABILIDAD'
df_fiab_activos = df_activos[
    (df_activos["ESTADO - ELABORACIÓN DE INFORME"].str.upper() == "REVISIÓN FIABILIDAD") |
    (df_activos["OBSERVACIÓN"].str.upper().str.contains("FIABILIDAD", na=False))
]

# 5. Pendiente Revisión por Especialista
df_pesp_det = df_activos[
    df_activos["OBSERVACIÓN"].str.upper().str.contains("PENDIENTE.*ESPECIALISTA", regex=True, na=False)
]

# 6. Revisión por Especialista
df_resp_det = df_activos[
    df_activos["OBSERVACIÓN"].str.upper().str.contains("REV.*ESPECIALISTA", regex=True, na=False) &
    ~df_activos["OBSERVACIÓN"].str.upper().str.contains("PENDIENTE", na=False)
]

# 7. Corrección PSAIM: OBSERVACIÓN contenga 'PSAIM' o 'CORRECCION'
df_psaim_det = df_activos[
    df_activos["OBSERVACIÓN"].str.upper().str.contains("PSAIM", na=False)
]

# --- CÁLCULO DE KPIS ---
tot_informes = len(df_data["CODIGO DE INFORME"].unique())
tot_pendientes = len(df_activos["CODIGO DE INFORME"].unique())
tot_valorizados = len(df_data[df_data["ESTADO - VALORIZACIÓN"].str.upper() == "VALORIZADO"]["CODIGO DE INFORME"].unique())

kpi_pasig = len(df_pend_asignacion["CODIGO DE INFORME"].unique())
kpi_proc = len(df_en_proceso["CODIGO DE INFORME"].unique())
kpi_pinsp = len(df_pend_inspeccion["CODIGO DE INFORME"].unique())
kpi_rfiab = len(df_fiab_activos["CODIGO DE INFORME"].unique())
kpi_pesp = len(df_pesp_det["CODIGO DE INFORME"].unique())
kpi_resp = len(df_resp_det["CODIGO DE INFORME"].unique())
kpi_psaim = len(df_psaim_det["CODIGO DE INFORME"].unique())

# --- TITULO Y TARJETAS KPI ALINEADAS ---
st.markdown("<h2 style='text-align: center;'>CONTROL INTERNO DE INFORMES DE INSPECCIÓN</h2>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

kpi_cols = st.columns(10)

metrics = [
    ("INFORMES TOTALES", tot_informes, "#1e293b"),
    ("PENDIENTES TOTAL", tot_pendientes, "#d97706"),
    ("VALORIZADOS (SI)", tot_valorizados, "#16a34a"),
    ("PEND. ASIGNAR INFORME", kpi_pasig, "#db2777"),
    ("EN PROCESO", kpi_proc, "#7c3aed"),
    ("PEND. INSPECCIÓN", kpi_pinsp, "#dc2626"),
    ("REV. FIABILIDAD", kpi_rfiab, "#0d9488"),
    ("PEND. REV. ESPECIALISTA", kpi_pesp, "#4f46e5"),
    ("REV. POR ESPECIALISTA", kpi_resp, "#0284c7"),
    ("CORRECCIÓN PSAIM", kpi_psaim, "#ca8a04"),
]

for col, (label, val, color) in zip(kpi_cols, metrics):
    with col:
        st.markdown(f"""
            <div style="
                border: 2px solid {color};
                border-radius: 8px;
                padding: 8px 4px;
                text-align: center;
                background-color: #ffffff;
                min-height: 90px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <span style="font-size: 9px; font-weight: bold; color: #475569; text-transform: uppercase; line-height: 1.1; margin-bottom: 4px;">{label}</span>
                <span style="font-size: 20px; font-weight: 800; color: {color};">{val}</span>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- FILTRO DINÁMICO POR MES EN BARRA LATERAL PARA TABLA GENERAL ---
st.sidebar.header("🔍 Filtros Globales")
meses_disponibles = sorted([m for m in df_data["MES"].dropna().unique() if str(m).strip() != ""])
meses_seleccionados = st.sidebar.multiselect("Filtrar Tabla General por Mes:", options=meses_disponibles, default=meses_disponibles)

if meses_seleccionados:
    df_data_filtrada = df_data[df_data["MES"].isin(meses_seleccionados)]
else:
    df_data_filtrada = df_data.copy()
    # --- NAVEGACIÓN DE PESTAÑAS Y TABLAS CON BÚSQUEDA DINÁMICA E ÍNDICE DESDE 1 ---
(
    t_admin, t_gen, t_pasig, t_proc, t_pinsp, t_rfiab, 
    t_pesp, t_resp, t_psaim, t_res_m, t_p_m, t_res_o
) = st.tabs([
    "🔔 Administración", "📋 Tabla General", "📝 Pend. Asignar", "🔄 En Proceso", 
    "⏳ Pend. Inspección", "🔍 Rev. Fiabilidad", "🧑‍🔬 Pend. Rev. Especialista", 
    "🔬 Rev. por Especialista", "🛠️ Correc. PSAIM", "📅 Resumen Mes (T3)", 
    "📊 Pend. Mes/Obs (T4)", "📌 Resumen Obs (T5)"
])

# --- 1. ADMINISTRACIÓN Y GESTIÓN DE BASE DE DATOS ---
with t_admin:
    st.subheader("⚙️ Gestión de Datos: Cargar / Restaurar Excel & Descargar Respaldo")
    with st.expander("⚙️ Opciones de Importación y Exportación", expanded=True):
        c_up, c_down = st.columns([2, 1])
        with c_up:
            st.markdown("##### 📥 Cargar Base de Datos desde Excel")
            file_excel = st.file_uploader("Seleccionar archivo Excel:", type=["xlsx", "xlsm"], key="up_excel")
            if file_excel is not None:
                if st.button("🔄 Reemplazar Base de Datos"):
                    try:
                        df_new = pd.read_excel(file_excel)
                        cols_req = ["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN", "ESTADO - VALORIZACIÓN"]
                        for cr in cols_req:
                            if cr not in df_new.columns:
                                df_new[cr] = ""
                            else:
                                df_new[cr] = df_new[cr].fillna("").astype(str)
                        if "LINEAS" in df_new.columns:
                            df_new["LINEAS"] = pd.to_numeric(df_new["LINEAS"], errors="coerce").fillna(1)
                        else:
                            df_new["LINEAS"] = 1
                        if guardar_base_datos(df_new):
                            st.success("¡Base de datos actualizada con éxito!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al procesar el archivo: {e}")
        with c_down:
            st.markdown("##### 💾 Descargar Respaldo Actual")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_export = df_data.copy()
                if "CLAVE_GLOBAL" in df_export.columns:
                    df_export = df_export.drop(columns=["CLAVE_GLOBAL"])
                df_export.to_excel(writer, index=False, sheet_name="BaseDatos")
            st.download_button(
                label="💾 Descargar Copia en Excel (.xlsx)",
                data=buffer.getvalue(),
                file_name="RESPALDO_BASE_DE_DATOS.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    st.markdown("---")
    st.subheader("🔔 Solicitudes Pendientes de Modificación")
    solicitudes = cargar_solicitudes()
    pendientes = [s for s in solicitudes if s["estado"] == "PENDIENTE"]
    
    if not pendientes:
        st.info("No hay solicitudes pendientes en este momento.")
    else:
        for sol in pendientes:
            with st.container():
                c_info, c_acc1, c_acc2 = st.columns([3, 1, 1])
                c_info.markdown(f"**[{sol['tipo']}]** Código: `{sol['codigo']}` | Grupo: `{sol['grupo']}` | Solicitado por: **{sol['usuario']}** ({sol['fecha']})")
                if c_acc1.button("🟢 Aceptar", key=f"ac_{sol['id']}"):
                    df_mod = cargar_base_datos()
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
                    
                    guardar_base_datos(df_mod)
                    sol["estado"] = "APROBADO"
                    guardar_solicitudes(solicitudes)
                    st.success("Solicitud aprobada y datos actualizados.")
                    st.rerun()

                if c_acc2.button("🔴 Rechazar", key=f"rc_{sol['id']}"):
                    sol["estado"] = "RECHAZADO"
                    guardar_solicitudes(solicitudes)
                    st.warning("Solicitud rechazada.")
                    st.rerun()

# --- 2. TABLA GENERAL (Aplica filtro dinámico por mes seleccionado de la Parte 1) ---
with t_gen:
    st.subheader("📋 Tabla General de Informes")
    if not df_data_filtrada.empty:
        search_gen = st.text_input("🔍 Buscar en Tabla General (por Código, Responsable, Grupo, etc.):", key="search_gen")
        df_gen_disp = df_data_filtrada.copy()
        if "CLAVE_GLOBAL" in df_gen_disp.columns:
            df_gen_disp = df_gen_disp.drop(columns=["CLAVE_GLOBAL"])
        
        if search_gen:
            mask_gen = df_gen_disp.astype(str).apply(lambda row: row.str.contains(search_gen, case=False, regex=False)).any(axis=1)
            df_gen_disp = df_gen_disp[mask_gen]

        df_gen_disp.index = pd.RangeIndex(start=1, stop=len(df_gen_disp) + 1, step=1)
        st.dataframe(df_gen_disp, use_container_width=True)
    else:
        st.info("No hay datos disponibles para los meses seleccionados.")

# --- 3. PENDIENTES DE ASIGNAR INFORME ---
with t_pasig:
    st.subheader("📝 Pendientes de Asignar Informe")
    if not df_pend_asignacion.empty:
        search_pasig = st.text_input("🔍 Buscar Pendiente Asignar:", key="search_pasig")
        res_pasig = df_pend_asignacion.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False).agg({"LINEAS": "sum"})
        
        if search_pasig:
            mask_pasig = res_pasig.astype(str).apply(lambda row: row.str.contains(search_pasig, case=False, regex=False)).any(axis=1)
            res_pasig = res_pasig[mask_pasig]

        res_pasig.index = pd.RangeIndex(start=1, stop=len(res_pasig) + 1, step=1)
        st.dataframe(res_pasig, use_container_width=True)
    else:
        st.info("No hay registros pendientes de asignación.")

# --- 4. EN PROCESO ---
with t_proc:
    st.subheader("🔄 Informes En Proceso")
    if not df_en_proceso.empty:
        search_proc = st.text_input("🔍 Buscar En Proceso:", key="search_proc")
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
        cod_s = c1.selectbox("Seleccionar Código de Informe:", tg["CODIGO DE INFORME"].unique(), key="spc")
        resp_s = c2.selectbox("Seleccionar Inspector Responsable:", PERSONAL_LISTA, key="spr")
        if c3.button("🟢 Enviar al 100%", key="b_proc"):
            ok, m = registrar_solicitud("INFORME COMPLETADO (GABINETE)", cod_s, tg[tg["CODIGO DE INFORME"] == cod_s]["GRUPO DE TUBERÍAS"].values[0], resp_s)
            st.success(m) if ok else st.warning(m)
    else:
        st.info("No hay informes en proceso.")

# --- 5. PENDIENTE INSPECCIÓN ---
with t_pinsp:
    st.subheader("⏳ Pendientes de Inspección")
    if not df_pend_inspeccion.empty:
        search_pinsp = st.text_input("🔍 Buscar Pendiente Inspección:", key="search_pinsp")
        res_pinsp = df_pend_inspeccion.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "sum"})
        
        if search_pinsp:
            mask_pinsp = res_pinsp.astype(str).apply(lambda row: row.str.contains(search_pinsp, case=False, regex=False)).any(axis=1)
            res_pinsp = res_pinsp[mask_pinsp]

        res_pinsp.index = pd.RangeIndex(start=1, stop=len(res_pinsp) + 1, step=1)
        st.dataframe(res_pinsp, use_container_width=True)
    else:
        st.info("No hay registros pendientes de inspección.")

# --- 6. REVISIÓN FIABILIDAD ---
with t_rfiab:
    st.subheader("🔍 Revisión Fiabilidad")
    if not df_fiab_activos.empty:
        search_rfiab = st.text_input("🔍 Buscar en Revisión Fiabilidad:", key="search_rfiab")
        res_fiab = df_fiab_activos.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "sum"})
        
        if search_rfiab:
            mask_rfiab = res_fiab.astype(str).apply(lambda row: row.str.contains(search_rfiab, case=False, regex=False)).any(axis=1)
            res_fiab = res_fiab[mask_rfiab]

        res_fiab.index = pd.RangeIndex(start=1, stop=len(res_fiab) + 1, step=1)
        st.dataframe(res_fiab, use_container_width=True)
    else:
        st.info("No hay registros en revisión por Fiabilidad.")

# --- 7. PENDIENTE REVISIÓN ESPECIALISTA ---
with t_pesp:
    st.subheader("🧑‍🔬 Pendiente Revisión por Especialista")
    if not df_pesp_det.empty:
        search_pesp = st.text_input("🔍 Buscar Pendiente Especialista:", key="search_pesp")
        tg_e = df_pesp_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "sum"})
        
        tg_e_disp = tg_e.copy()
        if search_pesp:
            mask_pesp = tg_e_disp.astype(str).apply(lambda row: row.str.contains(search_pesp, case=False, regex=False)).any(axis=1)
            tg_e_disp = tg_e_disp[mask_pesp]

        tg_e_disp.index = pd.RangeIndex(start=1, stop=len(tg_e_disp) + 1, step=1)
        st.dataframe(tg_e_disp, use_container_width=True)
        
        st.markdown("---")
        st.markdown("##### 📌 Control de Envío a Revisión de Especialista")
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_pe = c1.selectbox("Seleccionar Código de Informe:", tg_e["CODIGO DE INFORME"].unique(), key="pesp_c")
        resp_pe = c2.selectbox("Seleccionar Especialista Asignado:", ESPECIALISTAS_LISTA, key="pesp_r")
        if c3.button("🟢 Enviar a Revisión", key="b_pesp"):
            grupo_sel = tg_e[tg_e["CODIGO DE INFORME"] == cod_pe]["GRUPO DE TUBERÍAS"].values[0]
            ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_pe, grupo_sel, resp_pe)
            st.success(m) if ok else st.warning(m)
    else:
        st.info("No hay informes pendientes de revisión por Especialista.")

# --- 8. REVISIÓN POR ESPECIALISTA ---
with t_resp:
    st.subheader("🔬 Revisión por Especialista")
    if not df_resp_det.empty:
        search_resp = st.text_input("🔍 Buscar en Rev. Especialista:", key="search_resp")
        tg_re = df_resp_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "sum"})
        
        tg_re_disp = tg_re.copy()
        if search_resp:
            mask_resp = tg_re_disp.astype(str).apply(lambda row: row.str.contains(search_resp, case=False, regex=False)).any(axis=1)
            tg_re_disp = tg_re_disp[mask_resp]

        tg_re_disp.index = pd.RangeIndex(start=1, stop=len(tg_re_disp) + 1, step=1)
        st.dataframe(tg_re_disp, use_container_width=True)
        
        st.markdown("---")
        st.markdown("##### 📌 Control de Liberación de Especialista")
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_se = c1.selectbox("Seleccionar Código de Informe:", tg_re["CODIGO DE INFORME"].unique(), key="sec")
        resp_se = c2.selectbox("Seleccionar Especialista:", ESPECIALISTAS_LISTA, key="ser")
        if c3.button("🟢 Liberar Especialista", key="b_esp"):
            ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_se, tg_re[tg_re["CODIGO DE INFORME"] == cod_se]["GRUPO DE TUBERÍAS"].values[0], resp_se)
            st.success(m) if ok else st.warning(m)
    else:
        st.info("No hay informes en revisión por Especialista.")

# --- 9. CORRECCIÓN PSAIM ---
with t_psaim:
    st.subheader("🛠️ Corrección PSAIM")
    if not df_psaim_det.empty:
        search_psaim = st.text_input("🔍 Buscar en Corrección PSAIM:", key="search_psaim")
        tg_p = df_psaim_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "sum"})
        
        tg_p_disp = tg_p.copy()
        if search_psaim:
            mask_psaim = tg_p_disp.astype(str).apply(lambda row: row.str.contains(search_psaim, case=False, regex=False)).any(axis=1)
            tg_p_disp = tg_p_disp[mask_psaim]

        tg_p_disp.index = pd.RangeIndex(start=1, stop=len(tg_p_disp) + 1, step=1)
        st.dataframe(tg_p_disp, use_container_width=True)
        
        st.markdown("---")
        st.markdown("##### 📌 Control de Conformidad PSAIM")
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_sp = c1.selectbox("Seleccionar Código de Informe:", tg_p["CODIGO DE INFORME"].unique(), key="spc_p")
        resp_sp = c2.selectbox("Seleccionar Revisor PSAIM:", REVISORES_PSAIM_LISTA, key="spr_p")
        if c3.button("🟢 PSAIM Corregido", key="b_psaim"):
            ok, m = registrar_solicitud("CORRECCIÓN PSAIM", cod_sp, tg_p[tg_p["CODIGO DE INFORME"] == cod_sp]["GRUPO DE TUBERÍAS"].values[0], resp_sp)
            st.success(m) if ok else st.warning(m)
    else:
        st.info("No hay informes pendientes por Corrección PSAIM.")

# --- 10. TABLAS DE RESUMEN (T3, T4, T5) ---
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
