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

# --- ESTILOS CSS PROFESIONALES Y PALETA CORPORATIVA ORIGINAL ---
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
