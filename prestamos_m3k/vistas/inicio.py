"""Inicio: indicadores, avance del mes, cobranza y gráficos de la cartera."""

import streamlit as st

import calculos as calc
import contabilidad as cont
import datos
import estilos as ui
import graficos as g
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
        {"etiqueta": "Para cobrar hoy", "valor": ui.soles(ind["cobros_hoy_monto"]), "tono": "info",
         "nota": f"{ind['cobros_hoy_n']} cuota(s) vencen hoy"},
    ])

    mes = calc.avance_mes(db, evals, hoy)
    if mes["esperado"]:
        nombre_mes = cont.nombre_mes(cont.periodo_de(hoy)).split()[0].lower()
        st.markdown(g.panel("Avance de la cobranza del mes", g.avance(mes["cobrado"], mes["esperado"], nombre_mes)), unsafe_allow_html=True)

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

    proximos = calc.proximos_cobros(db, evals, hoy)
    st.subheader("Próximos cobros", anchor=False)
    if any(d["monto"] for d in proximos):
        st.markdown(g.panel("Lo que vence en los próximos días", g.proximos_dias(proximos, hoy), "No se cuentan los domingos."), unsafe_allow_html=True)
    else:
        st.caption("No hay cuotas que venzan en los próximos días.")

    semanas = calc.cuotas_por_semana(db, evals, hoy)
    composicion = calc.composicion_cartera(db, evals)
    if any(sm["esperado"] for sm in semanas) or composicion:
        st.subheader("Cartera", anchor=False)
        izq, der = st.columns([3, 2])
        if any(sm["esperado"] for sm in semanas):
            izq.markdown(g.panel("Cobrado frente a lo que vencía, por semana", g.semanas(semanas), "Se comparan las cuotas que vencían cada semana con lo ya cobrado de ellas."),
                         unsafe_allow_html=True)
        if composicion:
            total = sum(c["monto"] for c in composicion)
            der.markdown(g.panel("Lo que te deben, por antigüedad", g.dona(composicion, f"S/ {total:,.0f}", "te deben")), unsafe_allow_html=True)

    serie = cont.serie_caja(cont.asientos(db, hoy, hoy), hoy, 30)
    if len({v for _, v in serie}) > 1:
        st.subheader("Caja", anchor=False)
        st.markdown(g.panel("Dinero disponible, últimos 30 días", g.linea(serie)), unsafe_allow_html=True)
