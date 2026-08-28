import streamlit as st
import pandas as pd
import unicodedata

# Configuración inicial de la página
st.set_page_config(page_title="Gestión de Informes", layout="wide")

# --- CONSTANTES ---
COLUMNAS_EXCEL = [
    "ITEM POR MES", "IT2", "UNIDAD", "MES", "LINEAS", "CODIGO DE INFORME",
    "GRUPO DE TUBERÍAS", "SAP", "ALCANCE DEL SERVICIO", 
    "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "OBSERVACIÓN", "ESTADO - VALORIZACIÓN"
]

ORDEN_MESES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SETIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
]

# --- FUNCIONES AUXILIARES DE LIMPIEZA Y FORMATEO ---
def texto_normalizado(val):
    if pd.isna(val):
        return ""
    txt = str(val).strip().upper()
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

def formatear_entero_limpio(val):
    if pd.isna(val):
        return ""
    try:
        f = float(val)
        if f.is_integer():
            return str(int(f))
        return str(f)
    except ValueError:
        return str(val).strip()

def limpiar_estado_y_responsable(df):
    df_clean = df.copy()
    for idx, row in df_clean.iterrows():
        est_val = str(row["ESTADO - VALORIZACIÓN"]).strip().upper()
        if est_val == "SI":
            df_clean.at[idx, "ESTADO - ELABORACIÓN DE INFORME"] = "Finalizado"
            df_clean.at[idx, "RESPONSABLE"] = "Julio Ponce / Omar"
            df_clean.at[idx, "OBSERVACIÓN"] = ""
    return df_clean

# --- GESTIÓN DE DATOS Y ENTORNO ---
def cargar_datos():
    if "df_data" not in st.session_state:
        # Estructura inicial de ejemplo (reemplazar con lectura desde tu Excel o BD)
        datos_ejemplo = {
            "ITEM POR MES": [1, 2, 3],
            "IT2": [101, 102, 103],
            "UNIDAD": ["U-01", "U-01", "U-02"],
            "MES": ["ENERO", "ENERO", "FEBRERO"],
            "LINEAS": ["48-AMINA_POBRE-GT-001", "48-AMINA_POBRE-GT-001", "32-GAS-002"],
            "CODIGO DE INFORME": ["ADEMINSAC-FIAB-RLP-379-2026", "ADEMINSAC-FIAB-RLP-379-2026", "ADEMINSAC-FIAB-RLP-380-2026"],
            "GRUPO DE TUBERÍAS": ["48-AMINA_POBRE-GT-001", "48-AMINA_POBRE-GT-001", "32-GAS-002"],
            "SAP": [10044162, 10044164, 10044234],
            "ALCANCE DEL SERVICIO": ["LINEAS", "VT-CIRCUITOS - PENDIENTE INSPECCION", "VT-CIRCUITOS - INSPECCION COMPLEMENTARIA"],
            "ESTADO - ELABORACIÓN DE INFORME": ["Finalizado", "En proceso", "Pendiente"],
            "RESPONSABLE": ["Julio Ponce / Omar", "Julio Ponce / Omar", "Sin Asignar"],
            "OBSERVACIÓN": ["", "Revisión técnica", ""],
            "ESTADO - VALORIZACIÓN": ["SI", "Pendiente - valorización", "Pendiente - valorización"]
        }
        st.session_state.df_data = pd.DataFrame(datos_ejemplo)

def guardar_datos(df):
    st.session_state.df_data = df

# Carga de datos
cargar_datos()
df = st.session_state.df_data
# --- INTERFAZ DE USUARIO CON PESTAÑAS ---
t_kpi, t_gen = st.tabs(["📊 KPIs / Resumen", "📋 Tabla General"])

# --- PESTAÑA 1: KPI ---
with t_kpi:
    st.title("Métricas del Servicio")
    
    # Cálculo dinámico de indicadores
    total_registros = len(df)
    total_valorizados = len(df[df["ESTADO - VALORIZACIÓN"].astype(str).str.strip().str.upper() == "SI"])
    pendientes_val = total_registros - total_valorizados
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Informes/Items", total_registros)
    c2.metric("Valorizados (SI)", total_valorizados)
    c3.metric("Pendientes Valorización", pendientes_val)

# --- PESTAÑA 2: TABLA GENERAL Y EDICIÓN ---
with t_gen:
    c_m, c_b, c_sw = st.columns([1, 2, 1])
    
    # Filtro dinámico por mes
    meses_disp = ["Todos"] + sorted([m for m in df["MES"].dropna().astype(str).str.strip().str.upper().unique() if m], key=lambda x: ORDEN_MESES.index(x) if x in ORDEN_MESES else 99)
    
    m_sel = c_m.selectbox("Filtrar Mes:", meses_disp)
    txt_b = c_b.text_input("🔍 Buscador:")
    modo_edicion = c_sw.toggle("✏️ Modo Edición", value=False)
    
    # Copia de trabajo para la vista
    df_dis = df[COLUMNAS_EXCEL].copy()
    
    # Formateo de números enteros
    for column in df_dis.columns:
        df_dis[column] = df_dis[column].apply(formatear_entero_limpio)

    # Aplicación de filtros de mes y búsqueda rápida
    if m_sel != "Todos": 
        df_dis = df_dis[df_dis["MES"].astype(str).str.strip().str.upper() == m_sel]
    if txt_b.strip():
        q = texto_normalizado(txt_b)
        df_dis = df_dis[df_dis.apply(lambda r: q in texto_normalizado(r["LINEAS"]) or q in texto_normalizado(r["SAP"]) or q in texto_normalizado(r["CODIGO DE INFORME"]) or q in texto_normalizado(r["GRUPO DE TUBERÍAS"]), axis=1)]
    
    df_dis["ESTADO - VALORIZACIÓN"] = df_dis["ESTADO - VALORIZACIÓN"].apply(
        lambda x: "SI" if texto_normalizado(x) == "SI" else "Pendiente - valorización"
    )

    # Configuración de anchos y tipos de campos para el renderizado
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

    # Lógica de colores según condiciones
    def resaltar_filas(row):
        val_estado = str(row.get("ESTADO - VALORIZACIÓN", "")).strip().upper()
        val_alcance = texto_normalizado(row.get("ALCANCE DEL SERVICIO", ""))

        # 1. Verde claro si ESTADO - VALORIZACIÓN indica SI
        if val_estado == "SI":
            return ["background-color: #D1FAE5; color: #065F46; font-weight: bold;"] * len(row)

        # 2. Amarillo claro para los pendientes de inspección / carpeta
        if val_alcance in [
            "VT-CIRCUITOS - PENDIENTE INSPECCION",
            "VT-CIRCUITOS - FALTA CARPETA",
            "LINEAS - PENDIENTE INSPECCION"
        ]:
            return ["background-color: #FEF08A; color: #713F12; font-weight: bold;"] * len(row)

        # 3. Celeste claro para inspecciones complementarias
        if val_alcance == "VT-CIRCUITOS - INSPECCION COMPLEMENTARIA":
            return ["background-color: #BAE6FD; color: #0C4A6E; font-weight: bold;"] * len(row)

        return [""] * len(row)

    # Objeto Styler para aplicar estilos
    df_styled = df_dis.style.apply(resaltar_filas, axis=1)

    if modo_edicion:
        # VISTA 1: Editor de datos sin visualización de colores
        ed_df = st.data_editor(
            df_dis,
            column_config=config_columnas,
            hide_index=True,
            use_container_width=True, 
            key="editor_tabla_general_select"
        )

        if st.button("💾 Guardar Cambios", key="btn_guardar_gen"):
            for real_idx, row in ed_df.iterrows():
                for col in COLUMNAS_EXCEL:
                    st.session_state.df_data.at[real_idx, col] = row[col]

                if str(row["ESTADO - VALORIZACIÓN"]).strip().upper() == "SI":
                    st.session_state.df_data.at[real_idx, "OBSERVACIÓN"] = ""

            st.session_state.df_data = limpiar_estado_y_responsable(st.session_state.df_data[COLUMNAS_EXCEL])
            guardar_datos(st.session_state.df_data)
            st.success("Cambios guardados con éxito en la base de datos.")
            st.rerun()
    else:
        # VISTA 2: Renderizador visual con resaltado de colores garantizado
        st.dataframe(
            df_styled,
            column_config=config_columnas,
            hide_index=True,
            use_container_width=True
        )
