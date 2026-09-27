"""Tema visual de la app: "Corporativo oscuro" (azul marino y dorado).

Los colores base de Streamlit (fondo, texto, tablas nativas, fuente) están en
.streamlit/config.toml; aquí van los estilos de los elementos propios (cabecera,
tarjetas, KPIs, pestañas, tablas HTML) y los ajustes de las otras páginas.
"""

import html

import pandas as pd
import streamlit as st

# Paleta
FONDO = "#0C1622"
SUPERFICIE = "#132131"
BLOQUE = "#162739"
ITEM = "#1B2E43"
BORDE = "#26405A"
TEXTO = "#E6EDF5"
TEXTO_SUAVE = "#9AAEC2"
CABECERA = "#0A1C2E"
CABECERA_SUB = "#93A9BF"
DORADO = "#E0B04F"
CABECERA_TABLA = "#1A2D42"

# Tonos de los indicadores (legibles sobre fondo oscuro)
TONOS = {
    "azul": "#86B6E8",
    "verde": "#52C58E",
    "naranja": "#F0A04B",
    "violeta": "#AC98F2",
    "rosa": "#E78AB8",
    "dorado": "#E0B04F",
    "turquesa": "#52C2CE",
    "rojo": "#F27C74",
    "indigo": "#93A8F6",
}

# Iconos de línea (24x24, trazo con el color del bloque) para los bloques KPI
_SVG = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>'
)
ICONOS = {
    "grafico": _SVG.format('<path d="M3 3v18h18"/><path d="M8 16v-5"/><path d="M13 16V8"/><path d="M18 16v-3"/>'),
    "carpeta": _SVG.format('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'),
    "especialista": _SVG.format('<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0"/><path d="m16 11 2 2 4-4"/>'),
    "campo": _SVG.format('<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>'),
    "cliente": _SVG.format('<rect x="4" y="3" width="16" height="18" rx="1"/><path d="M9 7h1M14 7h1M9 11h1M14 11h1M9 15h1M14 15h1"/>'),
    "anexo": _SVG.format('<path d="m21 11-8.5 8.5a5 5 0 0 1-7-7L14 4a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L15 7"/>'),
}


def tinte(color_hex, alfa):
    """Color hex con transparencia, para fondos y bordes teñidos."""
    r, g, b = (int(color_hex[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {alfa})"


CSS = f"""
<style>
footer {{visibility: hidden;}}
.stApp {{ background-color: {FONDO}; }}
.block-container {{ padding-top: 1.6rem !important; }}

/* CABECERA */
.header-banner {{
    background: {CABECERA} !important;
    border: 1px solid {BORDE};
    padding: 24px 32px;
    border-radius: 14px;
    color: {TEXTO};
    margin-bottom: 20px;
    box-shadow: none !important;
    position: relative;
    overflow: hidden;
}}
.header-banner::after {{
    content: "";
    position: absolute; top: 50%; right: 32px; bottom: auto;
    width: 56px; height: 6px; margin-top: -3px;
    border-radius: 3px;
    background: {DORADO} !important;
}}
.header-title {{
    font-size: 26px; font-weight: 700; letter-spacing: 0.02em;
    margin: 0; padding-right: 90px; color: #F2F6FA !important;
}}
.header-subtitle {{ font-size: 14px; color: {CABECERA_SUB} !important; margin-top: 6px; font-weight: 400; }}

/* CABECERA CON INDICADORES (página principal) */
.header-banner.header-indicadores {{
    display: flex; justify-content: space-between; align-items: center; gap: 24px;
    flex-wrap: wrap; padding: 22px 28px;
}}
.header-banner.header-indicadores::after {{ display: none; }}
.header-indicadores .header-title {{ padding-right: 0; }}
.header-marca {{ display: flex; align-items: center; gap: 18px; min-width: 0; }}
.header-icono {{
    width: 52px; height: 52px; border-radius: 12px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    background: {tinte(DORADO, 0.14)}; border: 1px solid {tinte(DORADO, 0.45)}; color: {DORADO};
}}
.header-chips {{ display: flex; gap: 10px; flex-wrap: wrap; }}
.header-chip {{
    display: flex; flex-direction: column; justify-content: center; gap: 4px;
    padding: 10px 14px; border-radius: 10px; background: {SUPERFICIE}; border: 1px solid {BORDE};
}}
.header-chip-avance {{ width: 190px; gap: 6px; }}
.chip-titulo {{
    display: flex; justify-content: space-between; gap: 10px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; color: {TEXTO_SUAVE};
}}
.chip-porcentaje {{ color: {TONOS["verde"]}; }}
.chip-barra {{ height: 6px; border-radius: 3px; background: #0F1C2A; overflow: hidden; }}
.chip-barra div {{ height: 100%; background: {TONOS["verde"]}; }}
.chip-detalle {{ font-size: 12px; color: #C9D6E3; }}
.chip-valor {{ font-size: 15px; font-weight: 600; color: {TEXTO}; }}
.chip-dorado {{ font-size: 17px; font-weight: 700; color: {DORADO}; }}

/* BARRA DE GESTIÓN DE DATOS */
.st-key-barra_datos {{
    background: {SUPERFICIE}; border: 1px solid {BORDE}; border-radius: 10px;
    padding: 6px 16px; margin-bottom: 20px;
}}
.barra-datos-texto {{
    display: flex; align-items: center; gap: 10px; font-size: 14px; color: {TEXTO_SUAVE};
}}
.barra-datos-texto svg {{ color: {TEXTO_SUAVE}; flex-shrink: 0; }}
.barra-datos-titulo {{ font-weight: 600; color: #C9D6E3; }}
[data-testid="stPopover"] button {{
    background: {ITEM} !important; border: 1px solid {BORDE} !important;
    color: {TEXTO} !important; font-weight: 600 !important; border-radius: 8px !important;
}}
[data-testid="stPopover"] button:hover {{ border-color: {DORADO} !important; color: {DORADO} !important; }}
.st-key-barra_datos [data-testid="stElementContainer"]:has([data-testid="stDownloadButton"]),
.st-key-barra_datos [data-testid="stDownloadButton"],
.st-key-barra_datos [data-testid="stDownloadButton"] button {{ width: 100% !important; }}
.st-key-barra_datos [data-testid="stMarkdownContainer"] {{ margin-bottom: 0 !important; }}
.st-key-barra_datos [data-testid="stMarkdownContainer"] > div {{ margin: 0 !important; }}

/* TARJETAS / CONTENEDORES */
.st-key-panel_control, .st-key-sistema_control,
.st-key-tarjeta_estado, .st-key-tarjeta_carga, .st-key-tarjeta_iso,
.st-key-tarjeta_resultados {{
    background: {SUPERFICIE} !important;
    border: 1px solid {BORDE} !important;
    border-radius: 14px;
    padding: 20px 22px 22px;
    margin-bottom: 20px;
    box-shadow: none !important;
}}
.section-title {{
    font-size: 1.15rem;
    font-weight: 700;
    color: {TEXTO} !important;
    margin-bottom: 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid {BORDE};
}}
.section-title-row {{ border-bottom: 1px solid {BORDE} !important; }}
.section-title-row .section-title {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
div[data-testid="stExpander"] {{
    background: {SUPERFICIE}; border: 1px solid {BORDE}; border-radius: 10px;
}}
div[data-testid="stExpander"] details {{ border: none; }}

/* KPIs */
.kpi-row {{
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    align-items: stretch;
    gap: 12px;
}}
@media (max-width: 1100px) {{ .kpi-row {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }} }}
@media (max-width: 700px) {{ .kpi-row {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
.kpi-block-card {{
    background: {BLOQUE};
    border: 1px solid {BORDE};
    border-radius: 10px;
    padding: 14px;
    min-width: 0;
    display: flex;
    flex-direction: column;
    height: 100%;
    box-sizing: border-box;
}}
.kpi-block-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }}
.kpi-block-icon {{
    width: 32px; height: 32px; border-radius: 8px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    color: var(--tone); background: var(--tone-bg); border: 1px solid var(--tone-borde);
}}
.kpi-block-head .kpi-block-title {{ margin-bottom: 0; }}
.kpi-block-title {{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {TEXTO_SUAVE};
    margin-bottom: 10px;
    white-space: nowrap;
}}
.kpi-items {{ display: grid; grid-template-columns: minmax(0, 1fr); gap: 10px; flex: 1; align-content: start; }}
.kpi-item {{
    background: {ITEM};
    border: 1px solid {BORDE};
    border-radius: 8px;
    padding: 10px 12px;
}}
.kpi-item-label {{
    display: flex; align-items: center; gap: 8px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    color: {TEXTO_SUAVE};
    letter-spacing: 0.04em;
    line-height: 1.3;
}}
.kpi-dot {{ width: 8px; height: 8px; border-radius: 4px; flex-shrink: 0; background: var(--tone); }}
.kpi-item-value {{ font-size: 28px; font-weight: 700; color: var(--tone); line-height: 1.1; margin-top: 4px; }}
.kpi-item.alerta {{ background: var(--tone-bg); border-color: var(--tone-borde); }}

/* PESTAÑAS */
.stTabs [data-baseweb="tab-list"],
.stTabs [role="tablist"] {{
    display: flex !important;
    width: 100% !important;
    gap: 6px !important;
    flex-wrap: wrap;
    background: transparent !important;
    padding: 0 0 6px 0;
}}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"],
.stTabs [role="tab"]::before, .stTabs [role="tab"]::after {{ display: none !important; }}
.stTabs [role="tab"] {{
    display: inline-flex !important; align-items: center;
    flex: 0 1 auto !important;
    justify-content: center !important;
    min-height: 40px;
    height: auto;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
    color: #C9D6E3 !important;
    padding: 0 16px !important;
    background: {SUPERFICIE} !important;
    border: 1px solid {BORDE} !important;
    white-space: nowrap;
}}
.stTabs [role="tab"] p {{ font-size: 14px; font-weight: 600; color: inherit; }}
.stTabs [role="tab"]:hover {{ border-color: {DORADO} !important; }}
.stTabs [aria-selected="true"] {{
    background: {DORADO} !important;
    color: {FONDO} !important;
    border-color: {DORADO} !important;
}}
.stTabs [aria-selected="true"] p {{ color: {FONDO} !important; }}

/* CAMPOS DE FILTRO Y BÚSQUEDA */
[data-testid="stSelectbox"] [role="group"],
[data-testid="stMultiSelect"] [role="group"],
[data-testid="stTextInputRootElement"],
[data-testid="stNumberInputContainer"],
[data-testid="stDateInputField"],
[data-testid="stTextArea"] textarea {{
    background: {ITEM} !important;
    border: 1px solid {BORDE} !important;
    border-radius: 8px !important;
}}
[data-testid="stSelectbox"] [role="group"]:focus-within,
[data-testid="stMultiSelect"] [role="group"]:focus-within,
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stNumberInputContainer"]:focus-within,
[data-testid="stDateInputField"]:focus-within,
[data-testid="stTextArea"] textarea:focus {{
    border-color: {DORADO} !important;
}}
[data-testid="stTextInputRootElement"] input,
[data-testid="stNumberInputContainer"] input {{ background: transparent !important; }}

/* TABLAS NATIVAS (tabla general editable) */
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {{
    border-radius: 10px;
    margin-top: 10px !important;
}}

/* BOTONES */
.stDownloadButton button, .stButton > button[kind="secondary"] {{
    background: {ITEM} !important;
    border: 1px solid {BORDE} !important;
    color: {TEXTO} !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}}
.stDownloadButton button:hover, .stButton > button[kind="secondary"]:hover {{
    border-color: {DORADO} !important; color: {DORADO} !important;
}}
.stButton > button[kind="primary"] {{
    background: {DORADO} !important;
    color: {FONDO} !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    box-shadow: none !important;
}}
.stButton > button[kind="primary"] p {{ color: {FONDO} !important; }}
.stButton > button[kind="primary"]:hover {{ filter: brightness(1.08); }}

/* CARGA DE ARCHIVOS */
[data-testid="stFileUploaderDropzone"] {{
    border: 1.5px dashed {BORDE} !important;
    border-radius: 12px !important;
    background: {BLOQUE} !important;
}}
[data-testid="stFileUploaderDropzone"]:hover {{ border-color: {DORADO} !important; box-shadow: none !important; }}
.upload-label-title {{ color: {TEXTO} !important; }}
.upload-label-sub {{ color: {TEXTO_SUAVE} !important; }}
.iso-row-name {{ color: #C9D6E3 !important; }}

/* ETIQUETAS Y ESTADOS (página de elaboración) */
.badge-oblig {{ color: #F0CD7C !important; background: #3A2F14 !important; border: 1px solid #5A4A22 !important; }}
.badge-opt {{ color: #BFD3E8 !important; background: #1F3650 !important; }}
.status-pill.ok {{ background: #12301F !important; border: 1px solid #1E5A3A !important; }}
.status-pill.bad {{ background: #3A1715 !important; border: 1px solid #6B2A26 !important; }}
.status-label {{ color: #BDEBD0 !important; }}
.status-pill.bad .status-label {{ color: #F7C3BF !important; }}
.status-icon.ok {{ background: #2E9E68 !important; }}
.status-icon.bad {{ background: #D8534F !important; }}
.st-key-dl_compilado {{
    background: {CABECERA} !important; border: 1px solid {BORDE};
}}
.dl-compilado-title {{ color: #F2F6FA !important; }}
.dl-compilado-sub {{ color: {CABECERA_SUB} !important; }}
.st-key-dl_compilado .stDownloadButton button {{
    background: {DORADO} !important; color: {FONDO} !important; border: none !important;
}}
.st-key-dl_word, .st-key-dl_excel, .st-key-dl_anexos {{
    background: {BLOQUE} !important; border: 1px solid {BORDE} !important;
}}

/* TABLAS DE CONSULTA (HTML) */
.tabla-wrap {{
    max-height: 600px;
    overflow: auto;
    border: 1px solid {BORDE};
    border-radius: 12px;
    background: {SUPERFICIE};
    margin-top: 10px;
}}
.tabla-html {{ width: 100%; border-collapse: separate; border-spacing: 0; font-size: 14px; }}
.tabla-html th {{
    position: sticky; top: 0; z-index: 1;
    background: {CABECERA_TABLA};
    color: {TEXTO_SUAVE};
    font-size: 12px; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase;
    text-align: left; padding: 11px 14px; white-space: nowrap;
}}
.tabla-html td {{
    padding: 11px 14px; border-top: 1px solid {BORDE}; color: {TEXTO}; vertical-align: middle;
}}
.tabla-html tr:hover td {{ background: rgba(224, 176, 79, 0.16); }}
.tabla-html tr:hover td:first-child {{ box-shadow: inset 3px 0 0 {DORADO}; }}
.tabla-html td.t-idx {{ color: {TEXTO_SUAVE}; width: 1%; }}
.tabla-html td.t-codigo {{ font-weight: 600; white-space: nowrap; }}
.tabla-html td.t-suave {{ color: {TEXTO_SUAVE}; white-space: nowrap; }}
.tabla-html td.t-alerta {{ font-weight: 700; color: {TONOS["rojo"]}; }}
.tabla-html tr.t-total td {{ font-weight: 700; background: {CABECERA_TABLA}; }}
.chip {{
    display: inline-block; padding: 3px 10px; border-radius: 999px;
    font-size: 12px; font-weight: 700; white-space: nowrap;
    background: #1F3650; color: #BFD3E8;
}}
.chip-anexo {{ background: #3A2F14; color: #F0CD7C; }}
/* CARGA POR RESPONSABLE */
.carga-tarjetas {{
    display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 6px 0 14px;
}}
@media (max-width: 900px) {{ .carga-tarjetas {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
.carga-panel {{
    background: {BLOQUE}; border: 1px solid {BORDE}; border-radius: 12px;
    padding: 16px 18px; margin-bottom: 14px;
}}
.carga-titulo {{ font-size: 16px; font-weight: 700; color: {TEXTO}; margin-bottom: 8px; }}
.carga-leyenda {{ display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 10px; }}
.carga-leyenda-item {{ display: flex; align-items: center; gap: 6px; font-size: 12px; color: #C9D6E3; }}
.carga-lista {{ display: flex; flex-direction: column; gap: 6px; }}
.carga-fila {{
    display: flex; align-items: center; gap: 14px; padding: 8px 12px;
    border-radius: 10px; border: 1px solid transparent;
}}
.carga-fila:hover {{ background: rgba(224, 176, 79, 0.10); border-color: {DORADO}; }}
.carga-fila.sin-asignar {{ background: {tinte(TONOS["rojo"], 0.08)}; border-color: {tinte(TONOS["rojo"], 0.45)}; }}
.carga-fila.sin-asignar .carga-nombre {{ color: {TONOS["rojo"]}; }}
.carga-nombre {{ width: 150px; flex-shrink: 0; font-size: 14px; font-weight: 600; color: {TEXTO}; }}
.carga-barra {{
    flex-grow: 1; min-width: 0; display: flex; gap: 2px; height: 26px;
    border-radius: 6px; background: #0F1C2A; overflow: hidden;
}}
.carga-seg {{
    display: flex; align-items: center; justify-content: center; height: 100%;
    min-width: 24px; flex-shrink: 1; box-sizing: border-box;
    font-size: 12px; font-weight: 700; color: {FONDO};
}}
.carga-total {{
    width: 190px; flex-shrink: 0; display: flex; justify-content: flex-end; align-items: center;
    gap: 8px; font-size: 13px; color: #C9D6E3;
}}
.carga-total b {{ color: {TEXTO}; }}
.chip-saturado {{
    padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 700;
    background: {tinte(TONOS["naranja"], 0.18)}; color: {TONOS["naranja"]};
}}
.tabla-nota {{ font-size: 14px; color: {TEXTO_SUAVE}; margin: 4px 0 6px; }}
</style>
"""


def aplicar_tema():
    st.markdown(CSS, unsafe_allow_html=True)


def _celda(columna, valor):
    texto = "" if valor is None or (isinstance(valor, float) and pd.isna(valor)) else str(valor)
    contenido = html.escape(texto)
    nombre = str(columna).strip().upper()
    if nombre == "TIPO" and texto:
        clase = "chip chip-anexo" if texto.upper() == "ANEXO" else "chip"
        return f'<td><span class="{clase}">{contenido}</span></td>'
    if nombre == "CODIGO DE INFORME":
        return f'<td class="t-codigo">{contenido}</td>'
    if nombre == "GRUPO DE TUBERÍAS":
        return f'<td class="t-suave">{contenido}</td>'
    if nombre == "LINEAS SIN INSPECCIONAR" and texto not in ("", "0"):
        return f'<td class="t-alerta">{contenido}</td>'
    return f"<td>{contenido}</td>"


def tabla_html(df, nota=None):
    """Tabla de solo lectura con el estilo del tema (etiquetas de tipo, alertas)."""
    if nota:
        st.html(f'<div class="tabla-nota">{html.escape(nota)}</div>')
    encabezado = "<th></th>" + "".join(
        f"<th>{html.escape(str(c).strip())}</th>" for c in df.columns
    )
    filas = []
    for indice, fila in df.iterrows():
        es_total = str(fila.iloc[0]).strip().upper() == "TOTAL"
        celdas = "".join(_celda(c, v) for c, v in zip(df.columns, fila))
        clase = ' class="t-total"' if es_total else ""
        filas.append(
            f'<tr{clase}><td class="t-idx">{html.escape(str(indice))}</td>{celdas}</tr>'
        )
    st.html(
        '<div class="tabla-wrap"><table class="tabla-html">'
        f"<thead><tr>{encabezado}</tr></thead>"
        f"<tbody>{''.join(filas)}</tbody></table></div>"
    )
