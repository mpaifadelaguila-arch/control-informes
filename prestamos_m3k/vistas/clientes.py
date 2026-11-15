"""Clientes: alta, edición, activación y búsqueda."""

import streamlit as st

import calculos as calc
import datos
import estilos as ui
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

    buscar = st.text_input("Buscar", placeholder="Nombre, DNI o teléfono", label_visibility="collapsed")
    q = buscar.strip().lower()
    lista = [c for c in db["clientes"] if not q or q in c["nombre"].lower() or q in c["dni"] or q in c.get("telefono", "")]
    if not lista:
        ui.vacio("Sin resultados", f"Ningún cliente coincide con «{buscar}». Prueba con otro nombre o con el DNI.")
        return

    for c in sorted(lista, key=lambda x: x["nombre"].lower()):
        suyos = [p for p in db["prestamos"] if p["cliente_id"] == c["id"]]
        activos = [p for p in suyos if evals[p["id"]]["estado"] in ("vigente", "vencido")]
        deuda = sum(evals[p["id"]]["saldo"] for p in activos)
        vencido = any(evals[p["id"]]["estado"] == "vencido" for p in activos)
        chips = ui.chip("Activo", "ok") if c["activo"] else ui.chip("Inactivo", "neutro")
        if vencido:
            chips += ui.chip("Con deuda vencida", "malo")
        with st.container(border=True):
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap">'
                f'<div><b>{ui.esc(c["nombre"])}</b><br><small style="color:{ui.TEXTO_SUAVE}">DNI {ui.esc(c["dni"])} · '
                f'{ui.esc(c.get("telefono") or "sin teléfono")}</small></div>'
                f'<div style="text-align:right">{chips}<br><small class="num" style="color:{ui.TEXTO_SUAVE}">'
                f'{len(activos)} crédito(s) activo(s) · debe {ui.soles(deuda)}</small></div></div>',
                unsafe_allow_html=True,
            )
            b1, b2 = st.columns(2)
            if b1.button("Nuevo crédito", key=f"nc_{c['id']}", disabled=not c["activo"], icon=":material/add_card:"):
                st.session_state["_vista_prestamos"] = "Nuevo crédito"
                st.session_state["nuevo_credito_cliente"] = c["id"]
                comun.ir_a("prestamos")
            if b2.button("Desactivar" if c["activo"] else "Activar", key=f"ac_{c['id']}"):
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
