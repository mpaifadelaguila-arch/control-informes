"""Resumen general: balance total de «Plan de líneas» y «Planes adicionales»."""

import importlib
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.append(str(RAIZ))

import drive  # noqa: E402
import lineas_kpis  # noqa: E402
import planes  # noqa: E402
import resumen  # noqa: E402
import ui_kpi  # noqa: E402
from tema import aplicar_tema, tabla_html  # noqa: E402

# Streamlit conserva los módulos en memoria: se recargan para aplicar cambios.
for _modulo in (lineas_kpis, planes, resumen, ui_kpi):
    importlib.reload(_modulo)

st.set_page_config(
    page_title="Resumen general - Ademinsac",
    page_icon=":material/dashboard:",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)
aplicar_tema()

DB_LINEAS = str(RAIZ / "database_informes.json")
DB_PLANES = str(RAIZ / "database_planes.json")
HORA_LIMA = timezone(timedelta(hours=-5), "Lima")


@st.cache_data(ttl=5, show_spinner=False)
def cargar_kpis():
    drive.descargar("database_informes.json", DB_LINEAS)
    drive.descargar("database_planes.json", DB_PLANES)
    kl = lineas_kpis.calcular(lineas_kpis.cargar(DB_LINEAS))
    ka = resumen.kpis_adicionales(
        planes.procesar_planes(planes.cargar_json(DB_PLANES))["kpis"]["TOTAL"]
    )
    return kl, ka


def fecha_de(ruta):
    fecha = None
    try:
        with open(f"{ruta}.modificado") as marca:
            texto = marca.read().strip()
        if texto:
            fecha = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except (OSError, ValueError):
        fecha = None
    if fecha is None and os.path.exists(ruta):
        fecha = datetime.fromtimestamp(os.path.getmtime(ruta), timezone.utc)
    return fecha.astimezone(HORA_LIMA).strftime("%d/%m %H:%M") if fecha else "Sin datos"


kl, ka = cargar_kpis()
kt = resumen.total(kl, ka)

# ------------------------------------------------------------------ Cabecera
ICONO = (
    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/>'
    '<rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>'
)
av = resumen.avance(kt)
chips = (
    "<div class='header-chip header-chip-avance'>"
    f"<div class='chip-titulo'><span>Avance total</span><span class='chip-porcentaje'>{av:.1f}%</span></div>"
    f"<div class='chip-barra'><div style='width:{av:.1f}%'></div></div>"
    f"<div class='chip-detalle'>{kt['finalizados']} de {kt['informes']} finalizados</div></div>"
    "<div class='header-chip'><div class='chip-titulo'>Plan de líneas</div>"
    f"<div class='chip-valor'>{fecha_de(DB_LINEAS)}</div></div>"
    "<div class='header-chip'><div class='chip-titulo'>Planes adicionales</div>"
    f"<div class='chip-valor'>{fecha_de(DB_PLANES)}</div></div>"
)
st.markdown(
    "<div class='header-banner header-indicadores'>"
    f"<div class='header-marca'><div class='header-icono'>{ICONO}</div>"
    "<div><div class='header-title'>RESUMEN GENERAL — ADEMINSAC</div>"
    "<div class='header-subtitle'>Balance total · Plan de líneas y Planes adicionales"
    " · Refinería La Pampilla</div></div></div>"
    f"<div class='header-chips'>{chips}</div></div>",
    unsafe_allow_html=True,
)

barra = st.container(key="barra_datos")
with barra:
    texto, descarga = st.columns([4, 1], vertical_alignment="center")
    texto.markdown(
        "<div class='barra-datos-texto'><span class='barra-datos-titulo'>"
        "Balance total</span><span>· los números se calculan con los datos"
        " guardados de cada plan</span></div>",
        unsafe_allow_html=True,
    )
    descarga.download_button(
        "Descargar resumen",
        data=resumen.excel_resumen(kl, ka),
        file_name="Resumen_General_Planes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:",
    )

# ------------------------------------------------------------------ Balance total
panel = st.container(key="panel_control")
panel.markdown(
    "<div class='section-title'>Balance total de ambos planes</div>",
    unsafe_allow_html=True,
)
bloques = [
    ui_kpi.bloque_kpi("General", "grafico", "azul", [
        ("Informes totales", kt["informes"], "azul", False, kt["lineas"]),
        ("Informes finalizados", kt["finalizados"], "verde"),
        ("Pendientes elaborar", kt["pend_elaborar"], "naranja", True),
        ("% avance", f"{av:.1f}%", "dorado"),
    ]),
    ui_kpi.bloque_kpi("Campo", "campo", "naranja", [
        ("Pend. inspección", kt["pend_inspeccion"], "naranja", True),
    ]),
    ui_kpi.bloque_kpi("Gabinete", "carpeta", "violeta", [
        ("Por elaborar", kt["por_elaborar"], "rojo", True),
        ("En elaboración", kt["en_proceso"], "indigo"),
    ]),
    ui_kpi.bloque_kpi("Especialista", "especialista", "turquesa", [
        ("Revisados", kt["revisados"], "verde"),
        ("Por revisar", kt["por_revisar"], "naranja", True),
    ]),
    ui_kpi.bloque_kpi("Cliente", "cliente", "verde", [
        ("Valorizados", kt["valorizados"], "verde"),
        ("En revisión", kt["en_revision"], "dorado", True),
    ]),
]
panel.markdown(f"<div class='kpi-row'>{''.join(bloques)}</div>", unsafe_allow_html=True)

# ------------------------------------------------------------------ Tarjetas por plan
st.markdown("<div class='section-title' style='margin:18px 0 8px'>Por plan</div>",
            unsafe_allow_html=True)


def tarjeta(titulo, icono, color, k):
    pct = resumen.avance(k)
    return ui_kpi.bloque_kpi(titulo, icono, color, [
        ("Informes totales", k["informes"], "azul", False, k["lineas"]),
        ("Finalizados", k["finalizados"], "verde"),
        ("% avance", f"{pct:.1f}%", "dorado"),
        ("Pend. inspección", k["pend_inspeccion"], "naranja", True),
        ("Gabinete · por elaborar", k["por_elaborar"], "rojo", True),
        ("Gabinete · en elaboración", k["en_proceso"], "indigo"),
        ("Especialista · por revisar", k["por_revisar"], "naranja", True),
        ("Especialista · revisados", k["revisados"], "verde"),
        ("Cliente · en revisión", k["en_revision"], "dorado", True),
        ("Cliente · valorizados", k["valorizados"], "verde"),
    ], extra_html=ui_kpi.barra_avance(pct))


c1, c2 = st.columns(2)
with c1:
    st.markdown(f"<div class='kpi-row' style='grid-template-columns:1fr'>"
                f"{tarjeta('Plan de líneas', 'grafico', 'azul', kl)}</div>",
                unsafe_allow_html=True)
    st.page_link("plan_de_lineas.py", label="Abrir Plan de líneas",
                 icon=":material/arrow_forward:")
with c2:
    st.markdown(f"<div class='kpi-row' style='grid-template-columns:1fr'>"
                f"{tarjeta('Planes adicionales', 'campo', 'turquesa', ka)}</div>",
                unsafe_allow_html=True)
    st.page_link("pages/1_Planes_Adicionales.py", label="Abrir Planes adicionales",
                 icon=":material/arrow_forward:")

# ------------------------------------------------------------------ Alertas y comparativo
sistema = st.container(key="sistema_control")
with sistema:
    st.markdown("**Alertas: pendientes que requieren acción**")
    tabla_alertas = resumen.alertas(kl, ka)
    if tabla_alertas.empty:
        st.success("No hay pendientes críticos.", icon=":material/check_circle:")
    else:
        tabla_html(tabla_alertas)
    st.markdown("**Comparativo por plan**")
    tabla_html(resumen.comparativo(kl, ka))
