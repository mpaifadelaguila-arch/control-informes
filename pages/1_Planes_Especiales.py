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

import importlib  # noqa: E402

import drive  # noqa: E402
import planes  # noqa: E402

# Streamlit conserva en memoria los módulos ya importados: se recarga para que
# una actualización de planes.py se aplique sin reiniciar la app.
planes = importlib.reload(planes)
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
    ok = drive.subir(NOMBRE_DRIVE, DB_PLANES)
    st.cache_data.clear()
    if not ok:
        # Se avisa en la siguiente carga (la página se reinicia tras guardar).
        st.session_state["aviso_drive"] = st.session_state.get(
            "error_drive", "No se pudo escribir en Google Drive."
        )


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


def item_kpi(titulo, valor, color, alerta=False, puntos=None, unidad="informe"):  # «puntos» = filas de la matriz (líneas)
    clase = "kpi-item alerta" if alerta and valor else "kpi-item"
    detalle = "del total" if isinstance(valor, str) else unidad + ("" if valor == 1 else "s")
    if puntos is not None:
        detalle += f" · {puntos} línea{'' if puntos == 1 else 's'}"
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
        ("Listos para elaborar", k["pend_elaboracion"], "rojo", True,
         k["puntos_pend_elaboracion"]),
        ("En proceso de elaboración", k["en_proceso"], "indigo", False,
         k["puntos_en_proceso"]),
        ("Retirados", k["retirados"], "violeta", False, None, "línea"),
    ])


# ------------------------------------------------------------------ Datos
if "df_planes" not in st.session_state:
    st.session_state.df_planes = cargar_planes()
df = planes.normalizar_planes(st.session_state.df_planes)

if "aviso_drive" in st.session_state:
    st.error(
        "Los cambios NO se guardaron en Google Drive y se perderán al reiniciar la"
        f" app. Detalle: {st.session_state.pop('aviso_drive')}. Si el archivo"
        " database_planes.json no existe en la carpeta de Drive, súbelo ahí"
        " manualmente (el sistema solo puede actualizar archivos ya creados).",
        icon=":material/error:",
    )

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
        ("En proceso de elaboración", t["en_proceso"], "indigo", False,
         t["puntos_en_proceso"]),
        ("Retirados", t["retirados"], "violeta", False, None, "línea"),
    ]),
    bloque_de_plan("Puntos de inyección", "campo", "turquesa",
                   kpis["PUNTOS DE INYECCIÓN"]),
    bloque_de_plan("Dead legs", "carpeta", "indigo", kpis["DEAD LEG"]),
    bloque_de_plan("Sulfidación", "cliente", "rosa", kpis["SULFIDACIÓN"]),
    bloque_kpi("Especialista", "especialista", "turquesa", [
        ("Por enviar a revisión", t["sin_enviar"], "naranja", True,
         t["puntos_sin_enviar"]),
        ("Pend. revisión especialista", t["por_revisar"], "naranja", True,
         t["puntos_por_revisar"]),
        ("Revisados", t["revisados"], "verde", False, t["puntos_revisados"]),
        ("En revisión de fiabilidad", t["en_revision"], "dorado", True,
         t["puntos_en_revision"]),
    ]),
    bloque_kpi("Valorización", "carpeta", "dorado", [
        ("Valorizados", t["valorizados"], "verde", False, t["puntos_valorizados"]),
        ("Pend. valorizar", t["pend_valorizar"], "naranja", True,
         t["puntos_pend_valorizar"]),
        ("% valorizado", f"{t['avance_valorizacion']:.1f}%", "dorado", False),
    ]),
]
panel.markdown(
    f"<div class='kpi-row'>{''.join(bloques)}</div>", unsafe_allow_html=True
)

# ------------------------------------------------------------------ Tablas
COLS_TABLA = ["PLAN", "MES", "UNIDAD", "CODIGO DE INFORME", "GRUPO DE TUBERÍAS",
              "N° LÍNEAS", "ESTADO", "ETAPA", "RESPONSABLE", "OBSERVACIÓN", "VALORIZACIÓN"]


def detalle_de(clave):
    sub = activos[activos["CLAVE"] == clave]
    d = sub[["UNIDAD", "LINEAS", "SAP", planes.COL_ESTADO, "NOTAS"]].copy()
    d["_PEND"] = sub[planes.COL_ESTADO].map(
        lambda e: "PENDIENTE" in planes.texto_normalizado(e)
    )
    return d.reset_index(drop=True)


ESPECIALISTAS = [
    "Jesús Rehkoff Díaz", "M. Paifa", "Julio Ponce", "Omar", "Christopher",
    "Timana", "Ingrid",
]


def etiqueta(fila):
    codigo = fila["CODIGO DE INFORME"]
    base = fila["GRUPO DE TUBERÍAS"] if planes.es_codigo_provisional(codigo) else codigo
    return f"{fila['PLAN']} · {fila['MES']} · {base}"


def barra_accion(sub, llave, boton, accion, mensaje, con_especialista=False,
                 tipo="primary", icono=":material/send:"):
    """Selector de informes y botón que aplica ``accion`` a los elegidos."""
    if sub.empty:
        return
    opciones = {etiqueta(f): f["CLAVE"] for _, f in sub.iterrows()}
    c_sel, c_esp, c_btn = st.columns([4, 2, 1.2], vertical_alignment="bottom")
    elegidos = c_sel.multiselect(
        "Informes", list(opciones), key=f"sel_{llave}",
        placeholder="Elige uno o varios informes",
    )
    especialista = ""
    if con_especialista:
        especialista = c_esp.selectbox(
            "Especialista", ESPECIALISTAS, key=f"esp_{llave}"
        )
    if c_btn.button(boton, key=f"btn_{llave}", icon=icono, type=tipo,
                    disabled=not elegidos):
        nuevo = st.session_state.df_planes
        for nombre in elegidos:
            nuevo = planes.aplicar_accion(nuevo, opciones[nombre], accion, especialista)
        st.session_state.df_planes = nuevo
        guardar_planes(nuevo)
        st.toast(f"{mensaje}: {len(elegidos)} informe(s).", icon="✅")
        st.rerun()


def mostrar_informes(sub, archivo):
    if sub.empty:
        st.info("No hay informes en esta vista.", icon=":material/info:")
        return
    vista = sub[COLS_TABLA].copy().rename(
        columns={planes.COL_GRUPO: planes.ENCABEZADO_GRUPO})
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


def contiene(texto, consulta):
    return planes.texto_normalizado(consulta) in planes.texto_normalizado(texto)


# Texto de búsqueda de cada informe: sus datos y los de sus puntos/líneas.
_blob_lineas = (
    activos.assign(_t=activos[["LINEAS", "SAP", "NOTAS"]].agg(" ".join, axis=1))
    .groupby("CLAVE")["_t"].agg(" ".join)
)


def filtrar(sub_informes, sub_retiradas, buscar, planes_sel, meses_sel, unidades_sel):
    inf = sub_informes
    ret = sub_retiradas
    if planes_sel:
        inf = inf[inf["PLAN"].isin(planes_sel)]
        ret = ret[ret["ALCANCE DEL SERVICIO"].isin(planes_sel)]
    if meses_sel:
        inf = inf[inf["MES"].isin(meses_sel)]
        ret = ret[ret["MES"].isin(meses_sel)]
    if unidades_sel:
        inf = inf[inf["UNIDAD"].map(
            lambda u: any(x.strip() in unidades_sel for x in u.split(","))
        )]
        ret = ret[ret["UNIDAD"].isin(unidades_sel)]
    if buscar.strip():
        inf = inf[inf.apply(
            lambda f: contiene(
                " ".join([f["CODIGO DE INFORME"], f["GRUPO DE TUBERÍAS"], f["UNIDAD"],
                          f["MES"], f["PLAN"], f["ESTADO"], f["RESPONSABLE"],
                          f["OBSERVACIÓN"], _blob_lineas.get(f["CLAVE"], "")]),
                buscar), axis=1)]
        ret = ret[ret.apply(lambda f: contiene(" ".join(f.astype(str)), buscar), axis=1)]
    return inf, ret


ESTADOS = ["Finalizado", "En proceso", "Pendiente inspección",
           "Pendiente elaboración", "Retirado"]


def senal(fila):
    if planes.es_retirada(fila):
        return "🔴 Retirado"
    if planes.texto_normalizado(fila["VALORIZACIÓN"]) == "SI":
        return "🟢 Valorizado (SI)"
    estado = planes.texto_normalizado(fila[planes.COL_ESTADO])
    if "PENDIENTE INSPECCION" in estado:
        return "🟡 Pend. inspección"
    if "PENDIENTE ELABORACION" in estado:
        return "🟠 Pend. elaboración"
    if planes.es_pendiente_especialista(fila["OBSERVACIÓN"]):
        return "🔵 Pend. especialista"
    return "⚪ Sin alerta"


def vista_editable(df, buscar, planes_sel, meses_sel, unidades_sel):
    """Matriz editable como en el panel principal: se llena y se guarda en Drive."""
    vista = df
    if planes_sel:
        vista = vista[vista["ALCANCE DEL SERVICIO"].isin(planes_sel)]
    if meses_sel:
        vista = vista[vista["MES"].isin(meses_sel)]
    if unidades_sel:
        vista = vista[vista["UNIDAD"].isin(unidades_sel)]
    if buscar.strip():
        vista = vista[vista.apply(
            lambda f: contiene(" ".join(f.astype(str)), buscar), axis=1)]
    st.caption(
        "Llena estado, responsable, observación y valorización directamente en la"
        " tabla y pulsa «Guardar cambios». Respeta los filtros de arriba."
    )
    vista = vista.copy()
    vista["VALORIZACIÓN"] = vista["VALORIZACIÓN"].map(
        lambda v: "SI" if planes.texto_normalizado(v) == "SI"
        else ("Retirado" if planes.texto_normalizado(v) == "RETIRADO" else "Pendiente")
    )
    vista.insert(0, "SEÑAL", vista.apply(senal, axis=1))
    # El grupo de tuberías no aplica a los planes especiales: se oculta aquí.
    vista = vista.drop(columns=["GRUPO DE TUBERÍAS"])
    config = {
        "SEÑAL": st.column_config.TextColumn("Señal", width=170, disabled=True, pinned=True),
        "ITEM POR MES": st.column_config.TextColumn("Item", width=70),
        "IT2": st.column_config.TextColumn("IT2", width=55),
        "UNIDAD": st.column_config.TextColumn("Unidad", width=65),
        "MES": st.column_config.TextColumn("Mes", width=90),
        "LINEAS": st.column_config.TextColumn("Líneas", width=190),
        "CODIGO DE INFORME": st.column_config.TextColumn("Código de informe", width=210),
        "SAP": st.column_config.TextColumn("SAP", width=85),
        "ALCANCE DEL SERVICIO": st.column_config.TextColumn("Plan", width=170),
        "NOTAS": st.column_config.TextColumn("Notas", width=200),
        planes.COL_ESTADO: st.column_config.SelectboxColumn(
            "Estado de elaboración",
            options=ESTADOS + sorted(set(df[planes.COL_ESTADO]) - set(ESTADOS) - {""}),
            width=190),
        "RESPONSABLE": st.column_config.TextColumn("Responsable", width=135),
        "OBSERVACIÓN": st.column_config.TextColumn("Observación", width=280),
        "VALORIZACIÓN": st.column_config.SelectboxColumn(
            "Valorización", options=["Pendiente", "SI", "Retirado"],
            required=True, width=145),
    }
    editado = st.data_editor(
        vista, column_config=config, hide_index=True, width="stretch",
        height=600, disabled=["SEÑAL"], key="editor_planes",
    )
    if st.button("Guardar cambios", key="guardar_matriz_planes",
                 icon=":material/save:", type="primary"):
        cambios = editado.drop(columns=["SEÑAL"], errors="ignore").fillna("")
        cambios = cambios.replace(["None", "none", "NONE"], "")
        # SI = valorizado: se limpia la observación, como en el panel principal.
        cambios.loc[cambios["VALORIZACIÓN"].map(
            lambda v: planes.texto_normalizado(v) == "SI"), "OBSERVACIÓN"] = ""
        # Retirado: el resto de columnas de control quedan como retiradas.
        ret = cambios[planes.COL_ESTADO].map(
            lambda v: planes.texto_normalizado(v) == "RETIRADO")
        for col in ("RESPONSABLE", "OBSERVACIÓN", "VALORIZACIÓN"):
            cambios.loc[ret, col] = "Retirado"
        nuevo = planes.normalizar_planes(st.session_state.df_planes)
        nuevo.update(cambios)
        st.session_state.df_planes = nuevo
        guardar_planes(nuevo)
        st.toast("¡Cambios guardados con éxito!", icon="💾")
        st.rerun()


sistema = st.container(key="sistema_control")
with sistema:
    c_buscar, c_plan, c_mes, c_unidad = st.columns([2.2, 1.6, 1.2, 1.2])
    buscar = c_buscar.text_input(
        "Buscar", placeholder="Código de informe, línea, SAP, grupo, nota…",
        icon=":material/search:",
    )
    planes_sel = c_plan.multiselect(
        "Plan", sorted(set(informes["PLAN"]) | set(retiradas["ALCANCE DEL SERVICIO"])),
        placeholder="Todos los planes",
    )
    meses_disp = [m for m in planes.ORDEN_MESES if m in set(informes["MES"]) | set(retiradas["MES"])]
    meses_sel = c_mes.multiselect("Mes", meses_disp, placeholder="Todos")
    unidades_disp = sorted(
        {x.strip() for u in informes["UNIDAD"] for x in u.split(",") if x.strip()}
        | {u for u in retiradas["UNIDAD"] if u}
    )
    unidades_sel = c_unidad.multiselect("Unidad", unidades_disp, placeholder="Todas")

    informes_total = informes
    informes, retiradas = filtrar(
        informes, retiradas, buscar, planes_sel, meses_sel, unidades_sel
    )
    if buscar.strip() or planes_sel or meses_sel or unidades_sel:
        st.caption(
            f"{len(informes)} de {len(informes_total)} informes · "
            f"{len(retiradas)} puntos retirados con el filtro aplicado"
        )

    tabs = st.tabs([
        "Matriz (llenar)", "Pend. inspección", "Listos para elaborar",
        "En proceso",
        "Revisión especialista", "Valorización", "Finalizados", "Retirados",
        "Resumen",
    ])
    with tabs[0]:
        vista_editable(df, buscar, planes_sel, meses_sel, unidades_sel)
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
            informes[informes["ESTADO"] == planes.OTRO], "Planes_En_Proceso.xlsx"
        )
    with tabs[4]:
        vista = st.radio(
            "Vista",
            ["Por enviar", "Pendientes de revisión", "Revisados por el especialista"],
            horizontal=True, key="radio_esp",
        )
        if vista == "Por enviar":
            sub = informes[informes["ETAPA"].isin(
                [planes.ETAPA_SIN_ENVIAR, planes.ETAPA_FIABILIDAD])]
            barra_accion(sub, "enviar", "Enviar a revisión", "enviar_revision",
                         "Enviados a revisión", con_especialista=True)
            mostrar_informes(sub, "Planes_Por_Enviar_Revision.xlsx")
        elif vista == "Pendientes de revisión":
            sub = informes[informes["ETAPA"] == planes.ETAPA_PEND_ESP]
            barra_accion(sub, "revisar", "Marcar revisado", "revisado",
                         "Marcados como revisados", con_especialista=True,
                         icono=":material/check:")
            mostrar_informes(sub, "Planes_Pend_Revision_Especialista.xlsx")
        else:
            sub = informes[informes["ETAPA"] == planes.ETAPA_REVISADO]
            mostrar_informes(sub, "Planes_Revisados_Especialista.xlsx")
    with tabs[5]:
        vista = st.radio(
            "Vista", ["Pendientes de valorizar", "Valorizados"],
            horizontal=True, key="radio_val",
        )
        if vista == "Pendientes de valorizar":
            sub = informes[(informes["ESTADO"] == planes.FINALIZADO)
                           & (informes["ETAPA"] != planes.ETAPA_VALORIZADO)]
            st.caption(
                "Lo habitual es valorizar informes ya revisados por el especialista"
                " (etapa «Revisado por especialista»)."
            )
            barra_accion(sub, "valorizar", "Valorizar", "valorizar",
                         "Valorizados", icono=":material/paid:")
            mostrar_informes(sub, "Planes_Pend_Valorizar.xlsx")
        else:
            sub = informes[informes["ETAPA"] == planes.ETAPA_VALORIZADO]
            barra_accion(sub, "desval", "Quitar valorización", "quitar_valorizacion",
                         "Valorización quitada", tipo="secondary",
                         icono=":material/undo:")
            mostrar_informes(sub, "Planes_Valorizados.xlsx")
    with tabs[6]:
        mostrar_informes(
            informes[informes["ESTADO"] == planes.FINALIZADO],
            "Planes_Finalizados.xlsx",
        )
    with tabs[7]:
        if retiradas.empty:
            st.info("No hay puntos retirados.", icon=":material/info:")
        else:
            vista = retiradas[["ALCANCE DEL SERVICIO", "MES", "UNIDAD", "LINEAS",
                               "CODIGO DE INFORME", "SAP", "NOTAS"]].copy()
            vista.index = range(1, len(vista) + 1)
            tabla_html(vista)
    with tabs[8]:
        st.markdown("**Resumen por plan**")
        tabla_html(planes.resumen_por_plan(kpis))
        st.markdown("**Informes por mes**")
        tabla_html(planes.resumen_por_mes(informes_total))
        st.caption("El resumen no se ve afectado por los filtros.")
