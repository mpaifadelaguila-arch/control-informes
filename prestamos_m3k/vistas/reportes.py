"""Reportes: resultado del periodo, cobranza por semana, rendimiento por modalidad y mora."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

import calculos as calc
import datos
import estilos as ui
import operaciones as ops
from vistas import comun

PERIODOS = ["Este mes", "Mes anterior", "Últimos 30 días", "Este año", "Todo", "Personalizado"]


def _rango(nombre: str, hoy: date) -> tuple[date, date]:
    primero = hoy.replace(day=1)
    if nombre == "Este mes":
        return primero, hoy
    if nombre == "Mes anterior":
        fin = primero - timedelta(days=1)
        return fin.replace(day=1), fin
    if nombre == "Últimos 30 días":
        return hoy - timedelta(days=29), hoy
    if nombre == "Este año":
        return date(hoy.year, 1, 1), hoy
    if nombre == "Todo":
        return date(2000, 1, 1), hoy
    c1, c2 = st.columns(2)
    return c1.date_input("Desde", value=primero, format="DD/MM/YYYY"), c2.date_input("Hasta", value=hoy, format="DD/MM/YYYY")


def mostrar() -> None:
    db = datos.cargar()
    hoy = calc.hoy()
    ui.encabezado("Reporte financiero", "Resultados de cobranza y estado de la cartera")
    periodo = st.selectbox("Periodo", PERIODOS)
    desde, hasta = _rango(periodo, hoy)
    if desde > hasta:
        st.error("La fecha «Desde» no puede ser posterior a «Hasta».")
        return

    prestamos = {p["id"]: p for p in db["prestamos"]}
    filas = []
    for p in db["pagos"]:
        f = calc.fecha(p["fecha"])
        if p.get("anulado") or not (desde <= f <= hasta):
            continue
        pr = prestamos.get(p["prestamo_id"])
        if not pr:
            continue
        capital = p["monto_cuota"] * pr["monto"] / pr["total"]
        filas.append({"fecha": f, "folio": p["folio"], "cliente": comun.nombre_cliente(db, pr["cliente_id"]),
                      "prestamo": pr["numero"], "modalidad": pr["modalidad"], "medio": p["metodo"],
                      "cuota": p["monto_cuota"], "mora": p.get("monto_mora", 0.0),
                      "capital": round(capital, 2), "interes": round(p["monto_cuota"] - capital, 2)})
    df = pd.DataFrame(filas, columns=["fecha", "folio", "cliente", "prestamo", "modalidad", "medio", "cuota", "mora", "capital", "interes"])
    desembolsos = [p for p in db["prestamos"] if not p.get("anulado") and desde <= calc.fecha(p["fecha_desembolso"]) <= hasta]
    evals = calc.evaluar_cartera(db, hoy)
    ind = calc.indicadores(db, evals, hoy)

    ui.kpis([
        {"etiqueta": "Cobrado en el periodo", "valor": ui.soles(float(df["cuota"].sum() + df["mora"].sum())), "heroe": True,
         "nota": f"{len(df)} cobro(s)"},
        {"etiqueta": "Capital recuperado", "valor": ui.soles(float(df["capital"].sum())), "tono": "info", "nota": "Parte de las cuotas que devuelve capital"},
        {"etiqueta": "Ganancia real", "valor": ui.soles(float(df["interes"].sum() + df["mora"].sum())), "tono": "ok", "nota": "Intereses y mora cobrados"},
        {"etiqueta": "Desembolsado", "valor": ui.soles(sum(p["monto"] for p in desembolsos)), "nota": f"{len(desembolsos)} crédito(s) nuevo(s)"},
    ])
    st.subheader("Cobrado por semana", anchor=False)
    if df.empty:
        ui.vacio("Sin cobros en este periodo", "Prueba con otro periodo o registra cobros en «Registrar cobro».")
    else:
        inicio_semana = df["fecha"].map(lambda f: f - timedelta(days=f.weekday()))
        semanal = (df["cuota"] + df["mora"]).groupby(inicio_semana).sum()
        semanal.index = [f"Semana del {ui.fecha_txt(f)}" for f in semanal.index]
        st.bar_chart(pd.DataFrame({"Cobrado (S/)": semanal.round(2)}), color=ui.TONOS["ok"])

    st.subheader("Rendimiento por modalidad", anchor=False)
    filas_mod = []
    for clave, datos_m in calc.MODALIDADES.items():
        nuevos = [p for p in desembolsos if p["modalidad"] == clave]
        sub = df[df["modalidad"] == clave]
        filas_mod.append([datos_m["nombre"], len(nuevos), ui.soles(sum(p["monto"] for p in nuevos)),
                          ui.soles(float(sub["cuota"].sum() + sub["mora"].sum())), ui.soles(float(sub["interes"].sum() + sub["mora"].sum()))])
    ui.tabla(["Modalidad", "Créditos nuevos", "Desembolsado", "Cobrado", "Ganancia real"], filas_mod, numericas=(1, 2, 3, 4),
             etiqueta="Rendimiento por modalidad")

    if not df.empty:
        csv = df.assign(fecha=df["fecha"].map(ui.fecha_txt)).to_csv(index=False).encode("utf-8-sig")
        st.download_button("Descargar cobros del periodo (CSV)", csv, file_name=f"cobros_{desde}_{hasta}.csv", mime="text/csv",
                           icon=":material/download:")
