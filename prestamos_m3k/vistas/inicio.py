"""Inicio: indicadores, avance del mes, cobranza y gráficos de la cartera."""

from datetime import timedelta

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
                 "Empieza registrando tu primer cliente.", "👥")
        c1, c2 = st.columns(2)
        if c1.button("Registrar el primer cliente", type="primary", icon=":material/person_add:"):
            comun.ir_a("clientes")
        if c2.button("Ir a Configuración", icon=":material/settings:"):
            comun.ir_a("config")
        return

    # accesos directos a lo más usado (en el celular el menú lateral queda escondido)
    a1, a2, a3, a4 = st.columns(4)
    if a1.button("Cobrar", key="qa_cobrar", icon=":material/payments:", use_container_width=True, type="primary"):
        comun.ir_a("cobros")
    if a2.button("Nuevo crédito", key="qa_credito", icon=":material/add_circle:", use_container_width=True):
        st.session_state["_vista_prestamos"] = "Nuevo crédito"
        comun.ir_a("prestamos")
    if a3.button("Nuevo cliente", key="qa_cliente", icon=":material/person_add:", use_container_width=True):
        st.session_state["_abrir_nuevo_cliente"] = True
        comun.ir_a("clientes")
    if a4.button("Recibos", key="qa_recibos", icon=":material/receipt_long:", use_container_width=True):
        comun.ir_a("recibos")

    ui.kpis([
        {"etiqueta": "Para cobrar hoy", "valor": ui.soles(ind["cobros_hoy_monto"]), "heroe": True, "tono": "info",
         "nota": f"{ind['cobros_hoy_n']} cuota(s) vencen hoy"},
        {"etiqueta": "Vencido", "valor": ui.soles(ind["vencido"]), "tono": "malo" if ind["vencido"] > 0 else "ok",
         "nota": "Cuotas atrasadas" if ind["vencido"] > 0 else "Nadie atrasado"},
        {"etiqueta": "Prestado en la calle", "valor": ui.soles(ind["capital_en_calle"]), "tono": "aviso",
         "nota": f"{ind['prestamos_activos']} préstamo(s) · te deben {ui.soles(ind['por_cobrar'])} con interés"},
        {"etiqueta": "Dinero en caja", "valor": ui.soles(caja["liquidez"]), "tono": "ok" if caja["liquidez"] >= 0 else "malo",
         "nota": "Disponible para prestar"},
    ])

    st.subheader("Cobranza", anchor=False)
    cola = calc.cola_cobranza(db, evals, hoy)
    if not cola:
        ui.vacio("Todo al día", "No hay cuotas vencidas ni cobros pendientes para hoy.", "✅")
    for i, fila in enumerate(cola[:10]):
        pr = fila["prestamo"]
        detalle = []
        if fila["vencido"] > 0:
            detalle.append(f"{ui.soles(fila['vencido'])} vencido · {fila['cuotas_vencidas']} cuota(s) · {fila['atraso']} días de atraso")
        if fila["hoy"] > 0:
            detalle.append(f"{ui.soles(fila['hoy'])} vence hoy")
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 4, 1.3], vertical_alignment="center")
            c1.markdown(
                f'<b>{ui.esc(fila["cliente"].get("nombre", "—"))}</b><br><small style="color:{ui.TEXTO_SUAVE}">Préstamo {pr["numero"]:04d} · '
                f'{ui.esc(comun.nombre_modalidad(pr["modalidad"]))} · {ui.esc(fila["cliente"].get("telefono") or "sin teléfono")}</small>',
                unsafe_allow_html=True)
            c2.markdown(f'{ui.chip("Vencido" if fila["vencido"] > 0 else "Vence hoy", "malo" if fila["vencido"] > 0 else "info")} '
                        f'<span class="num">{ui.esc(" · ".join(detalle))}</span>', unsafe_allow_html=True)
            if c3.button("Cobrar", key=f"cobrar_{i}_{pr['id']}", icon=":material/payments:", use_container_width=True):
                st.session_state["cobro_prestamo"] = pr["id"]
                comun.ir_a("cobros")
    if len(cola) > 10:
        st.caption(f"Mostrando 10 de {len(cola)}. El detalle completo está en «Préstamos».")
    st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

    proximos = calc.proximos_cobros(db, evals, hoy + timedelta(days=1))  # lo de hoy ya está en «Cobranza»
    st.subheader("Próximos cobros", anchor=False)
    if any(d["monto"] for d in proximos):
        st.markdown(g.panel("Lo que vence desde mañana", g.proximos_dias(proximos, hoy), "Lo de hoy está arriba, en Cobranza. No se cuentan los domingos."), unsafe_allow_html=True)
    else:
        st.caption("No hay cuotas que venzan en los próximos días.")

    mes = calc.avance_mes(db, evals, hoy)
    if mes["esperado"]:
        nombre_mes = cont.nombre_mes(cont.periodo_de(hoy)).split()[0].lower()
        st.markdown(g.panel("Avance de la cobranza del mes", g.avance(mes["cobrado"], mes["esperado"], nombre_mes)), unsafe_allow_html=True)

    semanas = calc.cuotas_por_semana(db, evals, hoy)
    composicion = calc.composicion_cartera(db, evals)
    if any(sm["esperado"] for sm in semanas) or composicion:
        st.subheader("Cartera", anchor=False)
        izq, der = st.columns([3, 2])
        if any(sm["esperado"] for sm in semanas):
            primera = next(k for k, sm in enumerate(semanas) if sm["esperado"] or sm["actual"])
            semanas = semanas[min(primera, len(semanas) - 4):]
            izq.markdown(g.panel("Cobrado frente a lo que vencía, por semana", g.semanas(semanas), "Cada grupo es una semana de lunes a sábado (la fecha es su lunes): en gris, lo que vencía; en verde, lo que ya se cobró de eso."),
                         unsafe_allow_html=True)
        if composicion:
            total = sum(c["monto"] for c in composicion)
            if any(c["gravedad"] > 0 for c in composicion):
                der.markdown(g.panel("Lo que te deben, por antigüedad", g.dona(composicion, f"S/ {total:,.0f}", "te deben"),
                                     "Cada color es un tramo de atraso, de verde (al día) a rojo (muy atrasado)."), unsafe_allow_html=True)
            else:
                der.markdown(g.panel("Lo que te deben", g.todo_al_dia(total)), unsafe_allow_html=True)

    serie = cont.serie_caja(cont.asientos(db, hoy, hoy), hoy, 30)
    if len({v for _, v in serie}) > 1:
        st.subheader("Caja", anchor=False)
        st.markdown(g.panel("Dinero disponible, últimos 30 días", g.linea(serie)), unsafe_allow_html=True)
