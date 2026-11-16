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
        ("Los asientos cuadran", bc["cuadra"], "El total del Debe es igual al del Haber."),
        ("Lo que tienes = de dónde viene", bal["cuadra"], "Los dos totales de la situación del negocio son iguales."),
        ("Caja contable = Caja de la app", caja_ok, "La caja del libro coincide con el saldo disponible de Caja."),
        ("Lo que te deben = cuentas por cobrar", cxc["cuadra"], "El detalle por cliente coincide con lo anotado en los libros."),
    ]


def seccion(db: dict, hoy) -> None:
    """Cierre de mes: verifica que todo cuadre, guarda las cifras y bloquea nuevas operaciones con fecha en ese mes."""
    periodos = cont.estado_periodos(db, hoy)
    cerrados = sorted(db.get("cierres", {}))
    if not periodos:
        st.caption("Aún no hay meses para cerrar.")
        return
    st.caption("Un mes cerrado queda protegido: no se pueden registrar operaciones con fecha en él. "
               + (f"Cerrados: {', '.join(cont.nombre_mes(c) for c in cerrados)}." if cerrados else "Todavía no has cerrado ningún mes."))

    difs = cont.diferencias_con_cierre(db, hoy)
    for d in difs:
        detalle = ", ".join(f"{k}: {a:,.2f} → {b:,.2f}" for k, (a, b) in d["cambios"].items())
        st.error(f"{cont.nombre_mes(d['periodo'])} ya cerrado cambió desde el cierre ({detalle}). Revisa la auditoría de Configuración.")

    cerrable = next((f for f in periodos if f["puede_cerrar"]), None)
    if not cerrable:
        siguiente = next((f for f in periodos if f["estado"] == "en curso"), None)
        st.info(f"No hay meses pendientes de cierre. {cont.nombre_mes(siguiente['periodo'])} podrá cerrarse desde el día siguiente a su último día."
                if siguiente else "No hay meses pendientes de cierre.")
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
