import streamlit as st
import pandas as pd
import json
import os
import unicodedata

# ==========================================
# CONFIGURACIÓN GENERAL Y ARCHIVO
# ==========================================
DB_FILE = "base_datos.json"

COLUMNAS_EXCEL = [
    "ITEM POR MES", "IT2", "UNIDAD", "MES", "LINEAS",
    "CODIGO DE INFORME", "GRUPO DE TUBERÍAS", "SAP",
    "ALCANCE DEL SERVICIO", "ESTADO - ELABORACIÓN DE INFORME",
    "RESPONSABLE", "OBSERVACIÓN", "ESTADO - VALORIZACIÓN"
]

ORDEN_MESES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SETIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
]

# ==========================================
# FUNCIONES AUXILIARES DE TEXTO Y FORMATO
# ==========================================
def texto_normalizado(texto):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().lower()
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def formatear_entero_limpio(valor):
    if pd.isna(valor) or valor is None:
        return ""
    val_str = str(valor).strip()
    if val_str.endswith(".0"):
        return val_str[:-2]
    return val_str

def limpiar_estado_y_responsable(df):
    def ajustar_estado(row):
        val = texto_normalizado(row.get("ESTADO - VALORIZACIÓN", ""))
        resp = str(row.get("RESPONSABLE", "")).strip()
        obs = str(row.get("OBSERVACIÓN", "")).strip()
        
        if val == "si":
            return "ENTREGADO EN FISICO Y VIRTUAL"
        if resp != "" or obs != "":
            return "EN REVISIÓN"
        return row.get("ESTADO - ELABORACIÓN DE INFORME", "")

    def ajustar_responsable(row):
        val = texto_normalizado(row.get("ESTADO - VALORIZACIÓN", ""))
        if val == "si":
            return ""
        return row.get("RESPONSABLE", "")

    df["ESTADO - ELABORACIÓN DE INFORME"] = df.apply(ajustar_estado, axis=1)
    df["RESPONSABLE"] = df.apply(ajustar_responsable, axis=1)
    return df

# ==========================================
# CARGA Y GUARDADO DE DATOS (JSON)
# ==========================================
def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                df = pd.DataFrame(data)
                for col in COLUMNAS_EXCEL:
                    if col not in df.columns:
                        df[col] = ""
                return df[COLUMNAS_EXCEL]
        except Exception as e:
            st.error(f"Error al cargar la base de datos: {e}")
            return pd.DataFrame(columns=COLUMNAS_EXCEL)
    else:
        return pd.DataFrame(columns=COLUMNAS_EXCEL)

def guardar_datos(df):
    try:
        data = df.to_dict(orient="records")
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"Error al guardar la base de datos: {e}")

# ==========================================
# INICIALIZACIÓN DEL ESTADO DE SESIÓN Y APP
# ==========================================
if "df_data" not in st.session_state:
    st.session_state.df_data = cargar_datos()

st.session_state.df_data = limpiar_estado_y_responsable(st.session_state.df_data)

st.set_page_config(page_title="Gestión de Informes", layout="wide")
st.title("📋 Sistema de Gestión y Valorización de Informes")

t_gen, t_pen, t_val = st.tabs(["📊 Tabla General", "⏳ Pendientes / En Revisión", "✅ Valorizados"])
# ------------------------------------------
# 1. PESTAÑA: TABLA GENERAL
# ------------------------------------------
with t_gen:
    c_m, c_b = st.columns([1, 3])
    
    meses_presentes = [m for m in df["MES"].dropna().astype(str).str.strip().str.upper().unique() if m]
    meses_ordenados = sorted(meses_presentes, key=lambda x: ORDEN_MESES.index(x) if x in ORDEN_MESES else 99)
    meses_disp = ["Todos"] + meses_ordenados
    
    m_sel = c_m.selectbox("Filtrar Mes:", meses_disp, key="sel_mes_gen")
    txt_b = c_b.text_input("🔍 Buscador:", key="input_busqueda_gen")
    
    # Se genera una vista filtrada conservando los índices originales de df
    df_dis = df[COLUMNAS_EXCEL].copy()
    
    for column in df_dis.columns:
        df_dis[column] = df_dis[column].apply(formatear_entero_limpio)

    if m_sel != "Todos": 
        df_dis = df_dis[df_dis["MES"].astype(str).str.strip().str.upper() == m_sel]
    if txt_b.strip():
        q = texto_normalizado(txt_b)
        df_dis = df_dis[df_dis.apply(
            lambda r: q in texto_normalizado(r["LINEAS"]) or 
                      q in texto_normalizado(r["SAP"]) or 
                      q in texto_normalizado(r["CODIGO DE INFORME"]) or 
                      q in texto_normalizado(r["GRUPO DE TUBERÍAS"]), axis=1
        )]
    
    df_dis["ESTADO - VALORIZACIÓN"] = df_dis["ESTADO - VALORIZACIÓN"].apply(
        lambda x: "SI" if texto_normalizado(x) == "SI" else "Pendiente - valorización"
    )

    def procesar_cambios_tabla():
        estado_editor = st.session_state.get("editor_tabla_general_select", {})
        filas_editadas = estado_editor.get("edited_rows", {})
        
        for idx_relativo, dict_cols in filas_editadas.items():
            idx_real = df_dis.index[idx_relativo]
            if "ESTADO - VALORIZACIÓN" in dict_cols:
                nuevo_val = str(dict_cols["ESTADO - VALORIZACIÓN"]).strip().upper()
                if nuevo_val == "SI":
                    st.session_state.df_data.at[idx_real, "OBSERVACIÓN"] = ""

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

    ed_df = st.data_editor(
        df_dis,
        column_config=config_columnas,
        hide_index=False,
        use_container_width=True, 
        key="editor_tabla_general_select",
        on_change=procesar_cambios_tabla
    )

    if st.button("💾 Guardar Cambios", key="btn_guardar_gen"):
        for idx_real in ed_df.index:
            for col in COLUMNAS_EXCEL:
                st.session_state.df_data.at[idx_real, col] = ed_df.at[idx_real, col]

        st.session_state.df_data = limpiar_estado_y_responsable(st.session_state.df_data[COLUMNAS_EXCEL])
        guardar_datos(st.session_state.df_data)
        st.success("Cambios guardados con éxito en la base de datos.")
        st.rerun()

# ------------------------------------------
# 2. PESTAÑA: PENDIENTES / EN REVISIÓN
# ------------------------------------------
with t_pen:
    st.subheader("Informes Pendientes o En Revisión")
    df_pen = df[df["ESTADO - VALORIZACIÓN"].apply(lambda x: texto_normalizado(x) != "si")].copy()
    
    if not df_pen.empty:
        df_pen_dis = df_pen.reset_index(drop=True)
        df_pen_dis.index = df_pen_dis.index + 1
        st.dataframe(df_pen_dis[COLUMNAS_EXCEL], use_container_width=True)
    else:
        st.info("No hay registros pendientes.")

# ------------------------------------------
# 3. PESTAÑA: VALORIZADOS
# ------------------------------------------
with t_val:
    st.subheader("Informes Valorizados")
    df_val = df[df["ESTADO - VALORIZACIÓN"].apply(lambda x: texto_normalizado(x) == "si")].copy()
    
    if not df_val.empty:
        df_val_dis = df_val.reset_index(drop=True)
        df_val_dis.index = df_val_dis.index + 1
        st.dataframe(df_val_dis[COLUMNAS_EXCEL], use_container_width=True)
    else:
        st.info("No hay registros valorizados.")
df = st.session_state.df_data.copy()
