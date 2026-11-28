"""Respaldo de la base de datos en una carpeta de Google Drive (cuenta de servicio).

Streamlit Community Cloud borra el disco al reiniciar, así que sin este respaldo los
datos se perderían. Se activa solo si en los secretos de la app existen
`gcp_service_account` y `prestamos_drive_folder_id` (carpeta distinta a la de informes).
"""

from __future__ import annotations

import io
import time

import streamlit as st

NOMBRE_ARCHIVO = "prestamos_m3k.json"
_ID_ARCHIVO: dict[str, str] = {}  # id del archivo por carpeta: evita buscarlo en Drive en cada guardado


def _secreto(clave: str):
    try:
        return st.secrets.get(clave)
    except Exception:  # sin archivo de secretos
        return None


def configurado() -> bool:
    return bool(_secreto("gcp_service_account") and _secreto("prestamos_drive_folder_id"))


@st.cache_resource
def _servicio():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    info = dict(st.secrets["gcp_service_account"])
    info["private_key"] = info["private_key"].replace("\\n", "\n").replace("\r\n", "\n")
    credenciales = Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=credenciales)


def _buscar(servicio, carpeta: str):
    res = servicio.files().list(
        q=f"'{carpeta}' in parents and name = '{NOMBRE_ARCHIVO}' and trashed = false",
        fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute()
    archivos = res.get("files", [])
    return archivos[0]["id"] if archivos else None


def descargar() -> tuple[bytes | None, str | None]:
    """Devuelve (contenido, error). Contenido None sin error = todavía no hay respaldo."""
    if not configurado():
        return None, None
    try:
        from googleapiclient.http import MediaIoBaseDownload

        servicio = _servicio()
        carpeta = _secreto("prestamos_drive_folder_id")
        id_archivo = _buscar(servicio, carpeta)
        if not id_archivo:
            return None, None
        _ID_ARCHIVO[carpeta] = id_archivo
        buffer = io.BytesIO()
        descargador = MediaIoBaseDownload(buffer, servicio.files().get_media(fileId=id_archivo))
        listo = False
        while not listo:
            _, listo = descargador.next_chunk()
        return buffer.getvalue(), None
    except Exception as e:
        return None, str(e)


def subir(contenido: bytes, reintentos: int = 3) -> str | None:
    """Sube el respaldo. Devuelve None si salió bien, o el texto del error."""
    if not configurado():
        return None
    from googleapiclient.http import MediaIoBaseUpload

    ultimo_error = None
    for intento in range(1, reintentos + 1):
        try:
            servicio = _servicio()
            carpeta = _secreto("prestamos_drive_folder_id")
            id_archivo = _ID_ARCHIVO.get(carpeta) or _buscar(servicio, carpeta)
            # archivo pequeño: se sube en una sola petición (resumable=False) en lugar de varias
            media = MediaIoBaseUpload(io.BytesIO(contenido), mimetype="application/json", resumable=False)
            if id_archivo:
                servicio.files().update(fileId=id_archivo, media_body=media, supportsAllDrives=True).execute()
            else:
                creado = servicio.files().create(
                    body={"name": NOMBRE_ARCHIVO, "parents": [carpeta]},
                    media_body=media, supportsAllDrives=True, fields="id",
                ).execute()
                id_archivo = creado.get("id")
            if id_archivo:
                _ID_ARCHIVO[carpeta] = id_archivo
            return None
        except Exception as e:
            _ID_ARCHIVO.pop(_secreto("prestamos_drive_folder_id"), None)  # por si el archivo cambió: se vuelve a buscar
            ultimo_error = str(e)
            time.sleep(1.2 * intento)
    return ultimo_error
