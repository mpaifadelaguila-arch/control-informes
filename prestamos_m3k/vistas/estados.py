"""Estados financieros: resultados, balance general y flujo de caja mensual."""

import streamlit as st

import calculos as calc
import contabilidad as cont
import datos
import estilos as ui
from vistas import comun


def _resultados(lib: list[dict], desde, hasta) -> None:
    er = cont.estado_resultados(lib, desde, hasta)
    ui.tabla(["Concepto", "Importe (S/)"], [
        ["Intereses ganados", ui.monto(er["intereses"])],
        ["Mora cobrada", ui.monto(er["mora"])],
        {"celdas": ["Total ingresos", ui.monto(er["ingresos"])], "clase": "sub"},
        ["Gastos y servicios", ui.monto(-er["gastos"] if er["gastos"] else 0)],
    ], numericas=(1,), etiqueta="Estado de resultados", pie=["Utilidad del periodo", ui.monto(er["utilidad"])])
    st.caption("Los intereses se cuentan como ganados día a día entre la entrega y la última cuota, aunque el cliente aún no haya pagado.")


def _balance(lib: list[dict], hasta) -> None:
    b = cont.balance_general(lib, hasta)
    st.caption(f"Situación al {ui.fecha_txt(hasta)}.")
    ui.tabla(["Concepto", "Importe (S/)"], [
        {"celdas": ["ACTIVO", ""], "clase": "cab"},
        ["  Caja y bancos", ui.monto(b["caja"])],
        ["  Cartera de créditos", ui.monto(b["cartera"])],
        ["  (−) Intereses no devengados", ui.monto(-b["no_devengados"] if b["no_devengados"] else 0)],
        {"celdas": ["Total activo", ui.monto(b["activo"])], "clase": "sub"},
        {"celdas": ["PATRIMONIO", ""], "clase": "cab"},
        ["  Capital aportado", ui.monto(b["capital"])],
        ["  (−) Retiros de capital", ui.monto(-b["retiros"] if b["retiros"] else 0)],
        ["  Resultados acumulados", ui.monto(b["resultados"])],
        {"celdas": ["Total patrimonio", ui.monto(b["patrimonio"])], "clase": "sub"},
    ], numericas=(1,), etiqueta="Balance general")
    if b["cuadra"]:
        st.caption("El balance cuadra: el activo es igual al patrimonio.")
    else:
        st.error("El activo y el patrimonio no son iguales. Revisa los asientos en el Libro diario.")


def _flujo(db: dict, lib: list[dict], hoy) -> None:
    inicio = cont.periodo_de(cont.fecha_apertura(db, hoy))
    filas, tot = [], None
    for p in cont.meses(inicio, cont.periodo_de(hoy)):
        f = cont.flujo_caja(lib, cont.primer_dia(p), min(cont.ultimo_dia(p), hoy))
        m = f["movimientos"]
        filas.append([cont.nombre_mes(p), ui.monto(f["inicial"]), ui.monto(m["cobro"]), ui.monto(m["aporte"]), ui.monto(m["desembolso"]),
                      ui.monto(m["retiro"]), ui.monto(m["gasto"]), ui.monto(f["final"])])
    if not filas:
        ui.vacio("Sin movimientos de caja", "Registra un aporte, un desembolso o un cobro.")
        return
    total = cont.flujo_caja(lib, cont.primer_dia(inicio), hoy)
    m = total["movimientos"]
    ui.tabla(["Mes", "Saldo inicial", "Cobros", "Aportes", "Desembolsos", "Retiros", "Gastos", "Saldo final"], filas[::-1], numericas=tuple(range(1, 8)),
             etiqueta="Flujo de caja mensual",
             pie=["Total", ui.monto(total["inicial"]), ui.monto(m["cobro"]), ui.monto(m["aporte"]), ui.monto(m["desembolso"]), ui.monto(m["retiro"]),
                  ui.monto(m["gasto"]), ui.monto(total["final"])])
    st.caption("Las salidas aparecen entre paréntesis. Saldo final = saldo inicial + entradas − salidas, y coincide con el saldo de Caja.")


def mostrar() -> None:
    db = datos.cargar()
    hoy = calc.hoy()
    ui.encabezado("Estados financieros", "Resultados, balance general y flujo de caja")
    if not (db["prestamos"] or db["movimientos"] or db["config"]["capital_base"]):
        ui.vacio("Aún no hay información contable", "Registra un crédito, un cobro o un aporte de capital.")
        return
    periodo, desde, hasta = comun.selector_periodo(db, hoy, "periodo_estados", "Periodo del estado de resultados")
    lib = cont.asientos(db, hoy, hoy)
    t1, t2, t3 = st.tabs(["Estado de resultados", "Balance general", "Flujo de caja"])
    with t1:
        _resultados(lib, desde, hasta)
    with t2:
        _balance(lib, hasta)
    with t3:
        _flujo(db, lib, hoy)
