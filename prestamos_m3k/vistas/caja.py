"""Caja: liquidez, movimientos manuales, historial único y capital base con auditoría."""

import streamlit as st

import calculos as calc
import datos
import estilos as ui
import operaciones as ops


def _monto_coloreado(importe: float) -> ui.Raw:
    tono = ui.TONOS["ok"] if importe >= 0 else ui.TONOS["malo"]
    return ui.Raw(f'<span style="color:{tono};font-weight:600">{ui.esc(ui.soles(importe, signo=True))}</span>')


def mostrar() -> None:
    db = datos.cargar()
    hoy = calc.hoy()
    r = calc.resumen_caja(db)
    ui.encabezado("Caja", "Todo el dinero que entra y sale del negocio")

    entradas, salidas = r["cobrado"] + r["aportes"], r["desembolsado"] + r["salidas"]
    ui.kpis([
        {"etiqueta": "Saldo disponible", "valor": ui.soles(r["liquidez"]), "heroe": True, "tono": "ok" if r["liquidez"] >= 0 else "malo",
         "nota": "Lo que hay hoy en caja"},
        {"etiqueta": "Entradas", "valor": ui.soles(entradas), "tono": "ok", "nota": f"Cobros {ui.soles(r['cobrado'])} · aportes {ui.soles(r['aportes'])}"},
        {"etiqueta": "Salidas", "valor": ui.soles(salidas), "tono": "aviso", "nota": f"Créditos {ui.soles(r['desembolsado'])} · retiros y gastos {ui.soles(r['salidas'])}"},
    ])

    with st.expander("Registrar movimiento", expanded=not db["movimientos"] and not db["prestamos"]):
        with st.form("form_movimiento", clear_on_submit=True):
            tipo = st.selectbox("Tipo", list(ops.TIPOS_MOVIMIENTO), format_func=ops.TIPOS_MOVIMIENTO.get)
            c1, c2 = st.columns(2)
            monto = c1.number_input("Monto (S/)", min_value=0.0, step=10.0, format="%.2f")
            fecha = c2.date_input("Fecha", value=hoy, format="DD/MM/YYYY")
            detalle = st.text_input("Detalle", placeholder="Ej.: aporte del socio, pasajes, internet")
            if st.form_submit_button("Guardar movimiento", type="primary"):
                try:
                    ops.registrar_movimiento(db, tipo, monto, fecha, detalle)
                except ValueError as e:
                    st.error(str(e))
                else:
                    datos.guardar(db)
                    ui.avisar("ok", "Movimiento registrado.")
                    st.rerun()

    st.subheader("Historial", anchor=False)
    historial = calc.movimientos_caja(db)
    filtro = st.selectbox("Mostrar", ["Todo", "Desembolso", "Cobro", "Movimientos manuales"], label_visibility="collapsed")
    if filtro == "Movimientos manuales":
        historial = [h for h in historial if h["tipo"] not in ("Desembolso", "Cobro")]
    elif filtro != "Todo":
        historial = [h for h in historial if h["tipo"] == filtro]
    if not historial:
        ui.vacio("Sin movimientos", "Los desembolsos, cobros y movimientos manuales aparecerán aquí.")
    else:
        ui.tabla(["Fecha", "Tipo", "Detalle", "Folio", "Monto"],
                 [[ui.fecha_txt(h["fecha"]), h["tipo"], h["detalle"], h["folio"] or "—", _monto_coloreado(h["monto"])] for h in historial[:200]],
                 numericas=(4,), sin_corte=(0, 3), etiqueta="Historial de caja")
        if len(historial) > 200:
            st.caption(f"Se muestran los 200 más recientes de {len(historial)}.")

    manuales = [m for m in db["movimientos"] if not m.get("anulado")]
    if manuales:
        with st.expander("Anular un movimiento manual"):
            etiquetas = {m["id"]: f"{ui.fecha_txt(m['fecha'])} · {ops.TIPOS_MOVIMIENTO[m['tipo']].split(' (')[0]} · {ui.soles(m['monto'])} · {m.get('detalle', '')}" for m in manuales}
            elegido = st.selectbox("Movimiento", list(etiquetas), format_func=etiquetas.get)
            if st.button("Anular movimiento", key="anular_mov"):
                ops.anular_movimiento(db, elegido)
                datos.guardar(db)
                ui.avisar("ok", "Movimiento anulado.")
                st.rerun()

    with st.expander("Cambiar el capital base"):
        st.caption("Es el punto de partida de la liquidez. Para aportes o retiros normales usa «Registrar movimiento»; "
                   "este cambio exige un motivo y queda en la auditoría.")
        nuevo = st.number_input("Nuevo capital base (S/)", min_value=0.0, value=float(r["capital_base"]), step=100.0, format="%.2f")
        motivo = st.text_input("Motivo", key="motivo_base")
        if st.button("Guardar capital base"):
            try:
                ops.cambiar_capital_base(db, nuevo, motivo)
            except ValueError as e:
                st.error(str(e))
            else:
                datos.guardar(db)
                ui.avisar("ok", "Capital base actualizado.")
                st.rerun()
