"""Préstamos: cartera con filtros y detalle por cuotas, y el simulador para crear un crédito nuevo."""

import streamlit as st

import calculos as calc
import datos
import estilos as ui
import graficos as g
import operaciones as ops
from vistas import comun

FILTROS = {"Todos": None, "Al día": "vigente", "Vencidos": "vencido", "Cancelados": "cancelado", "Anulados": "anulado"}


def _cartera(db: dict, evals: dict) -> None:
    if not db["prestamos"]:
        ui.vacio("Aún no hay créditos", "Crea el primero en la pestaña «Nuevo crédito».")
        return
    # filtros con su conteo: sirven también de resumen de la cartera
    conteo = {k: sum(1 for p in db["prestamos"] if v is None or evals[p["id"]]["estado"] == v) for k, v in FILTROS.items()}
    visibles = [k for k in FILTROS if k == "Todos" or conteo[k]]
    if st.session_state.get("filtro_prestamo") not in visibles:
        st.session_state["filtro_prestamo"] = "Todos"
    filtro = st.radio("Estado", visibles, format_func=lambda k: f"{k} ({conteo[k]})", horizontal=True, key="filtro_prestamo", label_visibility="collapsed")
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
        ["N.º", "Cliente", "Modalidad", "Desembolso", "Capital", "Total", "Cobrado", "Saldo", "Estado"],
        [[f"{p['numero']:04d}", comun.nombre_cliente(db, p["cliente_id"]),
          f"{comun.nombre_modalidad(p['modalidad'])} · {len(p['cuotas'])} cuota(s)", ui.fecha_txt(p["fecha_desembolso"]),
          ui.soles(p["monto"]), ui.soles(p["total"]), ui.barra(evals[p["id"]]["avance"]), ui.soles(evals[p["id"]]["saldo"]),
          ui.chip_prestamo(evals[p["id"]]["estado"])] for p in lista],
        numericas=(4, 5, 7), sin_corte=(0, 1, 3), etiqueta="Cartera de créditos",
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
                        f"interés {p['tasa']:g} % = {ui.soles(p['total'] - p['monto'])}"), unsafe_allow_html=True)
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


def _nuevo(db: dict, hoy) -> None:
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
    nombres = {c["id"]: f"{c['nombre']} · DNI {c['dni']}" for c in activos}
    cliente_id = st.selectbox("Cliente", ids, format_func=nombres.get, key="nc_cliente")

    col1, col2 = st.columns(2)
    monto = col1.number_input("Monto del crédito (S/)", min_value=0.0, value=0.0, step=50.0, format="%.2f", key="nc_monto")
    tasa = col2.number_input("Interés total del periodo (%)", min_value=0.0, max_value=100.0,
                             value=float(db["config"].get("tasa_default", 20.0)), step=1.0, key="nc_tasa")
    modalidad = st.radio("Modalidad", list(calc.MODALIDADES), horizontal=True, key="nc_modalidad",
                         format_func=lambda k: calc.MODALIDADES[k]["nombre"])
    st.caption(calc.MODALIDADES[modalidad]["texto"] + ". Los domingos no se cuentan.")
    n_cuotas = None
    if modalidad == "semanal":
        n_cuotas = int(st.number_input("Número de cuotas semanales", min_value=1, max_value=8, value=calc.CUOTAS_SEMANALES[0], step=1, key="nc_ncuotas"))
    col3, col4 = st.columns(2)
    f0 = col3.date_input("Fecha de desembolso", value=hoy, format="DD/MM/YYYY", key="nc_fecha")
    entrega = col4.selectbox("Forma de entrega", calc.ENTREGAS, key="nc_entrega")

    if monto <= 0:
        ui.vacio("Escribe el monto para simular", "Verás la cuota, el total y el cronograma antes de confirmar.")
        return

    plan = calc.generar_cronograma(monto, tasa, modalidad, f0, n_cuotas)
    total = calc.total_a_pagar(monto, tasa)
    iguales = len({q["monto"] for q in plan[:-1]}) <= 1
    ui.kpis([
        {"etiqueta": "Cuota", "valor": ui.soles(plan[0]["monto"]), "nota": f"{len(plan)} cuota(s)" + ("" if iguales else " · la última ajusta céntimos")},
        {"etiqueta": "Total a pagar", "valor": ui.soles(total), "tono": "info", "nota": f"Hasta el {ui.fecha_txt(plan[-1]['vence'])}"},
        {"etiqueta": "Interés", "valor": ui.soles(total - monto), "tono": "ok", "nota": f"{tasa:g} % sobre el capital"},
    ])
    st.caption("Los domingos no se cuentan: el plazo son 24 días de trabajo (lunes a sábado).")
    st.markdown(g.panel("Cronograma proyectado", g.cuotas([{**q, "pagado": 0.0, "estado": "pendiente", "atraso": 0} for q in plan])), unsafe_allow_html=True)

    liquidez = calc.resumen_caja(db)["liquidez"]
    forzar = True
    if liquidez < monto:
        st.warning(f"La caja tiene {ui.soles(liquidez)}, menos que el monto a entregar. Revisa la caja o registra un aporte de capital.")
        forzar = st.checkbox("Entregar de todos modos", key="nc_forzar")
    if st.button("Confirmar y registrar desembolso", type="primary", disabled=not forzar, icon=":material/check_circle:"):
        try:
            p = ops.crear_prestamo(db, cliente_id, monto, tasa, modalidad, f0, entrega, n_cuotas)
        except ValueError as e:
            st.error(str(e))
        else:
            datos.guardar(db)
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
    vista = st.radio("Vista", ["Cartera", "Nuevo crédito"], horizontal=True, key="vista_prestamos", label_visibility="collapsed")
    if vista == "Cartera":
        _cartera(db, evals)
    else:
        _nuevo(db, hoy)
