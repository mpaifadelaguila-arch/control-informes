import html
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from tema import ICONOS, TONOS, aplicar_tema, tabla_html, tinte

# ==============================================================================
# CONFIGURACIÓN DE RUTAS DINÁMICAS (ACTUALIZADA)
# ==============================================================================
RUTA_ACTUAL = Path(__file__).resolve().parent
DIR_RAIZ = RUTA_ACTUAL

DIR_COMPLEMENTO = DIR_RAIZ / "COMPLEMENTO"
DIR_CONTROL_INFORME = DIR_RAIZ / "control-informe"

RUTA_BASE_DATOS_MAESTRA = DIR_CONTROL_INFORME / "BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx"
RUTA_COMPENDIO = DIR_COMPLEMENTO / "COMPENDIO TÉCNICO UNIFICADO DE HALLAZGOS Y RECOMENDACIONES TÉCNICAS.REV.1.docx"
RUTA_POE = DIR_COMPLEMENTO / "PROCEDIMIENTO OPERATIVO ESTANDARIZADO (POE).docx"
RUTA_ROL = DIR_COMPLEMENTO / "ROL_Y_OBJETIVO.REV2.txt"
RUTA_PLANTILLA_WORD = DIR_RAIZ / "plantilla_base.docx"

if str(DIR_RAIZ) not in sys.path:
    sys.path.append(str(DIR_RAIZ))

# Configuración de la interfaz Streamlit (Barra lateral desplegada)
st.set_page_config(
    page_title="Control interno de informes - Ademinsac",
    page_icon=":material/assignment:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    '<meta name="google" content="notranslate">', unsafe_allow_html=True
)

FOLDER_ID = "1gUyx6PbtLd7tG_C20x00CVmVdF0oYm_8"


@st.cache_resource
def conectar_drive():
    try:
        scopes = ["https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = (
            creds_dict["private_key"]
            .replace("\\n", "\n")
            .replace("\r\n", "\n")
        )
        credentials = Credentials.from_service_account_info(
            creds_dict, scopes=scopes
        )
        service = build("drive", "v3", credentials=credentials)
        return service
    except Exception as e:
        st.error(f"Error al conectar con Google Drive: {e}")
        return None


drive_service = conectar_drive()


def descargar_archivo_de_drive(nombre_archivo, ruta_local, max_reintentos=3):
    if not drive_service:
        return False

    for intento in range(1, max_reintentos + 1):
        try:
            query = f"'{FOLDER_ID}' in parents and name = '{nombre_archivo}' and trashed = false"
            res = (
                drive_service.files()
                .list(
                    q=query,
                    fields="files(id, modifiedTime)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            archivos = res.get("files", [])

            if archivos:
                file_id = archivos[0]["id"]
                request = drive_service.files().get_media(fileId=file_id)
                with open(ruta_local, "wb") as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()
                # Fecha de modificación en Drive, para la cabecera.
                with open(f"{ruta_local}.modificado", "w") as f:
                    f.write(archivos[0].get("modifiedTime", ""))
                return True
            return False
        except Exception as e:
            msg_error = str(e)
            if (
                "RECORD_LAYER_FAILURE" in msg_error
                or "SSL" in msg_error
                or "Connection" in msg_error
            ) and intento < max_reintentos:
                time.sleep(1.2 * intento)
                continue
            st.error(
                f"Error al descargar desde Google Drive ({nombre_archivo}): {e}"
            )
            break
    return False


def subir_archivo_a_drive(
    nombre_archivo, ruta_local, mime_type="application/json", max_reintentos=3
):
    if not drive_service:
        return False

    for intento in range(1, max_reintentos + 1):
        try:
            query = f"'{FOLDER_ID}' in parents and name = '{nombre_archivo}' and trashed = false"
            res = (
                drive_service.files()
                .list(
                    q=query,
                    fields="files(id)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            archivos = res.get("files", [])

            with open(ruta_local, "rb") as f:
                contenido_binario = io.BytesIO(f.read())

            media = MediaIoBaseUpload(
                contenido_binario, mimetype=mime_type, resumable=True
            )

            if archivos:
                file_id = archivos[0]["id"]
                drive_service.files().update(
                    fileId=file_id, media_body=media, supportsAllDrives=True
                ).execute()
            else:
                file_metadata = {"name": nombre_archivo, "parents": [FOLDER_ID]}
                drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    supportsAllDrives=True,
                    fields="id",
                ).execute()

            return True
        except Exception as e:
            msg_error = str(e)
            if (
                "RECORD_LAYER_FAILURE" in msg_error
                or "SSL" in msg_error
                or "Connection" in msg_error
            ) and intento < max_reintentos:
                time.sleep(1.2 * intento)
                continue
            print(
                f"Error al respaldar en Google Drive ({nombre_archivo}): {e}"
            )
            break
    return False


# Estilos visuales (tema oscuro corporativo, ver tema.py)
aplicar_tema()

# Constantes y Archivos
DB_FILE = "database_informes.json"
SOLICITUDES_FILE = "database_solicitudes.json"

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
    "NOTAS",
    "ESTADO - ELABORACIÓN ",
    "RESPONSABLE",
    "OBSERVACIÓN",
    "VALORIZACIÓN",
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

ESPECIALISTAS_LISTA = [
    "Jesús Rehkoff Díaz",
    "M. Paifa",
    "Julio Ponce",
    "Omar",
    "Christopher",
    "Timana",
    "Ingrid",
]
REVISORES_PSAIM_LISTA = [
    "Franmary Gutierrez",
    "Alejandro Macury",
    "M. Paifa",
    "Julio Ponce",
    "Omar",
    "Christopher",
    "Timana",
    "Ingrid",
]
PERSONAL_LISTA_BASE = [
    "M. Paifa",
    "Julio Ponce",
    "Omar",
    "Christopher",
    "Timana",
    "Ingrid",
    "Juan José",
    "Dante",
    "Jesús Rehkoff Díaz",
    "Franmary Gutierrez",
    "Alejandro Macury",
    "Otro Inspector",
]


def texto_normalizado(valor):
    if pd.isna(valor) or valor is None:
        return ""
    texto = str(valor).strip().upper()
    return texto.translate(str.maketrans("ÁÉÍÓÚÜÑ", "AEIOUUN"))


def texto_limpio(valor):
    if pd.isna(valor) or valor is None:
        return ""
    texto = str(valor).strip()
    return texto[:-2] if texto.endswith(".0") else texto


def separar_alcance_y_notas(alcance, notas=""):
    alcance_limpio = texto_limpio(alcance)
    notas_limpias = texto_limpio(notas)
    patron = re.compile(
        r"^\s*(LINEAS|VT\s*-\s*CIRCUITOS)\s*(?:[-–—:]\s*(.+))?$",
        flags=re.IGNORECASE,
    )
    coincidencia = patron.match(alcance_limpio)
    if not coincidencia:
        return alcance_limpio, notas_limpias

    alcance_base = (
        "LINEAS"
        if texto_normalizado(coincidencia.group(1)) == "LINEAS"
        else "VT-CIRCUITOS"
    )
    nota_extraida = texto_limpio(coincidencia.group(2) or "")
    if nota_extraida and texto_normalizado(
        nota_extraida
    ) not in texto_normalizado(notas_limpias):
        notas_limpias = (
            f"{notas_limpias} | {nota_extraida}".strip(" |")
            if notas_limpias
            else nota_extraida
        )
    return alcance_base, notas_limpias


def normalizar_codigo_informe(codigo):
    # La escritura correcta es "FIAB"; en la base hay códigos con "FlAB" (l minúscula).
    return re.sub(r"(?i)(?<=-)FLAB(?=-)", "FIAB", texto_limpio(codigo))


# Anexo: líneas de un informe entregado que quedaron pendientes de inspección
# y se emiten después con un número entre el correlativo y el año,
# ej. "ADEMINSAC-FIAB-RLP-275-1-2026" es anexo de "ADEMINSAC-FIAB-RLP-275-2026".
PATRON_ANEXO = re.compile(r"^(.*-RLP-\d+)-\d+-(\d{4})$", flags=re.IGNORECASE)


def es_anexo(codigo):
    return bool(PATRON_ANEXO.match(texto_limpio(codigo)))


def normalizar_base(df_entrada):
    df = df_entrada.copy()
    for columna in COLUMNAS_EXCEL:
        if columna not in df.columns:
            df[columna] = ""
    df = df[COLUMNAS_EXCEL].fillna("")

    for indice, fila in df.iterrows():
        estado = texto_limpio(fila["ESTADO - ELABORACIÓN "])
        responsable = texto_limpio(fila["RESPONSABLE"])
        if "-" in estado:
            estado_base, responsable_estado = estado.split("-", 1)
            df.at[indice, "ESTADO - ELABORACIÓN "] = estado_base.strip()
            if not responsable or texto_normalizado(responsable) in {
                "NAN",
                "NONE",
            }:
                df.at[indice, "RESPONSABLE"] = responsable_estado.strip()

        alcance, notas = separar_alcance_y_notas(
            fila["ALCANCE DEL SERVICIO"], fila.get("NOTAS", "")
        )
        df.at[indice, "ALCANCE DEL SERVICIO"] = alcance
        df.at[indice, "NOTAS"] = notas
        df.at[indice, "CODIGO DE INFORME"] = normalizar_codigo_informe(
            fila["CODIGO DE INFORME"]
        )
        for columna in ["ITEM POR MES", "IT2", "SAP"]:
            df.at[indice, columna] = texto_limpio(fila[columna])
    return df


def es_codigo_provisional(codigo):
    codigo_normalizado = texto_normalizado(codigo)
    return codigo_normalizado in {"", "-"} or any(
        texto in codigo_normalizado
        for texto in [
            "PENDIENTE ASIGNAR",
            "PENDIENTE DE ASIGNAR",
            "POR ASIGNAR",
        ]
    )


def es_correccion_psaim(observacion):
    observacion = texto_normalizado(observacion)
    return "PSAIM" in observacion and any(
        texto in observacion
        for texto in ["CORRECCION", "CORREGIR", "CORREGIDO", "CORREGIDA"]
    )


def es_revision_fiabilidad(observacion):
    obs = texto_normalizado(observacion)
    return "FIABILIDAD" in obs and "REVISION" in obs


def es_pendiente_inspeccion(fila):
    estado = texto_normalizado(fila.get("ESTADO - ELABORACIÓN ", ""))
    notas = texto_normalizado(fila.get("NOTAS", ""))
    observacion = texto_normalizado(fila.get("OBSERVACIÓN", ""))
    return any(
        texto in estado or texto in notas or texto in observacion
        for texto in [
            "PENDIENTE COMPLETAR INSPECCION",
            "PENDIENTE INSPECCION",
            "FALTA CARPETA",
            "COMPLETAR INSPECCION",
        ]
    )


@st.cache_data(ttl=5, show_spinner=False)
def cargar_datos():
    descargar_archivo_de_drive(DB_FILE, DB_FILE)
    if not os.path.exists(DB_FILE):
        return pd.DataFrame(columns=COLUMNAS_EXCEL)
    try:
        with open(DB_FILE, "r", encoding="utf-8") as archivo:
            return normalizar_base(pd.DataFrame(json.load(archivo)))
    except Exception:
        return pd.DataFrame(columns=COLUMNAS_EXCEL)


def guardar_datos(df):
    normalizar_base(df).to_json(DB_FILE, orient="records", force_ascii=False)
    subir_archivo_a_drive(DB_FILE, DB_FILE)
    st.cache_data.clear()


@st.cache_data(ttl=5, show_spinner=False)
def cargar_solicitudes():
    descargar_archivo_de_drive(SOLICITUDES_FILE, SOLICITUDES_FILE)
    if not os.path.exists(SOLICITUDES_FILE):
        return []
    try:
        with open(SOLICITUDES_FILE, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except Exception:
        return []


def guardar_solicitudes(solicitudes):
    with open(SOLICITUDES_FILE, "w", encoding="utf-8") as archivo:
        json.dump(solicitudes, archivo, ensure_ascii=False)
    subir_archivo_a_drive(SOLICITUDES_FILE, SOLICITUDES_FILE)
    st.cache_data.clear()


def registrar_solicitud(tipo, codigo, grupo, solicitante):
    solicitudes = cargar_solicitudes()
    repetida = any(
        normalizar_codigo_informe(solicitud["codigo"])
        == normalizar_codigo_informe(codigo)
        and solicitud["grupo"] == grupo
        and solicitud["tipo"] == tipo
        and solicitud["estado"] == "PENDIENTE"
        for solicitud in solicitudes
    )
    if repetida:
        return False, "Ya existe una solicitud pendiente para este informe."
    siguiente_id = (
        max((solicitud.get("id", 0) for solicitud in solicitudes), default=0)
        + 1
    )
    solicitudes.append({
        "id": siguiente_id,
        "tipo": tipo,
        "codigo": codigo,
        "grupo": grupo,
        "solicitante": solicitante,
        "estado": "PENDIENTE",
    })
    guardar_solicitudes(solicitudes)
    return True, "Solicitud enviada al administrador."


def excel_con_formato(df, nombre_hoja="CONTROL"):
    salida = io.BytesIO()
    datos = df.copy().fillna("")
    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        datos.to_excel(escritor, index=False, sheet_name=nombre_hoja[:31])
        hoja = escritor.book[nombre_hoja[:31]]
        hoja.freeze_panes = "A2"
        hoja.row_dimensions[1].height = 30
        relleno = PatternFill("solid", fgColor="0E2A47")
        for celda in hoja[1]:
            celda.font = Font(color="FFFFFF", bold=True)
            celda.fill = relleno
            celda.alignment = Alignment(
                horizontal="center", vertical="center", wrap_text=True
            )

        for columna in hoja.columns:
            letra = get_column_letter(columna[0].column)
            ancho = max(len(texto_limpio(celda.value)) for celda in columna)
            hoja.column_dimensions[letra].width = min(max(ancho + 2, 12), 42)
            for celda in columna[1:]:
                celda.alignment = Alignment(vertical="top", wrap_text=True)

        ultima_columna = get_column_letter(max(1, len(datos.columns)))
        ultima_fila = len(datos) + 1
        if len(datos.columns) and len(datos):
            tabla = Table(
                displayName=f"Tabla_{datetime.now():%H%M%S%f}",
                ref=f"A1:{ultima_columna}{ultima_fila}",
            )
            tabla.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium2",
                showFirstColumn=False,
                showLastColumn=False,
                showRowStripes=True,
                showColumnStripes=False,
            )
            hoja.add_table(tabla)
        else:
            hoja.auto_filter.ref = f"A1:{ultima_columna}1"
    salida.seek(0)
    return salida.getvalue()


def boton_descarga_excel(df, archivo, etiqueta="Descargar Excel"):
    st.download_button(
        etiqueta,
        data=excel_con_formato(df),
        file_name=archivo,
        mime=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        icon=":material/download:",
        use_container_width=False,
    )


def senal_visual(fila):
    notas = texto_normalizado(fila.get("NOTAS", ""))
    observacion = texto_normalizado(fila.get("OBSERVACIÓN", ""))
    val = texto_normalizado(fila.get("VALORIZACIÓN", ""))
    if "RETIRADO" in notas or "RETIRADO" in observacion or val == "RETIRADO":
        return "🔴 Retirado"
    if val == "SI":
        return "🟢 Valorizado (SI)"
    if "FALTA CARPETA" in notas or "PENDIENTE INSPECCION" in notas:
        return "🟡 Pend. inspección"
    if "INSPECCION COMPLEMENTARIA" in notas:
        return "🔵 Inspección complem."
    return "⚪ Sin alerta"


# Perú no tiene horario de verano: UTC-5 fijo, sin depender de la base de
# zonas horarias del servidor.
HORA_LIMA = timezone(timedelta(hours=-5), "Lima")


def fecha_actualizacion_base():
    # Fecha en que se guardó por última vez la base en Drive (hora de Lima).
    # Se lee de la marca que deja la descarga: no hace consultas extra a Drive,
    # porque su conexión no admite llamadas simultáneas desde varias sesiones.
    fecha = None
    try:
        with open(f"{DB_FILE}.modificado") as marca:
            texto = marca.read().strip()
        if texto:
            fecha = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except (OSError, ValueError):
        fecha = None
    if fecha is None and os.path.exists(DB_FILE):
        fecha = datetime.fromtimestamp(os.path.getmtime(DB_FILE), timezone.utc)
    if fecha is None:
        return "Sin datos"
    return fecha.astimezone(HORA_LIMA).strftime("%d/%m/%Y · %H:%M")


ICONO_INFORME = (
    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2'
    ' 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/></svg>'
)
ICONO_BASE_DATOS = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3'
    ' 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/></svg>'
)


CABECERA_SIMPLE = (
    "<div class='header-banner'><div class='header-title'>CONTROL INTERNO DE"
    " INFORMES — ADEMINSAC</div><div class='header-subtitle'>Monitoreo de"
    " inspecciones técnicas y valorización · Refinería La Pampilla</div></div>"
)


def html_cabecera(finalizados=None, total=None, mes_en_curso=None):
    # Si falla algún indicador, se muestra la cabecera simple en vez de
    # interrumpir la app.
    try:
        return _html_cabecera(finalizados, total, mes_en_curso)
    except Exception:
        return CABECERA_SIMPLE


def _html_cabecera(finalizados, total, mes_en_curso):
    chips = ""
    if total:
        avance = finalizados / total * 100
        chips += (
            "<div class='header-chip header-chip-avance'>"
            "<div class='chip-titulo'><span>Avance general</span>"
            f"<span class='chip-porcentaje'>{avance:.1f}%</span></div>"
            f"<div class='chip-barra'><div style='width:{avance:.1f}%'></div></div>"
            f"<div class='chip-detalle'>{finalizados} de {total} finalizados</div></div>"
        )
    if mes_en_curso:
        chips += (
            "<div class='header-chip'><div class='chip-titulo'>Mes en curso</div>"
            f"<div class='chip-valor chip-dorado'>{mes_en_curso.capitalize()}</div></div>"
        )
    chips += (
        "<div class='header-chip'><div class='chip-titulo'>Última actualización</div>"
        f"<div class='chip-valor'>{fecha_actualizacion_base()}</div></div>"
    )
    return (
        "<div class='header-banner header-indicadores'>"
        f"<div class='header-marca'><div class='header-icono'>{ICONO_INFORME}</div>"
        "<div><div class='header-title'>CONTROL INTERNO DE INFORMES — ADEMINSAC</div>"
        "<div class='header-subtitle'>Monitoreo de inspecciones técnicas y"
        " valorización · Refinería La Pampilla</div></div></div>"
        f"<div class='header-chips'>{chips}</div></div>"
    )


if "df_data" not in st.session_state:
    st.session_state.df_data = cargar_datos()

df = normalizar_base(st.session_state.df_data)

# La cabecera se completa con el avance cuando los KPIs están calculados.
cabecera = st.empty()
cabecera.markdown(html_cabecera(), unsafe_allow_html=True)

barra_datos = st.container(key="barra_datos")
with barra_datos:
    texto_datos, carga, respaldo = st.columns(
        [3, 1, 1], vertical_alignment="center"
    )
    texto_datos.markdown(
        f"<div class='barra-datos-texto'>{ICONO_BASE_DATOS}"
        "<span class='barra-datos-titulo'>Gestión de datos</span>"
        f"<span>· base en Google Drive, {len(df)} líneas</span></div>",
        unsafe_allow_html=True,
    )
    with carga.popover(
        "Cargar Excel", icon=":material/upload:", width="stretch"
    ):
        st.markdown("**Cargar base de datos**")
        archivo_excel = st.file_uploader(
            "Selecciona un archivo Excel", type=["xlsx", "xlsm"]
        )
        if (
            archivo_excel
            and st.button(
                "Reemplazar base de datos",
                icon=":material/upload:",
                type="primary",
            )
        ):
            try:
                libro = pd.ExcelFile(archivo_excel)
                hoja = (
                    "CONTROL"
                    if "CONTROL" in libro.sheet_names
                    else libro.sheet_names[0]
                )
                df_cargado = pd.read_excel(libro, sheet_name=hoja)
                mapa = {
                    str(columna).strip().upper(): columna
                    for columna in df_cargado.columns
                }
                renombre = {
                    mapa[columna.strip().upper()]: columna
                    for columna in COLUMNAS_EXCEL
                    if columna.strip().upper() in mapa
                }
                df_cargado = df_cargado.rename(columns=renombre)
                st.session_state.df_data = normalizar_base(df_cargado)
                guardar_datos(st.session_state.df_data)
                st.success(
                    "Base de datos cargada, migrada y guardada en Google Drive."
                )
                st.rerun()
            except Exception as error:
                st.error(f"No se pudo cargar el Excel: {error}")
    with respaldo:
        if not df.empty:
            boton_descarga_excel(
                df,
                "Respaldo_Control_Informes.xlsx",
                "Descargar respaldo",
            )

if df.empty:
    st.info(
        "Carga un archivo Excel con el botón «Cargar Excel» para iniciar el control.",
        icon=":material/info:",
    )
    st.stop()


@st.cache_data(ttl=5, show_spinner=False)
def procesar_agrupaciones_y_kpis(df_input):
    mascara_retirado = (
        df_input["OBSERVACIÓN"].apply(
            lambda v: "RETIRADO" in texto_normalizado(v)
        )
        | df_input["NOTAS"].apply(lambda v: "RETIRADO" in texto_normalizado(v))
        | df_input["VALORIZACIÓN"].apply(
            lambda v: texto_normalizado(v) == "RETIRADO"
        )
    )
    df_activos = df_input[~mascara_retirado].copy()

    df_activos["CLAVE_GLOBAL"] = df_activos.apply(
        lambda fila: (
            f"{texto_limpio(fila['MES'])}|SIN-CODIGO-GRUPO|{texto_normalizado(fila['GRUPO DE TUBERÍAS'])}"
            if es_codigo_provisional(fila["CODIGO DE INFORME"])
            else f"{texto_limpio(fila['MES'])}|{texto_limpio(fila['CODIGO DE INFORME'])}"
        ),
        axis=1,
    )
    df_activos["TIPO"] = df_activos["CODIGO DE INFORME"].apply(
        lambda codigo: "Anexo" if es_anexo(codigo) else "Principal"
    )

    # Los anexos se contabilizan en su propio bloque; el resto de KPIs
    # cuenta solo informes principales.
    df_anexos = df_activos[df_activos["TIPO"] == "Anexo"]
    mask_anexo_pend_inspeccion = df_anexos.apply(es_pendiente_inspeccion, axis=1)
    anexos_total = df_anexos["CLAVE_GLOBAL"].nunique()
    anexos_pend_inspeccion = df_anexos[mask_anexo_pend_inspeccion][
        "CLAVE_GLOBAL"
    ].nunique()
    anexos_valorizados = df_anexos[
        df_anexos["VALORIZACIÓN"].apply(texto_normalizado) == "SI"
    ]["CLAVE_GLOBAL"].nunique()
    df_principales = df_activos[df_activos["TIPO"] == "Principal"]

    mask_psaim = df_activos["OBSERVACIÓN"].apply(es_correccion_psaim)
    mask_pend_inspeccion = df_activos.apply(es_pendiente_inspeccion, axis=1)
    mask_pend_elaboracion = (
        df_activos["ESTADO - ELABORACIÓN "]
        .apply(texto_normalizado)
        .str.contains("PENDIENTE ELABORACION")
    )

    df_psaim = df_activos[mask_psaim]
    df_pend_inspeccion = df_activos[mask_pend_inspeccion]
    df_pend_asignacion = df_activos[mask_pend_elaboracion]
    df_en_proceso = df_activos[
        df_activos["ESTADO - ELABORACIÓN "]
        .apply(texto_normalizado)
        .str.contains("EN PROCESO")
        # Un informe con alguna línea pendiente de inspección espera al campo,
        # no al gabinete: se cuenta en "Pend. inspección", no en "En proceso".
        & ~df_activos["CLAVE_GLOBAL"].isin(
            df_activos.loc[mask_pend_inspeccion, "CLAVE_GLOBAL"]
        )
    ]

    unicos, psaim_unicos = set(), set()
    unicos_finalizados = set()

    por_mes = {
        "valorizados": {},
        "pendientes": {},
        "ademinsac": {},
        "fiabilidad": {},
        "psaim": {},
    }
    detalle_pendientes = {}
    revision_fiabilidad = (
        revision_especialista_pendiente
    ) = revision_especialista = 0

    for _, fila in df_principales.iterrows():
        mes = texto_limpio(fila["MES"])
        codigo = texto_limpio(fila["CODIGO DE INFORME"])
        grupo = texto_limpio(fila["GRUPO DE TUBERÍAS"])
        observacion = texto_limpio(fila["OBSERVACIÓN"])
        estado_elab = texto_normalizado(fila["ESTADO - ELABORACIÓN "])
        clave = fila["CLAVE_GLOBAL"]
        if not mes or not grupo:
            continue
        if not es_codigo_provisional(codigo) and es_correccion_psaim(
            observacion
        ):
            clave_psaim = f"{mes}|{codigo}"
            if clave_psaim not in psaim_unicos:
                psaim_unicos.add(clave_psaim)
                por_mes["psaim"][mes] = por_mes["psaim"].get(mes, 0) + 1
        if clave in unicos:
            continue
        unicos.add(clave)

        if "FINALIZADO" in estado_elab or "100%" in estado_elab:
            unicos_finalizados.add(clave)

        for clave_mes in ["valorizados", "pendientes", "ademinsac", "fiabilidad"]:
            por_mes[clave_mes].setdefault(mes, 0)
        if texto_normalizado(fila["VALORIZACIÓN"]) == "SI":
            por_mes["valorizados"][mes] += 1
            continue
        por_mes["pendientes"][mes] += 1
        observacion_norm = texto_normalizado(observacion)
        if es_revision_fiabilidad(observacion):
            revision_fiabilidad += 1
        if "PENDIENTE REVISION POR EL ESPECIALISTA" in observacion_norm:
            revision_especialista_pendiente += 1

        if (
            "REV. POR EL ESPECIALISTA" in observacion_norm
            or "REVISION POR EL ESPECIALISTA" in observacion_norm
            or "REVISADO POR ESPECIALISTA" in observacion_norm
        ) and "PENDIENTE" not in observacion_norm:
            revision_especialista += 1

        if "ADEMINSAC" in observacion_norm:
            por_mes["ademinsac"][mes] += 1
        else:
            por_mes["fiabilidad"][mes] += 1
        etiqueta = "(En blanco)" if not observacion else observacion
        detalle_pendientes[(mes, etiqueta)] = (
            detalle_pendientes.get((mes, etiqueta), 0) + 1
        )

    total_inf_unicos = len(unicos)
    tot_finalizados = len(unicos_finalizados)
    tot_pendientes_elaborar = max(0, total_inf_unicos - tot_finalizados)

    tot_valorizados = sum(por_mes["valorizados"].values())

    def claves_principales(df_origen):
        return df_origen[df_origen["TIPO"] == "Principal"]["CLAVE_GLOBAL"].nunique()

    val_para_asignar = claves_principales(df_pend_asignacion)
    val_en_proceso = claves_principales(df_en_proceso)
    val_pend_inspeccion = claves_principales(df_pend_inspeccion)
    val_psaim = sum(por_mes["psaim"].values())

    kpis = {
        "total_inf_unicos": total_inf_unicos,
        "tot_finalizados": tot_finalizados,
        "tot_pendientes_elaborar": tot_pendientes_elaborar,
        "tot_valorizados": tot_valorizados,
        "val_para_asignar": val_para_asignar,
        "val_en_proceso": val_en_proceso,
        "val_pend_inspeccion": val_pend_inspeccion,
        "val_psaim": val_psaim,
        "revision_especialista": revision_especialista,
        "revision_especialista_pendiente": revision_especialista_pendiente,
        "revision_fiabilidad": revision_fiabilidad,
        "anexos_total": anexos_total,
        "anexos_pend_inspeccion": anexos_pend_inspeccion,
        "anexos_entregados": anexos_total - anexos_pend_inspeccion,
        "anexos_valorizados": anexos_valorizados,
    }

    return (
        mascara_retirado,
        df_activos,
        df_psaim,
        df_pend_inspeccion,
        df_pend_asignacion,
        df_en_proceso,
        kpis,
        detalle_pendientes,
    )


(
    mascara_retirado,
    df_activos,
    df_psaim,
    df_pend_inspeccion,
    df_pend_asignacion,
    df_en_proceso,
    kpis,
    detalle_pendientes,
) = procesar_agrupaciones_y_kpis(df)

meses_con_datos = {texto_normalizado(m) for m in df_activos["MES"]}
cabecera.markdown(
    html_cabecera(
        kpis["tot_finalizados"],
        kpis["total_inf_unicos"],
        next((m for m in reversed(ORDEN_MESES) if m in meses_con_datos), None),
    ),
    unsafe_allow_html=True,
)


def estilo_tono(color):
    tono = TONOS[color]
    return (
        f"--tone:{tono};--tone-bg:{tinte(tono, 0.12)};"
        f"--tone-borde:{tinte(tono, 0.45)}"
    )


def item_kpi(titulo, valor, color, alerta=False):
    # Los pendientes con valor mayor que cero se resaltan con fondo teñido.
    clase = "kpi-item alerta" if alerta and valor else "kpi-item"
    return (
        f"<div class='{clase}' style='{estilo_tono(color)}'>"
        f"<div class='kpi-item-label'><span class='kpi-dot'></span>{titulo}</div>"
        f"<div class='kpi-item-value'>{valor}</div>"
        "</div>"
    )


def bloque_kpi(titulo_bloque, icono, color, items):
    filas = "".join(item_kpi(*i) for i in items)
    return (
        "<div class='kpi-block-card'>"
        f"<div class='kpi-block-head' style='{estilo_tono(color)}'>"
        f"<div class='kpi-block-icon'>{ICONOS[icono]}</div>"
        f"<div class='kpi-block-title'>{titulo_bloque}</div></div>"
        f"<div class='kpi-items'>{filas}</div></div>"
    )


panel_control = st.container(key="panel_control")
panel_control.markdown(
    "<div class='section-title'>Panel de control de informes</div>",
    unsafe_allow_html=True,
)

bloques_html = "".join([
    bloque_kpi(
        "General",
        "grafico", "azul",
        [
            ("Informes totales", kpis["total_inf_unicos"], "azul"),
            ("Informes finalizados", kpis["tot_finalizados"], "verde"),
            ("Pendientes elaborar", kpis["tot_pendientes_elaborar"], "naranja", True),
        ],
    ),
    bloque_kpi(
        "Gabinete",
        "carpeta", "violeta",
        [
            ("En proceso", kpis["val_en_proceso"], "violeta"),
            ("Pend. asignar", kpis["val_para_asignar"], "rosa"),
            ("Correc. PSAIM", kpis["val_psaim"], "dorado"),
        ],
    ),
    bloque_kpi(
        "Especialista",
        "especialista", "turquesa",
        [
            ("Revisados", kpis["revision_especialista"], "turquesa"),
            (
                "Por revisar",
                kpis["revision_especialista_pendiente"],
                "indigo",
                True,
            ),
        ],
    ),
    bloque_kpi(
        "Campo",
        "campo", "rojo",
        [
            ("Pend. inspección", kpis["val_pend_inspeccion"], "rojo", True),
        ],
    ),
    bloque_kpi(
        "Cliente",
        "cliente", "verde",
        [
            ("Valorizados", kpis["tot_valorizados"], "verde"),
            ("En revisión", kpis["revision_fiabilidad"], "turquesa"),
        ],
    ),
    bloque_kpi(
        "Anexos",
        "anexo", "dorado",
        [
            ("Total anexos", kpis["anexos_total"], "azul"),
            ("Pend. inspección", kpis["anexos_pend_inspeccion"], "rojo", True),
            ("Entregados", kpis["anexos_entregados"], "verde"),
            ("Valorizados", kpis["anexos_valorizados"], "verde"),
        ],
    ),
])

panel_control.markdown(
    f"<div class='kpi-row'>{bloques_html}</div>", unsafe_allow_html=True
)

solicitudes_activas = [
    solicitud
    for solicitud in cargar_solicitudes()
    if solicitud["estado"] == "PENDIENTE"
]

sistema_control = st.container(key="sistema_control")
sistema_control.markdown(
    "<div class='section-title'>Sistema de control y resúmenes</div>",
    unsafe_allow_html=True,
)

tabs = sistema_control.tabs([
    f"Admin ({len(solicitudes_activas)})",
    "Tabla general",
    "Pend. asignar",
    "En proceso",
    "Pend. inspección",
    "Rev. fiabilidad",
    "Revisión especialista",
    "Correc. PSAIM",
    "Resumen por mes",
    "Carga por responsable",
])

# 1. ADMIN
with tabs[0]:

    @st.fragment
    def vista_admin():
        st.subheader("Bandeja de aprobación")
        sols = [s for s in cargar_solicitudes() if s["estado"] == "PENDIENTE"]
        if not sols:
            st.success(
                "No hay solicitudes pendientes.", icon=":material/check_circle:"
            )
        for solicitud in sols:
            with st.container(border=True):
                informacion, aprobar, rechazar = st.columns(
                    [5, 1, 1], vertical_alignment="center"
                )
                informacion.write(
                    f"**{solicitud['tipo']}**  \nCódigo: `{solicitud['codigo']}`"
                    f" | Grupo: `{solicitud['grupo']}` | Solicitante:"
                    f" {solicitud['solicitante']}"
                )
                if aprobar.button(
                    "Aprobar",
                    key=f"aprobar_{solicitud['id']}",
                    icon=":material/check:",
                ):
                    mascara_base = (
                        df["CODIGO DE INFORME"]
                        == normalizar_codigo_informe(solicitud["codigo"])
                    ) & (df["GRUPO DE TUBERÍAS"] == solicitud["grupo"])

                    if solicitud["tipo"] == "INFORME COMPLETADO (GABINETE)":
                        mascara_no_retirado = mascara_base & ~mascara_retirado
                        df.loc[mascara_no_retirado, "ESTADO - ELABORACIÓN "] = (
                            "Finalizado"
                        )
                        df.loc[mascara_no_retirado, "OBSERVACIÓN"] = (
                            "Pendiente revisión por el especialista - Ademinsac"
                        )
                    elif solicitud["tipo"] == "CORRECCIÓN PSAIM":
                        df.loc[mascara_base, "OBSERVACIÓN"] = "PSAIM CORREGIDO"
                        df.loc[mascara_base, "ESTADO - ELABORACIÓN "] = (
                            "En proceso"
                        )
                    elif solicitud["tipo"] == "REVISIÓN ESPECIALISTA":
                        df.loc[mascara_base, "OBSERVACIÓN"] = (
                            "INFORME REVISADO POR ESPECIALISTA"
                        )

                    solicitudes = cargar_solicitudes()
                    for item in solicitudes:
                        if item["id"] == solicitud["id"]:
                            item["estado"] = "APROBADO"
                    guardar_solicitudes(solicitudes)
                    st.session_state.df_data = normalizar_base(df)
                    guardar_datos(st.session_state.df_data)
                    st.rerun()
                if rechazar.button(
                    "Rechazar",
                    key=f"rechazar_{solicitud['id']}",
                    icon=":material/close:",
                ):
                    solicitudes = cargar_solicitudes()
                    for item in solicitudes:
                        if item["id"] == solicitud["id"]:
                            item["estado"] = "RECHAZADO"
                    guardar_solicitudes(solicitudes)
                    st.rerun()

    vista_admin()

# 2. TABLA GENERAL
with tabs[1]:

    @st.fragment
    def vista_tabla_general():
        filtros = st.columns([1, 1, 2])
        meses = ["Todos"] + sorted(
            {texto_limpio(m).upper() for m in df["MES"] if texto_limpio(m)},
            key=lambda m: ORDEN_MESES.index(m) if m in ORDEN_MESES else 99,
        )
        mes = filtros[0].selectbox("Filtrar mes", meses)
        alcance = filtros[1].selectbox(
            "Alcance del servicio", ["Todos", "LINEAS", "VT-CIRCUITOS"]
        )
        consulta = filtros[2].text_input(
            "Buscar por líneas, código, grupo, SAP, notas o alcance extendido",
            icon=":material/search:",
        )

        df_vista = df.copy()
        if mes != "Todos":
            df_vista = df_vista[
                df_vista["MES"].apply(lambda v: texto_normalizado(v) == mes)
            ]
        if alcance != "Todos":
            df_vista = df_vista[
                df_vista["ALCANCE DEL SERVICIO"].apply(texto_normalizado)
                == alcance
            ]
        if consulta.strip():
            consulta_norm = texto_normalizado(consulta)
            columnas_busqueda = [
                "LINEAS",
                "CODIGO DE INFORME",
                "GRUPO DE TUBERÍAS",
                "SAP",
                "NOTAS",
                "ALCANCE DEL SERVICIO",
            ]
            mascara_busqueda = df_vista[columnas_busqueda].apply(
                lambda fila: any(
                    consulta_norm in texto_normalizado(v) for v in fila
                ),
                axis=1,
            )
            df_vista = df_vista[mascara_busqueda]

        df_vista = df_vista.map(texto_limpio)
        df_vista["VALORIZACIÓN"] = df_vista["VALORIZACIÓN"].apply(
            lambda v: (
                "SI"
                if texto_normalizado(v) == "SI"
                else (
                    "Retirado"
                    if texto_normalizado(v) == "RETIRADO"
                    else "Pendiente"
                )
            )
        )
        df_vista.insert(0, "SEÑAL", df_vista.apply(senal_visual, axis=1))

        encabezados = {
            "SEÑAL": st.column_config.TextColumn(
                "Señal", width=190, disabled=True, pinned=True
            ),
            "ITEM POR MES": st.column_config.TextColumn("Item", width=70),
            "IT2": st.column_config.TextColumn("IT2", width=55),
            "UNIDAD": st.column_config.TextColumn("Unidad", width=65),
            "MES": st.column_config.TextColumn("Mes", width=80),
            "LINEAS": st.column_config.TextColumn("Líneas", width=180),
            "CODIGO DE INFORME": st.column_config.TextColumn(
                "Código de informe", width=190
            ),
            "GRUPO DE TUBERÍAS": st.column_config.TextColumn(
                "Grupo de tuberías", width=180
            ),
            "SAP": st.column_config.TextColumn("SAP", width=85),
            "ALCANCE DEL SERVICIO": st.column_config.TextColumn(
                "Alcance", width=120
            ),
            "NOTAS": st.column_config.TextColumn("Notas", width=170),
            "ESTADO - ELABORACIÓN ": st.column_config.TextColumn(
                "Estado de elaboración", width=190
            ),
            "RESPONSABLE": st.column_config.TextColumn(
                "Responsable", width=135
            ),
            "OBSERVACIÓN": st.column_config.TextColumn(
                "Observación", width=280
            ),
            "VALORIZACIÓN": st.column_config.SelectboxColumn(
                "Valorización",
                options=["Pendiente", "SI", "Retirado"],
                required=True,
                width=145,
            ),
        }

        st.html("""
            <div style="background-color: #162739; border: 1px solid #26405A; padding: 8px 14px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; color: #C9D6E3; margin-bottom: 10px; display: inline-block;">
                🟢 Valorizado (SI) &nbsp;&nbsp;|&nbsp;&nbsp; 🟡 Pendiente de inspección o falta carpeta &nbsp;&nbsp;|&nbsp;&nbsp; 🔵 Inspección complementaria &nbsp;&nbsp;|&nbsp;&nbsp; 🔴 Retirado
            </div>
        """)

        with st.expander(
            "⚡ Valorización masiva por Código de Informe", expanded=False
        ):
            col_cod, col_est, col_btn = st.columns(
                [3, 2, 1], vertical_alignment="bottom"
            )

            codigos_disponibles = sorted([
                c
                for c in df["CODIGO DE INFORME"].unique()
                if c and str(c) != "-" and not es_codigo_provisional(c)
            ])

            codigo_sel = col_cod.selectbox(
                "Seleccionar Código de Informe",
                codigos_disponibles,
                key="val_masiva_cod",
            )
            estado_sel = col_est.selectbox(
                "Estado a aplicar", ["SI", "Pendiente"], key="val_masiva_est"
            )

            if col_btn.button(
                "Aplicar a todo", icon=":material/done_all:", type="primary"
            ):
                mascara_objetivo = (
                    df["CODIGO DE INFORME"] == codigo_sel
                ) & ~mascara_retirado

                df.loc[mascara_objetivo, "VALORIZACIÓN"] = estado_sel
                if estado_sel == "SI":
                    df.loc[mascara_objetivo, "OBSERVACIÓN"] = ""

                st.session_state.df_data = normalizar_base(df)
                guardar_datos(st.session_state.df_data)
                st.toast(
                    f"Valorización actualizada a '{estado_sel}' para"
                    f" {codigo_sel}",
                    icon="✅",
                )
                st.rerun()

        boton_descarga_excel(
            df_vista, "Tabla_general_informes.xlsx", "Descargar tabla general"
        )

        # Texto rojo en la señal de las filas retiradas (Streamlit solo aplica
        # estilos a columnas no editables, y "SEÑAL" es la única).
        df_estilo = df_vista.style.map(
            lambda v: (
                f"color: {TONOS['rojo']}; font-weight: 600"
                if "RETIRADO" in texto_normalizado(v)
                else ""
            ),
            subset=["SEÑAL"],
        )
        editado = st.data_editor(
            df_estilo,
            column_config=encabezados,
            hide_index=True,
            width="stretch",
            height=600,
            disabled=["SEÑAL"],
            key="editor_tabla_general",
        )

        if st.button(
            "Guardar cambios",
            key="guardar_tabla",
            icon=":material/save:",
            type="primary",
        ):
            df_actualizado = editado.drop(columns=["SEÑAL"], errors="ignore")
            df_actualizado = df_actualizado.fillna("")
            df_actualizado = df_actualizado.replace(
                ["None", "none", "NONE", None], ""
            )

            mascara_si = df_actualizado["VALORIZACIÓN"].apply(
                lambda x: texto_normalizado(x) == "SI"
            )
            df_actualizado.loc[mascara_si, "OBSERVACIÓN"] = ""

            st.session_state.df_data.update(df_actualizado)
            st.cache_data.clear()
            guardar_datos(st.session_state.df_data)
            st.toast("¡Cambios guardados con éxito!", icon="💾")
            st.rerun()

    vista_tabla_general()


# AUXILIARES PARA AGRUPACIÓN DE TABLAS
def ordenar_por_mes(tabla):
    # Tablas de resumen en orden cronológico (enero a diciembre); dentro de
    # cada mes, primero los informes principales y después los anexos.
    if "MES" not in tabla.columns:
        return tabla
    claves = {
        "_MES": tabla["MES"].apply(
            lambda v: (
                ORDEN_MESES.index(texto_normalizado(v))
                if texto_normalizado(v) in ORDEN_MESES
                else 99
            )
        )
    }
    if "TIPO" in tabla.columns:
        claves["_ANEXO"] = tabla["TIPO"] == "Anexo"
    return (
        tabla.assign(**claves)
        .sort_values(list(claves), kind="stable")
        .drop(columns=list(claves))
    )


def tabla_agrupada(df_origen, columnas, nombre_archivo, nombre_hoja):
    if df_origen.empty:
        st.info("No hay registros para mostrar.", icon=":material/info:")
        return pd.DataFrame()
    if "TIPO" in df_origen.columns and "TIPO" not in columnas:
        columnas = ["TIPO"] + list(columnas)
    tabla = (
        df_origen.groupby(columnas, as_index=False, dropna=False)
        .agg(LINEAS=("LINEAS", "count"))
        .fillna("")
    )
    tabla = ordenar_por_mes(tabla)
    tabla.index = range(1, len(tabla) + 1)
    boton_descarga_excel(tabla, nombre_archivo, "Descargar Excel")
    tabla_html(tabla)
    return tabla


def mostrar_resumen(df_resumen, nombre_archivo, es_metricas=False):
    if df_resumen.empty:
        st.info("No hay registros para mostrar.", icon=":material/info:")
        return

    df_mostrar = df_resumen.copy()
    if es_metricas:
        tot_informes = df_mostrar["TOTAL INFORMES"].sum()
        tot_elaborados = df_mostrar["INFORMES ELABORADOS"].sum()
        tot_pendientes = df_mostrar["PENDIENTES POR ELABORAR"].sum()
        pct_total = (
            (tot_elaborados / tot_informes * 100) if tot_informes > 0 else 0.0
        )

        fila_total = pd.DataFrame({
            "MES": ["TOTAL"],
            "TOTAL INFORMES": [tot_informes],
            "INFORMES ELABORADOS": [tot_elaborados],
            "PENDIENTES POR ELABORAR": [tot_pendientes],
            "% AVANCE ELABORACIÓN": [f"{pct_total:.1f}%"],
        })
        df_mostrar["% AVANCE ELABORACIÓN"] = df_mostrar[
            "% AVANCE ELABORACIÓN"
        ].apply(
            lambda v: (
                f"{v:.1f}%" if isinstance(v, (int, float)) else str(v)
            )
        )
        df_mostrar = pd.concat([df_mostrar, fila_total], ignore_index=True)
    elif "CANTIDAD" in df_mostrar.columns:
        tot_cantidad = df_mostrar["CANTIDAD"].sum()
        fila_total = pd.DataFrame({
            "MES": ["TOTAL"],
            "OBSERVACIÓN PENDIENTE": ["-"],
            "CANTIDAD": [tot_cantidad],
        })
        df_mostrar = pd.concat([df_mostrar, fila_total], ignore_index=True)

    df_mostrar.index = range(1, len(df_mostrar) + 1)
    boton_descarga_excel(df_mostrar, nombre_archivo, "Descargar Excel")
    tabla_html(df_mostrar)


# 3. PENDIENTE ASIGNAR
with tabs[2]:
    tabla_agrupada(
        df_pend_asignacion,
        [
            "MES",
            "ESTADO - ELABORACIÓN ",
            "RESPONSABLE",
            "GRUPO DE TUBERÍAS",
            "CODIGO DE INFORME",
        ],
        "Pendientes_asignar.xlsx",
        "PEND_ASIGNAR",
    )

# 4. EN PROCESO
with tabs[3]:

    @st.fragment
    def vista_en_proceso():
        tabla_proceso = tabla_agrupada(
            df_en_proceso,
            [
                "MES",
                "ESTADO - ELABORACIÓN ",
                "RESPONSABLE",
                "GRUPO DE TUBERÍAS",
                "CODIGO DE INFORME",
            ],
            "En_proceso.xlsx",
            "EN_PROCESO",
        )
        if not tabla_proceso.empty:
            responsables = sorted(
                set(
                    PERSONAL_LISTA_BASE
                    + [
                        texto_limpio(valor)
                        for valor in df["RESPONSABLE"]
                        if texto_limpio(valor)
                    ]
                )
            )
            codigo, inspector, enviar = st.columns(
                [2, 2, 1], vertical_alignment="bottom"
            )
            codigo_seleccionado = codigo.selectbox(
                "Código",
                tabla_proceso["CODIGO DE INFORME"].unique(),
                key="proceso_codigo",
            )
            inspector_seleccionado = inspector.selectbox(
                "Inspector", responsables, key="proceso_inspector"
            )
            if enviar.button("Enviar al 100%", icon=":material/send:"):
                grupo = tabla_proceso.loc[
                    tabla_proceso["CODIGO DE INFORME"] == codigo_seleccionado,
                    "GRUPO DE TUBERÍAS",
                ].iloc[0]
                correcto, mensaje = registrar_solicitud(
                    "INFORME COMPLETADO (GABINETE)",
                    codigo_seleccionado,
                    grupo,
                    inspector_seleccionado,
                )
                if correcto:
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.warning(mensaje)

    vista_en_proceso()

# 5. PENDIENTE INSPECCIÓN
def tabla_pend_inspeccion_por_informe(df_origen, df_todas):
    # Una fila por informe (igual que el KPI "Pend. inspección"): un informe
    # avanzado de forma parcial tiene líneas en distintos estados.
    if df_origen.empty:
        st.info("No hay registros para mostrar.", icon=":material/info:")
        return

    def unir(valores):
        return " / ".join(dict.fromkeys(v for v in map(texto_limpio, valores) if v))

    tabla = (
        df_origen.assign(
            PEND=df_origen["ESTADO - ELABORACIÓN "]
            .apply(texto_normalizado)
            .str.contains("PENDIENTE INSPECCION")
        )
        .groupby("CLAVE_GLOBAL", sort=False)
        .agg(**{
            "TIPO": ("TIPO", "first"),
            "MES": ("MES", "first"),
            "CODIGO DE INFORME": ("CODIGO DE INFORME", "first"),
            "GRUPO DE TUBERÍAS": ("GRUPO DE TUBERÍAS", unir),
            "ESTADO - ELABORACIÓN ": ("ESTADO - ELABORACIÓN ", unir),
            "RESPONSABLE": ("RESPONSABLE", unir),
            "LINEAS SIN INSPECCIONAR": ("PEND", "sum"),
        })
    )
    # Total de líneas del informe, incluidas las que ya no están pendientes.
    tabla.insert(
        len(tabla.columns) - 1,
        "LINEAS",
        df_todas.groupby("CLAVE_GLOBAL")["LINEAS"].count().reindex(tabla.index),
    )
    tabla = tabla.reset_index(drop=True)
    tabla = ordenar_por_mes(tabla)
    tabla["LINEAS SIN INSPECCIONAR"] = tabla["LINEAS SIN INSPECCIONAR"].astype(int)
    tabla.index = range(1, len(tabla) + 1)
    principales = (tabla["TIPO"] == "Principal").sum()
    boton_descarga_excel(tabla, "Pendientes_inspeccion.xlsx", "Descargar Excel")
    tabla_html(
        tabla,
        nota=f"{principales} informes principales y {len(tabla) - principales}"
        " anexos pendientes de inspección.",
    )


with tabs[4]:
    tabla_pend_inspeccion_por_informe(df_pend_inspeccion, df_activos)

# 6. REV. FIABILIDAD
with tabs[5]:
    df_fiabilidad = df_activos[
        df_activos["OBSERVACIÓN"].apply(es_revision_fiabilidad)
    ]
    tabla_agrupada(
        df_fiabilidad,
        [
            "MES",
            "ESTADO - ELABORACIÓN ",
            "RESPONSABLE",
            "GRUPO DE TUBERÍAS",
            "CODIGO DE INFORME",
            "OBSERVACIÓN",
        ],
        "Revision_fiabilidad.xlsx",
        "REV_FIABILIDAD",
    )


# 7. REVISIÓN ESPECIALISTA
def vista_revision_especialista(condicion, archivo, llave):
    df_revision = df_activos[df_activos["OBSERVACIÓN"].apply(condicion)]
    tabla_revision = tabla_agrupada(
        df_revision,
        [
            "MES",
            "ESTADO - ELABORACIÓN ",
            "RESPONSABLE",
            "GRUPO DE TUBERÍAS",
            "CODIGO DE INFORME",
            "OBSERVACIÓN",
        ],
        archivo,
        llave,
    )
    if tabla_revision.empty:
        return
    codigo, especialista, enviar = st.columns(
        [2, 2, 1], vertical_alignment="bottom"
    )
    codigo_seleccionado = codigo.selectbox(
        "Código",
        tabla_revision["CODIGO DE INFORME"].unique(),
        key=f"codigo_{llave}",
    )
    especialista_seleccionado = especialista.selectbox(
        "Especialista", ESPECIALISTAS_LISTA, key=f"especialista_{llave}"
    )
    if enviar.button(
        "Enviar a revisión", key=f"enviar_{llave}", icon=":material/send:"
    ):
        grupo = tabla_revision.loc[
            tabla_revision["CODIGO DE INFORME"] == codigo_seleccionado,
            "GRUPO DE TUBERÍAS",
        ].iloc[0]
        correcto, mensaje = registrar_solicitud(
            "REVISIÓN ESPECIALISTA",
            codigo_seleccionado,
            grupo,
            especialista_seleccionado,
        )
        if correcto:
            st.success(mensaje)
            st.rerun()
        else:
            st.warning(mensaje)


with tabs[6]:
    st.subheader("Revisión especialista")

    @st.fragment
    def vista_sub_especialista():
        opcion_especialista = st.radio(
            "Seleccionar tipo de vista:",
            ["Pendientes de revisión", "Revisados por el especialista"],
            horizontal=True,
            key="radio_especialistas",
        )
        if opcion_especialista == "Pendientes de revisión":
            vista_revision_especialista(
                lambda valor: "PENDIENTE REVISION POR EL ESPECIALISTA"
                in texto_normalizado(valor),
                "Pendientes_revision_especialista.xlsx",
                "PEND_REV_ESP",
            )
        else:
            vista_revision_especialista(
                lambda valor: (
                    "REV. POR EL ESPECIALISTA" in texto_normalizado(valor)
                    or "REVISION POR EL ESPECIALISTA"
                    in texto_normalizado(valor)
                    or "REVISADO POR ESPECIALISTA" in texto_normalizado(valor)
                )
                and "PENDIENTE" not in texto_normalizado(valor),
                "Revision_por_especialista.xlsx",
                "REV_POR_ESP",
            )

    vista_sub_especialista()

# 8. CORRECCIÓN PSAIM
with tabs[7]:

    @st.fragment
    def vista_correc_psaim():
        df_psaim_lineas = df_psaim[
            df_psaim["ALCANCE DEL SERVICIO"].apply(texto_normalizado)
            == "LINEAS"
        ].copy()
        columnas_psaim = [
            "MES",
            "ESTADO - ELABORACIÓN ",
            "RESPONSABLE",
            "ITEM POR MES",
            "IT2",
            "LINEAS",
            "GRUPO DE TUBERÍAS",
            "CODIGO DE INFORME",
            "NOTAS",
            "OBSERVACIÓN",
        ]
        tabla_psaim = tabla_agrupada(
            df_psaim_lineas,
            columnas_psaim[:-3]
            + ["CODIGO DE INFORME", "NOTAS", "OBSERVACIÓN"],
            "Correccion_PSAIM.xlsx",
            "CORRECCION_PSAIM",
        )
        if not tabla_psaim.empty:
            codigo, revisor, enviar = st.columns(
                [2, 2, 1], vertical_alignment="bottom"
            )
            codigo_seleccionado = codigo.selectbox(
                "Código",
                tabla_psaim["CODIGO DE INFORME"].unique(),
                key="psaim_codigo",
            )
            revisor_seleccionado = revisor.selectbox(
                "Revisor PSAIM", REVISORES_PSAIM_LISTA, key="psaim_revisor"
            )
            if enviar.button("PSAIM corregido", icon=":material/check_circle:"):
                grupo = tabla_psaim.loc[
                    tabla_psaim["CODIGO DE INFORME"] == codigo_seleccionado,
                    "GRUPO DE TUBERÍAS",
                ].iloc[0]
                correcto, mensaje = registrar_solicitud(
                    "CORRECCIÓN PSAIM",
                    codigo_seleccionado,
                    grupo,
                    revisor_seleccionado,
                )
                if correcto:
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.warning(mensaje)

    vista_correc_psaim()


# 9. RESUMEN POR MES
@st.cache_data(show_spinner=False)
def generar_resumenes_mes(df_activos_input, detalle_pendientes_input):
    filas_elaboracion = []
    meses_unicos = sorted(
        set(df_activos_input["MES"].apply(texto_limpio)),
        key=lambda m: (
            ORDEN_MESES.index(m.upper()) if m.upper() in ORDEN_MESES else 99
        ),
    )

    df_principales_input = df_activos_input[
        df_activos_input["TIPO"] == "Principal"
    ]
    for mes in meses_unicos:
        if not mes:
            continue
        df_mes = df_principales_input[
            df_principales_input["MES"].apply(lambda v: texto_limpio(v) == mes)
        ]
        df_mes_unicos = df_mes.drop_duplicates(subset=["CLAVE_GLOBAL"])
        total_informes = len(df_mes_unicos)

        elaborados = len(
            df_mes_unicos[
                df_mes_unicos["ESTADO - ELABORACIÓN "].apply(
                    lambda v: (
                        "FINALIZADO" in texto_normalizado(v)
                        or "100%" in texto_normalizado(v)
                    )
                )
            ]
        )
        pendientes_elaborar = total_informes - elaborados
        porcentaje = (
            round((elaborados / total_informes * 100), 1)
            if total_informes > 0
            else 0.0
        )

        filas_elaboracion.append({
            "MES": mes,
            "TOTAL INFORMES": total_informes,
            "INFORMES ELABORADOS": elaborados,
            "PENDIENTES POR ELABORAR": pendientes_elaborar,
            "% AVANCE ELABORACIÓN": porcentaje,
        })

    df_metricas_elaboracion = pd.DataFrame(filas_elaboracion)

    df_t4 = pd.DataFrame([
        {"MES": mes, "OBSERVACIÓN PENDIENTE": observacion, "CANTIDAD": cantidad}
        for (mes, observacion), cantidad in detalle_pendientes_input.items()
    ])
    if not df_t4.empty:
        df_t4["ORDEN"] = df_t4["MES"].apply(
            lambda valor: (
                ORDEN_MESES.index(texto_normalizado(valor))
                if texto_normalizado(valor) in ORDEN_MESES
                else 99
            )
        )
        df_t4 = df_t4.sort_values(
            ["ORDEN", "CANTIDAD"], ascending=[True, False]
        ).drop(columns="ORDEN")

    return df_metricas_elaboracion, df_t4


df_metricas_elaboracion, df_t4 = generar_resumenes_mes(
    df_activos, detalle_pendientes
)

with tabs[8]:
    st.subheader("Resumen por mes")

    @st.fragment
    def vista_sub_resumen():
        opcion_resumen = st.radio(
            "Seleccionar tipo de vista:",
            ["Métricas por mes", "Detalle pendientes por mes / observación"],
            horizontal=True,
            key="radio_resumen",
        )
        if opcion_resumen == "Métricas por mes":
            mostrar_resumen(
                df_metricas_elaboracion,
                "Metricas_Elaboracion_Por_Mes.xlsx",
                es_metricas=True,
            )
        else:
            mostrar_resumen(
                df_t4, "Pendientes_mes_observacion_T4.xlsx", es_metricas=False
            )

    vista_sub_resumen()


# 10. CARGA POR RESPONSABLE
UMBRAL_SATURADO = 5  # informes en proceso a partir de los cuales se marca "Saturado"
ETAPAS_CARGA = {
    "proc": ("En proceso", "violeta"),
    "esp": ("Por revisar especialista", "naranja"),
    "rev": ("Revisado especialista", "rosa"),
    "cli": ("En revisión cliente", "turquesa"),
    "insp": ("Pend. inspección", "rojo"),
    "otro": ("Otros", "dorado"),
    "val": ("Valorizado", "verde"),
}


@st.cache_data(show_spinner=False)
def informes_por_responsable(df_activos_input):
    # Un registro por informe principal (como los KPIs), con la etapa en la
    # que está y su responsable (quien lo elabora).
    principales = df_activos_input[df_activos_input["TIPO"] == "Principal"]
    if principales.empty:
        return pd.DataFrame(
            columns=["RESPONSABLE", "MES", "CODIGO DE INFORME", "GRUPO DE TUBERÍAS", "ETAPA"]
        )
    claves_inspeccion = set(
        principales.loc[
            principales.apply(es_pendiente_inspeccion, axis=1), "CLAVE_GLOBAL"
        ]
    )
    filas = []
    for clave, grupo in principales.groupby("CLAVE_GLOBAL", sort=False):
        fila = grupo.iloc[0]
        estado = texto_normalizado(fila["ESTADO - ELABORACIÓN "])
        observacion = texto_normalizado(fila["OBSERVACIÓN"])
        if clave in claves_inspeccion:
            etapa = "insp"
        elif "EN PROCESO" in estado:
            etapa = "proc"
        elif texto_normalizado(fila["VALORIZACIÓN"]) == "SI":
            etapa = "val"
        elif "PENDIENTE REVISION POR EL ESPECIALISTA" in observacion:
            etapa = "esp"
        elif es_revision_fiabilidad(observacion):
            etapa = "cli"
        elif "REVISADO POR ESPECIALISTA" in observacion:
            etapa = "rev"
        else:
            etapa = "otro"
        codigo = texto_limpio(fila["CODIGO DE INFORME"])
        filas.append({
            "RESPONSABLE": texto_limpio(fila["RESPONSABLE"]) or "Sin asignar",
            "MES": texto_limpio(fila["MES"]).upper(),
            "CODIGO DE INFORME": (
                "Pendiente Asignar Código" if es_codigo_provisional(codigo) else codigo
            ),
            "GRUPO DE TUBERÍAS": texto_limpio(fila["GRUPO DE TUBERÍAS"]),
            "ETAPA": etapa,
        })
    return pd.DataFrame(filas)


def barras_carga(conteo, activos, orden_personas):
    maximo = max(1, int(conteo.sum(axis=1).max()))
    filas = []
    for persona in orden_personas:
        # Cada tramo lleva su número dentro para leer la cantidad por etapa.
        segmentos = "".join(
            f"<span class='carga-seg' title='{ETAPAS_CARGA[e][0]}: {int(n)}'"
            f" style='width:{n / maximo * 100:.2f}%;background:"
            f"{TONOS[ETAPAS_CARGA[e][1]]}'>{int(n)}</span>"
            for e in ETAPAS_CARGA
            if e in conteo.columns and (n := conteo.at[persona, e]) > 0
        )
        en_proceso = int(conteo.at[persona, "proc"]) if "proc" in conteo.columns else 0
        saturado = (
            "<span class='chip-saturado'>Saturado</span>"
            if en_proceso >= UMBRAL_SATURADO
            else ""
        )
        clase = "carga-fila sin-asignar" if persona == "Sin asignar" else "carga-fila"
        filas.append(
            f"<div class='{clase}'>"
            f"<span class='carga-nombre'>{html.escape(persona)}</span>"
            f"<span class='carga-barra'>{segmentos}</span>"
            f"<span class='carga-total'>{saturado}<b>{int(activos.get(persona, 0))}</b>"
            f" activos · {int(conteo.loc[persona].sum())}</span></div>"
        )
    leyenda = "".join(
        f"<span class='carga-leyenda-item'><span class='kpi-dot' style='--tone:"
        f"{TONOS[color]}'></span>{nombre}</span>"
        for clave, (nombre, color) in ETAPAS_CARGA.items()
        if clave in conteo.columns
    )
    return (
        f"<div class='carga-leyenda'>{leyenda}</div>"
        f"<div class='carga-lista'>{''.join(filas)}</div>"
    )


with tabs[9]:

    @st.fragment
    def vista_carga_responsable():
        df_carga = informes_por_responsable(df_activos)
        if df_carga.empty:
            st.info("No hay registros para mostrar.", icon=":material/info:")
            return

        filtros = st.columns([1, 1, 2], vertical_alignment="bottom")
        meses = ["Todos"] + sorted(
            set(df_carga["MES"]) - {""},
            key=lambda m: ORDEN_MESES.index(m) if m in ORDEN_MESES else 99,
        )
        mes = filtros[0].selectbox("Filtrar mes", meses, key="carga_mes")
        con_valorizados = filtros[1].toggle(
            "Incluir valorizados", value=True, key="carga_valorizados"
        )

        datos = df_carga if mes == "Todos" else df_carga[df_carga["MES"] == mes]
        if datos.empty:
            st.info("No hay informes en este mes.", icon=":material/info:")
            return
        visibles = datos if con_valorizados else datos[datos["ETAPA"] != "val"]

        etapas = datos["ETAPA"].value_counts()
        sin_asignar = int((datos["RESPONSABLE"] == "Sin asignar").sum())
        tarjetas = "".join([
            item_kpi("En proceso", int(etapas.get("proc", 0)), "violeta"),
            item_kpi(
                "Esperando especialista", int(etapas.get("esp", 0)), "naranja", True
            ),
            item_kpi(
                "En revisión cliente",
                int(etapas.get("cli", 0) + etapas.get("rev", 0)),
                "turquesa",
            ),
            item_kpi("Sin asignar", sin_asignar, "rojo", True),
        ])
        st.html(f"<div class='carga-tarjetas'>{tarjetas}</div>")

        if visibles.empty:
            st.info("Todos los informes de este filtro están valorizados.")
            return
        conteo = pd.crosstab(visibles["RESPONSABLE"], visibles["ETAPA"])
        activos = datos[datos["ETAPA"] != "val"].groupby("RESPONSABLE").size()
        orden_personas = sorted(
            conteo.index,
            key=lambda p: (
                p == "Sin asignar",
                -int(activos.get(p, 0)),
                -int(conteo.loc[p].sum()),
            ),
        )
        st.html(
            "<div class='carga-panel'><div class='carga-titulo'>Informes por"
            f" persona</div>{barras_carga(conteo, activos, orden_personas)}</div>"
        )

        persona = st.selectbox(
            "Ver informes de", orden_personas, key="carga_persona"
        )
        detalle = visibles[visibles["RESPONSABLE"] == persona].copy()
        detalle["ETAPA"] = detalle["ETAPA"].map(lambda e: ETAPAS_CARGA[e][0])
        detalle = ordenar_por_mes(
            detalle[["MES", "CODIGO DE INFORME", "GRUPO DE TUBERÍAS", "ETAPA"]]
        )
        detalle.index = range(1, len(detalle) + 1)
        boton_descarga_excel(
            detalle, f"Carga_{persona.replace(' ', '_')}.xlsx", "Descargar Excel"
        )
        tabla_html(detalle, nota=f"{len(detalle)} informes de {persona}.")

    vista_carga_responsable()
