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
    m = lambda c: ui.monto(cont.importe(c))
    ui.kpis([
        {"etiqueta": "Te deben en total", "valor": ui.soles(cont.importe(t["por_cobrar"])), "heroe": True, "tono": "info", "nota": f"{t['creditos']} crédito(s) activo(s)"},
        {"etiqueta": "Vencido", "valor": ui.soles(cont.importe(t["vencido"])), "tono": "malo" if t["vencido"] else "ok",
         "nota": "Cuotas cuya fecha ya pasó" if t["vencido"] else "Nadie está atrasado"},
    ])
    ui.tabla(["Cliente", "DNI", "Por vencer", "Vencido", "Total que debe"],
             [[f["cliente"], f["dni"], m(f["por_vencer"]), m(f["vencido"]), m(f["por_cobrar"])] for f in cxc["filas"]],
             numericas=(2, 3, 4), sin_corte=(0, 1), etiqueta="Cuentas por cobrar por cliente",
             pie=["Total", "", m(t["por_vencer"]), m(t["vencido"]), m(t["por_cobrar"])])

    if t["vencido"]:
        st.subheader("Cuánto tiempo llevan atrasadas", anchor=False)
        tramos = [t_[0] for t_ in calc.TRAMOS_MORA]
        ui.tabla(["Cliente"] + tramos, [[f["cliente"]] + [m(x) for x in f["tramos"]] for f in cxc["filas"] if f["vencido"]],
                 numericas=tuple(range(1, len(tramos) + 1)), sin_corte=(0,), etiqueta="Antigüedad del saldo vencido",
                 pie=["Total"] + [m(x) for x in t["tramos"]])

    if cxc["cuadra"]:
        st.caption("Estas cifras coinciden con el libro mayor.")
    else:
        st.error("El detalle por cliente no coincide con el libro mayor. Revisa los créditos y cobros anulados antes de cerrar el mes.")

    df = pd.DataFrame([{"cliente": f["cliente"], "dni": f["dni"], "por_cobrar": cont.importe(f["por_cobrar"]), "por_vencer": cont.importe(f["por_vencer"]),
                        "vencido": cont.importe(f["vencido"])}
                       for f in cxc["filas"]])
    st.download_button("Descargar cuentas por cobrar (CSV)", df.to_csv(index=False).encode("utf-8-sig"), file_name=f"cuentas_por_cobrar_{hoy}.csv",
                       mime="text/csv", icon=":material/download:")
