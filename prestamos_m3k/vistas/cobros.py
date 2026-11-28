"""Registrar cobro: eliges las cuotas a cobrar en el cronograma y el monto se calcula solo."""

import streamlit as st

import calculos as calc
import datos
import estilos as ui
import navegacion as nav
import operaciones as ops
from vistas import comun, recibos


def _clave(sel: str, n: int) -> str:
    return f"cq_{sel}_{n}"


def _marcar_hasta(sel: str, pendientes: list[dict], hasta: int) -> None:
    """Marca las cuotas pendientes hasta la número `hasta` (inclusive) y desmarca las siguientes."""
    for c in pendientes:
        st.session_state[_clave(sel, c["n"])] = c["n"] <= hasta


def _inicializar_seleccion(sel: str, pendientes: list[dict]) -> None:
    """La primera vez que se abre un crédito se proponen las cuotas vencidas, o la próxima si está al día."""
    # Streamlit olvida las casillas de un crédito si se muestra otro; sin casillas guardadas se vuelve a proponer.
    if not pendientes or any(str(k).startswith(f"cq_{sel}_") for k in st.session_state):
        return
    vencidas = [c["n"] for c in pendientes if c["estado"] == "vencida"]
    _marcar_hasta(sel, pendientes, max(vencidas) if vencidas else pendientes[0]["n"])


def _atajo(sel: str, pendientes: list[dict], cual: str) -> None:
    if cual == "vencidas":
        vencidas = [c["n"] for c in pendientes if c["estado"] == "vencida"]
        _marcar_hasta(sel, pendientes, max(vencidas) if vencidas else 0)
    elif cual == "proxima":
        _marcar_hasta(sel, pendientes, pendientes[0]["n"] if pendientes else 0)
    else:
        _marcar_hasta(sel, pendientes, pendientes[-1]["n"] if pendientes else 0)


def _al_marcar(sel: str, pendientes: list[dict], n: int) -> None:
    """Marcar una cuota marca las anteriores; desmarcarla desmarca las posteriores (se cobra de la más antigua a la más nueva)."""
    marcada = st.session_state.get(_clave(sel, n), False)
    _marcar_hasta(sel, pendientes, n if marcada else n - 1)


def _limpiar_seleccion(sel: str) -> None:
    for k in [k for k in st.session_state if str(k).startswith(f"cq_{sel}_")]:
        del st.session_state[k]


def mostrar() -> None:
    db = datos.cargar()
    hoy = calc.hoy()
    evals = calc.evaluar_cartera(db, hoy)
    ui.encabezado("Registrar cobro", "Elige el crédito, confirma el monto y listo")

    ultimo = st.session_state.get("ultimo_pago")
    if ultimo:
        a, b = st.columns([3, 1], vertical_alignment="center")
        a.success(f"Último cobro registrado: {ultimo['folio']} por {ui.soles(ultimo['total'])}.")
        if b.button("Ver recibo", icon=":material/receipt_long:"):
            recibos.ventana(ultimo["id"])

    activos = [p for p in db["prestamos"] if evals[p["id"]]["estado"] in ("vigente", "vencido")]
    if not activos:
        ui.vacio("No hay créditos por cobrar", "Cuando registres un crédito, aparecerá aquí para cobrar sus cuotas.", "💵")
        if st.button("Crear un crédito", type="primary", icon=":material/add_card:"):
            st.session_state["_vista_prestamos"] = "Nuevo crédito"
            comun.ir_a("prestamos")
        return

    busqueda = st.text_input("Buscar cliente", placeholder="Nombre, DNI o teléfono").strip().lower()
    clientes = {c["id"]: c for c in db["clientes"]}

    def coincide(p):
        c = clientes.get(p["cliente_id"], {})
        return not busqueda or busqueda in c.get("nombre", "").lower() or busqueda in c.get("dni", "") or busqueda in c.get("telefono", "")

    candidatos = [p for p in activos if coincide(p)]
    if not candidatos:
        ui.vacio("Sin resultados", f"Ningún crédito activo coincide con «{busqueda}».", "🔍")
        return
    ids = [p["id"] for p in candidatos]

    elegido = st.session_state.pop("cobro_prestamo", None)
    if elegido in ids:
        st.session_state["cobro_sel"] = elegido
    if st.session_state.get("cobro_sel") not in ids:
        st.session_state.pop("cobro_sel", None)

    def rotulo(id_):
        p = ops.buscar(db["prestamos"], id_)
        ev = evals[id_]
        marca = " · VENCIDO" if ev["estado"] == "vencido" else ""
        return f"{comun.etiqueta_prestamo(db, p)} · debe {ui.soles(ev['saldo'])}{marca}"

    sel = st.selectbox("Crédito", ids, format_func=rotulo, key="cobro_sel")
    prestamo = ops.buscar(db["prestamos"], sel)
    ev = evals[sel]
    prox = ev["proxima"]

    ui.kpis([
        {"etiqueta": "Saldo del crédito", "valor": ui.soles(ev["saldo"]), "tono": "info", "nota": f"{ev['cuotas_con_saldo']} cuota(s) pendiente(s)"},
        {"etiqueta": "Vencido", "valor": ui.soles(ev["vencido"]), "tono": "malo" if ev["vencido"] else "ok",
         "nota": f"{ev['atraso_max']} días de atraso" if ev["vencido"] else "Al día"},
        {"etiqueta": "Próxima cuota", "valor": ui.soles(prox["saldo"]) if prox else "—",
         "nota": f"Vence {ui.fecha_dia(prox['vence'])}" if prox else "Crédito cancelado"},
    ])

    izq, der = st.columns([3, 2], gap="large")
    with izq:
        f_cobro = st.date_input("Fecha del cobro", value=hoy, max_value=hoy, format="DD/MM/YYYY", key=f"fc_{sel}")
        pagos = [p for p in db["pagos"] if not p.get("anulado")]
        ev_f = calc.evaluar_prestamo(prestamo, pagos, f_cobro, float(db["config"].get("mora_diaria_pct", 0) or 0))
        pendientes = [c for c in ev_f["cuotas"] if c["saldo"] > 0.004]
        mora = ev_f["mora_pendiente"]

        # ---- elegir cuotas: se cobran siempre de la más antigua a la más nueva ----
        st.subheader("¿Qué cuotas se cobran?", anchor=False)
        _inicializar_seleccion(sel, pendientes)
        a1, a2, a3 = st.columns(3)
        a1.button("Vencidas", on_click=_atajo, args=(sel, pendientes, "vencidas"), icon=":material/schedule:", use_container_width=True)
        a2.button("Próxima", on_click=_atajo, args=(sel, pendientes, "proxima"), icon=":material/looks_one:", use_container_width=True)
        a3.button("Todas", on_click=_atajo, args=(sel, pendientes, "todas"), icon=":material/done_all:", use_container_width=True)
        st.caption("Marca una cuota y se marcan también las anteriores, porque siempre se cobra desde la más antigua.")

        pagadas = [c for c in ev_f["cuotas"] if c["saldo"] <= 0.004]
        if pagadas:
            lista = " · ".join(f"Cuota {c['n']} ({ui.fecha_dia(c['vence'])})" for c in pagadas)
            st.markdown(f'<div class="m3k-pagadas">✅ <b>Ya pagadas:</b> {ui.esc(lista)}</div>', unsafe_allow_html=True)

        for c in pendientes:
            vence = c["vence"] if not isinstance(c["vence"], str) else calc.fecha(c["vence"])
            dias = (vence - f_cobro).days
            if dias < 0:
                cuando, tono = f"venció hace {-dias} día(s)", ui.TONOS["malo"]
            elif dias == 0:
                cuando, tono = "vence hoy", ui.TONOS["aviso"]
            else:
                cuando, tono = f"vence en {dias} día(s)", ui.TEXTO_SUAVE
            with st.container(key=f"tarj_cuota_{c['n']}"):
                fila = st.columns([1.6, 2.6, 2, 1.6], vertical_alignment="center")
                fila[0].checkbox(f"Cuota {c['n']} de {len(ev_f['cuotas'])}", key=_clave(sel, c["n"]), on_change=_al_marcar, args=(sel, pendientes, c["n"]))
                fila[1].markdown(f'<b>{ui.fecha_dia(c["vence"])}</b><br><small style="color:{tono};font-weight:600">{cuando}</small>', unsafe_allow_html=True)
                detalle = f"Pagado {ui.soles(c['pagado'])} de {ui.soles(c['monto'])}" if c["pagado"] > 0.004 else ""
                fila[2].markdown(f'{ui.chip_cuota(c["estado"])}' + (f'<br><small style="color:{ui.TEXTO_SUAVE}">{ui.esc(detalle)}</small>' if detalle else ""),
                                 unsafe_allow_html=True)
                fila[3].markdown(f'<div class="num" style="text-align:right;font-size:1.15rem"><b>{ui.soles(c["saldo"])}</b></div>', unsafe_allow_html=True)

        marcadas = [c for c in pendientes if st.session_state.get(_clave(sel, c["n"]))]
        suma_cuotas = round(sum(c["saldo"] for c in marcadas), 2)
        total_elegido = round(suma_cuotas + (mora if marcadas or not pendientes else 0.0), 2)
        deuda_total = round(ev_f["saldo"] + mora, 2)

    with der:
        with st.container(key="cobro_resumen"):
            st.markdown('<div style="font-size:.875rem;margin-bottom:.3rem">Medio de pago</div>', unsafe_allow_html=True)
            metodo = nav.pestanas(list(calc.METODOS_COBRO), f"mp_{sel}", ancho_completo=True,
                                  iconos={"Efectivo": ":material/payments:"})
            if mora:
                st.info(f"Este crédito tiene mora pendiente de {ui.soles(mora)}. Se cobra primero, antes de las cuotas.")

            # ---- monto: lo calcula la selección; el abono parcial es opcional ----
            parcial = st.toggle("Cobrar otro monto (abono parcial)", key=f"parcial_{sel}",
                                help="Úsalo si el cliente paga menos que las cuotas marcadas. El monto se aplica desde la cuota más antigua.")
            if parcial:
                monto = st.number_input("Monto cobrado (S/)", min_value=0.0, max_value=float(deuda_total), value=float(min(total_elegido, deuda_total)),
                                        step=10.0, format="%.2f", key=f"mc_{sel}_{total_elegido}")
            else:
                monto = total_elegido
            nota = st.text_input("Nota (opcional)", key=f"nt_{sel}", placeholder="Ej.: pagó con Yape")

            a_mora = min(monto, mora)
            a_cuotas = round(monto - a_mora, 2)
            detalle_cuotas = f"{len(marcadas)} cuota(s) marcada(s)" if not parcial else "abono parcial"
            st.markdown(
                f'<div class="m3k-fila" style="--tono:{ui.TONOS["ok"] if monto > 0 else ui.TONOS["neutro"]}"><div>'
                f'<small>Vas a cobrar</small><b class="num" style="font-size:1.5rem">{ui.soles(monto)}</b>'
                f'<small>{"Mora " + ui.soles(a_mora) + " + " if a_mora else ""}cuotas {ui.soles(a_cuotas)} · {detalle_cuotas}</small></div>'
                f'<div class="num"><small>Quedará pendiente</small><b style="display:block">{ui.soles(max(0.0, round(deuda_total - monto, 2)))}</b></div></div>',
                unsafe_allow_html=True,
            )

            st.markdown('<div style="height:.9rem"></div>', unsafe_allow_html=True)
            if st.button("Registrar cobro", key="cobro_registrar", type="primary", disabled=monto <= 0, icon=":material/check_circle:", use_container_width=True):
                try:
                    pago = ops.registrar_pago(db, sel, f_cobro, monto, metodo, nota, hoy_=hoy)
                except ValueError as e:
                    st.error(str(e))
                else:
                    datos.guardar(db)
                    _limpiar_seleccion(sel)
                    st.session_state["ultimo_pago"] = {"id": pago["id"], "folio": pago["folio"], "total": round(pago["monto_cuota"] + pago["monto_mora"], 2)}
                    ui.avisar("ok", f"Cobro {pago['folio']} registrado.")
                    st.rerun()
