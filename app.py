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

DB_FILE = "database_informes.json"

COLUMNAS_EXCEL = [
    "ITEM POR MES",
    "IT2",
    "UNIDAD",
    "MES",
    "LINEAS",
    "CODIGO DE INFORME",
    "GRUPO DE TUBERÍAS",
    "SAP",
    "ALCANCE DEL SERVICIO",
    "ESTADO - ELABORACIÓN DE INFORME",
    "RESPONSABLE",
    "OBSERVACIÓN",
    "ESTADO - VALORIZACIÓN",
]

ORDEN_MESES = [
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SETIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
]

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📋 Tabla General"

# --- INYECCIÓN DE ESTILOS CSS CON COLORES VISIBLES Y RESALTADO ACTIVO ---
st.markdown(
    """
    <style>
    footer {visibility: hidden;}
    .stAppDeployButton {display:none !important;}
    header {visibility: hidden !important;}
    
    .stApp {
        background-color: #F1F5F9;
    }

    div[data-testid="column"] {
        padding: 0px 2px !important;
    }

    .header-banner {
        background: linear-gradient(135deg, #0E2A47 0%, #1A3E68 100%);
        padding: 18px 25px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(14, 42, 71, 0.15);
        border-left: 6px solid #D4AF37;
    }
    .header-title {
        font-size: 22px;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin: 0;
        color: #FFFFFF;
    }
    .header-subtitle {
        font-size: 13px;
        color: #CBD5E1;
        margin-top: 4px;
        font-weight: 400;
    }

    /* ESTILO GENERAL DE LOS BOTONES KPI */
    div[data-testid="column"] div.stButton > button {
        width: 100% !important;
        height: 80px !important;
        min-height: 80px !important;
        max-height: 80px !important;
        border-radius: 8px !important;
        padding: 6px 2px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08) !important;
        transition: all 0.2s ease-in-out !important;
        white-space: pre-wrap !important;
        font-weight: 700 !important;
        font-size: 11px !important;
    }

    /* COLORES INACTIVOS INDIVIDUALES */
    div.st-key-nav_TABLA_GENERAL > button { background-color: #E2E8F0 !important; color: #1E293B !important; border: 1px solid #CBD5E1 !important; }
    div.st-key-nav_PEND_TOTALES > button { background-color: #FEF3C7 !important; color: #92400E !important; border: 1px solid #FCD34D !important; }
    div.st-key-nav_PEND_ASIGNAR > button { background-color: #FCE7F3 !important; color: #9D174D !important; border: 1px solid #FBCFE8 !important; }
    div.st-key-nav_EN_PROCESO > button { background-color: #EDE9FE !important; color: #5B21B6 !important; border: 1px solid #DDD6FE !important; }
    div.st-key-nav_PEND_INSPECCION > button { background-color: #FEE2E2 !important; color: #991B1B !important; border: 1px solid #FCA5A5 !important; }
    div.st-key-nav_REV_FIABILIDAD > button { background-color: #CCFBF1 !important; color: #115E59 !important; border: 1px solid #99F6E4 !important; }
    div.st-key-nav_PEND_REV_ESP > button { background-color: #E0E7FF !important; color: #3730A3 !important; border: 1px solid #C7D2FE !important; }
    div.st-key-nav_REV_POR_ESP > button { background-color: #CFFAFE !important; color: #155E75 !important; border: 1px solid #A5F3FC !important; }
    div.st-key-nav_CORREC_PSAIM > button { background-color: #FEF9C3 !important; color: #854D0E !important; border: 1px solid #FDE047 !important; }
    div.st-key-nav_VALORIZADOS > button { background-color: #D1FAE5 !important; color: #065F46 !important; border: 1px solid #A7F3D0 !important; }
    div.st-key-nav_RESUMEN_OBS > button { background-color: #E2E8F0 !important; color: #334155 !important; border: 1px solid #CBD5E1 !important; }

    /* HOVER EFFECT */
    div[data-testid="column"] div.stButton > button:hover {
        transform: translateY(-2px) !important;
        filter: brightness(0.95) !important;
    }

    /* ESTILO PARA EL BOTÓN SELECCIONADO (ACTIVO) */
    .kpi-active > button {
        background-color: #0E2A47 !important;
        color: #FFFFFF !important;
        border: 2px solid #D4AF37 !important;
        box-shadow: 0 4px 10px rgba(14, 42, 71, 0.5) !important;
        transform: scale(1.03) !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)


def texto_normalizado(texto):
    if pd.isna(texto):
        return ""
    t = str(texto).strip().upper()
    replacements = {
        "Á": "A",
        "É": "E",
        "Í": "I",
        "Ó": "O",
        "Ú": "U",
        "Ü": "U",
        "Ñ": "N",
    }
    for orig, repl in replacements.items():
        t = t.replace(orig, repl)
    return t


def limpiar_estado_y_responsable(df_input):
    df_clean = df_input.copy()
    for idx, row in df_clean.iterrows():
        val_estado = str(row["ESTADO - ELABORACIÓN DE INFORME"]).strip()
        val_resp = str(row["RESPONSABLE"]).strip()

        if "-" in val_estado:
            partes = val_estado.split("-", 1)
            estado_puro = partes[0].strip()
            persona = partes[1].strip()

            df_clean.at[idx, "ESTADO - ELABORACIÓN DE INFORME"] = estado_puro
            if val_resp in ["", "nan", "None"]:
                df_clean.at[idx, "RESPONSABLE"] = persona
    return df_clean


def es_codigo_provisional(codigo):
    t = texto_normalizado(codigo)
    if t in ["", "-"]:
        return True
    if any(
        p in t
        for p in ["PENDIENTE ASIGNAR", "PENDIENTE DE ASIGNAR", "POR ASIGNAR"]
    ):
        return True
    return False


def es_correccion_psaim(observacion):
    t = texto_normalizado(observacion)
    return "PSAIM" in t and any(
        word in t for word in ["CORRECCION", "CORREGIR", "CORREGIDO", "CORREGIDA"]
    )


def es_pendiente_inspeccion_fn(row):
    estado = texto_normalizado(row.get("ESTADO - ELABORACIÓN DE INFORME", ""))
    alcance = texto_normalizado(row.get("ALCANCE DEL SERVICIO", ""))
    obs = texto_normalizado(row.get("OBSERVACIÓN", ""))

    if (
        "PENDIENTE COMPLETAR INSPECCION" in estado
        or "PENDIENTE INSPECCION" in estado
    ):
        return True
    if "PENDIENTE INSPECCION" in alcance or "FALTA CARPETA" in alcance:
        return True
    if "COMPLETAR INSPECCION" in obs or "COMPLETAR INSPECCIÓN" in obs:
        return True

    return False


def cargar_datos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            df = pd.DataFrame(data)
            for col in COLUMNAS_EXCEL:
                if col not in df.columns:
                    df[col] = ""
            df = limpiar_estado_y_responsable(df)
            return df[COLUMNAS_EXCEL]
    else:
        df = pd.DataFrame(columns=COLUMNAS_EXCEL)
        guardar_datos(df)
        return df


def guardar_datos(df):
    df.to_json(DB_FILE, orient="records", force_ascii=False, indent=4)


if "df_data" not in st.session_state:
    st.session_state.df_data = cargar_datos()

df = st.session_state.df_data

st.markdown(
    """
    <div class="header-banner">
        <div class="header-title">CONTROL INTERNO DE INFORMES - ADEMINSAC</div>
        <div class="header-subtitle">Sistema de Monitoreo de Inspección Técnicas y Valorización | Refinería La Pampilla</div>
    </div>
""",
    unsafe_allow_html=True,
)

if not df.empty:
    df_activos = df[
        df["OBSERVACIÓN"].apply(texto_normalizado) != "RETIRADO"
    ].copy()

    def generar_clave(row):
        mes = str(row["MES"]).strip()
        cod = str(row["CODIGO DE INFORME"]).strip()
        grupo = str(row["GRUPO DE TUBERÍAS"]).strip()
        if es_codigo_provisional(cod):
            return f"{mes}|SIN-CODIGO-GRUPO|{texto_normalizado(grupo)}"
        return f"{mes}|{cod}"

    df_activos["CLAVE_GLOBAL"] = df_activos.apply(generar_clave, axis=1)

    mask_psaim = df_activos["OBSERVACIÓN"].apply(es_correccion_psaim)
    mask_pend_insp = df_activos.apply(es_pendiente_inspeccion_fn, axis=1)
    mask_pend_elab = df_activos[
        "ESTADO - ELABORACIÓN DE INFORME"
    ].apply(texto_normalizado).str.contains("PENDIENTE ELABORACION")

    df_psaim_det = df_activos[mask_psaim]
    df_pend_inspeccion = df_activos[mask_pend_insp]
    df_pend_asignacion = df_activos[mask_pend_elab]
    df_en_proceso = df_activos[
        df_activos["ESTADO - ELABORACIÓN DE INFORME"]
        .apply(texto_normalizado)
        .str.contains("EN PROCESO")
        & ~mask_pend_insp
    ]

    cnt_en_proceso = df_en_proceso["CLAVE_GLOBAL"].nunique()
    cnt_pend_inspeccion = df_pend_inspeccion["CLAVE_GLOBAL"].nunique()
    cnt_pend_asignacion = df_pend_asignacion["CLAVE_GLOBAL"].nunique()

    dict_unicos = {}
    dict_psaim_unicos = set()
    dict_t3_val, dict_t3_pen = {}, {}
    dict_t3_ademinsac, dict_t3_fiabilidad = {}, {}
    dict_t5 = {}

    cnt_revision_fiabilidad = 0
    cnt_pend_revision_especialista = 0
    cnt_revision_por_especialista = 0

    for _, row in df_activos.iterrows():
        mes = str(row["MES"]).strip()
        cod = str(row["CODIGO DE INFORME"]).strip()
        grupo = str(row["GRUPO DE TUBERÍAS"]).strip()
        obs = (
            str(row["OBSERVACIÓN"]).strip()
            if pd.notna(row["OBSERVACIÓN"])
            else ""
        )
        estado_val = texto_normalizado(row["ESTADO - VALORIZACIÓN"])
        clave_global = row["CLAVE_GLOBAL"]

        if mes != "" and grupo != "":
            if not es_codigo_provisional(cod) and es_correccion_psaim(obs):
                clave_psaim = f"{mes}|{cod}"
                if clave_psaim not in dict_psaim_unicos:
                    dict_psaim_unicos.add(clave_psaim)

            if clave_global not in dict_unicos:
                dict_unicos[clave_global] = True
                dict_t3_val.setdefault(mes, 0)
                dict_t3_pen.setdefault(mes, 0)
                obs_norm = texto_normalizado(obs)

                if estado_val == "SI":
                    dict_t3_val[mes] += 1
                else:
                    dict_t3_pen[mes] += 1
                    if "FIABILIDAD" in obs_norm and "ENTREGADO PARA SU REVISION" in obs_norm:
                        cnt_revision_fiabilidad += 1
                    if "PENDIENTE REVISION POR EL ESPECIALISTA" in obs_norm:
                        cnt_pend_revision_especialista += 1
                    if ("REV. POR EL ESPECIALISTA" in obs_norm or "REVISION POR EL ESPECIALISTA" in obs_norm) and "PENDIENTE" not in obs_norm:
                        cnt_revision_por_especialista += 1

                    obs_key = "(En blanco)" if obs == "" else obs
                    dict_t5[obs_key] = dict_t5.get(obs_key, 0) + 1

    tot_informes = len(dict_unicos)
    tot_val = sum(dict_t3_val.values())
    tot_pen = sum(dict_t3_pen.values())

    cols = st.columns(11)

    kpis = [
        (cols[0], "📋 TABLA GENERAL", tot_informes, "nav_TABLA_GENERAL", "📋 Tabla General"),
        (cols[1], "📊 PEND. TOTALES", tot_pen, "nav_PEND_TOTALES", "📋 Tabla General"),
        (cols[2], "📋 PEND. ASIGNAR", cnt_pend_asignacion, "nav_PEND_ASIGNAR", "📋 Pend. Asignar Informe"),
        (cols[3], "🔄 EN PROCESO", cnt_en_proceso, "nav_EN_PROCESO", "🔄 En Proceso"),
        (cols[4], "⏳ PEND. INSPECCIÓN", cnt_pend_inspeccion, "nav_PEND_INSPECCION", "⏳ Pend. Inspección"),
        (cols[5], "🔍 REV. FIABILIDAD", cnt_revision_fiabilidad, "nav_REV_FIABILIDAD", "🔍 Rev. Fiabilidad"),
        (cols[6], "👨‍🔬 PEND. REV. ESP.", cnt_pend_revision_especialista, "nav_PEND_REV_ESP", "👨‍🔬 Pend. Rev. Especialista"),
        (cols[7], "🔬 REV. POR ESP.", cnt_revision_por_especialista, "nav_REV_POR_ESP", "🔬 Rev. por Especialista"),
        (cols[8], "🛠️ CORREC. PSAIM", len(dict_psaim_unicos), "nav_CORREC_PSAIM", "🛠️ Correc. PSAIM"),
        (cols[9], "📅 VALORIZADOS", tot_val, "nav_VALORIZADOS", "📅 Resumen Mes (T3)"),
        (cols[10], "📌 RESUMEN OBS", len(dict_t5), "nav_RESUMEN_OBS", "📌 Resumen Obs (T5)"),
    ]

    for col, titulo, valor, key_btn, target_tab in kpis:
        is_active = (st.session_state.active_tab == target_tab)
        active_class = "kpi-active" if is_active else ""
        
        with col:
            st.markdown(f'<div class="{active_class}">', unsafe_allow_html=True)
            if st.button(f"{titulo}\n\n{valor}", key=key_btn):
                st.session_state.active_tab = target_tab
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    if st.session_state.active_tab == "📋 Tabla General":
        st.markdown("#### **TABLA GENERAL DE CONTROL DE INFORMES**")
        edited_df = st.data_editor(
            df[COLUMNAS_EXCEL],
            num_rows="dynamic",
            use_container_width=True,
            key="editor_general",
        )
        if st.button("💾 Guardar Cambios"):
            cleaned_df = limpiar_estado_y_responsable(edited_df)
            st.session_state.df_data = cleaned_df
            guardar_datos(cleaned_df)
            st.success("¡Datos guardados correctamente!")
            st.rerun()
