import streamlit as st
import pandas as pd
import numpy as np
import os
import unicodedata

# Configuración de página
st.set_page_config(
    page_title="Gestión de Inspecciones",
    page_icon="📋",
    layout="wide"
)

# Constantes
ORDEN_MESES = [
    "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", 
    "JULIO", "AGOSTO", "SETIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
]

COLUMNAS_EXCEL = [
    "ITEM POR MES", "IT2", "UNIDAD", "MES", "LINEAS", 
    "CODIGO DE INFORME", "GRUPO DE TUBERÍAS", "SAP", 
    "ALCANCE DEL SERVICIO", "ESTADO - ELABORACIÓN DE INFORME", 
    "RESPONSABLE", "OBSERVACIÓN", "ESTADO - VALORIZACIÓN"
]

# Funciones auxiliares
def texto_normalizado(val):
    if pd.isna(val):
        return ""
    val_str = str(val).strip().upper()
    return ''.join(
        c for c in unicodedata.normalize('NFD', val_str)
        if unicodedata.category(c) != 'Mn'
    )

def formatear_entero_limpio(val):
    if pd.isna(val) or val is None or str(val).strip() == "":
        return ""
    try:
        val_float = float(val)
        if val_float.is_integer():
            return str(int(val_float))
        return str(val_float)
    except ValueError:
        return str(val).strip()

def preparar_tabla_con_indice_1(df_in):
    df_res = df_in.copy()
    df_res.index = range(1, len(df_res) + 1)
    return df_res

def limpiar_estado_y_responsable(df_in):
    df_res = df_in.copy()
    for col in df_res.columns:
        df_res[col] = df_res[col].astype(str).str.strip()
    return df_res

def guardar_datos(df_guardar):
    df_guardar.to_excel("base_datos_inspecciones.xlsx", index=False)

# Inicialización de estado
if "df_data" not in st.session_state:
    if os.path.exists("base_datos_inspecciones.xlsx"):
        st.session_state.df_data = pd.read_excel("base_datos_inspecciones.xlsx")
    else:
        st.session_state.df_data = pd.DataFrame(columns=COLUMNAS_EXCEL)

st.title("📋 Control y Gestión de Informes de Inspección")

df = st.session_state.df_data

t_gen, t_otros = st.tabs(["📊 Tabla General", "⚙️ Configuración / Otros"])

with t_gen:
    c_m, c_b = st.columns([1, 3])
    meses_disp = ["Todos"] + sorted(
        [m for m in df["MES"].dropna().astype(str).str.strip().str.upper().unique() if m],
        key=lambda x: ORDEN_MESES.index(x) if x in ORDEN_MESES else 99
    )
    m_sel = c_m.selectbox("Filtrar Mes:", meses_disp)
    txt_b = c_b.text_input("🔍 Buscador:")
    
    df_dis = df[COLUMNAS_EXCEL].copy()
    
    # Convierte todos los campos a texto limpio
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

    df_dis = preparar_tabla_con_indice_1(df_dis)

    # Configuración de columnas
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
        key="editor_tabla_general_select"
    )

    if st.button("💾 Guardar Cambios", key="btn_guardar_gen"):
        df_global = st.session_state.df_data

        for idx_filtrado in ed_df.index:
            # Extraer identificadores del registro editado en la vista filtrada
            cod_info = str(ed_df.at[idx_filtrado, "CODIGO DE INFORME"]).strip()
            linea = str(ed_df.at[idx_filtrado, "LINEAS"]).strip()

            # Localizar la fila correspondiente exacta en el DataFrame global original
            coincidencias = df_global[
                (df_global["CODIGO DE INFORME"].astype(str).str.strip() == cod_info) & 
                (df_global["LINEAS"].astype(str).str.strip() == linea)
            ]

            if not coincidencias.empty:
                idx_real = coincidencias.index[0]

                # Actualizar directamente la fila global sin duplicar registros
                for col in COLUMNAS_EXCEL:
                    df_global.at[idx_real, col] = ed_df.at[idx_filtrado, col]
                
                # Limpiar la observación si la valorización pasa a "SI"
                if str(ed_df.at[idx_filtrado, "ESTADO - VALORIZACIÓN"]).strip().upper() == "SI":
                    df_global.at[idx_real, "OBSERVACIÓN"] = ""

        # Sincronizar y persistir
        st.session_state.df_data = limpiar_estado_y_responsable(df_global[COLUMNAS_EXCEL])
        guardar_datos(st.session_state.df_data)
        st.success("Cambios guardados correctamente sin alteración de registros.")
        st.rerun()

with t_otros:
    st.write("Sección reservada para otras configuraciones o módulos.")
