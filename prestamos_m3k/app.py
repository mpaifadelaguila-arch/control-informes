"""M3K Préstamos Personales: punto de entrada (acceso con clave y menú de navegación).

Ejecutar:  streamlit run prestamos_m3k/app.py
Clave:     secreto `app_password` (en local, .streamlit/secrets.toml). Solo para pruebas
           locales se puede entrar sin clave con la variable PRESTAMOS_SIN_CLAVE=1.
"""

import hmac
import os
import time

import streamlit as st

st.set_page_config(page_title="M3K Préstamos", page_icon=":material/payments:", layout="wide", initial_sidebar_state="expanded")

import calculos as calc  # noqa: E402
import datos  # noqa: E402
import drive_json  # noqa: E402
import estilos  # noqa: E402
from vistas import (caja, clientes, cobros, configuracion, cuentas_por_cobrar, inicio,  # noqa: E402
                    libro_diario, prestamos, recibos, reportes, resumen)  # noqa: E402

estilos.aplicar()


def _clave_configurada() -> str | None:
    try:
        return st.secrets.get("app_password")
    except Exception:
        return None


def acceso() -> bool:
    """Puerta de entrada: esta app guarda DNI, teléfonos y deudas, no debe quedar abierta."""
    if st.session_state.get("_acceso"):
        return True
    clave = _clave_configurada()
    if not clave:
        if os.environ.get("PRESTAMOS_SIN_CLAVE") == "1":
            return True
        estilos.encabezado("Acceso protegido", "Falta configurar la clave de la aplicación.")
        st.error(
            "No hay clave configurada. Agrega `app_password = \"tu clave\"` en los secretos de la app "
            "(Streamlit Cloud: Settings → Secrets; en local: `.streamlit/secrets.toml`)."
        )
        return False
    estilos.encabezado("M3K Préstamos Personales", "Ingresa tu clave para continuar.")
    with st.form("acceso"):
        ingresada = st.text_input("Clave", type="password", autocomplete="current-password")
        enviar = st.form_submit_button("Entrar", type="primary")
    if enviar:
        if hmac.compare_digest(ingresada.encode(), str(clave).encode()):
            st.session_state["_acceso"] = True
            st.rerun()
        time.sleep(1)  # frena los intentos repetidos
        st.error("La clave no es correcta. Inténtalo de nuevo.")
    return False


if not acceso():
    st.stop()

paginas = {
    "inicio": st.Page(inicio.mostrar, title="Inicio", icon=":material/home:", url_path="inicio", default=True),
    "cobros": st.Page(cobros.mostrar, title="Registrar cobro", icon=":material/payments:", url_path="cobros"),
    "prestamos": st.Page(prestamos.mostrar, title="Préstamos", icon=":material/request_quote:", url_path="prestamos"),
    "clientes": st.Page(clientes.mostrar, title="Clientes", icon=":material/group:", url_path="clientes"),
    "caja": st.Page(caja.mostrar, title="Caja", icon=":material/account_balance_wallet:", url_path="caja"),
    "reportes": st.Page(reportes.mostrar, title="Reportes", icon=":material/bar_chart:", url_path="reportes"),
    "recibos": st.Page(recibos.mostrar, title="Recibos", icon=":material/receipt_long:", url_path="recibos"),
    "libro": st.Page(libro_diario.mostrar, title="Libros contables", icon=":material/menu_book:", url_path="libro"),
    "cxc": st.Page(cuentas_por_cobrar.mostrar, title="Cuentas por cobrar", icon=":material/account_balance:", url_path="cxc"),
    "resumen": st.Page(resumen.mostrar, title="Resumen contable", icon=":material/finance:", url_path="resumen"),
    "config": st.Page(configuracion.mostrar, title="Configuración", icon=":material/settings:", url_path="configuracion"),
}
st.session_state["_paginas"] = paginas  # las vistas lo usan para saltar de una a otra

navegacion = st.navigation({
    "Operación": [paginas[k] for k in ("inicio", "cobros", "prestamos", "clientes")],
    "Contabilidad": [paginas[k] for k in ("resumen", "cxc", "libro")],
    "Control": [paginas[k] for k in ("caja", "reportes", "recibos")],
    "Aplicación": [paginas["config"]],
})

db = datos.cargar()
with st.sidebar:
    caja_ = calc.resumen_caja(db)
    st.caption("Liquidez en caja")
    st.markdown(f'<div class="num" style="font-size:1.35rem;font-weight:700">{estilos.soles(caja_["liquidez"])}</div>',
                unsafe_allow_html=True)
    if drive_json.configurado():
        st.caption("Respaldo en Google Drive activo")
    else:
        st.caption("Sin respaldo en Drive: los datos solo están en este equipo")
    if st.button("Cerrar sesión", icon=":material/logout:"):
        st.session_state.clear()
        st.rerun()

estilos.mensaje_pendiente()
if st.session_state.get("_error_respaldo"):
    st.warning("El último cambio se guardó aquí pero no se pudo respaldar en Google Drive. "
               f"Detalle: {st.session_state['_error_respaldo']}")
navegacion.run()
