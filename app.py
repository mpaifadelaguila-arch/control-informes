import streamlit as st
import pandas as pd
import unicodedata
import os
import threading
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Control interno de informes - Ademinsac",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# CONSTANTES Y CONFIGURACIÓN DE RUTAS
# -----------------------------------------------------------------------------
EXCEL_FILE = "Base_Datos_General.xlsx"
FOLDER_ID_DRIVE = "1-XXXXXX_TU_FOLDER_ID_AQUI_XXXXXX"  # Coloca aquí tu ID de carpeta de Google Drive

ESTADOS_VALIDOS = [
    "VALORIZADO (SI)",
    "Pendiente de inspección o falta carpeta",
    "Inspección complementaria",
    "Retirado"
]

COLORES_ESTADO = {
    "VALORIZADO (SI)": "🟢",
    "Pendiente de inspección o falta carpeta": "🟡",
    "Inspección complementaria": "🔵",
    "Retirado": "🔴"
}

# -----------------------------------------------------------------------------
# UTILIDADES Y NORMALIZACIÓN DE TEXTO
# -----------------------------------------------------------------------------
def texto_normalizado(val):
    """Normaliza texto eliminando acentos y espacios adicionales para comparaciones uniformes."""
    if pd.isna(val):
        return ""
    s = str(val).strip().upper()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s

def calcular_señal(row):
    """Calcula dinámicamente la etiqueta de estado basada en la columna VALORIZACIÓN."""
    val = texto_normalizado(row.get("VALORIZACIÓN", ""))
    if val == "SI":
        return "VALORIZADO (SI)"
    elif val in ["NO", "PENDIENTE DE INSPECCION O FALTA CARPETA", "PENDIENTE"]:
        return "Pendiente de inspección o falta carpeta"
    elif val == "INSPECCION COMPLEMENTARIA":
        return "Inspección complementaria"
    elif val == "RETIRADO":
        return "Retirado"
    else:
        return "Pendiente de inspección o falta carpeta"

# -----------------------------------------------------------------------------
# SUBIDA ASÍNCRONA A GOOGLE DRIVE (SEGUNDO PLANO)
# -----------------------------------------------------------------------------
def subida_drive_hilo(ruta_archivo):
    """Ejecuta la autenticación y subida del archivo Excel a Google Drive en un hilo independiente."""
    try:
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile("credentials.json")
        if gauth.credentials is None:
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Authorize()
        
        drive = GoogleDrive(gauth)
        
        # Buscar si el archivo ya existe en Drive
        query = f"'{FOLDER_ID_DRIVE}' in parents and title='{EXCEL_FILE}' and trashed=false"
        file_list = drive.ListFile({'q': query}).GetList()
        
        if file_list:
            file_drive = file_list[0]
        else:
            file_drive = drive.CreateFile({
                'title': EXCEL_FILE,
                'parents': [{'id': FOLDER_ID_DRIVE}]
            })
            
        file_drive.SetContentFile(ruta_archivo)
        file_drive.Upload()
        print("Subida a Google Drive completada exitosamente.")
    except Exception as e:
        print(f"Error durante la subida síncrona/asíncrona a Google Drive: {e}")

# -----------------------------------------------------------------------------
# CARGA Y GUARDADO DE DATOS LOCALES
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def cargar_datos_disco():
    """Carga los datos iniciales desde el archivo Excel en disco."""
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
    else:
        # Estructura por defecto si no existe el archivo local
        df = pd.DataFrame(columns=[
            "Señal", "N°", "U_O", "Mes", "N° Línea", "Código de informe", 
            "Etiqueta de equipo", "SAP", "Alcance", "Notas", 
            "Estado de informe/emisión", "Responsable", "OBSERVACIÓN", "VALORIZACIÓN"
        ])
    return df

def guardar_datos(df):
    """Guarda los datos en Excel local e inicia la sincronización con Drive en un hilo secundario."""
    df.to_excel(EXCEL_FILE, index=False)
    # Lanza la subida en segundo plano para evitar bloquear la interfaz del usuario
    threading.Thread(target=subida_drive_hilo, args=(EXCEL_FILE,), daemon=True).start()

# -----------------------------------------------------------------------------
# INICIALIZACIÓN DEL SESSION STATE
# -----------------------------------------------------------------------------
if "df_data" not in st.session_state:
    st.session_state.df_data = cargar_datos_disco()

# -----------------------------------------------------------------------------
# VISTAS DE LA APLICACIÓN
# -----------------------------------------------------------------------------
def vista_tabla_general():
    st.title("Control interno de informes - Ademinsac")
    
    df = st.session_state.df_data.copy()
    
    # Asegurar columna calculada para representación visual
    df["SEÑAL"] = df.apply(calcular_señal, axis=1)

    # --- FILTROS DE BÚSQUEDA Y SELECCIÓN ---
    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1:
        filtro_estado = st.selectbox("Filtrar por mes", ["Todos"] + list(df["Mes"].dropna().unique()))
    with col_filtro2:
        filtro_alcance = st.selectbox("Alcance del servicio", ["Todos"] + list(df["Alcance"].dropna().unique()))

    busqueda = st.text_input("Buscar por líneas, código, grupo, SAP o notas", placeholder="🔍 Digite término a buscar...")

    # Aplicar filtrado
    df_filtrado = df.copy()
    if filtro_estado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Mes"] == filtro_estado]
    if filtro_alcance != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Alcance"] == filtro_alcance]
    if busqueda:
        b_upper = busqueda.upper()
        df_filtrado = df_filtrado[
            df_filtrado.apply(lambda row: b_upper in str(row.values).upper(), axis=1)
        ]

    # --- LEYENDA DE ESTADOS ---
    st.markdown(" ".join([f"`{COLORES_ESTADO[k]} {k}` |" for k in ESTADOS_VALIDOS]))
    
    st.divider()

    # --- CONFIGURACIÓN DE COLUMNAS PARA DATA EDITOR ---
    column_config = {
        "SEÑAL": st.column_config.SelectboxColumn(
            "Señal",
            options=ESTADOS_VALIDOS,
            disabled=True,
            help="Columna autocalculada según el valor de VALORIZACIÓN"
        ),
        "VALORIZACIÓN": st.column_config.SelectboxColumn(
            "VALORIZACIÓN",
            options=["SI", "NO", "PENDIENTE DE INSPECCION O FALTA CARPETA", "INSPECCION COMPLEMENTARIA", "RETIRADO"],
            required=True
        ),
        "OBSERVACIÓN": st.column_config.TextColumn(
            "OBSERVACIÓN",
            help="Desactivado automáticamente si VALORIZACIÓN es 'SI'"
        )
    }

    # --- EDITOR DE DATOS STREAMLIT ---
    editado = st.data_editor(
        df_filtrado,
        column_config=column_config,
        use_container_width=True,
        num_rows="dynamic",
        key="editor_tabla_general"
    )

    # --- BOTÓN DE GUARDADO SIN PARPADEO DE PANTALLA EN BLANCO ---
    if st.button("Guardar cambios", key="guardar_tabla", icon=":material/save:", type="primary"):
        # 1. Eliminar columna calculada temporal antes de persistir
        df_actualizado = editado.drop(columns=["SEÑAL"], errors="ignore")
        
        # 2. Aplicar regla de negocio: Limpiar observación si se valorizó
        mascara_si = df_actualizado["VALORIZACIÓN"].apply(lambda x: texto_normalizado(x) == "SI")
        df_actualizado.loc[mascara_si, "OBSERVACIÓN"] = ""
        
        # 3. Actualizar la memoria principal de la sesión
        st.session_state.df_data.update(df_actualizado)
        
        # 4. Guardar archivo local e iniciar subida en segundo plano
        guardar_datos(st.session_state.df_data)
        
        # 5. Notificación flotante fluida (SIN ejecutarse st.rerun)
        st.toast("¡Cambios guardados con éxito!", icon="💾")


# -----------------------------------------------------------------------------
# EJECUCIÓN PRINCIPAL
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    vista_tabla_general()
