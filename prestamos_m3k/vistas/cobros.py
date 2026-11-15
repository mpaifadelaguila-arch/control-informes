"""Registrar cobro: el flujo más usado, pensado para hacerse en pocos toques desde el teléfono."""

import streamlit as st

import calculos as calc
import datos
import estilos as ui
import operaciones as ops
from vistas import comun


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
            st.session_state["recibo_sel"] = ultimo["id"]
            comun.ir_a("recibos")

    activos = [p for p in db["prestamos"] if evals[p["id"]]["estado"] in ("vigente", "vencido")]
    if not activos:
        ui.vacio("No hay créditos por cobrar", "Cuando registres un crédito, aparecerá aquí para cobrar sus cuotas.")
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
        ui.vacio("Sin resultados", f"Ningún crédito activo coincide con «{busqueda}».")
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
        {"etiqueta": "Saldo del crédito", "valor": ui.soles(ev["saldo"]), "tono": "info",
         "nota": f"{ev['cuotas_con_saldo']} cuota(s) pendiente(s)"},
        {"etiqueta": "Vencido", "valor": ui.soles(ev["vencido"]), "tono": "malo" if ev["vencido"] else "ok",
         "nota": f"{ev['atraso_max']} días de atraso" if ev["vencido"] else "Al día"},
        {"etiqueta": "Mora pendiente", "valor": ui.soles(ev["mora_pendiente"]), "tono": "aviso" if ev["mora_pendiente"] else "ok"},
        {"etiqueta": "Próxima cuota", "valor": ui.soles(prox["saldo"]) if prox else "—",
         "nota": f"Vence {ui.fecha_txt(prox['vence'])}" if prox else "Crédito cancelado"},
    ])

    col1, col2 = st.columns(2)
    f_cobro = col1.date_input("Fecha del cobro", value=hoy, max_value=hoy, format="DD/MM/YYYY", key=f"fc_{sel}")
    metodo = col2.selectbox("Medio de pago", calc.METODOS_COBRO, key=f"mp_{sel}")

    pagos = [p for p in db["pagos"] if not p.get("anulado")]
    ev_f = calc.evaluar_prestamo(prestamo, pagos, f_cobro, float(db["config"].get("mora_diaria_pct", 0) or 0))
    deuda_total = round(ev_f["saldo"] + ev_f["mora_pendiente"], 2)
    sugerido = round(ev_f["vencido"] + ev_f["mora_pendiente"], 2) or (ev_f["proxima"]["saldo"] if ev_f["proxima"] else 0.0)
    monto = st.number_input("Monto cobrado (S/)", min_value=0.0, max_value=float(deuda_total), value=float(min(sugerido, deuda_total)),
                            step=10.0, format="%.2f", key=f"mc_{sel}_{f_cobro}")
    nota = st.text_input("Nota (opcional)", key=f"nt_{sel}", placeholder="Ej.: pagó con Yape")

    a_mora = min(monto, ev_f["mora_pendiente"])
    a_cuotas = round(monto - a_mora, 2)
    st.markdown(
        f'<div class="m3k-fila" style="--tono:{ui.TONOS["info"]}"><div><b class="num">{ui.soles(monto)}</b>'
        f'<small>{"A mora " + ui.soles(a_mora) + " · " if a_mora else ""}A cuotas {ui.soles(a_cuotas)}</small></div>'
        f'<div class="num">Quedará pendiente: <b>{ui.soles(max(0.0, round(deuda_total - monto, 2)))}</b></div></div>',
        unsafe_allow_html=True,
    )

    if st.button("Registrar cobro", type="primary", disabled=monto <= 0, icon=":material/check_circle:"):
        try:
            pago = ops.registrar_pago(db, sel, f_cobro, monto, metodo, nota, hoy_=hoy)
        except ValueError as e:
            st.error(str(e))
        else:
            datos.guardar(db)
            st.session_state["ultimo_pago"] = {"id": pago["id"], "folio": pago["folio"], "total": round(pago["monto_cuota"] + pago["monto_mora"], 2)}
            ui.avisar("ok", f"Cobro {pago['folio']} registrado.")
            st.rerun()

    with st.expander("Ver cronograma de cuotas"):
        ui.tabla(["N.º", "Vence", "Cuota", "Pagado", "Saldo", "Estado"],
                 [[c["n"], ui.fecha_txt(c["vence"]), ui.soles(c["monto"]), ui.soles(c["pagado"]), ui.soles(c["saldo"]), ui.chip_cuota(c["estado"])]
                  for c in ev["cuotas"]], numericas=(2, 3, 4), etiqueta="Cronograma de cuotas")
