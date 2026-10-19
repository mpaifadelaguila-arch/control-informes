"""Control de informes de planes especiales (puntos de inyección, dead legs,
sulfidación). Matriz independiente de la del plan general de tuberías."""

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
import planes  # noqa: E402
from tema import ICONOS, TONOS, aplicar_tema, tabla_html, tinte  # noqa: E402

st.set_page_config(
    page_title="Planes especiales - Ademinsac",
    page_icon=":material/assignment:",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)
aplicar_tema()

DB_PLANES = str(RAIZ / "database_planes.json")
NOMBRE_DRIVE = "database_planes.json"
HORA_LIMA = timezone(timedelta(hours=-5), "Lima")


@st.cache_data(ttl=5, show_spinner=False)
def cargar_planes():
    drive.descargar(NOMBRE_DRIVE, DB_PLANES)
    return planes.cargar_json(DB_PLANES)


def guardar_planes(df):
    planes.guardar_json(df, DB_PLANES)
    drive.subir(NOMBRE_DRIVE, DB_PLANES)
    st.cache_data.clear()


def fecha_actualizacion():
    fecha = None
    try:
        with open(f"{DB_PLANES}.modificado") as marca:
            texto = marca.read().strip()
        if texto:
            fecha = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except (OSError, ValueError):
        fecha = None
    if fecha is None and os.path.exists(DB_PLANES):
        fecha = datetime.fromtimestamp(os.path.getmtime(DB_PLANES), timezone.utc)
    if fecha is None:
        return "Sin datos"
    return fecha.astimezone(HORA_LIMA).strftime("%d/%m/%Y · %H:%M")


# ------------------------------------------------------------------ Cabecera
ICONO = (
    '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"'
    ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>'
)


def html_cabecera(finalizados=None, total=None):
    chips = ""
    if total:
        avance = finalizados / total * 100
        chips += (
            "<div class='header-chip header-chip-avance'>"
            "<div class='chip-titulo'><span>Avance general</span>"
            f"<span class='chip-porcentaje'>{avance:.1f}%</span></div>"
            f"<div class='chip-barra'><div style='width:{avance:.1f}%'></div></div>"
            f"<div class='chip-detalle'>{finalizados} de {total} finalizados</div></div>"
        )
    chips += (
        "<div class='header-chip'><div class='chip-titulo'>Última actualización</div>"
        f"<div class='chip-valor'>{fecha_actualizacion()}</div></div>"
    )
    return (
        "<div class='header-banner header-indicadores'>"
        f"<div class='header-marca'><div class='header-icono'>{ICONO}</div>"
        "<div><div class='header-title'>PLANES ESPECIALES — ADEMINSAC</div>"
        "<div class='header-subtitle'>Puntos de inyección · Dead legs · Sulfidación"
        " · Refinería La Pampilla</div></div></div>"
        f"<div class='header-chips'>{chips}</div></div>"
    )


# ------------------------------------------------------------------ KPIs
def estilo_tono(color):
    tono = TONOS[color]
    return (
        f"--tone:{tono};--tone-bg:{tinte(tono, 0.12)};"
        f"--tone-borde:{tinte(tono, 0.45)}"
    )


def item_kpi(titulo, valor, color, alerta=False, puntos=None, unidad="informe"):
    clase = "kpi-item alerta" if alerta and valor else "kpi-item"
    detalle = unidad + ("" if valor == 1 else "s")
    if puntos is not None:
        detalle += f" · {puntos} punto{'' if puntos == 1 else 's'}"
    return (
        f"<div class='{clase}' style='{estilo_tono(color)}'>"
        f"<div class='kpi-item-label'><span class='kpi-dot'></span>{titulo}</div>"
        f"<div class='kpi-item-value'>{valor}"
        f"<span class='kpi-item-lineas'>{detalle}</span></div></div>"
    )


def bloque_kpi(titulo, icono, color, items):
    filas = "".join(item_kpi(*i) for i in items)
    return (
        "<div class='kpi-block-card'>"
        f"<div class='kpi-block-head' style='{estilo_tono(color)}'>"
        f"<div class='kpi-block-icon'>{ICONOS[icono]}</div>"
        f"<div class='kpi-block-title'>{titulo}</div></div>"
        f"<div class='kpi-items'>{filas}</div></div>"
    )


def bloque_de_plan(titulo, icono, color, k):
    return bloque_kpi(titulo, icono, color, [
        ("Informes totales", k["informes"], "azul", False, k["puntos"]),
        ("Finalizados", k["finalizados"], "verde", False, k["puntos_finalizados"]),
        ("Pend. inspección", k["pend_inspeccion"], "naranja", True,
         k["puntos_pend_inspeccion"]),
        ("Pend. elaboración", k["pend_elaboracion"], "rojo", True,
         k["puntos_pend_elaboracion"]),
        ("Retirados", k["retirados"], "violeta", False, None, "punto"),
    ])


# ------------------------------------------------------------------ Datos
if "df_planes" not in st.session_state:
    st.session_state.df_planes = cargar_planes()
df = planes.normalizar_planes(st.session_state.df_planes)

cabecera = st.empty()
cabecera.markdown(html_cabecera(), unsafe_allow_html=True)

with st.container(key="barra_datos"):
    texto, carga, respaldo = st.columns([3, 1, 1], vertical_alignment="center")
    texto.markdown(
        "<div class='barra-datos-texto'><span class='barra-datos-titulo'>"
        f"Gestión de datos</span><span>· matriz de planes especiales, {len(df)}"
        " filas</span></div>",
        unsafe_allow_html=True,
    )
    with carga.popover("Cargar Excel", icon=":material/upload:", width="stretch"):
        st.markdown("**Cargar matriz de planes especiales**")
        archivo = st.file_uploader(
            "Selecciona un archivo Excel", type=["xlsx", "xlsm"], key="subir_planes"
        )
        if archivo and st.button(
            "Reemplazar matriz", icon=":material/upload:", type="primary"
        ):
            try:
                st.session_state.df_planes = planes.leer_excel_planes(archivo)
                guardar_planes(st.session_state.df_planes)
                st.success("Matriz cargada y guardada en Google Drive.")
                st.rerun()
            except Exception as error:
                st.error(f"No se pudo cargar el Excel: {error}")
    with respaldo:
        if not df.empty:
            st.download_button(
                "Descargar respaldo",
                data=planes.excel_con_formato(df),
                file_name="Matriz_Planes_Especiales.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                icon=":material/download:",
            )

if df.empty:
    st.info(
        "Carga la matriz de planes especiales con el botón «Cargar Excel».",
        icon=":material/info:",
    )
    st.stop()

res = planes.procesar_planes(df)
informes, activos, retiradas, kpis = (
    res["informes"], res["activos"], res["retiradas"], res["kpis"]
)
t = kpis["TOTAL"]
cabecera.markdown(html_cabecera(t["finalizados"], t["informes"]), unsafe_allow_html=True)

# ------------------------------------------------------------------ Panel
panel = st.container(key="panel_control")
panel.markdown(
    "<div class='section-title'>Panel de control de planes especiales</div>",
    unsafe_allow_html=True,
)
bloques = [
    bloque_kpi("General", "grafico", "azul", [
        ("Informes totales", t["informes"], "azul", False, t["puntos"]),
        ("Informes finalizados", t["finalizados"], "verde", False,
         t["puntos_finalizados"]),
        ("Pendientes de elaborar", t["pend_elaborar"], "naranja", True,
         t["puntos_pend_elaborar"]),
        ("Retirados", t["retirados"], "violeta", False, None, "punto"),
        ("Valorizados", t["valorizados"], "dorado", False, t["puntos_valorizados"]),
    ]),
    bloque_de_plan("Puntos de inyección", "campo", "turquesa",
                   kpis["PUNTOS DE INYECCIÓN"]),
    bloque_de_plan("Dead legs", "carpeta", "indigo", kpis["DEAD LEG"]),
    bloque_de_plan("Sulfidación", "cliente", "rosa", kpis["SULFIDACIÓN"]),
    bloque_kpi("Campo", "campo", "naranja", [
        ("Pend. inspección", t["pend_inspeccion"], "naranja", True,
         t["puntos_pend_inspeccion"]),
        ("Inspeccionados", t["informes"] - t["pend_inspeccion"], "verde", False),
    ]),
    bloque_kpi("Cliente", "especialista", "dorado", [
        ("En revisión de fiabilidad", t["en_revision"], "dorado", True,
         t["puntos_en_revision"]),
        ("Pend. revisión especialista", t["por_revisar"], "naranja", True,
         t["puntos_por_revisar"]),
    ]),
]
panel.markdown(
    f"<div class='kpi-row'>{''.join(bloques)}</div>", unsafe_allow_html=True
)

# ------------------------------------------------------------------ Tablas
COLS_TABLA = ["PLAN", "MES", "UNIDAD", "CODIGO DE INFORME", "GRUPO DE TUBERÍAS",
              "PUNTOS", "ESTADO", "RESPONSABLE", "OBSERVACIÓN"]


def detalle_de(clave):
    sub = activos[activos["CLAVE"] == clave]
    d = sub[["UNIDAD", "LINEAS", "SAP", planes.COL_ESTADO, "NOTAS"]].copy()
    d["_PEND"] = sub[planes.COL_ESTADO].map(
        lambda e: "PENDIENTE" in planes.texto_normalizado(e)
    )
    return d.reset_index(drop=True)


def mostrar_informes(sub, archivo):
    if sub.empty:
        st.info("No hay informes en esta vista.", icon=":material/info:")
        return
    vista = sub[COLS_TABLA].copy()
    vista.index = range(1, len(vista) + 1)
    tabla_html(vista, detalles=[detalle_de(c) for c in sub["CLAVE"]])
    st.download_button(
        "Descargar Excel",
        data=planes.excel_con_formato(sub[COLS_TABLA]),
        file_name=archivo,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:",
        key=f"dl_{archivo}",
    )


sistema = st.container(key="sistema_control")
with sistema:
    tabs = st.tabs([
        "Tabla general", "Pend. inspección", "Pend. elaboración",
        "Finalizados", "Retirados", "Resumen",
    ])
    with tabs[0]:
        mostrar_informes(informes, "Planes_Especiales_General.xlsx")
    with tabs[1]:
        mostrar_informes(
            informes[informes["ESTADO"] == planes.PEND_INSPECCION],
            "Planes_Pend_Inspeccion.xlsx",
        )
    with tabs[2]:
        mostrar_informes(
            informes[informes["ESTADO"] == planes.PEND_ELABORACION],
            "Planes_Pend_Elaboracion.xlsx",
        )
    with tabs[3]:
        mostrar_informes(
            informes[informes["ESTADO"] == planes.FINALIZADO],
            "Planes_Finalizados.xlsx",
        )
    with tabs[4]:
        if retiradas.empty:
            st.info("No hay puntos retirados.", icon=":material/info:")
        else:
            vista = retiradas[["ALCANCE DEL SERVICIO", "MES", "UNIDAD", "LINEAS",
                               "CODIGO DE INFORME", "SAP", "NOTAS"]].copy()
            vista.index = range(1, len(vista) + 1)
            tabla_html(vista)
    with tabs[5]:
        st.markdown("**Resumen por plan**")
        tabla_html(planes.resumen_por_plan(kpis))
        st.markdown("**Informes por mes**")
        tabla_html(planes.resumen_por_mes(informes))
