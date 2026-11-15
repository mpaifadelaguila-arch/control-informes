"""Inicio: posición financiera, cobranza del día y antigüedad de la mora."""

import streamlit as st

import calculos as calc
import datos
import estilos as ui
from vistas import comun


def mostrar() -> None:
    db = datos.cargar()
    hoy = calc.hoy()
    evals = calc.evaluar_cartera(db, hoy)
    ind = calc.indicadores(db, evals, hoy)
    caja = calc.resumen_caja(db)

    ui.encabezado("Control de cartera", ui.hoy_txt(hoy))

    if not db["clientes"]:
        ui.vacio("Aún no hay clientes",
                 "Empieza registrando un cliente en «Clientes», o carga datos de ejemplo en «Configuración».")
        c1, c2 = st.columns(2)
        if c1.button("Registrar el primer cliente", type="primary", icon=":material/person_add:"):
            comun.ir_a("clientes")
        if c2.button("Ir a Configuración", icon=":material/settings:"):
            comun.ir_a("config")
        return

    sobre_vencido = ind["vencido"] > 0
    ui.kpis([
        {"etiqueta": "Liquidez en caja", "valor": ui.soles(caja["liquidez"]), "heroe": True, "tono": "ok" if caja["liquidez"] >= 0 else "malo",
         "nota": f"Capital base {ui.soles(caja['capital_base'])}"},
        {"etiqueta": "Capital en calle", "valor": ui.soles(ind["capital_en_calle"]), "tono": "info",
         "nota": f"{ind['prestamos_activos']} préstamo(s) activo(s) · sin contar lo ya recuperado"},
        {"etiqueta": "Por cobrar", "valor": ui.soles(ind["por_cobrar"]), "tono": "aviso",
         "nota": f"{ui.soles(ind['vencido'])} vencido" if sobre_vencido else "Nada vencido"},
        {"etiqueta": "Cartera vencida", "valor": ui.pct(ind["morosidad"]), "tono": "malo" if sobre_vencido else "ok",
         "nota": f"{ind['cuotas_vencidas']} cuota(s) vencida(s)" + (f" · mora {ui.soles(ind['mora_pendiente'])}" if ind["mora_pendiente"] else "")},
        {"etiqueta": "Para cobrar hoy", "valor": ui.soles(ind["cobros_hoy_monto"]), "tono": "info",
         "nota": f"{ind['cobros_hoy_n']} cuota(s) vencen hoy"},
        {"etiqueta": "Ganancia cobrada", "valor": ui.soles(ind["ganancia_realizada"]), "tono": "ok",
         "nota": f"de {ui.soles(ind['ganancia_proyectada'])} proyectados en toda la cartera"},
    ])

    st.subheader("Cobranza", anchor=False)
    cola = calc.cola_cobranza(db, evals, hoy)
    if not cola:
        ui.vacio("Todo al día", "No hay cuotas vencidas ni cobros pendientes para hoy.")
    for i, fila in enumerate(cola[:10]):
        pr = fila["prestamo"]
        tono = "malo" if fila["vencido"] > 0 else "info"
        detalle = []
        if fila["vencido"] > 0:
            detalle.append(f"{ui.soles(fila['vencido'])} vencido · {fila['cuotas_vencidas']} cuota(s) · {fila['atraso']} días de atraso")
        if fila["hoy"] > 0:
            detalle.append(f"{ui.soles(fila['hoy'])} vence hoy")
        izq, der = st.columns([5, 1], vertical_alignment="center")
        izq.markdown(
            f'<div class="m3k-fila" style="--tono:{ui.TONOS[tono]}"><div><b>{ui.esc(fila["cliente"].get("nombre", "—"))}</b>'
            f'<small>Préstamo {pr["numero"]:04d} · {ui.esc(comun.nombre_modalidad(pr["modalidad"]))} · '
            f'{ui.esc(fila["cliente"].get("telefono") or "sin teléfono")}</small></div>'
            f'<div>{ui.esc(" · ".join(detalle))}</div></div>',
            unsafe_allow_html=True,
        )
        if der.button("Cobrar", key=f"cobrar_{i}_{pr['id']}", icon=":material/payments:"):
            st.session_state["cobro_prestamo"] = pr["id"]
            comun.ir_a("cobros")
    if len(cola) > 10:
        st.caption(f"Mostrando 10 de {len(cola)}. El detalle completo está en «Préstamos».")

    st.subheader("Antigüedad de la mora", anchor=False)
    antig = calc.antiguedad_mora(evals)
    if not any(f["cuotas"] for f in antig):
        ui.vacio("Sin mora", "Cuando haya cuotas vencidas aparecerán agrupadas por días de atraso.")
    else:
        ui.tabla(["Atraso", "Cuotas", "Monto vencido"],
                 [[f["tramo"], f["cuotas"], ui.soles(f["monto"])] for f in antig], numericas=(1, 2),
                 etiqueta="Deuda vencida por días de atraso")
