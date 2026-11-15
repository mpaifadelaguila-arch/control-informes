"""Piezas compartidas por las vistas."""

import streamlit as st

import calculos as calc
import operaciones as ops


def ir_a(clave: str) -> None:
    st.switch_page(st.session_state["_paginas"][clave])


def nombre_cliente(db: dict, cliente_id: str) -> str:
    c = ops.buscar(db["clientes"], cliente_id)
    return c["nombre"] if c else "—"


def etiqueta_prestamo(db: dict, prestamo: dict) -> str:
    return f"Préstamo {prestamo['numero']:04d} · {nombre_cliente(db, prestamo['cliente_id'])}"


def nombre_modalidad(clave: str) -> str:
    return calc.MODALIDADES.get(clave, {}).get("nombre", clave)


def selector_periodo(db: dict, hoy, clave: str, etiqueta: str = "Periodo", acumulado: bool = True):
    """Selector de mes contable. Devuelve (periodo|None, desde, hasta); None = todo el historial."""
    import contabilidad as cont

    inicio = cont.periodo_de(cont.fecha_apertura(db, hoy))
    opciones = list(reversed(cont.meses(inicio, cont.periodo_de(hoy))))
    if acumulado:
        opciones = [None] + opciones
    sel = st.selectbox(etiqueta, opciones, key=clave,
                       format_func=lambda p: "Todo el historial" if p is None else cont.nombre_mes(p))
    if sel is None:
        return None, cont.primer_dia(inicio), hoy
    return sel, cont.primer_dia(sel), min(cont.ultimo_dia(sel), hoy)
