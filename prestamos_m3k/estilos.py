"""Estilos y piezas de interfaz: aspecto de software contable (fondo claro, tablas densas tipo libro).

Criterios aplicados, tomados de las Web Interface Guidelines de Vercel:
- foco visible en todo lo que se puede pulsar y áreas táctiles de al menos 44 px;
- números tabulares alineados a la derecha para que las columnas de importes se lean en vertical;
- el estado nunca va solo en color: siempre lleva texto (pastillas «Vencido», «Cuadra»);
- estados vacíos con una salida (qué hacer a continuación) y sin callejones sin salida;
- importes y fechas con formato local (S/ 1,234.50 · 15/11/2026);
- respeto a prefers-reduced-motion y sin bloquear el zoom.
"""

from __future__ import annotations

import html
from datetime import date

import streamlit as st

import calculos as calc

# Paleta clara: verde sobrio como acento y colores de estado separados del acento.
FONDO, PAPEL, BORDE = "#FFFFFF", "#F4F7F5", "#D3DCD7"
TEXTO, TEXTO_SUAVE, ACENTO, CABECERA_TABLA = "#1B2A22", "#5A6B62", "#1F6B4F", "#E8EEEA"
TONOS = {"ok": "#1E7B4B", "aviso": "#A8600A", "malo": "#B3261E", "info": "#1D5F9A", "neutro": "#5A6B62"}


class Raw(str):
    """Texto que ya es HTML seguro (el resto se escapa)."""


def esc(valor) -> str:
    return valor if isinstance(valor, Raw) else html.escape(str(valor))


def soles(importe: float, signo: bool = False) -> str:
    texto = f"S/ {abs(importe):,.2f}"
    if importe < 0:
        return f"−{texto}"
    return f"+{texto}" if signo and importe > 0 else texto


def monto(importe: float) -> str:
    """Importe sin símbolo para columnas contables; el cero se muestra como guion."""
    return "–" if abs(importe) < 0.005 else (f"({abs(importe):,.2f})" if importe < 0 else f"{importe:,.2f}")


def fecha_txt(valor) -> str:
    return calc.fecha(valor).strftime("%d/%m/%Y")


def pct(valor: float, decimales: int = 1) -> str:
    return f"{valor * 100:,.{decimales}f} %"


CSS = f"""
<style>
:root {{ --fondo:{FONDO}; --papel:{PAPEL}; --borde:{BORDE}; --texto:{TEXTO}; --suave:{TEXTO_SUAVE}; --acento:{ACENTO};
  --ok:{TONOS['ok']}; --aviso:{TONOS['aviso']}; --malo:{TONOS['malo']}; --info:{TONOS['info']}; }}
.block-container {{ padding-top: 1.2rem; max-width: 1240px; }}
html {{ scroll-behavior: smooth; }}
.num {{ font-variant-numeric: tabular-nums; }}

/* Cabecera de página */
.m3k-cab {{ border-bottom: 2px solid var(--acento); padding-bottom:.55rem; margin: 0 0 1rem; display:flex;
  justify-content:space-between; align-items:flex-end; gap:1rem; flex-wrap:wrap; }}
.m3k-cab .marca {{ font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:var(--acento); font-weight:700; }}
.m3k-cab h1 {{ font-size:1.5rem; line-height:1.25; margin:0; padding:0; text-wrap:balance; }}
.m3k-cab p {{ margin:.15rem 0 0; color:var(--suave); font-size:.9rem; }}

/* Indicadores: tarjetas planas con filete de color */
.m3k-kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:.7rem; margin:.3rem 0 1.1rem; }}
.m3k-kpi {{ background:var(--fondo); border:1px solid var(--borde); border-left:4px solid var(--tono, var(--borde));
  border-radius:6px; padding:.7rem .9rem; }}
.m3k-kpi .e {{ color:var(--suave); font-size:.76rem; letter-spacing:.03em; text-transform:uppercase; }}
.m3k-kpi .v {{ font-size:1.5rem; font-weight:700; margin:.1rem 0; font-variant-numeric:tabular-nums; overflow-wrap:anywhere; }}
.m3k-kpi .nota {{ color:var(--suave); font-size:.78rem; }}
.m3k-kpi.heroe {{ background:var(--papel); }}

/* Pastillas de estado (siempre con texto) */
.m3k-chip {{ display:inline-block; padding:.08rem .55rem; border-radius:4px; font-size:.74rem; font-weight:600; white-space:nowrap;
  color:var(--c); background:color-mix(in srgb, var(--c) 10%, white); border:1px solid color-mix(in srgb, var(--c) 35%, white); }}

/* Tablas tipo libro */
.m3k-scroll {{ overflow-x:auto; border:1px solid var(--borde); border-radius:6px; margin:.3rem 0 1rem; max-height:70vh; }}
.m3k-tabla {{ width:100%; border-collapse:collapse; font-size:.84rem; }}
.m3k-tabla th {{ text-align:left; background:{CABECERA_TABLA}; color:var(--suave); font-weight:600; font-size:.72rem;
  letter-spacing:.04em; text-transform:uppercase; padding:.45rem .65rem; white-space:nowrap; position:sticky; top:0; z-index:1;
  border-bottom:1px solid var(--borde); }}
.m3k-tabla td {{ padding:.38rem .65rem; border-top:1px solid #E6ECE8; vertical-align:middle; }}
.m3k-tabla tbody tr:nth-child(even) td {{ background:#FAFBFA; }}
.m3k-tabla td.n, .m3k-tabla th.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
.m3k-tabla tr.cab td {{ background:var(--papel) !important; font-weight:600; border-top:1px solid var(--borde); }}
.m3k-tabla tr.sub td {{ font-weight:600; background:var(--papel) !important; }}
.m3k-tabla td.sangria {{ padding-left:1.6rem; color:var(--suave); }}
.m3k-tabla tfoot td {{ font-weight:700; background:{CABECERA_TABLA}; border-top:2px solid var(--borde); padding:.45rem .65rem;
  font-variant-numeric:tabular-nums; }}
.m3k-tabla tfoot td.n {{ text-align:right; }}
.m3k-tabla tbody tr:hover td {{ background:#EEF4F0; }}
.m3k-barra {{ height:6px; background:#E6ECE8; border-radius:99px; min-width:70px; overflow:hidden; }}
.m3k-barra i {{ display:block; height:100%; background:var(--ok); border-radius:99px; }}

/* Fila de cobranza y estados vacíos */
.m3k-fila {{ background:var(--fondo); border:1px solid var(--borde); border-left:4px solid var(--tono, var(--borde));
  border-radius:6px; padding:.6rem .85rem; display:flex; justify-content:space-between; gap:1rem; align-items:center; }}
.m3k-fila b {{ display:block; }} .m3k-fila small {{ color:var(--suave); }}
.m3k-vacio {{ border:1px dashed var(--borde); border-radius:8px; padding:1.3rem; text-align:center; color:var(--suave); background:var(--papel); }}
.m3k-vacio b {{ color:var(--texto); display:block; margin-bottom:.25rem; }}
.m3k-verif {{ display:flex; justify-content:space-between; gap:1rem; padding:.45rem .1rem; border-bottom:1px solid #E6ECE8; font-size:.9rem; }}

/* Recibo imprimible */
.m3k-recibo {{ background:#fff; color:#1B2A22; border:1px solid var(--borde); border-radius:8px; padding:1.3rem 1.5rem; max-width:520px;
  margin:.5rem 0 1rem; font-variant-numeric:tabular-nums; }}
.m3k-recibo h3 {{ margin:0 0 .2rem; color:var(--acento); }} .m3k-recibo hr {{ border:0; border-top:1px dashed #9aa79f; margin:.8rem 0; }}
.m3k-recibo .f {{ display:flex; justify-content:space-between; gap:1rem; padding:.18rem 0; }}
.m3k-recibo .t {{ font-size:1.2rem; font-weight:700; }} .m3k-recibo .anul {{ color:var(--malo); font-weight:700; }}

/* Controles: objetivos táctiles de 44 px, foco visible y sin retraso de doble toque */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {{ min-height:44px; touch-action:manipulation; font-weight:600; }}
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {{ min-height:44px; }}
div[data-baseweb="select"] > div {{ min-height:44px; }}
button:focus-visible, input:focus-visible, textarea:focus-visible, [role="tab"]:focus-visible, a:focus-visible,
[role="region"]:focus-visible, [data-baseweb="select"]:focus-within {{ outline:2px solid var(--acento) !important; outline-offset:2px; }}
[role="tab"] {{ min-height:44px; }}
@media (max-width: 640px) {{
  .block-container {{ padding-left:.9rem; padding-right:.9rem; }}
  .m3k-cab h1 {{ font-size:1.25rem; }} .m3k-kpi .v {{ font-size:1.3rem; }}
  .m3k-fila {{ flex-direction:column; align-items:flex-start; }}
}}
@media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; transition:none !important; scroll-behavior:auto !important; }} }}
</style>
"""


def aplicar() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def encabezado(titulo: str, subtitulo: str = "") -> None:
    sub = f"<p>{esc(subtitulo)}</p>" if subtitulo else ""
    st.markdown(f'<div class="m3k-cab"><div><div class="marca">M3K · Préstamos personales</div>'
                f"<h1>{esc(titulo)}</h1>{sub}</div></div>", unsafe_allow_html=True)


def chip(texto: str, tono: str = "neutro") -> Raw:
    return Raw(f'<span class="m3k-chip" style="--c:{TONOS.get(tono, TONOS["neutro"])}">{esc(texto)}</span>')


ESTADOS_PRESTAMO = {
    "vigente": ("Al día", "ok"), "vencido": ("Vencido", "malo"), "cancelado": ("Cancelado", "info"), "anulado": ("Anulado", "neutro"),
}
ESTADOS_CUOTA = {
    "pagada": ("Pagada", "ok"), "parcial": ("Pago parcial", "aviso"), "pendiente": ("Pendiente", "neutro"), "vencida": ("Vencida", "malo"),
}


def chip_prestamo(estado: str) -> Raw:
    return chip(*ESTADOS_PRESTAMO.get(estado, (estado, "neutro")))


def chip_cuota(estado: str) -> Raw:
    return chip(*ESTADOS_CUOTA.get(estado, (estado, "neutro")))


def chip_cuadre(cuadra: bool) -> Raw:
    return chip("Cuadra", "ok") if cuadra else chip("No cuadra", "malo")


def kpis(items: list[dict]) -> None:
    """items: dicts con etiqueta, valor, nota (opcional), tono (ok/aviso/malo/info) y heroe (opcional)."""
    tarjetas = []
    for it in items:
        tono = TONOS.get(it.get("tono", ""), BORDE)
        clase = "m3k-kpi heroe" if it.get("heroe") else "m3k-kpi"
        nota = f'<div class="nota">{esc(it["nota"])}</div>' if it.get("nota") else ""
        tarjetas.append(f'<div class="{clase}" style="--tono:{tono}"><div class="e">{esc(it["etiqueta"])}</div>'
                        f'<div class="v">{esc(it["valor"])}</div>{nota}</div>')
    st.markdown(f'<div class="m3k-kpis">{"".join(tarjetas)}</div>', unsafe_allow_html=True)


def tabla(columnas: list[str], filas: list, numericas: tuple[int, ...] = (), etiqueta: str = "", pie: list | None = None) -> None:
    """Tabla HTML con cabecera fija, desplazamiento propio y fila de totales opcional.

    Cada fila es una lista de celdas, o un dict {"celdas": [...], "clase": "cab"|"sub"} para filas de agrupación.
    Las celdas se escapan salvo que sean `Raw`. Una celda con prefijo «  » (dos espacios) se muestra con sangría.
    """
    def celda(i: int, valor) -> str:
        clase = "n" if i in numericas else ""
        texto = esc(valor)
        if isinstance(valor, str) and valor.startswith("  ") and not isinstance(valor, Raw):
            clase, texto = "sangria", esc(valor.strip())
        return f'<td class="{clase}">{texto}</td>'

    cab = "".join(f'<th class="{"n" if i in numericas else ""}">{esc(c)}</th>' for i, c in enumerate(columnas))
    cuerpo = []
    for fila in filas:
        celdas, clase = (fila["celdas"], fila.get("clase", "")) if isinstance(fila, dict) else (fila, "")
        cuerpo.append(f'<tr class="{clase}">' + "".join(celda(i, c) for i, c in enumerate(celdas)) + "</tr>")
    tfoot = ""
    if pie:
        tfoot = "<tfoot><tr>" + "".join(f'<td class="{"n" if i in numericas else ""}">{esc(c)}</td>' for i, c in enumerate(pie)) + "</tr></tfoot>"
    aria = f' aria-label="{html.escape(etiqueta)}"' if etiqueta else ""
    st.markdown(f'<div class="m3k-scroll" role="region" tabindex="0"{aria}><table class="m3k-tabla">'
                f'<thead><tr>{cab}</tr></thead><tbody>{"".join(cuerpo)}</tbody>{tfoot}</table></div>', unsafe_allow_html=True)


def barra(avance: float) -> Raw:
    ancho = max(0, min(100, round(avance * 100)))
    return Raw(f'<div class="m3k-barra" role="img" aria-label="{ancho} % cobrado"><i style="width:{ancho}%"></i></div>')


def vacio(titulo: str, ayuda: str) -> None:
    st.markdown(f'<div class="m3k-vacio"><b>{esc(titulo)}</b>{esc(ayuda)}</div>', unsafe_allow_html=True)


def verificaciones(items: list[tuple[str, bool, str]]) -> None:
    """Lista de comprobaciones: (descripción, cumple, detalle). Cada una con texto «Cuadra» / «No cuadra»."""
    filas = "".join(f'<div class="m3k-verif"><span>{esc(d)}<br><small style="color:{TEXTO_SUAVE}">{esc(det)}</small></span>'
                    f'<span>{chip_cuadre(ok)}</span></div>' for d, ok, det in items)
    st.markdown(f'<div style="margin:.3rem 0 1rem">{filas}</div>', unsafe_allow_html=True)


def mensaje_pendiente() -> None:
    """Muestra (una vez) el aviso guardado antes de un rerun, p. ej. «Cobro registrado»."""
    msg = st.session_state.pop("_flash", None)
    if msg:
        tipo, texto = msg
        {"ok": st.success, "error": st.error, "aviso": st.warning}.get(tipo, st.info)(texto)


def avisar(tipo: str, texto: str) -> None:
    st.session_state["_flash"] = (tipo, texto)


def hoy_txt(hoy_: date) -> str:
    dias = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
    return f"{dias[hoy_.weekday()].capitalize()} {hoy_.strftime('%d/%m/%Y')}"
