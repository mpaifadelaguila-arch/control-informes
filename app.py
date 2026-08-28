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
        --accent-gold: #D4AF37;
        --bg-card: #FFFFFF;
        --border-color: #E2E8F0;
        --texto-principal: #1E293B;
        --texto-sub: #64748B;
    }
    
    .stApp { background-color: #F8FAFC; }
    
    .kpi-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border-top: 4px solid var(--primary-navy);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .kpi-title {
        color: var(--texto-sub);
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 6px;
    }
    .kpi-value {
        color: var(--primary-navy);
        font-size: 1.8rem;
        font-weight: 800;
        line-height: 1.2;
    }
    .kpi-total { border-top-color: #0E2A47; }
    .kpi-pend { border-top-color: #F59E0B; }
    .kpi-val { border-top-color: #10B981; }
    .kpi-asig { border-top-color: #EC4899; }
    .kpi-proc { border-top-color: #8B5CF6; }
    .kpi-insp { border-top-color: #EF4444; }
    .kpi-fiab { border-top-color: #14B8A6; }
    .kpi-pesp { border-top-color: #6366F1; }
    .kpi-resp { border-top-color: #06B6D4; }
    .kpi-psaim { border-top-color: #EAB308; }
    </style>
    """,
    unsafe_allow_html=True
)

DB_PATH = "base_de_datos_informes.json"
SOLICITUDES_PATH = "database_solicitudes.json"

PERSONAL_LISTA = ["Dante", "Ingrid", "Jesús Maguiña", "Juan José", "Julio Ponce", "Omar", "Raúl A", "Timana", "Christopher"]
ESPECIALISTAS_LISTA = ["Luis Espinoza", "Marco Garcia"]
REVISORES_PSAIM_LISTA = ["Bryan Solis", "Maricielo"]

def texto_normalizado(texto):
    if not isinstance(texto, str):
        return ""
    import unicodedata
    s = unicodedata.normalize("NFD", texto)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.upper().strip()

def cargar_base_datos():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                df = pd.DataFrame(data)
                if not df.empty:
                    cols_str = ["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN", "ESTADO - VALORIZACIÓN"]
                    for col in cols_str:
                        if col in df.columns:
                            df[col] = df[col].fillna("").astype(str)
                    if "LINEAS" in df.columns:
                        df["LINEAS"] = pd.to_numeric(df["LINEAS"], errors="coerce").fillna(1)
                    else:
                        df["LINEAS"] = 1
                    df["CLAVE_GLOBAL"] = df["CODIGO DE INFORME"].str.strip() + "_" + df["GRUPO DE TUBERÍAS"].str.strip()
                    return df
        except Exception:
            pass
    return pd.DataFrame()

def guardar_base_datos(df):
    try:
        df_save = df.copy()
        if "CLAVE_GLOBAL" in df_save.columns:
            df_save = df_save.drop(columns=["CLAVE_GLOBAL"])
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(df_save.to_dict(orient="records"), f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def cargar_solicitudes():
    if os.path.exists(SOLICITUDES_PATH):
        try:
            with open(SOLICITUDES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def guardar_solicitudes(solicitudes):
    try:
        with open(SOLICITUDES_PATH, "w", encoding="utf-8") as f:
            json.dump(solicitudes, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def registrar_solicitud(tipo, codigo, grupo, usuario):
    solicitudes = cargar_solicitudes()
    clave = f"{codigo.strip()}_{grupo.strip()}"
    for s in solicitudes:
        if s["clave"] == clave and s["estado"] == "PENDIENTE":
            return False, "Ya existe una solicitud pendiente para este grupo/código."
    nueva = {
        "id": len(solicitudes) + 1,
        "tipo": tipo,
        "codigo": codigo,
        "grupo": grupo,
        "clave": clave,
        "usuario": usuario,
        "estado": "PENDIENTE",
        "fecha": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    solicitudes.append(nueva)
    if guardar_solicitudes(solicitudes):
        return True, "Solicitud enviada a la bandeja de Administración."
    return False, "Error al guardar la solicitud."

df_data = cargar_base_datos()

if df_data.empty:
    st.warning("⚠️ No se encontraron datos en la base de datos local. Utiliza la pestaña '🔔 Administración' para cargar un archivo Excel.")
    
    cnt_totales = cnt_valorizados = cnt_pendientes_total = 0
    cnt_pend_asignacion = cnt_en_proceso = cnt_pend_inspeccion = 0
    cnt_revision_fiabilidad = cnt_pend_rev_especialista = 0
    cnt_rev_por_especialista = cnt_correccion_psaim = 0
    
    cols_base = ["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN", "ESTADO - VALORIZACIÓN", "LINEAS", "CLAVE_GLOBAL"]
    df_activos = pd.DataFrame(columns=cols_base)
    df_pend_asignacion = df_en_proceso = df_pend_inspeccion = pd.DataFrame(columns=cols_base)
    df_fiab_activos = df_pesp_det = df_resp_det = df_psaim_det = pd.DataFrame(columns=cols_base)
else:
    cond_anulado = df_data["ESTADO - ELABORACIÓN DE INFORME"].apply(lambda x: "ANULADO" in texto_normalizado(x))
    cond_desestimado = df_data["OBSERVACIÓN"].apply(lambda x: "DESESTIMADO" in texto_normalizado(x))
    cond_no_corresponde = df_data["ESTADO - ELABORACIÓN DE INFORME"].apply(lambda x: "NO CORRESPONDE" in texto_normalizado(x))

    df_activos = df_data[~(cond_anulado | cond_desestimado | cond_no_corresponde)].copy()

    cnt_totales = df_activos["CLAVE_GLOBAL"].nunique()

    df_val = df_activos[df_activos["ESTADO - VALORIZACIÓN"].apply(lambda x: texto_normalizado(x) == "SI")]
    cnt_valorizados = df_val["CLAVE_GLOBAL"].nunique()

    cnt_pendientes_total = cnt_totales - cnt_valorizados

    df_pend_asignacion = df_activos[df_activos["RESPONSABLE"].apply(lambda x: texto_normalizado(x) in ["", "PENDIENTE", "SIN ASIGNAR", "POR ASIGNAR"])]
    cnt_pend_asignacion = df_pend_asignacion["CLAVE_GLOBAL"].nunique()

    df_en_proceso = df_activos[df_activos["ESTADO - ELABORACIÓN DE INFORME"].apply(lambda x: texto_normalizado(x) in ["EN PROCESO", "ELABORACION", "EN ELABORACION"])]
    cnt_en_proceso = df_en_proceso["CLAVE_GLOBAL"].nunique()

    df_pend_inspeccion = df_activos[df_activos["ESTADO - ELABORACIÓN DE INFORME"].apply(lambda x: "PENDIENTE INSPECCION" in texto_normalizado(x))]
    cnt_pend_inspeccion = df_pend_inspeccion["CLAVE_GLOBAL"].nunique()

    df_fiab_activos = df_activos[df_activos["OBSERVACIÓN"].apply(lambda x: "ENTREGADO PARA SU REVISION" in texto_normalizado(x) and "FIABILIDAD" in texto_normalizado(x))]
    cnt_revision_fiabilidad = df_fiab_activos["CLAVE_GLOBAL"].nunique()

    df_pesp_det = df_activos[df_activos["OBSERVACIÓN"].apply(lambda x: "PENDIENTE REVISION POR EL ESPECIALISTA" in texto_normalizado(x))]
    cnt_pend_rev_especialista = df_pesp_det["CLAVE_GLOBAL"].nunique()

    df_resp_det = df_activos[df_activos["OBSERVACIÓN"].apply(lambda x: ("REV. POR EL ESPECIALISTA" in texto_normalizado(x) or "REVISION POR EL ESPECIALISTA" in texto_normalizado(x)) and "PENDIENTE" not in texto_normalizado(x))]
    cnt_rev_por_especialista = df_resp_det["CLAVE_GLOBAL"].nunique()

    df_psaim_det = df_activos[df_activos["OBSERVACIÓN"].apply(lambda x: "CORRECCION PSAIM" in texto_normalizado(x))]
    cnt_correccion_psaim = df_psaim_det["CLAVE_GLOBAL"].nunique()

# --- HEADER Y KPIS ---
st.markdown("<h2 style='text-align: center; color: #0E2A47;'>CONTROL INTERNO DE INFORMES DE INSPECCIÓN</h2>", unsafe_allow_html=True)

col_k1, col_k2, col_k3, col_k4, col_k5, col_k6, col_k7, col_k8, col_k9, col_k10 = st.columns(10)

with col_k1:
    st.markdown(f'<div class="kpi-card kpi-total"><div class="kpi-title">INFORMES TOTALES</div><div class="kpi-value">{cnt_totales}</div></div>', unsafe_allow_html=True)
with col_k2:
    st.markdown(f'<div class="kpi-card kpi-pend"><div class="kpi-title">PENDIENTES TOTAL</div><div class="kpi-value">{cnt_pendientes_total}</div></div>', unsafe_allow_html=True)
with col_k3:
    st.markdown(f'<div class="kpi-card kpi-val"><div class="kpi-title">VALORIZADOS (SI)</div><div class="kpi-value">{cnt_valorizados}</div></div>', unsafe_allow_html=True)
with col_k4:
    st.markdown(f'<div class="kpi-card kpi-asig"><div class="kpi-title">PEND. ASIGNAR INFORME</div><div class="kpi-value">{cnt_pend_asignacion}</div></div>', unsafe_allow_html=True)
with col_k5:
    st.markdown(f'<div class="kpi-card kpi-proc"><div class="kpi-title">EN PROCESO</div><div class="kpi-value">{cnt_en_proceso}</div></div>', unsafe_allow_html=True)
with col_k6:
    st.markdown(f'<div class="kpi-card kpi-insp"><div class="kpi-title">PEND. INSPECCIÓN</div><div class="kpi-value">{cnt_pend_inspeccion}</div></div>', unsafe_allow_html=True)
with col_k7:
    st.markdown(f'<div class="kpi-card kpi-fiab"><div class="kpi-title">REV. FIABILIDAD</div><div class="kpi-value">{cnt_revision_fiabilidad}</div></div>', unsafe_allow_html=True)
with col_k8:
    st.markdown(f'<div class="kpi-card kpi-pesp"><div class="kpi-title">PEND. REV. ESPECIALISTA</div><div class="kpi-value">{cnt_pend_rev_especialista}</div></div>', unsafe_allow_html=True)
with col_k9:
    st.markdown(f'<div class="kpi-card kpi-resp"><div class="kpi-title">REV. POR ESPECIALISTA</div><div class="kpi-value">{cnt_rev_por_especialista}</div></div>', unsafe_allow_html=True)
with col_k10:
    st.markdown(f'<div class="kpi-card kpi-psaim"><div class="kpi-title">CORRECCIÓN PSAIM</div><div class="kpi-value">{cnt_correccion_psaim}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
# --- NAVEGACIÓN DE PESTAÑAS Y TABLAS CON ÍNDICE DESDE 1 ---
(
    t_admin, t_gen, t_pasig, t_proc, t_pinsp, t_rfiab, 
    t_pesp, t_resp, t_psaim, t_res_m, t_p_m, t_res_o
) = st.tabs([
    "🔔 Administración", "📋 Tabla General", "📝 Pend. Asignar", "🔄 En Proceso", 
    "⏳ Pend. Inspección", "🔍 Rev. Fiabilidad", "🧑‍🔬 Pend. Rev. Especialista", 
    "🔬 Rev. por Especialista", "🛠️ Correc. PSAIM", "📅 Resumen Mes (T3)", 
    "📊 Pend. Mes/Obs (T4)", "📌 Resumen Obs (T5)"
])

with t_admin:
    st.subheader("⚙️ Gestión de Datos: Cargar / Restaurar Excel & Descargar Respaldo")
    with st.expander("⚙️ Gestión de Datos: Cargar / Restaurar Excel & Descargar Respaldo", expanded=True):
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
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
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

with t_gen:
    st.subheader("📋 Tabla General de Informes")
    if not df_data.empty:
        df_gen_disp = df_data.copy()
        if "CLAVE_GLOBAL" in df_gen_disp.columns:
            df_gen_disp = df_gen_disp.drop(columns=["CLAVE_GLOBAL"])
        df_gen_disp.index = pd.RangeIndex(start=1, stop=len(df_gen_disp) + 1, step=1)
        st.dataframe(df_gen_disp, use_container_width=True)

with t_pasig:
    if not df_pend_asignacion.empty:
        res_pasig = df_pend_asignacion.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False).agg({"LINEAS": "count"})
        res_pasig.index = pd.RangeIndex(start=1, stop=len(res_pasig) + 1, step=1)
        st.dataframe(res_pasig, use_container_width=True)

with t_proc:
    if not df_en_proceso.empty:
        tg = df_en_proceso.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False).agg({"LINEAS": "count"})
        tg_disp = tg.copy()
        tg_disp.index = pd.RangeIndex(start=1, stop=len(tg_disp) + 1, step=1)
        st.dataframe(tg_disp, use_container_width=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_s = c1.selectbox("Código:", tg["CODIGO DE INFORME"].unique(), key="spc")
        resp_s = c2.selectbox("Inspector:", PERSONAL_LISTA, key="spr")
        if c3.button("🟢 Enviar al 100%", key="b_proc"):
            ok, m = registrar_solicitud("INFORME COMPLETADO (GABINETE)", cod_s, tg[tg["CODIGO DE INFORME"] == cod_s]["GRUPO DE TUBERÍAS"].values[0], resp_s)
            st.success(m) if ok else st.warning(m)

with t_pinsp:
    if not df_pend_inspeccion.empty:
        res_pinsp = df_pend_inspeccion.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False).agg({"LINEAS": "count"})
        res_pinsp.index = pd.RangeIndex(start=1, stop=len(res_pinsp) + 1, step=1)
        st.dataframe(res_pinsp, use_container_width=True)

with t_rfiab:
    if not df_fiab_activos.empty:
        res_fiab = df_fiab_activos.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "count"})
        res_fiab.index = pd.RangeIndex(start=1, stop=len(res_fiab) + 1, step=1)
        st.dataframe(res_fiab, use_container_width=True)

with t_pesp:
    if not df_pesp_det.empty:
        tg_e = df_pesp_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "count"})
        tg_e_disp = tg_e.copy()
        tg_e_disp.index = pd.RangeIndex(start=1, stop=len(tg_e_disp) + 1, step=1)
        st.dataframe(tg_e_disp, use_container_width=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_pe = c1.selectbox("Código:", tg_e["CODIGO DE INFORME"].unique(), key="pesp_c")
        resp_pe = c2.selectbox("Especialista:", ESPECIALISTAS_LISTA, key="pesp_r")
        if c3.button("🟢 Enviar a Revisión", key="b_pesp"):
            grupo_sel = tg_e[tg_e["CODIGO DE INFORME"] == cod_pe]["GRUPO DE TUBERÍAS"].values[0]
            ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_pe, grupo_sel, resp_pe)
            st.success(m) if ok else st.warning(m)

with t_resp:
    if not df_resp_det.empty:
        tg_re = df_resp_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "count"})
        tg_re_disp = tg_re.copy()
        tg_re_disp.index = pd.RangeIndex(start=1, stop=len(tg_re_disp) + 1, step=1)
        st.dataframe(tg_re_disp, use_container_width=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_se = c1.selectbox("Código:", tg_re["CODIGO DE INFORME"].unique(), key="sec")
        resp_se = c2.selectbox("Especialista:", ESPECIALISTAS_LISTA, key="ser")
        if c3.button("🟢 Liberar Especialista", key="b_esp"):
            ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_se, tg_re[tg_re["CODIGO DE INFORME"] == cod_se]["GRUPO DE TUBERÍAS"].values[0], resp_se)
            st.success(m) if ok else st.warning(m)

with t_psaim:
    if not df_psaim_det.empty:
        tg_p = df_psaim_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "count"})
        tg_p_disp = tg_p.copy()
        tg_p_disp.index = pd.RangeIndex(start=1, stop=len(tg_p_disp) + 1, step=1)
        st.dataframe(tg_p_disp, use_container_width=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_sp = c1.selectbox("Código:", tg_p["CODIGO DE INFORME"].unique(), key="spc_p")
        resp_sp = c2.selectbox("Revisor PSAIM:", REVISORES_PSAIM_LISTA, key="spr_p")
        if c3.button("🟢 PSAIM Corregido", key="b_psaim"):
            ok, m = registrar_solicitud("CORRECCIÓN PSAIM", cod_sp, tg_p[tg_p["CODIGO DE INFORME"] == cod_sp]["GRUPO DE TUBERÍAS"].values[0], resp_sp)
            st.success(m) if ok else st.warning(m)

with t_res_m:
    st.subheader("📅 Resumen Mes (T3)")
    if not df_activos.empty:
        piv_m = pd.pivot_table(df_activos, index="MES", columns="ESTADO - ELABORACIÓN DE INFORME", values="LINEAS", aggfunc="count", fill_value=0)
        piv_m.index = pd.RangeIndex(start=1, stop=len(piv_m) + 1, step=1)
        st.dataframe(piv_m, use_container_width=True)

with t_p_m:
    st.subheader("📊 Pend. Mes/Obs (T4)")
    if not df_activos.empty:
        piv_po = pd.pivot_table(df_activos, index="MES", columns="OBSERVACIÓN", values="LINEAS", aggfunc="count", fill_value=0)
        piv_po.index = pd.RangeIndex(start=1, stop=len(piv_po) + 1, step=1)
        st.dataframe(piv_po, use_container_width=True)

with t_res_o:
    st.subheader("📌 Resumen Obs (T5)")
    if not df_activos.empty:
        piv_o = pd.pivot_table(df_activos, index="OBSERVACIÓN", columns="ESTADO - ELABORACIÓN DE INFORME", values="LINEAS", aggfunc="count", fill_value=0)
        piv_o.index = pd.RangeIndex(start=1, stop=len(piv_o) + 1, step=1)
        st.dataframe(piv_o, use_container_width=True)
