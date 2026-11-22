"""Base de datos de la app: un solo diccionario guardado como JSON.

Orden de lectura al abrir la app: respaldo en Google Drive (si está configurado) y, si
no, el archivo local data/prestamos.json. Cada cambio se escribe en el disco y se sube
al respaldo. Streamlit se importa dentro de las funciones que lo necesitan para poder
probar el resto sin él.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import timedelta
from pathlib import Path

import calculos as calc
import operaciones as ops

RUTA = Path(__file__).parent / "data" / "prestamos.json"
VERSION = 1


def vacio() -> dict:
    return {
        "version": VERSION,
        "config": {"capital_base": 0.0, "tasa_default": 20.0, "mora_diaria_pct": 0.0, "fecha_apertura": None},
        "clientes": [], "prestamos": [], "pagos": [], "movimientos": [], "auditoria": [], "cierres": {},
        "contadores": {"prestamo": 0, "desembolso": 0, "pago": 0},
    }


def normalizar(db: dict) -> dict:
    """Completa las claves que falten (por si el archivo viene de una versión anterior)."""
    base = vacio()
    for clave, valor in base.items():
        db.setdefault(clave, valor)
    for clave, valor in base["config"].items():
        db["config"].setdefault(clave, valor)
    for clave, valor in base["contadores"].items():
        db["contadores"].setdefault(clave, valor)
    return db


def a_bytes(db: dict) -> bytes:
    return json.dumps(db, ensure_ascii=False, indent=2).encode("utf-8")


def desde_bytes(contenido: bytes) -> dict:
    """Lee un respaldo y comprueba que tenga la forma esperada."""
    try:
        db = json.loads(contenido.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError("El archivo no es un respaldo válido (no es JSON).") from e
    if not isinstance(db, dict):
        raise ValueError("El archivo no es un respaldo de M3K.")
    for clave in ("clientes", "prestamos", "pagos", "movimientos"):
        if not isinstance(db.get(clave, []), list):
            raise ValueError(f"El respaldo está dañado: «{clave}» debe ser una lista.")
    return normalizar(db)


def _escribir_local(db: dict) -> None:
    RUTA.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=RUTA.parent, suffix=".tmp")
    with os.fdopen(fd, "wb") as f:
        f.write(a_bytes(db))
    os.replace(tmp, RUTA)  # escritura atómica: nunca queda un archivo a medias


def cargar() -> dict:
    """Devuelve la base de la sesión (la lee una sola vez por sesión)."""
    import streamlit as st

    import drive_json

    if "_db" not in st.session_state:
        db, aviso = None, None
        contenido, error = drive_json.descargar()
        if contenido:
            try:
                db = desde_bytes(contenido)
            except ValueError as e:
                aviso = f"El respaldo de Drive no se pudo leer: {e}"
        elif error:
            aviso = f"No se pudo leer el respaldo de Google Drive: {error}"
        if db is None and RUTA.exists() and not drive_json.configurado():
            try:
                db = desde_bytes(RUTA.read_bytes())
            except ValueError as e:
                aviso = f"El archivo local está dañado: {e}"
        if db is None and aviso:
            # No se arranca con una base vacía si había datos que no se pudieron leer:
            # el primer guardado sobrescribiría el respaldo real.
            st.error(aviso)
            st.stop()
        st.session_state["_db"] = db or vacio()
    return st.session_state["_db"]


def guardar(db: dict) -> None:
    """Escribe en disco y sube el respaldo. Si Drive falla, lo avisa pero no pierde el cambio."""
    import streamlit as st

    import drive_json

    _escribir_local(db)
    error = drive_json.subir(a_bytes(db))
    st.session_state["_error_respaldo"] = error


def reemplazar(db_nueva: dict) -> dict:
    import streamlit as st

    st.session_state["_db"] = normalizar(db_nueva)
    guardar(st.session_state["_db"])
    return st.session_state["_db"]


# ───────────────────────── datos de ejemplo (ficticios) ─────────────────────────

def ejemplo(hoy_=None) -> dict:
    """Cartera ficticia para probar la app. No contiene datos de clientes reales."""
    hoy_ = calc.fecha(hoy_ or calc.hoy())
    db = vacio()
    db["config"]["capital_base"] = 5000.0
    ana = ops.crear_cliente(db, "Ana Torres Quispe", "00000001", "900000001")
    luis = ops.crear_cliente(db, "Luis Ramos Huamán", "00000002", "900000002")
    rosa = ops.crear_cliente(db, "Rosa Díaz Flores", "00000003", "900000003")
    ops.crear_cliente(db, "Pedro Salas Vega", "00000004", "900000004")

    # Semanal, desembolsado hace 40 días: pagó 2 cuotas y las demás están vencidas.
    f1 = hoy_ - timedelta(days=40)
    p1 = ops.crear_prestamo(db, ana["id"], 600, 20, "semanal", f1, hoy_=hoy_)
    for n in (0, 1):
        ops.registrar_pago(db, p1["id"], p1["cuotas"][n]["vence"], p1["cuotas"][n]["monto"], "Yape", hoy_=hoy_)

    # Diario, desembolsado hace 10 días: va al día (pagó todo lo vencido).
    f2 = hoy_ - timedelta(days=10)
    p2 = ops.crear_prestamo(db, luis["id"], 1000, 20, "diario", f2, hoy_=hoy_)
    for q in p2["cuotas"]:
        if calc.fecha(q["vence"]) < hoy_:
            ops.registrar_pago(db, p2["id"], q["vence"], q["monto"], "Efectivo", hoy_=hoy_)

    # Mensual de 1 mes, desembolsado hace 35 días: ya cancelado.
    f3 = hoy_ - timedelta(days=35)
    p3 = ops.crear_prestamo(db, rosa["id"], 500, 20, "mensual", f3, hoy_=hoy_)
    ops.registrar_pago(db, p3["id"], p3["cuotas"][0]["vence"], p3["total"], "Plin", hoy_=hoy_)

    ops.registrar_movimiento(db, "aporte", 800, hoy_ - timedelta(days=20), "Aporte de capital", hoy_=hoy_)
    ops.registrar_movimiento(db, "gasto", 60, hoy_ - timedelta(days=5), "Útiles y movilidad", hoy_=hoy_)
    return db
