"""Abre la app de Streamlit en un navegador y la despierta si está dormida.

Streamlit Community Cloud pone la app en reposo tras unas horas sin visitas.
Una petición HTTP simple no basta: hay que cargar la página (que ejecuta
JavaScript) y, si aparece el aviso de reposo, pulsar el botón para reactivarla.
"""

import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ["APP_URL"]
BOTON_DESPERTAR = "button:has-text('Yes, get this app back up')"

with sync_playwright() as p:
    navegador = p.chromium.launch()
    pagina = navegador.new_page()
    pagina.goto(URL, wait_until="domcontentloaded", timeout=120_000)
    pagina.wait_for_timeout(15_000)

    boton = pagina.locator(BOTON_DESPERTAR)
    if boton.count() > 0:
        print("La app estaba dormida: se pulsa el botón para despertarla.")
        boton.first.click()
        pagina.wait_for_timeout(90_000)
    else:
        print("La app está activa.")

    # Si sigue mostrándose el aviso de reposo, la tarea falla para que se note.
    if pagina.locator(BOTON_DESPERTAR).count() > 0:
        print("La app no se pudo despertar.")
        sys.exit(1)

    navegador.close()
