"""Cuentas por cobrar: una sola tabla con lo que debe cada cliente y cuánto lleva de atraso."""

import pandas as pd
import streamlit as st

import calculos as calc
import contabilidad as cont
import datos
import estilos as ui


def mostrar() -> None:
    db = datos.cargar()
    hoy = calc.hoy()
    ui.encabezado("Cuentas por cobrar", f"Lo que te deben al {ui.fecha_txt(hoy)}, por cliente")
    evals = calc.evaluar_cartera(db, hoy)
    cxc = cont.cuentas_por_cobrar(db, evals, hoy)
    if not cxc["filas"]:
        ui.vacio("No hay cuentas por cobrar", "Cuando registres un crédito, su saldo aparecerá aquí por cliente.", "🧾")
        return

    t = cxc["total"]
    m = lambda c: ui.monto(cont.importe(c))
    filas = [f for f in cxc["filas"] if f["por_cobrar"]]
    # solo se muestran las columnas de atraso que tienen algo
    usados = [i for i, (nombre, _, _) in enumerate(calc.TRAMOS_MORA) if t["tramos"][i]]
    cols = ["Cliente", "Al día"] + [f"Atraso {calc.TRAMOS_MORA[i][0]}" for i in usados] + ["Total que debe"]
    ui.tabla(cols,
             [[f["cliente"], m(f["por_vencer"])] + [m(f["tramos"][i]) for i in usados] + [m(f["por_cobrar"])] for f in filas],
             numericas=tuple(range(1, len(cols))), sin_corte=(0,), etiqueta="Cuentas por cobrar",
             pie=["Total", m(t["por_vencer"])] + [m(t["tramos"][i]) for i in usados] + [m(t["por_cobrar"])])
    st.caption(f"{t['creditos']} crédito(s) activo(s). «Al día» son las cuotas que aún no vencen; las columnas de atraso son las cuotas vencidas, "
               "según cuántos días llevan sin pagarse." if usados else f"{t['creditos']} crédito(s) activo(s). Nadie está atrasado.")
    if not cxc["cuadra"]:
        st.error("El detalle por cliente no coincide con los libros. Revisa los créditos y cobros anulados antes de cerrar el mes.")

    df = pd.DataFrame([{"cliente": f["cliente"], "dni": f["dni"], "por_cobrar": cont.importe(f["por_cobrar"]), "por_vencer": cont.importe(f["por_vencer"]),
                        "vencido": cont.importe(f["vencido"])}
                       for f in cxc["filas"]])
    st.download_button("Descargar cuentas por cobrar (CSV)", df.to_csv(index=False).encode("utf-8-sig"), file_name=f"cuentas_por_cobrar_{hoy}.csv",
                       mime="text/csv", icon=":material/download:")
