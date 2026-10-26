"""Resumen general: qué informes faltan en «Plan de líneas» y «Planes adicionales»."""

import importlib
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.append(str(RAIZ))

import drive  # noqa: E402
import lineas_kpis  # noqa: E402
import planes  # noqa: E402
import resumen  # noqa: E402
from tema import (BORDE, DORADO, ITEM, SUPERFICIE, TEXTO_SUAVE, TONOS,  # noqa: E402
                  aplicar_tema, tabla_html, tinte)

# Streamlit conserva los módulos en memoria: se recargan para aplicar cambios.
for _modulo in (lineas_kpis, planes, resumen):
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
def cargar():
    drive.descargar("database_informes.json", DB_LINEAS)
    drive.descargar("database_planes.json", DB_PLANES)
    df_l = lineas_kpis.cargar(DB_LINEAS)
    res_a = planes.procesar_planes(planes.cargar_json(DB_PLANES))
    kl = lineas_kpis.calcular(df_l)
    ka = resumen.kpis_adicionales(res_a["kpis"]["TOTAL"])
    insp_l, elab_l = lineas_kpis.listas(df_l)
    insp_a, elab_a = resumen.listas_adicionales(res_a)
    return kl, ka, resumen.ordenar(insp_l + insp_a), resumen.ordenar(elab_l + elab_a)


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
    return fecha.astimezone(HORA_LIMA).strftime("%d/%m · %H:%M") if fecha else "Sin datos"


kl, ka, pend_insp, pend_elab = cargar()
kt = resumen.total(kl, ka)

# ------------------------------------------------------------------ Cabecera
ICONO = (
    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/>'
    '<rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>'
)
chips = (
    "<div class='header-chip'><div class='chip-titulo'>Plan de líneas</div>"
    f"<div class='chip-valor'>{fecha_de(DB_LINEAS)}</div></div>"
    "<div class='header-chip'><div class='chip-titulo'>Planes adicionales</div>"
    f"<div class='chip-valor'>{fecha_de(DB_PLANES)}</div></div>"
)
st.markdown(
    "<div class='header-banner header-indicadores'>"
    f"<div class='header-marca'><div class='header-icono'>{ICONO}</div>"
    "<div><div class='header-title'>RESUMEN GENERAL — ADEMINSAC</div>"
    "<div class='header-subtitle'>Qué informes faltan y en qué etapa están · Plan de líneas"
    " y Planes adicionales</div></div></div>"
    f"<div class='header-chips'>{chips}</div></div>",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------ Balance (3 tarjetas)


def tarjeta(titulo, k, color):
    pct = resumen.avance(k)
    tono = TONOS[color]
    return (
        f"<div style='background:{SUPERFICIE};border:1px solid {tinte(tono, 0.45)};"
        "border-radius:14px;padding:16px 20px'>"
        f"<div style='color:{TEXTO_SUAVE};font-size:12px;letter-spacing:.08em;"
        f"text-transform:uppercase;font-weight:700'>{titulo}</div>"
        f"<div style='font-size:34px;font-weight:700;margin:6px 0 2px;color:{tono}'>"
        f"{pct:.1f}%<span style='font-size:14px;color:{TEXTO_SUAVE};font-weight:400;"
        f"margin-left:8px'>{k['finalizados']} de {k['informes']} informes finalizados</span></div>"
        f"<div style='height:8px;border-radius:6px;background:{BORDE};margin:8px 0 6px'>"
        f"<div style='height:8px;border-radius:6px;width:{min(pct, 100):.1f}%;"
        f"background:{tono}'></div></div>"
        f"<div style='color:{TEXTO_SUAVE};font-size:12px'>Faltan "
        f"<b style='color:{TONOS['naranja']}'>{k['pend_elaborar']}</b> informes por terminar"
        f" · {k['valorizados']} valorizados</div></div>"
    )


with st.container(key="panel_control"):
    st.markdown(
        "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));"
        f"gap:14px'>{tarjeta('Plan de líneas', kl, 'azul')}"
        f"{tarjeta('Planes adicionales', ka, 'turquesa')}"
        f"{tarjeta('Total ambos planes', kt, 'dorado')}</div>",
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------------ Filtros
with st.container(key="barra_datos"):
    c_plan, c_buscar, c_desc = st.columns([2.2, 3, 1.2], vertical_alignment="bottom")
    plan_sel = c_plan.radio(
        "Plan", ["Todos", "Plan de líneas", "Planes adicionales"],
        horizontal=True, key="resumen_plan",
    )
    consulta = c_buscar.text_input(
        "Buscar", placeholder="Informe, identificación, línea, SAP, responsable…",
        icon=":material/search:", key="resumen_buscar",
    )

insp = resumen.filtrar(pend_insp, plan_sel, consulta)
elab = resumen.filtrar(pend_elab, plan_sel, consulta)
tabla_insp, det_insp = resumen.tabla_lista(insp, True)
tabla_elab, det_elab = resumen.tabla_lista(elab, False)

with c_desc:
    st.download_button(
        "Descargar Excel",
        data=resumen.excel_resumen(kl, ka, {
            "PEND_INSPECCION": resumen.tabla_lista(pend_insp, True)[0],
            "POR_ELABORAR": resumen.tabla_lista(pend_elab, False)[0],
        }),
        file_name="Resumen_General_Planes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:",
    )

# ------------------------------------------------------------------ Listas de pendientes
with st.container(key="sistema_control"):
    st.markdown(
        f"#### 🟠 Pendientes de inspección · {len(insp)} informes\n"
        "El campo debe inspeccionar estas líneas. Pulsa un informe para ver sus líneas"
        " (las pendientes van en rojo)."
    )
    if insp:
        tabla_html(tabla_insp, detalles=det_insp)
    else:
        st.success("No hay informes pendientes de inspección.", icon=":material/check_circle:")

    st.markdown(
        f"#### 🔴 Pendientes por asignar / elaborar · {len(elab)} informes\n"
        "Ya están inspeccionados: falta asignar responsable y elaborar el informe."
    )
    if elab:
        tabla_html(tabla_elab, detalles=det_elab)
    else:
        st.success("No hay informes pendientes de elaborar.", icon=":material/check_circle:")

    st.markdown("#### Otras etapas")
    otras = [
        ("Por revisar · Especialista", "por_revisar"),
        ("En revisión · Cliente", "en_revision"),
        ("Valorizados", "valorizados"),
    ]
    cols = st.columns(len(otras))
    for col, (nombre, clave) in zip(cols, otras):
        col.metric(
            nombre, kt[clave],
            f"Líneas {kl[clave]} · Adicionales {ka[clave]}", delta_color="off",
            border=True,
        )
    b1, b2 = st.columns(2)
    b1.page_link("plan_de_lineas.py", label="Abrir Plan de líneas",
                 icon=":material/arrow_forward:")
    b2.page_link("pages/1_Planes_Adicionales.py", label="Abrir Planes adicionales",
                 icon=":material/arrow_forward:")
