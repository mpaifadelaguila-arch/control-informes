"""Préstamos: cartera con filtros y detalle por cuotas, y el simulador para crear un crédito nuevo."""

import streamlit as st

import calculos as calc
import datos
import estilos as ui
import navegacion as nav
import graficos as g
import operaciones as ops
from vistas import comun

FILTROS = {"Todos": None, "Al día": "vigente", "Vencidos": "vencido", "Cancelados": "cancelado", "Anulados": "anulado"}


def _proxima(ev: dict) -> str:
    prox = ev["proxima"]
    return f"{ui.soles(prox['saldo'])} · {ui.fecha_dia(prox['vence'])}" if prox else "—"


def _cartera(db: dict, evals: dict) -> None:
    if not db["prestamos"]:
        ui.vacio("Aún no hay créditos", "Crea el primero en la pestaña «Nuevo crédito».")
        return
    # filtros con su conteo: sirven también de resumen de la cartera
    conteo = {k: sum(1 for p in db["prestamos"] if v is None or evals[p["id"]]["estado"] == v) for k, v in FILTROS.items()}
    visibles = [k for k in FILTROS if k == "Todos" or conteo[k]]
    if st.session_state.get("filtro_prestamo") not in visibles:
        st.session_state["filtro_prestamo"] = "Todos"
    filtro = nav.pestanas(visibles, "filtro_prestamo", etiquetas={k: f"{k} ({conteo[k]})" for k in visibles})
    buscar = st.text_input("Buscar cliente", placeholder="Buscar por nombre del cliente", key="buscar_prestamo", label_visibility="collapsed").strip().lower()

    lista = []
    for p in sorted(db["prestamos"], key=lambda x: x["numero"]):
        if FILTROS[filtro] and evals[p["id"]]["estado"] != FILTROS[filtro]:
            continue
        if buscar and buscar not in comun.nombre_cliente(db, p["cliente_id"]).lower():
            continue
        lista.append(p)
    if not lista:
        ui.vacio("Sin créditos con ese filtro", "Cambia el estado o borra la búsqueda para ver más.")
        return

    ui.tabla(
        ["N.º", "Cliente", "Modalidad", "Desembolso", "Capital", "Próxima cuota", "Cobrado", "Saldo", "Estado"],
        [[f"{p['numero']:04d}", comun.nombre_cliente(db, p["cliente_id"]),
          comun.descripcion_credito(p), ui.fecha_txt(p["fecha_desembolso"]),
          ui.soles(p["monto"]), _proxima(evals[p["id"]]), ui.barra(evals[p["id"]]["avance"]), ui.soles(evals[p["id"]]["saldo"]),
          ui.chip_prestamo(evals[p["id"]]["estado"])] for p in lista],
        numericas=(4, 7), sin_corte=(0, 1, 3, 5), etiqueta="Cartera de créditos",
    )

    st.subheader("Detalle del crédito", anchor=False)
    ids = [p["id"] for p in lista]
    if st.session_state.get("prestamo_sel") not in ids:
        st.session_state.pop("prestamo_sel", None)
    sel = st.selectbox("Crédito", ids, format_func=lambda i: comun.etiqueta_prestamo(db, ops.buscar(db["prestamos"], i)), key="prestamo_sel", label_visibility="collapsed")
    p, ev = ops.buscar(db["prestamos"], sel), evals[sel]

    # lo que ya está en la tabla (capital, total, cobrado, saldo) no se repite: aquí va lo que la tabla no dice
    st.markdown(g.panel(f"Préstamo {p['numero']:04d} · {comun.nombre_cliente(db, p['cliente_id'])}",
                        g.avance(ev["pagado"], p["total"], detalle="del total a pagar" + (f" · {ui.soles(ev['vencido'])} vencido" if ev["vencido"] else "")),
                        f"Entregado el {ui.fecha_txt(p['fecha_desembolso'])} en {p['entrega']} · folio {p['folio_desembolso']} · "
                        + (f"interés {p['tasa']:g} % por mes × {p['meses']} meses = {ui.soles(p['total'] - p['monto'])}" if p.get("meses", 1) > 1
                         else f"interés {p['tasa']:g} % = {ui.soles(p['total'] - p['monto'])}")), unsafe_allow_html=True)
    st.markdown(g.cuotas(ev["cuotas"]), unsafe_allow_html=True)
    st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)

    if ev["estado"] in ("vigente", "vencido"):
        if st.button("Cobrar este crédito", type="primary", icon=":material/payments:"):
            st.session_state["cobro_prestamo"] = sel
            comun.ir_a("cobros")
    if ev["estado"] != "anulado":
        with st.expander("Anular este crédito"):
            st.caption("Solo se puede anular si no tiene cobros vigentes. El dinero vuelve a la caja y el folio queda registrado.")
            motivo = st.text_input("Motivo de la anulación", key=f"mot_anul_{sel}")
            if st.button("Anular crédito", key=f"anul_{sel}"):
                try:
                    ops.anular_prestamo(db, sel, motivo)
                except ValueError as e:
                    st.error(str(e))
                else:
                    datos.guardar(db)
                    ui.avisar("ok", "Crédito anulado.")
                    st.rerun()


MONTOS_RAPIDOS = (100, 200, 300, 500, 1000)
CLAVES_NUEVO = ("nc_monto", "nc_tasa", "nc_modalidad", "nc_meses", "nc_fecha", "nc_entrega", "nc_forzar")


def _poner_monto(valor: float) -> None:
    st.session_state["nc_monto"] = float(valor)


def _paso(n: int, titulo: str) -> None:
    st.markdown(f'<div class="m3k-paso"><span>{n}</span><b>{titulo}</b></div>', unsafe_allow_html=True)


def _nuevo(db: dict, hoy, evals: dict) -> None:
    activos = [c for c in db["clientes"] if c["activo"]]
    if not activos:
        ui.vacio("Primero registra un cliente", "Un crédito necesita un cliente activo.")
        if st.button("Ir a Clientes", icon=":material/group:"):
            comun.ir_a("clientes")
        return

    ids = [c["id"] for c in activos]
    previo = st.session_state.pop("nuevo_credito_cliente", None)
    if previo in ids:
        st.session_state["nc_cliente"] = previo
    if st.session_state.get("nc_cliente") not in ids:
        st.session_state.pop("nc_cliente", None)
    # valores iniciales en el estado de la sesión (así los atajos de monto pueden cambiarlos)
    st.session_state.setdefault("nc_monto", 0.0)
    st.session_state.setdefault("nc_tasa", float(db["config"].get("tasa_default", 20.0)))

    izq, der = st.columns([5, 6], gap="large")

    # ---------------- izquierda: los datos del crédito ----------------
    with izq:
        with st.container(border=True):
            _paso(1, "Cliente y monto")
            nombres = {c["id"]: f"{c['nombre']} · DNI {c['dni']}" for c in activos}
            cliente_id = st.selectbox("Cliente", ids, format_func=nombres.get, key="nc_cliente")
            vigentes = [p for p in db["prestamos"] if p["cliente_id"] == cliente_id and evals[p["id"]]["estado"] in ("vigente", "vencido")]
            if vigentes:
                deuda = sum(evals[p["id"]]["saldo"] for p in vigentes)
                atraso = any(evals[p["id"]]["estado"] == "vencido" for p in vigentes)
                (st.warning if atraso else st.info)(
                    f"Este cliente ya tiene {len(vigentes)} crédito(s) vigente(s) y debe {ui.soles(deuda)}" + (", con cuotas vencidas." if atraso else "."))
            monto = st.number_input("Monto del crédito (S/)", min_value=0.0, step=50.0, format="%.2f", key="nc_monto")
            atajos = st.columns(len(MONTOS_RAPIDOS))
            for col, v in zip(atajos, MONTOS_RAPIDOS):
                col.button(f"S/ {v:,}", key=f"nc_rapido_{v}", on_click=_poner_monto, args=(v,), use_container_width=True)
            tasa = st.number_input("Interés (%): total del periodo, o por mes si es mensual", min_value=0.0, max_value=100.0, step=1.0, key="nc_tasa")

        with st.container(border=True):
            _paso(2, "¿Cómo se paga?")
            modalidad = nav.pestanas(calc.modalidades_ofrecidas(), "nc_modalidad",
                                     etiquetas={k: calc.MODALIDADES[k]["nombre"] for k in calc.modalidades_ofrecidas()},
                                     iconos={"diario": ":material/today:", "semanal": ":material/date_range:", "mensual": ":material/calendar_month:"},
                                     ancho_completo=True)
            st.caption(calc.MODALIDADES[modalidad]["texto"] + (". Los domingos no se cuentan." if modalidad == "diario" else "."))
            meses = None
            if modalidad == "mensual":
                st.markdown("**¿Cuántos meses?**")
                meses = int(nav.pestanas(list(calc.MESES_MENSUAL), "nc_meses", etiquetas={m: f"{m} {'mes' if m == 1 else 'meses'}" for m in calc.MESES_MENSUAL},
                                         ancho_completo=True))

        with st.container(border=True):
            _paso(3, "Entrega del dinero")
            f0 = st.date_input("Fecha de desembolso", value=hoy, format="DD/MM/YYYY", key="nc_fecha")
            st.markdown("**¿Cómo se entrega?**")
            entrega = nav.pestanas(list(calc.ENTREGAS), "nc_entrega",
                                   iconos={"Efectivo": ":material/payments:", "Yape": ":material/smartphone:", "Plin": ":material/smartphone:",
                                           "Transferencia": ":material/account_balance:"}, ancho_completo=True)

    # ---------------- derecha: resumen en vivo y confirmación ----------------
    with der:
        _paso(4, "Resumen del crédito")
        if monto <= 0:
            st.markdown('<div class="m3k-simula"><div class="gran">🧮</div><b>Aquí verás la simulación</b>'
                        '<p>Escribe el monto, o elige uno de los atajos, y verás al instante:</p>'
                        '<ul><li>💵 cuánto paga el cliente en cada cuota</li><li>🧾 el total a pagar y el interés</li>'
                        '<li>📅 las fechas de cobro, antes de confirmar</li></ul></div>', unsafe_allow_html=True)
            return

        plan = calc.generar_cronograma(monto, tasa, modalidad, f0, None, meses)
        total = calc.total_a_pagar(monto, tasa, meses or 1)
        if modalidad == "mensual":
            nota_cuota = (f"{len(plan)} cuota(s): solo interés, y en la última el capital" if len(plan) > 1 else "1 cuota: interés y capital")
            nota_interes = f"{tasa:g} % por mes" + (f" × {meses} meses" if meses > 1 else "")
            pie = "Cada cuota vence el mismo día de cada mes; si cae domingo, pasa al lunes."
        else:
            iguales = len({q["monto"] for q in plan[:-1]}) <= 1
            nota_cuota = f"{len(plan)} cuota(s)" + ("" if iguales else " · la última ajusta céntimos")
            nota_interes = f"{tasa:g} % sobre el capital"
            pie = "Los domingos no se cuentan: el plazo son 24 días de trabajo (lunes a sábado)."
        ui.kpis([
            {"etiqueta": "Cuota" if modalidad != "mensual" or len(plan) == 1 else "Cuota mensual", "valor": ui.soles(plan[0]["monto"]), "heroe": True, "nota": nota_cuota},
            {"etiqueta": "Total a pagar", "valor": ui.soles(total), "tono": "info", "nota": f"Hasta el {ui.fecha_txt(plan[-1]['vence'])}"},
            {"etiqueta": "Interés", "valor": ui.soles(total - monto), "tono": "ok", "nota": nota_interes},
        ])
        tarjetas = g.panel("Cuándo se cobra", g.cuotas([{**q, "pagado": 0.0, "estado": "pendiente", "atraso": 0} for q in plan]), pie)
        if len(plan) > 8:  # 24 tarjetas seguidas cansan: se resumen y se pueden desplegar
            st.markdown(f"**{len(plan)} cuotas de {ui.soles(plan[0]['monto'])}**, de lunes a sábado: del {ui.fecha_dia(plan[0]['vence'])} al {ui.fecha_dia(plan[-1]['vence'])}.")
            with st.expander("Ver todas las fechas de cobro"):
                st.markdown(tarjetas, unsafe_allow_html=True)
        else:
            st.markdown(tarjetas, unsafe_allow_html=True)

        liquidez = calc.resumen_caja(db)["liquidez"]
        quedara = round(liquidez - monto, 2)
        forzar = True
        if quedara < 0:
            st.warning(f"La caja tiene {ui.soles(liquidez)}, menos que el monto a entregar. Revisa la caja o registra un aporte de capital.")
            forzar = st.checkbox("Entregar de todos modos", key="nc_forzar")
        else:
            st.caption(f"Caja ahora {ui.soles(liquidez)}. Después de entregar quedará {ui.soles(quedara)}.")
        if st.button(f"Confirmar y entregar {ui.soles(monto)}", type="primary", disabled=not forzar, icon=":material/check_circle:", use_container_width=True):
            try:
                p = ops.crear_prestamo(db, cliente_id, monto, tasa, modalidad, f0, entrega, meses=meses)
            except ValueError as e:
                st.error(str(e))
            else:
                datos.guardar(db)
                for k in CLAVES_NUEVO:  # el próximo crédito empieza con el formulario limpio
                    st.session_state.pop(k, None)
                st.session_state["_vista_prestamos"] = "Cartera"
                st.session_state["prestamo_sel"] = p["id"]
                ui.avisar("ok", f"Crédito {p['numero']:04d} registrado ({p['folio_desembolso']}).")
                st.rerun()


def mostrar() -> None:
    db = datos.cargar()
    hoy = calc.hoy()
    evals = calc.evaluar_cartera(db, hoy)
    ui.encabezado("Préstamos", f"{len(db['prestamos'])} crédito(s) registrado(s)")

    destino = st.session_state.pop("_vista_prestamos", None)
    if destino:
        st.session_state["vista_prestamos"] = destino
    vista = nav.pestanas(["Cartera", "Nuevo crédito"], "vista_prestamos",
                         iconos={"Cartera": ":material/list_alt:", "Nuevo crédito": ":material/add_circle:"})
    st.divider()
    if vista == "Cartera":
        _cartera(db, evals)
    else:
        _nuevo(db, hoy, evals)
