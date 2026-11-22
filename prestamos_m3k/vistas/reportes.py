"""Reportes: cobrado y ganancia del periodo, reparto capital/ganancia, semanas, medios de pago y modalidades."""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

import calculos as calc
import datos
import estilos as ui
import graficos as g
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


def cuerpo(db: dict, hoy: date) -> None:
    periodo = st.selectbox("Periodo", PERIODOS, key="periodo_cobranza")
    desde, hasta = _rango(periodo, hoy)
    if desde > hasta:
        st.error("La fecha «Desde» no puede ser posterior a «Hasta».")
        return

    prestamos = {p["id"]: p for p in db["prestamos"]}
    filas = []
    capitales = calc.capital_por_pago(db)
    for p in db["pagos"]:
        f = calc.fecha(p["fecha"])
        if p.get("anulado") or not (desde <= f <= hasta):
            continue
        pr = prestamos.get(p["prestamo_id"])
        if not pr:
            continue
        capital = capitales.get(p["id"], 0.0)
        filas.append({"fecha": f, "folio": p["folio"], "cliente": comun.nombre_cliente(db, pr["cliente_id"]),
                      "prestamo": pr["numero"], "modalidad": pr["modalidad"], "medio": p["metodo"],
                      "cuota": p["monto_cuota"], "mora": p.get("monto_mora", 0.0),
                      "capital": round(capital, 2), "interes": round(p["monto_cuota"] - capital, 2)})
    df = pd.DataFrame(filas, columns=["fecha", "folio", "cliente", "prestamo", "modalidad", "medio", "cuota", "mora", "capital", "interes"])
    desembolsos = [p for p in db["prestamos"] if not p.get("anulado") and desde <= calc.fecha(p["fecha_desembolso"]) <= hasta]

    cobrado = float(df["cuota"].sum() + df["mora"].sum())
    capital = float(df["capital"].sum())
    ganancia = float(df["interes"].sum() + df["mora"].sum())
    prestado = sum(p["monto"] for p in desembolsos)
    ui.kpis([
        {"etiqueta": "Cobrado", "valor": ui.soles(cobrado), "heroe": True, "tono": "ok", "nota": f"{len(df)} cobro(s) en el periodo"},
        {"etiqueta": "Ganancia real", "valor": ui.soles(ganancia), "tono": "ok", "nota": "Intereses y mora cobrados"},
        {"etiqueta": "Prestado", "valor": ui.soles(prestado), "tono": "info", "nota": f"{len(desembolsos)} crédito(s) nuevo(s)"},
    ])

    if df.empty:
        ui.vacio("Sin cobros en este periodo", "Prueba con otro periodo o registra cobros en «Registrar cobro».")
    else:
        st.markdown(g.panel("De lo que cobraste, ¿cuánto es tuyo?", g.reparto([
            ("Capital que te devuelven (lo que prestaste)", capital, ui.TONOS["info"]),
            ("Ganancia (intereses y mora)", ganancia, ui.TONOS["ok"])]),
            "El capital vuelve a tu caja para prestarlo otra vez; la ganancia es lo que realmente ganaste."), unsafe_allow_html=True)

        izq, der = st.columns([3, 2])
        semanal = (df["cuota"] + df["mora"]).groupby(df["fecha"].map(lambda f: f - timedelta(days=f.weekday()))).sum()
        lunes_fin = hasta - timedelta(days=hasta.weekday())
        lunes_ini = max(min(semanal.index), lunes_fin - timedelta(weeks=11))  # como máximo las últimas 12 semanas
        semanas, d = [], lunes_ini
        while d <= lunes_fin:
            semanas.append((f"{d.day}/{d.month}", round(float(semanal.get(d, 0.0)), 2), d == hoy - timedelta(days=hoy.weekday())))
            d += timedelta(weeks=1)
        izq.markdown(g.panel("Cobrado por semana", g.columnas(semanas), "Cada columna es una semana (de lunes a sábado), con su fecha de inicio."
                             + (" Se muestran las últimas 12." if len(semanal) > 12 else "")), unsafe_allow_html=True)
        por_medio = (df["cuota"] + df["mora"]).groupby(df["medio"]).sum().sort_values(ascending=False)
        paleta = [ui.TONOS["info"], ui.TONOS["ok"], ui.TONOS["aviso"], "#7A5AA6", ui.TONOS["neutro"]]
        der.markdown(g.panel("Cobrado por medio de pago", g.dona(
            [{"nombre": m, "monto": round(float(v), 2), "color": paleta[i % len(paleta)], "etiqueta": m} for i, (m, v) in enumerate(por_medio.items())],
            f"S/ {cobrado:,.0f}", "cobrado")), unsafe_allow_html=True)

    st.subheader("Rendimiento por modalidad", anchor=False)
    tarjetas = []
    en_uso = {p["modalidad"] for p in db["prestamos"]}
    for i, (clave, datos_m) in enumerate((k, v) for k, v in calc.MODALIDADES.items() if not v.get("oculta") or k in en_uso):
        nuevos = [p for p in desembolsos if p["modalidad"] == clave]
        sub = df[df["modalidad"] == clave]
        tarjetas.append(
            f'<div class="m3k-dia{"" if (nuevos or len(sub)) else " vacio"}" style="animation-delay:{i * 0.07:.2f}s"><div class="d">{ui.esc(datos_m["nombre"])}</div>'
            f'<div class="m num">{ui.soles(float(sub["cuota"].sum() + sub["mora"].sum()))}</div><div class="n">cobrado · ganancia {ui.soles(float(sub["interes"].sum() + sub["mora"].sum()))}</div>'
            f'<div class="n" style="margin-top:.35rem">{len(nuevos)} crédito(s) nuevo(s) · {ui.soles(sum(p["monto"] for p in nuevos))} prestados</div></div>')
    st.markdown(f'<div class="m3k-dias">{"".join(tarjetas)}</div>', unsafe_allow_html=True)

    if not df.empty:
        csv = df.assign(fecha=df["fecha"].map(ui.fecha_txt)).to_csv(index=False).encode("utf-8-sig")
        st.download_button("Descargar cobros del periodo (CSV)", csv, file_name=f"cobros_{desde}_{hasta}.csv", mime="text/csv",
                           icon=":material/download:")
