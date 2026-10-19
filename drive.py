"""Acceso a Google Drive para las páginas adicionales (misma carpeta que app.py)."""

import io
import time

import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

FOLDER_ID = "1gUyx6PbtLd7tG_C20x00CVmVdF0oYm_8"


@st.cache_resource
def conectar_drive():
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds_dict["private_key"] = (
            creds_dict["private_key"].replace("\\n", "\n").replace("\r\n", "\n")
        )
        credentials = Credentials.from_service_account_info(
            creds_dict, scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=credentials)
    except Exception as e:
        st.error(f"Error al conectar con Google Drive: {e}")
        return None


def _reintentable(error, intento, max_reintentos):
    msg = str(error)
    return (
        "RECORD_LAYER_FAILURE" in msg or "SSL" in msg or "Connection" in msg
    ) and intento < max_reintentos


def _buscar(servicio, nombre, campos):
    res = servicio.files().list(
        q=f"'{FOLDER_ID}' in parents and name = '{nombre}' and trashed = false",
        fields=f"files({campos})",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()
    return res.get("files", [])


def descargar(nombre, ruta_local, max_reintentos=3):
    servicio = conectar_drive()
    if not servicio:
        return False
    for intento in range(1, max_reintentos + 1):
        try:
            archivos = _buscar(servicio, nombre, "id, modifiedTime")
            if not archivos:
                return False
            peticion = servicio.files().get_media(fileId=archivos[0]["id"])
            with open(ruta_local, "wb") as f:
                descargador = MediaIoBaseDownload(f, peticion)
                listo = False
                while not listo:
                    _, listo = descargador.next_chunk()
            with open(f"{ruta_local}.modificado", "w") as f:
                f.write(archivos[0].get("modifiedTime", ""))
            return True
        except Exception as e:
            if _reintentable(e, intento, max_reintentos):
                time.sleep(1.2 * intento)
                continue
            st.error(f"Error al descargar desde Google Drive ({nombre}): {e}")
            break
    return False


def subir(nombre, ruta_local, mime_type="application/json", max_reintentos=3):
    servicio = conectar_drive()
    if not servicio:
        return False
    for intento in range(1, max_reintentos + 1):
        try:
            archivos = _buscar(servicio, nombre, "id")
            with open(ruta_local, "rb") as f:
                contenido = io.BytesIO(f.read())
            media = MediaIoBaseUpload(contenido, mimetype=mime_type, resumable=True)
            if archivos:
                servicio.files().update(
                    fileId=archivos[0]["id"], media_body=media, supportsAllDrives=True
                ).execute()
            else:
                servicio.files().create(
                    body={"name": nombre, "parents": [FOLDER_ID]},
                    media_body=media,
                    supportsAllDrives=True,
                    fields="id",
                ).execute()
            return True
        except Exception as e:
            if _reintentable(e, intento, max_reintentos):
                time.sleep(1.2 * intento)
                continue
            print(f"Error al respaldar en Google Drive ({nombre}): {e}")
            break
    return False
