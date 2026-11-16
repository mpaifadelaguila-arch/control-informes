"""Cierre mensual: verifica que todo cuadre, guarda las cifras del mes y bloquea nuevas operaciones en él."""

import streamlit as st

import calculos as calc
import contabilidad as cont
import datos
import estilos as ui
import operaciones as ops

ESTADOS = {"cerrado": ("Cerrado", "ok"), "abierto": ("Pendiente de cierre", "aviso"), "en curso": ("En curso", "neutro")}


def _verificaciones(db: dict, hoy) -> list[tuple[str, bool, str]]:
    lib = cont.asientos(db, hoy, hoy)
    bc = cont.balance_comprobacion(lib)
    bal = cont.balance_general(lib, hoy)
    caja_ok = cont.saldo(lib, "101") == calc.resumen_caja(db)["liquidez"]
    cxc = cont.cuentas_por_cobrar(db, calc.evaluar_cartera(db, hoy), hoy)
    return [
        ("El libro diario cuadra", bc["cuadra"], "Total debe = total haber en todos los asientos."),
        ("Activo = Patrimonio", bal["cuadra"], "El balance general está equilibrado."),
        ("Caja del libro = caja de la app", caja_ok, "La cuenta 101 coincide con el saldo disponible de Caja."),
        ("Cuentas por cobrar = libro mayor", cxc["cuadra"], "El detalle por cliente coincide con la cartera y los intereses no devengados del libro."),
    ]


def mostrar() -> None:
    db = datos.cargar()
    hoy = calc.hoy()
    ui.encabezado("Cierre mensual", "Cada mes cerrado queda protegido: no se pueden registrar operaciones con fecha en él")
    periodos = cont.estado_periodos(db, hoy)
    if not periodos or not (db["prestamos"] or db["movimientos"] or db["config"]["capital_base"]):
        ui.vacio("Aún no hay meses para cerrar", "Registra operaciones y aquí aparecerá cada mes con su estado.")
        return

    filas = []
    for f in periodos:
        cifras = f["cierre"]["cifras"] if f["cierre"] else cont.instantanea(db, f["periodo"], hoy)
        etiqueta, tono = ESTADOS[f["estado"]]
        filas.append([cont.nombre_mes(f["periodo"]), ui.chip(etiqueta, tono), ui.monto(cifras["caja"]), ui.monto(cifras["cartera"]),
                      ui.monto(cifras["ingresos"]), ui.monto(cifras["gastos"]), ui.monto(round(cifras["utilidad"], 2)),
                      ui.fecha_txt(f["cierre"]["cerrado"]) if f["cierre"] else "—"])
    ui.tabla(["Mes", "Estado", "Caja al cierre", "Cartera (121)", "Ingresos", "Gastos", "Utilidad", "Cerrado el"], filas, numericas=(2, 3, 4, 5, 6),
             etiqueta="Meses contables")
    st.caption("Los meses cerrados muestran las cifras guardadas al cerrar; los demás, las cifras de hoy.")

    difs = cont.diferencias_con_cierre(db, hoy)
    for d in difs:
        detalle = ", ".join(f"{k}: {a:,.2f} → {b:,.2f}" for k, (a, b) in d["cambios"].items())
        st.error(f"{cont.nombre_mes(d['periodo'])} ya cerrado cambió desde el cierre ({detalle}). Revisa la auditoría de Configuración.")

    cerrable = next((f for f in periodos if f["puede_cerrar"]), None)
    st.subheader("Cerrar un mes", anchor=False)
    if not cerrable:
        siguiente = next((f for f in periodos if f["estado"] == "en curso"), None)
        ui.vacio("No hay meses pendientes de cierre",
                 f"{cont.nombre_mes(siguiente['periodo'])} podrá cerrarse desde el día siguiente a su último día." if siguiente else "Todos los meses están cerrados.")
    else:
        verif = _verificaciones(db, hoy)
        st.markdown(f"**Mes a cerrar: {cont.nombre_mes(cerrable['periodo'])}**")
        ui.verificaciones(verif)
        todo_ok = all(ok for _, ok, _ in verif)
        if not todo_ok:
            st.error("Corrige las diferencias antes de cerrar el mes.")
        if st.button(f"Cerrar {cont.nombre_mes(cerrable['periodo'])}", type="primary", disabled=not todo_ok, icon=":material/lock:"):
            try:
                ops.cerrar_mes(db, cerrable["periodo"], hoy)
            except ValueError as e:
                st.error(str(e))
            else:
                datos.guardar(db)
                ui.avisar("ok", f"{cont.nombre_mes(cerrable['periodo'])} cerrado.")
                st.rerun()

    cerrados = sorted(db.get("cierres", {}))
    if cerrados:
        with st.expander("Reabrir el último mes cerrado"):
            ultimo = cerrados[-1]
            st.caption(f"Solo se puede reabrir el último mes cerrado ({cont.nombre_mes(ultimo)}). Queda anotado en la auditoría.")
            motivo = st.text_input("Motivo", key="motivo_reabrir")
            if st.button("Reabrir mes", key="reabrir"):
                try:
                    ops.reabrir_mes(db, ultimo, motivo)
                except ValueError as e:
                    st.error(str(e))
                else:
                    datos.guardar(db)
                    ui.avisar("ok", f"{cont.nombre_mes(ultimo)} reabierto.")
                    st.rerun()
