"""Clientes: directorio con alta, edición y activación. Los montos y cuotas viven en Préstamos y Cuentas por cobrar:
aquí solo se muestra una señal de situación (al día, con atraso o sin créditos) y atajos hacia esos apartados."""

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
    activos_n = sum(1 for c in db["clientes"] if c["activo"])
    ui.encabezado("Clientes", f"{len(db['clientes'])} registrado(s) · {activos_n} activo(s)")

    with st.expander("Nuevo cliente", expanded=not db["clientes"]):
        _formulario(db, None, "form_nuevo_cliente")

    if not db["clientes"]:
        ui.vacio("Todavía no hay clientes", "Completa el formulario de arriba para registrar el primero.", "👥")
        return

    resumen = {}
    for c in db["clientes"]:
        suyos = [p for p in db["prestamos"] if p["cliente_id"] == c["id"]]
        activos = [p for p in suyos if evals[p["id"]]["estado"] in ("vigente", "vencido")]
        resumen[c["id"]] = {"suyos": suyos, "activos": activos, "vencido": round(sum(evals[p["id"]]["vencido"] for p in activos), 2)}

    filtros = {"Todos": lambda c: True, "Activos": lambda c: c["activo"],
               "Con atraso": lambda c: resumen[c["id"]]["vencido"] > 0, "Inactivos": lambda c: not c["activo"]}
    conteo = {k: sum(1 for c in db["clientes"] if f(c)) for k, f in filtros.items()}
    visibles = [k for k in filtros if k == "Todos" or conteo[k]]
    if st.session_state.get("filtro_cliente") not in visibles:
        st.session_state["filtro_cliente"] = "Todos"
    filtro = nav.pestanas(visibles, "filtro_cliente", etiquetas={k: f"{k} ({conteo[k]})" for k in visibles})
    buscar = st.text_input("Buscar", placeholder="Buscar por nombre, DNI o teléfono", label_visibility="collapsed")
    q = buscar.strip().lower()
    lista = [c for c in db["clientes"] if filtros[filtro](c) and (not q or q in c["nombre"].lower() or q in c["dni"] or q in c.get("telefono", ""))]
    if not lista:
        ui.vacio("Sin resultados", "Ningún cliente coincide. Prueba con otro filtro, nombre o DNI.", "🔍")
        return

    orden = sorted(lista, key=lambda x: x["nombre"].lower())
    for ini in range(0, len(orden), 2):
        columnas = st.columns(2)
        for columna, c in zip(columnas, orden[ini:ini + 2]):
            with columna:
                r = resumen[c["id"]]
                suyos, activos = r["suyos"], r["activos"]
                if not c["activo"]:
                    estado, clase = "Inactivo", "off"
                elif r["vencido"] > 0:
                    estado, clase = "Con atraso", "mal"
                elif activos:
                    estado, clase = "Al día", "ok"
                else:
                    estado, clase = "Sin créditos", "off"
                iniciales = "".join(w[0] for w in c["nombre"].split()[:2]).upper() or "?"
                n = len(suyos)
                sub = "Sin créditos registrados" if n == 0 else f"{n} crédito{'s' if n != 1 else ''} registrado{'s' if n != 1 else ''}"

                def dato(icono, etq, val):
                    return (f'<div class="it"><i class="ic">{icono}</i><div><em>{etq}</em>'
                            f'<b>{ui.esc(val) if val else "—"}</b></div></div>')
                contacto = (dato("badge", "DNI", c["dni"]) + dato("call", "Teléfono", c.get("telefono"))
                            + dato("location_on", "Dirección", c.get("direccion")))
                activo_txt = "Activo" if c["activo"] else "Inactivo"
                with st.container(key=f"ficha_{c['id']}"):
                    st.markdown(
                        f'<div class="f-notch"><span class="f-pill {clase}">{estado}</span></div>'
                        f'<div class="f-cab"><div class="av">{ui.esc(iniciales)}</div><span>Cliente</span></div>'
                        f'<div class="f-panel"><div class="f-est"><span>• {activo_txt.upper()}</span>'
                        f'<i class="ic">{"check_circle" if c["activo"] else "pause_circle"}</i></div>{contacto}</div>'
                        f'<div class="f-nom"><b>{ui.esc(c["nombre"])}</b><small>{sub}</small></div>',
                        unsafe_allow_html=True,
                    )
                    _, b1, b2, _ = st.columns([1, 2, 2, 1])
                    if b1.button("Créditos", key=f"vc_{c['id']}", disabled=not suyos, icon=":material/receipt_long:", use_container_width=True):
                        st.session_state["_vista_prestamos"] = "Cartera"
                        st.session_state["filtro_prestamo"] = "Todos"
                        st.session_state["buscar_prestamo"] = c["nombre"]
                        comun.ir_a("prestamos")
                    if b2.button("Nuevo crédito", key=f"nc_{c['id']}", disabled=not c["activo"], icon=":material/add:", use_container_width=True):
                        st.session_state["_vista_prestamos"] = "Nuevo crédito"
                        st.session_state["nuevo_credito_cliente"] = c["id"]
                        comun.ir_a("prestamos")
                    with st.expander("Editar datos u otras opciones"):
                        if st.button("Desactivar cliente" if c["activo"] else "Activar cliente", key=f"ac_{c['id']}"):
                            ops.cambiar_estado_cliente(db, c["id"], not c["activo"])
                            datos.guardar(db)
                            st.rerun()
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
