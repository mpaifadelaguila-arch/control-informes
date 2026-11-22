"""Piezas compartidas por las vistas."""

import streamlit as st

import calculos as calc
import operaciones as ops
from estilos import soles as ui_soles


def ir_a(clave: str) -> None:
    st.switch_page(st.session_state["_paginas"][clave])


def nombre_cliente(db: dict, cliente_id: str) -> str:
    c = ops.buscar(db["clientes"], cliente_id)
    return c["nombre"] if c else "—"


def etiqueta_prestamo(db: dict, prestamo: dict) -> str:
    return f"Préstamo {prestamo['numero']:04d} · {nombre_cliente(db, prestamo['cliente_id'])}"


def descripcion_credito(p: dict) -> str:
    """«Semanal · 4 cuotas», «Mensual · 3 meses»..."""
    nombre = nombre_modalidad(p["modalidad"])
    if p["modalidad"] == "mensual":
        m = p.get("meses", len(p["cuotas"]))
        return f"{nombre} · {m} {'mes' if m == 1 else 'meses'}" + (" · fin de mes" if p.get("fin_de_mes") else "")
    n = len(p["cuotas"])
    return f"{nombre} · {n} cuota{'s' if n != 1 else ''}"


def texto_interes(p: dict) -> str:
    """El interés del crédito, dicho como corresponde a su modalidad."""
    ganancia = ui_soles(p["total"] - p["monto"])
    if p.get("meses", 1) > 1 or p.get("fin_de_mes"):
        extra = ", el primer tramo prorrateado" if p.get("fin_de_mes") else ""
        return f"{p['tasa']:g} % por mes × {p.get('meses', 1)} mes(es){extra} = {ganancia}"
    return f"{p['tasa']:g} % = {ganancia}"


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
