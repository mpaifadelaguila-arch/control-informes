"""Abre cada app de Streamlit en un navegador y la despierta si está dormida.

Streamlit Community Cloud pone la app en reposo tras unas horas sin visitas.
Una petición HTTP simple no basta: hay que cargar la página (que ejecuta
JavaScript) y, si aparece el aviso de reposo, pulsar el botón para reactivarla.

Las direcciones llegan en las variables APP_URL (informes) y APP_URL_PRESTAMOS (préstamos);
las que estén vacías se omiten. Si una app falla, se sigue con las demás y la tarea termina con error.
"""

import os
import sys

from playwright.sync_api import sync_playwright

APPS = {nombre: os.environ.get(var, "").strip() for nombre, var in (("informes", "APP_URL"), ("préstamos", "APP_URL_PRESTAMOS"))}
BOTON_DESPERTAR = "button:has-text('Yes, get this app back up')"

fallos = []
with sync_playwright() as p:
    navegador = p.chromium.launch()
    for nombre, url in APPS.items():
        if not url:
            continue
        pagina = navegador.new_page()
        try:
            pagina.goto(url, wait_until="domcontentloaded", timeout=120_000)
            pagina.wait_for_timeout(15_000)
            boton = pagina.locator(BOTON_DESPERTAR)
            if boton.count() > 0:
                print(f"[{nombre}] La app estaba dormida: se pulsa el botón para despertarla.")
                boton.first.click()
                pagina.wait_for_timeout(90_000)
            else:
                print(f"[{nombre}] La app está activa.")
            # Si sigue mostrándose el aviso de reposo, la tarea falla para que se note.
            if pagina.locator(BOTON_DESPERTAR).count() > 0:
                print(f"[{nombre}] La app no se pudo despertar.")
                fallos.append(nombre)
        except Exception as e:  # noqa: BLE001 - una app caída no debe impedir visitar la otra
            print(f"[{nombre}] Error al visitarla: {e}")
            fallos.append(nombre)
        finally:
            pagina.close()
    navegador.close()

sys.exit(1 if fallos else 0)
