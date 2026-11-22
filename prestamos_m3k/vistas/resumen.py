"""Resumen contable: ganancia, movimiento de caja, situación del negocio y cierre del mes, en una sola pantalla."""

import streamlit as st

import calculos as calc
import contabilidad as cont
import datos
import estilos as ui
import navegacion as nav
from vistas import cierre, comun, libro_diario, reportes


def _ganancia(lib: list[dict], desde, hasta) -> None:
    er = cont.estado_resultados(lib, desde, hasta)
    filas = [["Intereses ganados", ui.monto(er["intereses"])]]
    if er["mora"]:
        filas.append(["Mora cobrada", ui.monto(er["mora"])])
    filas.append(["Gastos y servicios", ui.monto(-er["gastos"] if er["gastos"] else 0)])
    ui.tabla(["Concepto", "S/"], filas, numericas=(1,), etiqueta="Cuánto ganaste", pie=["Ganancia del periodo", ui.monto(er["utilidad"])])
    st.caption("El interés se va ganando día a día, desde la entrega hasta la última cuota, aunque el cliente todavía no haya pagado.")


def _caja(lib: list[dict], desde, hasta) -> None:
    f = cont.flujo_caja(lib, desde, hasta)
    m = f["movimientos"]
    nombres = [("cobro", "+ Cobros a clientes", True), ("aporte", "+ Aportes de capital", False), ("desembolso", "− Préstamos entregados", True),
               ("retiro", "− Retiros de capital", False), ("gasto", "− Gastos y servicios", False)]
    filas = [["Caja al inicio", ui.monto(f["inicial"])]]
    filas += [[etiqueta, ui.monto(m[k])] for k, etiqueta, siempre in nombres if m[k] or siempre]
    ui.tabla(["Concepto", "S/"], filas, numericas=(1,), etiqueta="Movimiento de caja", pie=["Caja al final", ui.monto(f["final"])])


def _situacion(lib: list[dict], hasta) -> None:
    b = cont.balance_general(lib, hasta)
    ui.tabla(["Concepto", "S/"], [
        {"celdas": ["LO QUE TIENES", ""], "clase": "cab"},
        ["Dinero en caja", ui.monto(b["caja"])],
        ["Lo que te deben (capital + interés)", ui.monto(b["cartera"])],
        ["(−) Intereses que aún no ganas", ui.monto(-b["no_devengados"] if b["no_devengados"] else 0)],
        {"celdas": ["Total", ui.monto(b["activo"])], "clase": "sub"},
        {"celdas": ["DE DÓNDE VIENE", ""], "clase": "cab"},
        ["Capital que aportaste", ui.monto(b["capital"])],
        ["(−) Retiros de capital", ui.monto(-b["retiros"] if b["retiros"] else 0)],
        ["Ganancias acumuladas", ui.monto(b["resultados"])],
        {"celdas": ["Total", ui.monto(b["patrimonio"])], "clase": "sub"},
    ], numericas=(1,), etiqueta="Qué tienes y de dónde viene")
    if b["cuadra"]:
        st.caption(f"Situación al {ui.fecha_txt(hasta)}. Los dos totales son iguales: todo lo que tienes viene de tu capital o de tus ganancias.")
    else:
        st.error("Los dos totales no son iguales. Revisa los asientos en la pestaña «Para el contador».")


def mostrar() -> None:
    db = datos.cargar()
    hoy = calc.hoy()
    ui.encabezado("Resultados", "Cuánto cobraste, cuánto ganaste y qué tienes. Cada cifra aparece una sola vez")
    if not (db["prestamos"] or db["movimientos"] or db["config"]["capital_base"]):
        ui.vacio("Aún no hay información contable", "Registra un crédito, un cobro o un aporte de capital.", "📊")
        return
    vista = nav.pestanas(["Cobranza", "Ganancia y balance", "Para el contador"], "vista_resultados",
                         iconos={"Cobranza": ":material/payments:", "Ganancia y balance": ":material/account_balance:",
                                 "Para el contador": ":material/menu_book:"})
    st.divider()
    if vista == "Cobranza":
        reportes.cuerpo(db, hoy)
        return
    if vista == "Para el contador":
        libro_diario.cuerpo(db, hoy)
        return
    periodo, desde, hasta = comun.selector_periodo(db, hoy, "periodo_resumen", "Mes")
    lib = cont.asientos(db, hoy, hoy)

    st.subheader("1 · ¿Cuánto ganaste?", anchor=False)
    _ganancia(lib, desde, hasta)
    st.subheader("2 · ¿Cómo se movió tu caja?", anchor=False)
    _caja(lib, desde, hasta)
    st.subheader("3 · ¿Qué tienes y qué te deben?", anchor=False)
    _situacion(lib, hasta)
    if any(a["provisional"] for a in lib):
        st.caption("El mes en curso es provisional: el interés se recalcula cada día y queda definitivo cuando el mes termina.")

    st.subheader("4 · Cierre del mes", anchor=False)
    cierre.seccion(db, hoy)
