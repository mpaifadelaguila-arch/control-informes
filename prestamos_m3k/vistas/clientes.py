"""Clientes: resumen, filtros, tarjeta por cliente con su deuda, alta, edición y activación."""

import streamlit as st

import calculos as calc
import datos
import estilos as ui
import navegacion as nav
import operaciones as ops
from vistas import comun


def _formulario(db: dict, cliente: dict | None, clave: str) -> None:
    """Formulario de alta (cliente=None) o de edición."""
    c = cliente or {}
    with st.form(clave, clear_on_submit=cliente is None):
        nombre = st.text_input("Nombre completo", value=c.get("nombre", ""), autocomplete="name")
        col1, col2 = st.columns(2)
        dni = col1.text_input("DNI", value=c.get("dni", ""), max_chars=8, placeholder="8 dígitos")
        tel = col2.text_input("Teléfono o WhatsApp", value=c.get("telefono", ""), autocomplete="tel")
        direccion = st.text_input("Dirección (opcional)", value=c.get("direccion", ""), autocomplete="street-address")
        if st.form_submit_button("Guardar cambios" if cliente else "Guardar cliente", type="primary"):
            try:
                if cliente:
                    ops.editar_cliente(db, cliente["id"], nombre, dni, tel, direccion)
                else:
                    ops.crear_cliente(db, nombre, dni, tel, direccion)
                datos.guardar(db)
                ui.avisar("ok", "Cliente guardado.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))


def mostrar() -> None:
    db = datos.cargar()
    evals = calc.evaluar_cartera(db, calc.hoy())
    ui.encabezado("Clientes", f"{len(db['clientes'])} registrado(s)")

    with st.expander("Nuevo cliente", expanded=not db["clientes"]):
        _formulario(db, None, "form_nuevo_cliente")

    if not db["clientes"]:
        ui.vacio("Todavía no hay clientes", "Completa el formulario de arriba para registrar el primero.")
        return

    resumen = {}
    for c in db["clientes"]:
        suyos = [p for p in db["prestamos"] if p["cliente_id"] == c["id"]]
        activos = [p for p in suyos if evals[p["id"]]["estado"] in ("vigente", "vencido")]
        resumen[c["id"]] = {
            "suyos": suyos, "activos": activos,
            "deuda": round(sum(evals[p["id"]]["saldo"] for p in activos), 2),
            "vencido": round(sum(evals[p["id"]]["vencido"] for p in activos), 2),
            "total": sum(p["total"] for p in activos), "cobrado": sum(evals[p["id"]]["pagado"] for p in activos),
        }
    con_deuda = [c for c in db["clientes"] if resumen[c["id"]]["activos"]]
    atrasados = [c for c in db["clientes"] if resumen[c["id"]]["vencido"] > 0]
    ui.kpis([
        {"etiqueta": "Clientes", "valor": str(len(db["clientes"])), "nota": f"{sum(1 for c in db['clientes'] if c['activo'])} activo(s)"},
        {"etiqueta": "Con crédito vigente", "valor": str(len(con_deuda)), "tono": "info",
         "nota": f"Te deben {ui.soles(sum(resumen[c['id']]['deuda'] for c in con_deuda))}"},
        {"etiqueta": "Con atraso", "valor": str(len(atrasados)), "tono": "malo" if atrasados else "ok",
         "nota": f"{ui.soles(sum(resumen[c['id']]['vencido'] for c in atrasados))} vencido" if atrasados else "Nadie atrasado"},
    ])

    filtros = {"Todos": lambda c: True, "Con crédito vigente": lambda c: bool(resumen[c["id"]]["activos"]),
               "Con atraso": lambda c: resumen[c["id"]]["vencido"] > 0, "Sin crédito vigente": lambda c: not resumen[c["id"]]["activos"],
               "Inactivos": lambda c: not c["activo"]}
    conteo = {k: sum(1 for c in db["clientes"] if f(c)) for k, f in filtros.items()}
    visibles = [k for k in filtros if k == "Todos" or conteo[k]]
    if st.session_state.get("filtro_cliente") not in visibles:
        st.session_state["filtro_cliente"] = "Todos"
    filtro = nav.pestanas(visibles, "filtro_cliente", etiquetas={k: f"{k} ({conteo[k]})" for k in visibles})
    buscar = st.text_input("Buscar", placeholder="Buscar por nombre, DNI o teléfono", label_visibility="collapsed")
    q = buscar.strip().lower()
    lista = [c for c in db["clientes"] if filtros[filtro](c) and (not q or q in c["nombre"].lower() or q in c["dni"] or q in c.get("telefono", ""))]
    if not lista:
        ui.vacio("Sin resultados", "Ningún cliente coincide. Prueba con otro filtro, nombre o DNI.")
        return

    for c in sorted(lista, key=lambda x: x["nombre"].lower()):
        r = resumen[c["id"]]
        suyos, activos = r["suyos"], r["activos"]
        chips = str(ui.chip("Activo", "ok") if c["activo"] else ui.chip("Inactivo", "neutro"))
        if r["vencido"] > 0:
            chips += str(ui.chip("Con atraso", "malo"))
        iniciales = "".join(w[0] for w in c["nombre"].split()[:2]).upper() or "?"
        avance = (r["cobrado"] / r["total"]) if r["total"] else 0
        with st.container(border=True):
            st.markdown(
                f'<div class="m3k-cliente"><div class="av">{ui.esc(iniciales)}</div>'
                f'<div class="dat"><b>{ui.esc(c["nombre"])}</b><small>DNI {ui.esc(c["dni"])} · {ui.esc(c.get("telefono") or "sin teléfono")}</small></div>'
                f'<div class="est">{chips}</div>'
                f'<div class="monto"><b class="num">{ui.soles(r["deuda"]) if activos else "Sin deuda"}</b>'
                f'<small>{len(activos)} crédito(s) vigente(s) · {len(suyos)} en total</small>'
                f'{ui.barra(avance) if activos else ""}</div></div>',
                unsafe_allow_html=True,
            )
            b1, b2, b3 = st.columns(3)
            if b1.button("Nuevo crédito", key=f"nc_{c['id']}", disabled=not c["activo"], icon=":material/add_card:", use_container_width=True):
                st.session_state["_vista_prestamos"] = "Nuevo crédito"
                st.session_state["nuevo_credito_cliente"] = c["id"]
                comun.ir_a("prestamos")
            if b2.button("Ver sus créditos", key=f"vc_{c['id']}", disabled=not suyos, icon=":material/receipt_long:", use_container_width=True):
                st.session_state["_vista_prestamos"] = "Cartera"
                st.session_state["filtro_prestamo"] = "Todos"
                st.session_state["buscar_prestamo"] = c["nombre"]
                comun.ir_a("prestamos")
            if b3.button("Desactivar" if c["activo"] else "Activar", key=f"ac_{c['id']}", use_container_width=True):
                ops.cambiar_estado_cliente(db, c["id"], not c["activo"])
                datos.guardar(db)
                st.rerun()
            with st.expander("Editar datos u otras opciones"):
                _formulario(db, c, f"form_{c['id']}")
                if suyos:
                    st.caption("Tiene créditos registrados, por eso solo se puede desactivar.")
                else:
                    seguro = st.checkbox("Confirmo que quiero eliminar a este cliente", key=f"ok_del_{c['id']}")
                    if st.button("Eliminar cliente", key=f"del_{c['id']}", disabled=not seguro):
                        ops.eliminar_cliente(db, c["id"])
                        datos.guardar(db)
                        ui.avisar("ok", "Cliente eliminado.")
                        st.rerun()
