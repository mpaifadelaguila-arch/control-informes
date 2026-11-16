"""Cuentas por cobrar: saldo por cliente, antigüedad y conciliación con el libro mayor."""

import pandas as pd
import streamlit as st

import calculos as calc
import contabilidad as cont
import datos
import estilos as ui


def mostrar() -> None:
    db = datos.cargar()
    hoy = calc.hoy()
    ui.encabezado("Cuentas por cobrar", f"Cartera de créditos al {ui.fecha_txt(hoy)}, por cliente y por antigüedad")
    evals = calc.evaluar_cartera(db, hoy)
    cxc = cont.cuentas_por_cobrar(db, evals, hoy)
    if not cxc["filas"]:
        ui.vacio("No hay cuentas por cobrar", "Cuando registres un crédito, su saldo aparecerá aquí por cliente.")
        return

    t = cxc["total"]
    ui.kpis([
        {"etiqueta": "Cartera por cobrar", "valor": ui.soles(cont.importe(t["por_cobrar"])), "heroe": True, "tono": "info", "nota": "Capital más interés pendiente de cobro"},
        {"etiqueta": "Vencido", "valor": ui.soles(cont.importe(t["vencido"])), "tono": "malo" if t["vencido"] else "ok",
         "nota": ui.pct(t["vencido"] / t["por_cobrar"]) + " de la cartera" if t["por_cobrar"] else "Sin cartera"},
        {"etiqueta": "Intereses no devengados", "valor": ui.soles(cont.importe(t["no_devengado"])), "tono": "aviso", "nota": "Interés que se ganará en los próximos días"},
        {"etiqueta": "Cartera neta", "valor": ui.soles(cont.importe(t["cartera_neta"])), "tono": "ok", "nota": "Por cobrar menos intereses no devengados"},
    ])

    m = lambda c: ui.monto(cont.importe(c))
    cols = ["Cliente", "DNI", "Créditos", "Por cobrar", "Por vencer", "Vencido", "Int. no devengados", "Cartera neta"]
    filas = [[f["cliente"], f["dni"], f["creditos"], m(f["por_cobrar"]), m(f["por_vencer"]), m(f["vencido"]), m(f["no_devengado"]), m(f["cartera_neta"])]
             for f in cxc["filas"]]
    pie = ["Total", "", t["creditos"], m(t["por_cobrar"]), m(t["por_vencer"]), m(t["vencido"]), m(t["no_devengado"]), m(t["cartera_neta"])]
    ui.tabla(cols, filas, numericas=tuple(range(2, len(cols))), sin_corte=(0, 1), etiqueta="Cuentas por cobrar por cliente", pie=pie)
    st.caption("Por vencer: cuotas que aún no llegan a su fecha. Vencido: cuotas cuya fecha ya pasó. "
               "Cartera neta: lo que te deben menos el interés que todavía no has ganado.")

    st.subheader("Antigüedad del saldo vencido", anchor=False)
    tramos = [t_[0] for t_ in calc.TRAMOS_MORA]
    ui.tabla(["Cliente"] + tramos + ["Total vencido"],
             [[f["cliente"]] + [m(x) for x in f["tramos"]] + [m(f["vencido"])] for f in cxc["filas"]],
             numericas=tuple(range(1, len(tramos) + 2)), sin_corte=(0,), etiqueta="Antigüedad del saldo vencido",
             pie=["Total"] + [m(x) for x in t["tramos"]] + [m(t["vencido"])])
    st.caption("Los tramos cuentan los días de atraso de cada cuota vencida. Si no hay nada vencido, todo aparece en guion.")

    st.subheader("Conciliación con el libro mayor", anchor=False)
    ui.tabla(["Cuenta", "Auxiliar (por cliente)", "Libro mayor", "Diferencia", "Estado"],
             [[f"{c['cuenta']} {c['nombre']}", ui.monto(c["auxiliar"]), ui.monto(c["mayor"]), ui.monto(c["diferencia"]), ui.chip_cuadre(c["diferencia"] == 0)]
              for c in cxc["conciliacion"]], numericas=(1, 2, 3), etiqueta="Conciliación de cuentas por cobrar")
    if not cxc["cuadra"]:
        st.error("El detalle por cliente no coincide con el libro mayor. Revisa los créditos y cobros anulados antes de cerrar el mes.")

    df = pd.DataFrame([{"cliente": f["cliente"], "dni": f["dni"], "por_cobrar": cont.importe(f["por_cobrar"]), "por_vencer": cont.importe(f["por_vencer"]),
                        "vencido": cont.importe(f["vencido"]), "no_devengado": cont.importe(f["no_devengado"]), "cartera_neta": cont.importe(f["cartera_neta"])}
                       for f in cxc["filas"]])
    st.download_button("Descargar cuentas por cobrar (CSV)", df.to_csv(index=False).encode("utf-8-sig"), file_name=f"cuentas_por_cobrar_{hoy}.csv",
                       mime="text/csv", icon=":material/download:")
