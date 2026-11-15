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

    cols = ["Cliente", "DNI", "Créditos activos", "Por cobrar", "Por vencer", "Vencido"] + [t_[0] for t_ in calc.TRAMOS_MORA] + ["Int. no devengados", "Cartera neta"]
    filas = [[f["cliente"], f["dni"], f["creditos"], ui.monto(cont.importe(f["por_cobrar"])), ui.monto(cont.importe(f["por_vencer"])),
              ui.monto(cont.importe(f["vencido"]))] + [ui.monto(cont.importe(x)) for x in f["tramos"]]
             + [ui.monto(cont.importe(f["no_devengado"])), ui.monto(cont.importe(f["cartera_neta"]))] for f in cxc["filas"]]
    pie = ["Total", "", t["creditos"], ui.monto(cont.importe(t["por_cobrar"])), ui.monto(cont.importe(t["por_vencer"])), ui.monto(cont.importe(t["vencido"]))] \
        + [ui.monto(cont.importe(x)) for x in t["tramos"]] + [ui.monto(cont.importe(t["no_devengado"])), ui.monto(cont.importe(t["cartera_neta"]))]
    ui.tabla(cols, filas, numericas=tuple(range(2, len(cols))), etiqueta="Cuentas por cobrar por cliente", pie=pie)
    st.caption("Los tramos de antigüedad miden los días de atraso de cada cuota vencida. Los importes entre paréntesis son negativos.")

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
