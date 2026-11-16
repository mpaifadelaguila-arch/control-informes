"""Libro diario, libro mayor y balance de comprobación."""

import pandas as pd
import streamlit as st

import calculos as calc
import contabilidad as cont
import datos
import estilos as ui
from vistas import comun

MAX_ASIENTOS = 150


def _csv_diario(asientos: list[dict]) -> bytes:
    filas = [{"asiento": a["numero"], "fecha": ui.fecha_txt(a["fecha"]), "referencia": a["ref"], "glosa": a["glosa"],
              "cuenta": c, "nombre_cuenta": cont.CUENTAS[c][0], "debe": cont.importe(d), "haber": cont.importe(h)}
             for a in asientos for c, d, h in a["lineas"]]
    return pd.DataFrame(filas).to_csv(index=False).encode("utf-8-sig")


def _diario(lib: list[dict], desde) -> None:
    sel = [a for a in lib if a["fecha"] >= desde]
    if not sel:
        ui.vacio("Sin asientos en este periodo", "Los desembolsos, cobros, movimientos de caja y devengos generan asientos automáticamente.")
        return
    mostrados = sel[-MAX_ASIENTOS:]
    st.caption("Cada bloque gris es un asiento: arriba se explica qué pasó y debajo van las cuentas que se mueven. "
               "En cada asiento, lo que entra por Debe es igual a lo que sale por Haber.")
    filas, debe, haber = [], 0, 0
    for a in mostrados:
        filas.append({"celdas": [ui.fecha_txt(a["fecha"]), a["numero"], a["glosa"]], "clase": "cab"})
        for c, d, h in a["lineas"]:
            filas.append(["", "", f"  {c} {cont.CUENTAS[c][0]}", ui.monto(cont.importe(d)), ui.monto(cont.importe(h))])
            debe, haber = debe + d, haber + h
    ui.tabla(["Fecha", "Asiento", "Cuenta", "Debe", "Haber"], filas, numericas=(3, 4), sin_corte=(0, 1, 2), etiqueta="Libro diario",
             pie=["", "", f"Totales de los {len(mostrados)} asientos mostrados", ui.monto(cont.importe(debe)), ui.monto(cont.importe(haber))])
    if len(sel) > MAX_ASIENTOS:
        st.caption(f"Se muestran los últimos {MAX_ASIENTOS} de {len(sel)} asientos del periodo. Descarga el CSV para ver todos.")
    st.download_button("Descargar libro diario (CSV)", _csv_diario(sel), file_name="libro_diario.csv", mime="text/csv", icon=":material/download:")


def _mayor(lib: list[dict], desde) -> None:
    cuenta = st.selectbox("Cuenta", list(cont.CUENTAS), format_func=lambda c: f"{c} · {cont.CUENTAS[c][0]}", key="mayor_cuenta")
    todas = cont.mayor(lib, cuenta)
    previas = [f for f in todas if f["fecha"] < desde]
    periodo = [f for f in todas if f["fecha"] >= desde]
    saldo_ini = previas[-1]["saldo"] if previas else 0.0
    if not periodo and not previas:
        ui.vacio("Sin movimientos en esta cuenta", "Elige otra cuenta u otro periodo.")
        return
    filas = [{"celdas": ["", "", "Saldo anterior", "", "", ui.monto(saldo_ini)], "clase": "sub"}]
    filas += [[ui.fecha_txt(f["fecha"]), f["numero"], f"{f['glosa']} · {f['ref']}", ui.monto(f["debe"]), ui.monto(f["haber"]), ui.monto(f["saldo"])]
              for f in periodo]
    final = periodo[-1]["saldo"] if periodo else saldo_ini
    ui.tabla(["Fecha", "Asiento", "Detalle", "Debe", "Haber", "Saldo"], filas, numericas=(3, 4, 5), sin_corte=(0, 1), etiqueta="Libro mayor",
             pie=["", "", "Saldo final", ui.monto(round(sum(f["debe"] for f in periodo), 2)), ui.monto(round(sum(f["haber"] for f in periodo), 2)), ui.monto(final)])
    st.caption(f"Naturaleza de la cuenta: {'deudora' if cont.CUENTAS[cuenta][1] == 'D' else 'acreedora'}; el saldo se calcula en ese sentido.")


def _comprobacion(lib: list[dict]) -> None:
    bc = cont.balance_comprobacion(lib)
    ui.tabla(["Cuenta", "Nombre", "Debe", "Haber", "Saldo deudor", "Saldo acreedor"],
             [[f["cuenta"], f["nombre"], ui.monto(f["debe"]), ui.monto(f["haber"]), ui.monto(f["deudor"]), ui.monto(f["acreedor"])] for f in bc["filas"]],
             numericas=(2, 3, 4, 5), etiqueta="Balance de comprobación",
             pie=["", "Totales", ui.monto(bc["total"]["debe"]), ui.monto(bc["total"]["haber"]), ui.monto(bc["total"]["deudor"]), ui.monto(bc["total"]["acreedor"])])
    if bc["cuadra"]:
        st.caption("Todo cuadra: el total del Debe es igual al total del Haber.")
    else:
        st.error("El Debe y el Haber no son iguales. Avísame para revisar los asientos.")


def mostrar() -> None:
    db = datos.cargar()
    hoy = calc.hoy()
    ui.encabezado("Libro diario y mayor", "Asientos de partida doble generados por cada desembolso, cobro, movimiento y devengo de intereses")
    if not (db["prestamos"] or db["movimientos"] or db["config"]["capital_base"]):
        ui.vacio("Aún no hay asientos", "Registra un crédito, un cobro o un aporte de capital y aparecerán aquí.")
        return
    vista = st.radio("Vista", ["Libro diario", "Libro mayor", "Balance de comprobación"], horizontal=True, label_visibility="collapsed", key="vista_libro")
    periodo, desde, hasta = comun.selector_periodo(db, hoy, "periodo_libro")
    lib = cont.asientos(db, hasta, hoy)
    if vista == "Libro diario":
        _diario(lib, desde)
    elif vista == "Libro mayor":
        _mayor(lib, desde)
    else:
        st.caption(f"Saldos acumulados hasta el {ui.fecha_txt(hasta)}.")
        _comprobacion(lib)
    if any(a["provisional"] for a in lib):
        st.caption("El devengo del mes en curso es provisional: se recalcula cada día y queda definitivo al terminar el mes.")
