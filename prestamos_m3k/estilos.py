"""Estilos y piezas de interfaz: aspecto de software contable (fondo negro verdoso con acento lima, tablas densas tipo libro).

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
from datetime import date, datetime

import streamlit as st

import calculos as calc

# Paleta oscura: negro verdoso con lima como acento; los estados usan tonos claros que se leen sobre fondo oscuro.
PAGINA, FONDO, PAPEL, BORDE = "#0B0B0C", "#161617", "#1A1A1C", "#2A2A2D"
TEXTO, TEXTO_SUAVE, ACENTO, CABECERA_TABLA = "#F4F4F2", "#9A9AA0", "#B8F53A", "#1A1A1C"
SOBRE_ACENTO = "#0A1A05"  # texto sobre fondos lima
TONOS = {"ok": "#7EDC6A", "aviso": "#F2B84B", "malo": "#FF7A6B", "info": "#6CC4E8", "neutro": "#9A9AA0"}


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


DIAS_CORTOS = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")


def fecha_dia(valor) -> str:
    """Fecha con el día de la semana: «Sáb 21/11/2026»."""
    d = calc.fecha(valor)
    return f"{DIAS_CORTOS[d.weekday()]} {d.strftime('%d/%m/%Y')}"


def pct(valor: float, decimales: int = 1) -> str:
    return f"{valor * 100:,.{decimales}f} %"


def _banner_uri(nombre: str = "banner_billetes.jpg") -> str:
    """Foto del encabezado ya difuminada; si falta el archivo, el encabezado queda sin imagen."""
    import base64
    from pathlib import Path
    try:
        datos = base64.b64encode((Path(__file__).parent / "assets" / nombre).read_bytes()).decode()
    except OSError:
        return "none"
    return f"url(data:image/jpeg;base64,{datos})"


_BANNER = _banner_uri()
_BANNER_CONT = _banner_uri("banner_contabilidad.jpg")
_BANNER_CTRL = _banner_uri("banner_control.jpg")
_BANNER_APP = _banner_uri("banner_aplicacion.jpg")
def _logo_uri(nombre: str) -> str:
    """Logo (PNG pequeño) incrustado como imagen de fondo CSS; si falta el archivo no se muestra nada."""
    import base64
    from pathlib import Path
    try:
        datos = base64.b64encode((Path(__file__).parent / "assets" / "logos" / f"{nombre}.png").read_bytes()).decode()
    except OSError:
        return "none"
    return f"url(data:image/png;base64,{datos})"


_LOGO_YAPE, _LOGO_PLIN, _LOGO_WA = _logo_uri("yape"), _logo_uri("plin"), _logo_uri("whatsapp")
SECCIONES_CONTABILIDAD = {"Resultados", "Cuentas por cobrar"}
SECCIONES_CONTROL = {"Caja", "Recibos"}
SECCIONES_APLICACION = {"Configuración"}


CSS = f"""
<style>
:root {{ --fondo:{FONDO}; --papel:{PAPEL}; --borde:{BORDE}; --texto:{TEXTO}; --suave:{TEXTO_SUAVE}; --acento:{ACENTO};
  --ok:{TONOS['ok']}; --aviso:{TONOS['aviso']}; --malo:{TONOS['malo']}; --info:{TONOS['info']}; }}
.block-container {{ padding-top: 3.6rem; padding-left: 2.2rem; padding-right: 2.2rem; max-width: 1760px; }}
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
.m3k-kpi.heroe {{ box-shadow:0 0 28px rgba(184,245,58,.10); background:var(--papel); }}

/* Pastillas de estado (siempre con texto) */
.m3k-chip {{ display:inline-block; padding:.08rem .55rem; border-radius:4px; font-size:.74rem; font-weight:600; white-space:nowrap;
  color:var(--c); background:color-mix(in srgb, var(--c) 16%, #161617); border:1px solid color-mix(in srgb, var(--c) 40%, #161617); }}

/* Tablas tipo libro */
.m3k-scroll {{ overflow-x:auto; border:1px solid var(--borde); border-radius:6px; margin:.3rem 0 1rem; max-height:70vh; }}
.m3k-tabla {{ width:100%; border-collapse:collapse; font-size:.84rem; }}
.m3k-tabla th {{ text-align:left; background:{CABECERA_TABLA}; color:var(--suave); font-weight:600; font-size:.72rem;
  letter-spacing:.04em; text-transform:uppercase; padding:.45rem .65rem; white-space:nowrap; position:sticky; top:0; z-index:1;
  border-bottom:1px solid var(--borde); }}
.m3k-tabla td {{ padding:.38rem .65rem; border-top:1px solid #2A2A2D; vertical-align:middle; }}
.m3k-tabla tbody tr:nth-child(even) td {{ background:#121213; }}
.m3k-tabla td.n, .m3k-tabla th.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
.m3k-tabla tr.cab td {{ background:var(--papel) !important; font-weight:600; border-top:1px solid var(--borde); }}
.m3k-tabla tr.sub td {{ font-weight:600; background:var(--papel) !important; }}
.m3k-tabla td.sangria {{ padding-left:1.6rem; color:var(--texto); }}
.m3k-tabla td.nw, .m3k-tabla th.nw {{ white-space:nowrap; }}
.m3k-tabla tr.cab td {{ border-top:2px solid var(--borde); }}
.m3k-tabla tfoot td {{ font-weight:700; background:{CABECERA_TABLA}; border-top:2px solid var(--borde); padding:.45rem .65rem;
  font-variant-numeric:tabular-nums; }}
.m3k-tabla tfoot td.n {{ text-align:right; }}
.m3k-tabla tbody tr:hover td {{ background:#242426; }}
.m3k-barra {{ height:6px; background:#2A2A2D; border-radius:99px; min-width:70px; overflow:hidden; }}
.m3k-barra i {{ display:block; height:100%; background:var(--ok); border-radius:99px; }}

/* Fila de cobranza y estados vacíos */
.m3k-fila {{ background:var(--fondo); border:1px solid var(--borde); border-left:4px solid var(--tono, var(--borde));
  border-radius:6px; padding:.6rem .85rem; display:flex; justify-content:space-between; gap:1rem; align-items:center; }}
.m3k-fila b {{ display:block; }} .m3k-fila small {{ color:var(--suave); }}
.m3k-vacio {{ border:1px dashed var(--borde); border-radius:8px; padding:1.3rem; text-align:center; color:var(--suave); background:var(--papel); }}
.m3k-vacio b {{ color:var(--texto); display:block; margin-bottom:.25rem; }}
.m3k-verif {{ display:flex; justify-content:space-between; gap:1rem; padding:.45rem .1rem; border-bottom:1px solid #2A2A2D; font-size:.9rem; }}

/* Recibo imprimible */
.m3k-recibo {{ background:#F4F4F2; color:#0A1A05; border:1px solid #B8F53A; border-radius:8px; padding:1.3rem 1.5rem; max-width:520px;
  margin:.5rem 0 1rem; font-variant-numeric:tabular-nums; }}
.m3k-recibo h3 {{ margin:0 0 .2rem; color:#0A1A05; }} .m3k-recibo hr {{ border:0; border-top:1px dashed #9A9AA0; margin:.8rem 0; }}
.m3k-recibo .f {{ display:flex; justify-content:space-between; gap:1rem; padding:.18rem 0; }}
.m3k-recibo .t {{ font-size:1.2rem; font-weight:700; }} .m3k-recibo .anul {{ color:#B3261E; font-weight:700; }}

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
.m3k-login::after {{ content:''; position:absolute; left:50%; top:-10px; width:190px; height:190px; border-radius:50%; pointer-events:none; z-index:3;
  background:conic-gradient(from 0deg, transparent 0 55%, rgba(255,214,90,.0) 58%, rgba(255,214,90,.95) 100%);
  -webkit-mask:radial-gradient(circle closest-side, transparent 91%, #000 92%, #000 98%, transparent 100%);
  mask:radial-gradient(circle closest-side, transparent 91%, #000 92%, #000 98%, transparent 100%);
  animation:m3k-orbita 5s linear 1.2s infinite both; }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; transition:none !important; scroll-behavior:auto !important; }} }}

/* Gráficos del inicio y animaciones (se apagan con «reducir movimiento», más abajo) */
@keyframes m3k-subir {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:none; }} }}
@keyframes m3k-alto {{ from {{ transform:scaleY(0); }} to {{ transform:scaleY(1); }} }}
@keyframes m3k-ancho {{ from {{ transform:scaleX(0); }} to {{ transform:scaleX(1); }} }}
@keyframes m3k-aro {{ from {{ stroke-dasharray:0 var(--c); }} }}
@keyframes m3k-revela {{ from {{ clip-path:inset(0 100% 0 0); }} to {{ clip-path:inset(0 0 0 0); }} }}
.m3k-kpi {{ animation:m3k-subir .5s cubic-bezier(.2,.7,.2,1) both; transition:transform .2s ease, box-shadow .2s ease; }}
.m3k-kpi:nth-child(2) {{ animation-delay:.07s; }} .m3k-kpi:nth-child(3) {{ animation-delay:.14s; }} .m3k-kpi:nth-child(4) {{ animation-delay:.21s; }}
.m3k-kpi:hover {{ transform:translateY(-2px); box-shadow:0 6px 16px rgba(0,0,0,.45); }}
.m3k-fila {{ animation:m3k-subir .45s ease both; transition:box-shadow .2s ease; }} .m3k-fila:hover {{ box-shadow:0 3px 10px rgba(0,0,0,.4); }}
.m3k-panel {{ background:var(--fondo); border:1px solid var(--borde); border-radius:8px; padding:.85rem 1rem; margin:.2rem 0 1rem;
  animation:m3k-subir .55s cubic-bezier(.2,.7,.2,1) both; }}
.m3k-panel .t {{ font-size:.78rem; letter-spacing:.04em; text-transform:uppercase; color:var(--suave); font-weight:600; margin-bottom:.7rem; }}
.m3k-panel .pie {{ color:var(--suave); font-size:.78rem; margin-top:.55rem; }}
.m3k-avance .cab {{ display:flex; justify-content:space-between; align-items:baseline; gap:1rem; margin-bottom:.45rem; flex-wrap:wrap; }}
.m3k-avance strong {{ font-size:1.4rem; color:var(--ok); }}
.m3k-avance .pista {{ height:12px; background:#2A2A2D; border-radius:99px; overflow:hidden; }}
.m3k-avance .pista i {{ display:block; height:100%; background:linear-gradient(90deg,#4FA84A,var(--ok)); border-radius:99px; transform-origin:left;
  animation:m3k-ancho 1s cubic-bezier(.2,.7,.2,1) .15s both; }}
.m3k-dias {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(125px,1fr)); gap:.6rem; }}
.m3k-dia {{ border:1px solid var(--borde); border-radius:8px; padding:.6rem .75rem; background:var(--fondo); animation:m3k-subir .5s ease both;
  transition:transform .2s ease, box-shadow .2s ease; }}
.m3k-dia:hover {{ transform:translateY(-2px); box-shadow:0 5px 14px rgba(0,0,0,.4); }}
.m3k-dia.hoy {{ border-color:var(--acento); background:#1F1F21; }} .m3k-dia.vacio {{ opacity:.6; }}
.m3k-dia .d {{ font-size:.74rem; text-transform:uppercase; letter-spacing:.03em; color:var(--suave); }}
.m3k-dia .m {{ font-size:1.12rem; font-weight:700; margin:.1rem 0; }} .m3k-dia .n {{ font-size:.76rem; color:var(--suave); }}
.m3k-dia .qs {{ margin-top:.35rem; border-top:1px dashed var(--borde); padding-top:.3rem; }}
.m3k-dia .q {{ display:flex; justify-content:space-between; gap:.4rem; font-size:.76rem; color:#D4D4D8; line-height:1.5; }}
.m3k-dia .q span {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }} .m3k-dia .q b {{ color:var(--texto); font-weight:600; }}
.m3k-dia .nivel {{ height:4px; background:#2A2A2D; border-radius:99px; margin-top:.5rem; overflow:hidden; }}
.m3k-dia .nivel i {{ display:block; height:100%; background:var(--info); border-radius:99px; transform-origin:left; animation:m3k-ancho .8s ease .2s both; }}
.m3k-sem {{ display:grid; grid-template-columns:repeat(6,1fr); gap:.5rem; align-items:start; }}
.m3k-sem .c {{ display:flex; flex-direction:column; align-items:center; gap:.25rem; min-width:0; }}
.m3k-sem .barras {{ height:120px; width:100%; display:flex; align-items:flex-end; justify-content:center; gap:3px; border-bottom:1px solid var(--borde); }}
.m3k-sem .barras i {{ display:block; width:36%; max-width:34px; border-radius:3px 3px 0 0; transform-origin:bottom; animation:m3k-alto .75s cubic-bezier(.2,.7,.2,1) both;
  transition:filter .2s ease; }}
.m3k-sem .c:hover .barras i {{ filter:brightness(.92); }}
.m3k-sem i.esp, .leyenda i.esp {{ background:#4A4A4F; }} .m3k-sem i.cob, .leyenda i.cob {{ background:var(--ok); }}
.m3k-sem .rot {{ font-size:.72rem; color:var(--suave); white-space:nowrap; }} .m3k-sem .act .rot {{ color:var(--texto); font-weight:700; }}
.m3k-sem .val {{ font-size:.7rem; color:var(--suave); white-space:nowrap; }}
.leyenda {{ display:flex; gap:1rem; margin-top:.6rem; font-size:.76rem; color:var(--suave); }}
.leyenda i {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:.35rem; vertical-align:-1px; }}
.m3k-dona {{ display:flex; align-items:center; gap:1.1rem; flex-wrap:wrap; }}
.m3k-dona svg {{ flex:none; }} .m3k-dona .dc {{ font-size:13px; font-weight:700; fill:var(--texto); }} .m3k-dona .ds {{ font-size:8px; fill:var(--suave); }}
.m3k-dona .seg {{ animation:m3k-aro 1s cubic-bezier(.3,.7,.2,1) both; }}
.m3k-dona ul {{ list-style:none; margin:0; padding:0; flex:1; min-width:170px; max-width:380px; }}
.m3k-dona li {{ display:grid; grid-template-columns:12px 1fr auto 38px; gap:.5rem; align-items:center; padding:.3rem 0; border-bottom:1px solid #2A2A2D; font-size:.85rem; }}
.m3k-dona li:last-child {{ border-bottom:0; }} .m3k-dona li i {{ width:10px; height:10px; border-radius:50%; }}
.m3k-dona li em {{ font-style:normal; color:var(--suave); text-align:right; font-size:.78rem; }}
.m3k-panel svg.lin {{ width:100%; height:150px; display:block; }} .m3k-panel .revela {{ animation:m3k-revela 1.3s cubic-bezier(.4,.1,.2,1) both; }}
.extremos {{ display:flex; justify-content:space-between; align-items:flex-start; gap:.5rem; font-size:.76rem; color:var(--suave); margin-top:.35rem; flex-wrap:wrap; }}
.extremos b {{ display:block; color:var(--texto); font-size:.9rem; }} .extremos .der {{ text-align:right; }} .extremos .mm {{ align-self:center; }}

.m3k-sem.una .barras {{ height:140px; }}
.m3k-sem.una .col {{ width:70%; max-width:46px; display:flex; flex-direction:column; align-items:center; }}
.m3k-sem.una .col i {{ width:100%; max-width:none; flex:1; border-radius:3px 3px 0 0; }}
.m3k-sem.una .col .val {{ font-weight:600; color:var(--texto); font-size:.74rem; white-space:nowrap; line-height:1.5; animation:m3k-subir .6s ease .3s both; }}
.m3k-reparto .barra {{ display:flex; height:22px; border-radius:99px; overflow:hidden; background:#2A2A2D; animation:m3k-revela 1s cubic-bezier(.4,.1,.2,1) both; }}
.m3k-reparto .barra i {{ display:block; height:100%; }}
.m3k-reparto ul {{ list-style:none; margin:.7rem 0 0; padding:0; display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:.2rem 1.5rem; }}
.m3k-reparto li {{ display:grid; grid-template-columns:12px 1fr auto 38px; gap:.5rem; align-items:center; padding:.3rem 0; font-size:.88rem; border-bottom:1px solid #2A2A2D; }}
.m3k-reparto li i {{ width:10px; height:10px; border-radius:50%; }} .m3k-reparto li em {{ font-style:normal; color:var(--suave); text-align:right; font-size:.78rem; }}

.m3k-cascada .fila {{ display:grid; grid-template-columns:minmax(120px,190px) 1fr auto; gap:.8rem; align-items:center; padding:.38rem 0; border-bottom:1px solid #2A2A2D; font-size:.9rem; }}
.m3k-cascada .fila:last-child {{ border-bottom:0; }} .m3k-cascada .fila.total {{ border-top:2px solid var(--borde); margin-top:.2rem; font-weight:700; }}
.m3k-cascada .pista {{ height:12px; background:#252527; border-radius:99px; overflow:hidden; }}
.m3k-cascada .pista i {{ display:block; height:100%; border-radius:99px; transform-origin:left; animation:m3k-ancho .9s cubic-bezier(.2,.7,.2,1) both; }}
.m3k-cascada b {{ text-align:right; min-width:92px; }}
@media (max-width: 640px) {{ .m3k-cascada .fila {{ grid-template-columns:1fr auto; }} .m3k-cascada .pista {{ grid-column:1 / -1; grid-row:2; }} }}

[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"]) {{ border-color:var(--borde) !important; background:var(--fondo); border-radius:8px; }}

.m3k-dias.cuotas {{ grid-template-columns:repeat(auto-fill,minmax(118px,1fr)); gap:.5rem; }}
.m3k-dias.cuotas .m3k-dia {{ padding:.5rem .65rem; }} .m3k-dias.cuotas .m {{ font-size:1rem; }}
[class*="st-key-ficha_"] {{ position:relative; background:#161617; border:1px solid #2A2A2D; border-radius:22px; padding:0 0 1rem; overflow:hidden; gap:0 !important; margin-bottom:1rem; }}
[class*="st-key-ficha_"] > div {{ padding-left:0; }}
.f-notch {{ position:absolute; top:-1px; right:-1px; z-index:2; padding:9px 10px 11px 12px; background:#0B0B0C; border-bottom-left-radius:22px; box-shadow:-1px 1px 0 #2A2A2D; }}
.f-notch::before {{ content:''; position:absolute; top:1px; left:-22px; width:22px; height:22px; background:radial-gradient(circle at 0 100%, transparent 21.5px, #0B0B0C 22px); }}
.f-notch .f-pill, .f-notch .f-pill * {{ color:#0A1A05 !important; }}
.f-notch .f-pill {{ display:block; font-size:.78rem; font-weight:700; line-height:1.2; padding:6px 16px; border-radius:99px; background:#B8F53A; }}
.f-notch .f-pill.mal, .f-notch .f-pill.mal * {{ color:#3A1408 !important; }} .f-notch .f-pill.mal {{ background:#F0997B; }}
.f-notch .f-pill.off, .f-notch .f-pill.off * {{ color:#E4E4E8 !important; }} .f-notch .f-pill.off {{ background:#2A2A2D; }}
.f-cab {{ display:flex; align-items:center; gap:.65rem; padding:.9rem 1.1rem .8rem; color:var(--texto); font-weight:600; font-size:.85rem; }}
.f-cab .av {{ width:36px; height:36px; border-radius:50%; background:#B8F53A; color:#0A1A05; font-weight:700; font-size:.8rem; display:flex; align-items:center; justify-content:center; }}
.f-panel {{ margin:.2rem .8rem 0; background:#0F0F10; border:1px solid #2A2A2D; border-radius:16px; padding:.8rem 1rem; display:flex; flex-direction:column; gap:.7rem; }}
.f-est {{ display:flex; justify-content:space-between; align-items:center; color:var(--texto); font-size:.7rem; letter-spacing:.06em; }}
.f-est .ic, .f-panel .ic {{ font-family:'Material Symbols Rounded'; font-style:normal; line-height:1; font-feature-settings:'liga'; -webkit-font-feature-settings:'liga'; }}
.f-est .ic {{ color:#B8F53A; font-size:20px; }}
.f-panel .it {{ display:flex; align-items:center; gap:.7rem; }}
.f-panel .it .ic {{ font-size:19px; width:34px; height:34px; border-radius:10px; background:#222224; color:#B8F53A; display:flex; align-items:center; justify-content:center; flex:none; }}
.f-panel em {{ display:block; font-style:normal; font-size:.66rem; letter-spacing:.05em; text-transform:uppercase; color:var(--suave); }}
.f-panel b {{ display:block; color:#B8F53A; font-weight:600; font-size:.95rem; }}
.f-nom {{ text-align:center; padding:1rem 1rem 1rem; }} .f-nom b {{ display:block; color:var(--texto); font-size:1.1rem; }} .f-nom small {{ color:var(--suave); }}
[class*="st-key-ficha_"] [data-testid="stHorizontalBlock"] {{ padding:0 .8rem; margin-top:.2rem; }}
[class*="st-key-ficha_"] [data-testid="stHorizontalBlock"] button {{ border-radius:999px; }}
html body .stApp [class*="st-key-nc_"] button:not(:disabled) {{ background:#B8F53A !important; border-color:#B8F53A !important; }}
html body .stApp [class*="st-key-nc_"] button:not(:disabled), html body .stApp [class*="st-key-nc_"] button:not(:disabled) * {{ color:#0A1A05 !important; font-weight:600; }}
html body .stApp [class*="st-key-nc_"] button:not(:disabled):hover {{ background:#CBFA66 !important; }}
[class*="st-key-nc_"] button:disabled {{ background:#222224 !important; border-color:#2A2A2D !important; }}
[class*="st-key-nc_"] button:disabled, [class*="st-key-nc_"] button:disabled * {{ color:#6A6A70 !important; }}
[class*="st-key-ficha_"] [data-testid="stExpander"] {{ margin:.6rem .8rem 0; width:calc(100% - 1.6rem) !important; box-sizing:border-box; }}
html body .stApp [class*="st-key-ficha_"] [data-testid="stExpander"], html body .stApp [class*="st-key-ficha_"] [data-testid="stExpander"] details {{ background:#161617 !important; border-color:#2A2A2D !important; border-radius:14px !important; }}
html body .stApp [class*="st-key-ficha_"] [data-testid="stExpander"] summary, html body .stApp [class*="st-key-ficha_"] [data-testid="stExpander"] summary:hover, html body .stApp [class*="st-key-ficha_"] [data-testid="stExpander"] summary:focus, html body .stApp [class*="st-key-ficha_"] [data-testid="stExpander"] details[open] > summary {{ background:#161617 !important; color:#F4F4F2 !important; }}
html body .stApp [class*="st-key-ficha_"] [data-testid="stExpander"] summary *, html body .stApp [class*="st-key-ficha_"] [data-testid="stExpander"] summary:hover * {{ color:#F4F4F2 !important; fill:#F4F4F2 !important; }}
/* etiquetas de los campos con icono (formulario de cliente): icono lima, alineado con el texto */
[data-testid="stWidgetLabel"] [data-testid="stIconMaterial"] {{ color:#B8F53A !important; font-size:1.1rem !important; margin-right:.35rem; vertical-align:-.22rem; }}
[data-testid="stForm"] [data-testid="stWidgetLabel"] p {{ font-weight:600; letter-spacing:.01em; }}
[data-testid="stForm"] input::placeholder {{ color:#6B6B72 !important; }}
/* desplegables (p. ej. «Nuevo cliente»): siempre oscuros, abiertos o cerrados, con el texto legible */
html body .stApp [data-testid="stExpander"], html body .stApp [data-testid="stExpander"] details, html body .stApp [data-testid="stExpander"] details[open] {{ background:#161617 !important; border-color:#2A2A2D !important; }}
html body .stApp [data-testid="stExpander"] summary, html body .stApp [data-testid="stExpander"] summary:hover, html body .stApp [data-testid="stExpander"] summary:focus, html body .stApp [data-testid="stExpander"] summary:focus-visible, html body .stApp [data-testid="stExpander"] summary:active, html body .stApp [data-testid="stExpander"] details[open] > summary, html body .stApp [data-testid="stExpander"] details[open] > summary:hover {{ background:#161617 !important; color:#F4F4F2 !important; }}
html body .stApp [data-testid="stExpander"] summary *, html body .stApp [data-testid="stExpander"] summary:hover *, html body .stApp [data-testid="stExpander"] details[open] > summary * {{ color:#F4F4F2 !important; fill:#F4F4F2 !important; }}

.m3k-sem .val b {{ color:var(--texto); font-weight:600; }} .m3k-sem .val.f {{ color:var(--aviso); font-weight:600; }} .m3k-sem .val.ok {{ color:var(--ok); font-weight:600; }}
.m3k-aldia b {{ display:block; font-size:1.8rem; color:var(--ok); }} .m3k-aldia span {{ color:var(--suave); }} .m3k-aldia strong {{ color:var(--texto); }}

/* Selectores horizontales (st.radio) con aspecto de navegación: píldoras, la opción activa en verde.
   Si Streamlit cambia su estructura interna, estas reglas simplemente dejan de aplicarse y quedan los botones de opción normales. */
[data-testid="stRadio"] [role="radiogroup"] {{ gap:.45rem; flex-wrap:wrap; }}
[data-testid="stRadio"] label[data-baseweb="radio"] {{ background:var(--fondo); border:1px solid var(--borde); border-radius:999px; padding:.28rem .95rem; margin:0;
  cursor:pointer; transition:background .15s ease, border-color .15s ease, box-shadow .15s ease; }}
[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child:not(:has(p)) {{ display:none; }}
[data-testid="stRadio"] label[data-baseweb="radio"]:hover {{ border-color:var(--acento); background:#1F1F21; }}
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {{ background:var(--acento); border-color:var(--acento); box-shadow:0 2px 8px rgba(184,245,58,.25); }}
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p {{ color:#0A1A05 !important; font-weight:600; }}
[data-testid="stRadio"] label[data-baseweb="radio"] p {{ font-size:.9rem; margin:0; }}
/* selector principal de cada pantalla (st.container(key="nav_principal")): más grande, con una línea que lo separa del contenido */
.st-key-nav_principal {{ border-bottom:1px solid var(--borde); padding-bottom:.7rem; margin-bottom:.3rem; }}
.st-key-nav_principal [data-testid="stRadio"] label[data-baseweb="radio"] {{ padding:.5rem 1.25rem; border-radius:10px; }}
.st-key-nav_principal [data-testid="stRadio"] label[data-baseweb="radio"] p {{ font-size:1rem; }}

/* Encabezado con ícono y fondo de color por sección; tarjetas con ícono y tinte */
.m3k-cab {{ justify-content:flex-start; background:linear-gradient(100deg, color-mix(in srgb, var(--sec, var(--acento)) 16%, #161617) 0%, #161617 75%); border:1px solid var(--borde);
  border-bottom:3px solid var(--sec, var(--acento)); border-radius:12px; padding:.9rem 1.1rem; align-items:center; gap:1rem; }}
.m3k-cab .ico {{ width:54px; height:54px; border-radius:14px; background:color-mix(in srgb, var(--sec, var(--acento)) 20%, #161617); font-size:1.7rem;
  display:flex; align-items:center; justify-content:center; flex:none; box-shadow:inset 0 0 0 1px color-mix(in srgb, var(--sec, var(--acento)) 35%, #161617); }}
.m3k-cab .marca {{ color:var(--sec, var(--acento)); }}
.m3k-kpi {{ background:linear-gradient(135deg, color-mix(in srgb, var(--tono, #9A9AA0) 12%, #161617), #161617 70%); position:relative; padding-right:3.4rem; }}
.m3k-kpi.heroe {{ background:linear-gradient(135deg, color-mix(in srgb, var(--tono, #9A9AA0) 22%, #161617), #161617 80%); }}
.m3k-kpi .ic {{ position:absolute; top:.7rem; right:.7rem; width:38px; height:38px; border-radius:50%; font-size:1.2rem;
  background:color-mix(in srgb, var(--tono, #9A9AA0) 22%, #161617); display:flex; align-items:center; justify-content:center; }}
[data-testid="stSidebar"] {{ background:linear-gradient(180deg, #111112 0%, #0B0B0C 100%) !important; }}

.m3k-pagadas {{ background:#1F1F21; border:1px solid #38383C; color:#B8F53A; border-radius:8px; padding:.45rem .8rem; font-size:.85rem; margin:.2rem 0 .6rem; }}

.m3k-paso {{ display:flex; align-items:center; gap:.65rem; margin:.1rem 0 .6rem; font-size:1.15rem; }}
.m3k-paso span {{ width:30px; height:30px; border-radius:50%; background:var(--acento); color:#0A1A05; font-weight:700; font-size:.95rem;
  display:flex; align-items:center; justify-content:center; flex:none; box-shadow:0 0 0 3px rgba(184,245,58,.15); }}
.m3k-simula {{ background:linear-gradient(135deg,#1F1F21,#161617 70%); border:1px dashed #4A4A4F; border-radius:12px; padding:1.6rem 1.4rem; }}
.m3k-simula .gran {{ font-size:2.6rem; line-height:1; margin-bottom:.4rem; }}
.m3k-simula b {{ font-size:1.15rem; }} .m3k-simula p {{ color:var(--suave); margin:.4rem 0 .3rem; }} .m3k-simula ul {{ margin:0; padding-left:1.1rem; line-height:1.9; }}

/* Tema oscuro forzado: Streamlit Cloud usa la configuración de la raíz del repositorio, así que los colores base se fijan aquí
   para que esta app se vea igual en cualquier despliegue. */
:root {{ color-scheme: dark; }}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] {{ background-color:#0B0B0C !important; color:var(--texto) !important; }}
/* Fondo: resplandor lima en las esquinas y textura fina de puntos, como en las referencias */
[data-testid="stAppViewContainer"] {{ background-image:
  radial-gradient(ellipse 60% 45% at 100% 0%, rgba(184,245,58,.08), transparent 70%),
  radial-gradient(ellipse 50% 40% at 0% 100%, rgba(255,255,255,.03), transparent 70%),
  radial-gradient(rgba(184,245,58,.07) 1px, transparent 1px) !important;
  background-size:auto, auto, 22px 22px !important; background-attachment:fixed !important; }}
[data-testid="stHeader"] {{ background:#0B0B0C !important; }}  /* sólida: el contenido ya no se ve por detrás del logo y las flechas al desplazarse */
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {{ background-image:radial-gradient(ellipse 120% 35% at 0% 0%, rgba(255,255,255,.04), transparent 70%) !important; }}
[data-testid="stSidebar"], [data-testid="stSidebarContent"], [data-testid="stSidebarNav"] {{ background:#111112 !important; border-right:1px solid var(--borde); }}
.stApp, .stApp p, .stApp li, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stWidgetLabel"], .stApp [data-testid="stCaptionContainer"] {{ color:var(--texto); }}
.stApp [data-testid="stCaptionContainer"], .stApp small {{ color:var(--suave) !important; }}
[data-testid="stSidebar"] a, [data-testid="stSidebar"] [data-testid="stSidebarNavLink"] span, [data-testid="stSidebarNavSeparator"] span,
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {{ color:#D4D4D8 !important; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {{ background:#B8F53A !important; font-weight:700; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"], [data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] * {{ color:#0A1A05 !important; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{ background:#1F1F21 !important; }}
[data-testid="stSidebar"] hr {{ border-color:var(--borde) !important; }}
[data-testid="stSidebarNav"] header span, [data-testid="stSidebarNav"] [data-testid="stNavSectionHeader"], [data-testid="stSidebarNav"] ul li > div > span {{ color:var(--suave) !important; }}
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea, div[data-baseweb="select"] > div,
div[data-baseweb="input"], div[data-baseweb="base-input"], [data-testid="stNumberInputContainer"] {{ background:#161617 !important; color:var(--texto) !important; border-color:#38383C !important; }}
[data-testid="stNumberInputContainer"] button {{ background:#1F1F21 !important; color:var(--texto) !important; }}
div[data-baseweb="popover"] ul, div[data-baseweb="menu"], div[data-baseweb="popover"] li, div[data-baseweb="calendar"] {{ background:#161617 !important; color:var(--texto) !important; }}
div[data-baseweb="popover"] li:hover {{ background:#252527 !important; }}
::placeholder {{ color:#77777C !important; opacity:1; }}
.stButton button, .stDownloadButton button, .stFormSubmitButton button {{ background:#161617; color:#D4D4D8; border:1px solid #38383C; }}
.stButton button p, .stButton button span, .stDownloadButton button p, .stFormSubmitButton button p {{ color:inherit !important; }}
button[data-testid^="stBaseButton-secondary"], [data-testid="stFormSubmitButton"] button, [data-testid="stDownloadButton"] button {{ background:#161617 !important; color:#D4D4D8 !important; border:1px solid #38383C !important; }}
button[data-testid^="stBaseButton-secondary"] *, [data-testid="stFormSubmitButton"] button *, [data-testid="stDownloadButton"] button * {{ color:#D4D4D8 !important; }}
button[data-testid^="stBaseButton-secondary"]:hover, [data-testid="stFormSubmitButton"] button:hover, [data-testid="stDownloadButton"] button:hover {{ border-color:var(--acento) !important; background:#1F1F21 !important; }}
.stButton button[kind="primary"], button[data-testid="stBaseButton-primary"], .stFormSubmitButton button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"], [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primaryFormSubmit"] {{
  background:#B8F53A !important; border-color:#B8F53A !important; color:#0A1A05 !important; font-weight:700; }}
.stButton button[kind="primary"] *, button[data-testid="stBaseButton-primary"] *, .stFormSubmitButton button[kind="primary"] *,
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] *, [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primaryFormSubmit"] * {{ color:#0A1A05 !important; }}
.stButton button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:hover {{ background:#D9FB8C !important; border-color:#D9FB8C !important; }}
.stButton button:disabled {{ opacity:.45; }}
[data-testid="stExpander"] {{ background:#161617; border:1px solid var(--borde); }}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {{ color:var(--texto) !important; }}
[data-baseweb="tab-list"] button, [data-baseweb="tab-list"] button * {{ color:var(--suave) !important; }}
[data-baseweb="tab-list"] button[aria-selected="true"], [data-baseweb="tab-list"] button[aria-selected="true"] * {{ color:var(--acento) !important; font-weight:700; }}
[data-testid="stRadio"] label, [data-testid="stRadio"] label * {{ color:var(--texto) !important; }}
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked), [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) * {{ color:#0A1A05 !important; }}
[data-testid="stForm"] {{ border:1px solid var(--borde); background:var(--fondo); }}
[data-testid="stAlert"] {{ border:1px solid #38383C; background:#1A1A1C !important; }}
[data-testid="stAlert"], [data-testid="stAlert"] * {{ color:var(--texto) !important; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-color:var(--borde) !important; }}
hr {{ border-color:var(--borde) !important; }}
code {{ background:#252527 !important; color:#D9FB8C !important; }}

.stApp .m3k-recibo, .stApp .m3k-recibo * {{ color:#0A1A05; }} .stApp .m3k-recibo .anul {{ color:#B3261E; }} .stApp .m3k-recibo small {{ color:#3E5A2A !important; }}

/* ---- Correcciones de visibilidad: todo control con fondo oscuro y texto claro ---- */
div[data-baseweb="select"], div[data-baseweb="select"] * {{ background-color:#161617 !important; color:#F4F4F2 !important; border-color:#38383C !important; }}
div[data-baseweb="select"] svg {{ fill:#B8F53A !important; }}
div[data-baseweb="select"] > div:hover {{ border-color:#B8F53A !important; }}
[data-testid="stDateInput"] *, [data-testid="stDateInputField"], [data-baseweb="datepicker"] * {{ background-color:#161617 !important; color:#F4F4F2 !important; border-color:#38383C !important; }}
[data-testid="stDateInput"] svg {{ fill:#B8F53A !important; }}
[data-testid="stDateInput"] input::placeholder {{ color:#9A9AA0 !important; }}
[data-baseweb="popover"], [data-baseweb="popover"] > div, [data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="calendar"], [data-baseweb="calendar"] * {{ background-color:#161617 !important; color:#F4F4F2 !important; }}
[data-baseweb="popover"] {{ border:1px solid #38383C; border-radius:10px; }}
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] {{ background-color:#252527 !important; color:#B8F53A !important; }}
[data-baseweb="calendar"] [aria-selected="true"], [data-baseweb="calendar"] [aria-selected="true"] * {{ background-color:#B8F53A !important; color:#0A1A05 !important; }}
[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploaderDropzone"] * {{ background-color:#161617 !important; color:#D4D4D8 !important; }}
[data-testid="stFileUploaderDropzone"] {{ border:1.5px dashed #4A4A4F !important; border-radius:12px; transition:border-color .2s ease, box-shadow .2s ease; }}
[data-testid="stFileUploaderDropzone"]:hover {{ border-color:#B8F53A !important; box-shadow:0 0 18px rgba(184,245,58,.12); }}
[data-testid="stFileUploaderDropzone"] button {{ background-color:#B8F53A !important; color:#0A1A05 !important; }}
[data-testid="stFileUploaderDropzone"] button * {{ background-color:transparent !important; color:#0A1A05 !important; }}
[data-testid="stAlert"], [data-testid="stAlertContainer"], [data-baseweb="notification"], [role="alert"] {{ background-color:#1A1A1C !important; color:#F4F4F2 !important; border:1px solid #4A4A4F !important; border-left:4px solid #B8F53A !important; border-radius:10px; }}
[data-testid="stAlert"] *, [data-baseweb="notification"] * {{ background-color:transparent !important; color:#F4F4F2 !important; }}
[data-testid="stAlert"] svg {{ fill:#B8F53A !important; }}
[data-testid="stException"], [data-testid="stNotification"] {{ background:#1A1A1C !important; }}

/* Selectores (selectbox / multiselect): se cubren todos los envoltorios posibles con más especificidad */
html body .stApp [data-testid="stSelectbox"], html body .stApp [data-testid="stSelectbox"] *, html body .stApp [data-testid="stMultiSelect"] *,
html body .stApp div:has(> [data-baseweb="select"]), html body .stApp [data-baseweb="select"], html body .stApp [data-baseweb="select"] *,
html body .stApp [data-baseweb="select"] > div, html body .stApp [data-baseweb="select"] > div > div {{ background:#161617 !important; background-color:#161617 !important; color:#F4F4F2 !important; -webkit-text-fill-color:#F4F4F2 !important; }}
html body .stApp [data-testid="stSelectbox"] [data-baseweb="select"] > div {{ border:1px solid #38383C !important; border-radius:8px !important; box-shadow:none !important; }}
html body .stApp [data-testid="stSelectbox"] [data-baseweb="select"] > div:hover, html body .stApp [data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within {{ border-color:#B8F53A !important; }}
html body .stApp [data-testid="stSelectbox"] label, html body .stApp [data-testid="stSelectbox"] label * {{ background:transparent !important; }}
html body .stApp [data-testid="stSelectbox"] svg, html body .stApp [data-baseweb="select"] svg {{ fill:#B8F53A !important; color:#B8F53A !important; }}
html body [data-baseweb="popover"] [role="listbox"], html body [data-baseweb="popover"] [role="option"], html body [data-baseweb="popover"] [role="option"] *, html body [data-baseweb="menu"], html body [data-baseweb="menu"] * {{ background:#161617 !important; color:#F4F4F2 !important; -webkit-text-fill-color:#F4F4F2 !important; }}
html body [data-baseweb="popover"] [role="option"]:hover, html body [data-baseweb="popover"] [role="option"]:hover *, html body [data-baseweb="popover"] [aria-selected="true"], html body [data-baseweb="popover"] [aria-selected="true"] * {{ background:#252527 !important; color:#B8F53A !important; -webkit-text-fill-color:#B8F53A !important; }}

/* Tarjeta destacada: lima sólido con letras oscuras, como en las referencias */
.m3k-kpi.heroe {{ background:linear-gradient(135deg,#C9FB4E,#B8F53A 60%,#9BE02A) !important; border:1px solid #D9FB8C !important; border-left:4px solid #0A1A05 !important; }}
.m3k-kpi.heroe .e, .m3k-kpi.heroe .nota {{ color:#2B4A0C !important; font-weight:600; }}
.m3k-kpi.heroe .v {{ color:#0A1A05 !important; font-size:1.8rem; }}
.m3k-kpi.heroe .ic {{ background:#0A1A05 !important; box-shadow:none !important; }}
.m3k-kpi.heroe:hover {{ box-shadow:0 0 30px rgba(184,245,58,.35); }}
.m3k-vacio {{ background:radial-gradient(ellipse at 50% 0%, rgba(184,245,58,.10), transparent 70%), var(--fondo); border:1.5px dashed #4A4A4F; padding:1.6rem 1.3rem; }}
.m3k-vacio .gran {{ display:inline-flex; width:68px; height:68px; border-radius:20px; background:#DDF7A8; align-items:center; justify-content:center; font-size:2.1rem;
  margin-bottom:.7rem; box-shadow:0 0 0 6px rgba(184,245,58,.12); animation:m3k-subir .5s ease both; }}
.m3k-vacio b {{ font-size:1.1rem; }}
.m3k-login h1 span {{ color:#B8F53A; }}

/* Autocompletado del navegador (la clave guardada pinta el campo de azul claro) */
input:-webkit-autofill, input:-webkit-autofill:hover, input:-webkit-autofill:focus, textarea:-webkit-autofill {{
  -webkit-box-shadow:0 0 0 1000px #161617 inset !important; box-shadow:0 0 0 1000px #161617 inset !important;
  -webkit-text-fill-color:#F4F4F2 !important; caret-color:#B8F53A; transition:background-color 9999s ease-in-out 0s; }}
[data-testid="stTextInput"] button, [data-testid="stTextInput"] button * {{ background-color:#1F1F21 !important; color:#B8F53A !important; fill:#B8F53A !important; }}

/* Campos de texto y clave: todo el contenedor oscuro, incluido el ojo para ver la clave */
html body .stApp [data-testid="stTextInput"] [data-baseweb="input"], html body .stApp [data-testid="stTextInput"] [data-baseweb="base-input"],
html body .stApp [data-testid="stTextInput"] [data-baseweb="input"] > div, html body .stApp [data-testid="stTextInput"] input,
html body .stApp [data-testid="stTextArea"] [data-baseweb="textarea"], html body .stApp [data-testid="stTextArea"] textarea {{ background:#161617 !important; background-color:#161617 !important; color:#F4F4F2 !important; }}
html body .stApp [data-testid="stTextInput"] [data-baseweb="input"], html body .stApp [data-testid="stTextArea"] [data-baseweb="textarea"] {{ border:1px solid #38383C !important; border-radius:8px !important; overflow:hidden; }}
html body .stApp [data-testid="stTextInput"] [data-baseweb="input"]:focus-within, html body .stApp [data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within {{ border-color:#B8F53A !important; box-shadow:0 0 0 2px rgba(184,245,58,.18) !important; }}
html body .stApp [data-testid="stTextInput"] [data-baseweb="input"] > div:last-child:not(:first-child), html body .stApp [data-testid="stTextInput"] button {{ background:#161617 !important; border:0 !important; box-shadow:none !important; }}
html body .stApp [data-testid="stTextInput"] button svg, html body .stApp [data-testid="stTextInput"] button svg * {{ fill:#B8F53A !important; stroke:none !important; color:#B8F53A !important; }}
html body .stApp [data-testid="stTextInput"] button:hover svg * {{ fill:#D9FB8C !important; }}
html body .stApp [data-testid="stTextInput"] button:hover {{ transform:none; box-shadow:none; }}

/* Campo de clave: cualquier elemento dentro del campo es oscuro, sea cual sea la estructura interna de Streamlit */
html body .stApp [data-testid="stTextInput"] *:not(svg):not(path):not(circle):not(g), html body .stApp [data-testid="stTextInputRootElement"],
html body .stApp [data-testid="stTextInputRootElement"] * {{ background:#161617 !important; background-color:#161617 !important; border-color:#38383C !important; color:#F4F4F2 !important; }}
html body .stApp [data-testid="stTextInput"] > div > div, html body .stApp [data-testid="stTextInputRootElement"] {{ border:1px solid #38383C !important; border-radius:8px !important; overflow:hidden; }}
html body .stApp [data-testid="stTextInput"] input {{ border:0 !important; }}
html body .stApp [data-testid="stTextInputRootElement"]:focus-within {{ border-color:#B8F53A !important; box-shadow:0 0 0 2px rgba(184,245,58,.18) !important; }}
html body .stApp [data-testid="stTextInput"] button {{ border:0 !important; border-radius:0 !important; box-shadow:none !important; outline:none; }}
html body .stApp [data-testid="stTextInput"] svg, html body .stApp [data-testid="stTextInput"] svg * {{ fill:#B8F53A !important; stroke:none !important; background:transparent !important; }}

/* Iconos: fichas claras para que se vean sobre fondo oscuro */
.m3k-cab .ico {{ background:#B8F53A !important; box-shadow:0 0 0 4px rgba(184,245,58,.14), 0 0 22px rgba(184,245,58,.25) !important; }}
.m3k-kpi .ic {{ background:#DDF7A8 !important; box-shadow:0 0 0 3px rgba(184,245,58,.14); }}
.m3k-modo .ico {{ background:#DDF7A8 !important; }} .m3k-modo.sel .ico {{ background:#B8F53A !important; }}
.m3k-simula .gran {{ display:inline-flex; width:64px; height:64px; border-radius:18px; background:#DDF7A8; align-items:center; justify-content:center; font-size:2rem; }}

/* Barras y pistas: más contraste sobre las tarjetas */
.m3k-barra, .m3k-avance .pista, .m3k-dia .nivel, .m3k-cascada .pista, .m3k-reparto .barra {{ background:#4A4A4F !important; }}
.m3k-sem i.esp, .leyenda i.esp {{ background:#5E9B4A !important; }}
.m3k-sem .barras {{ border-bottom:1px solid #5A5A60 !important; }}
.m3k-dona circle[stroke="#2A2A2D"] {{ stroke:#4A4A4F; }}
.m3k-panel svg line {{ stroke:#4A4A4F !important; }}

/* Botones y pestañas: el texto se parte en dos líneas en vez de cortarse con «…» */
.stButton button p, .stDownloadButton button p, .stFormSubmitButton button p {{ white-space:normal !important; overflow:visible !important; text-overflow:clip !important; line-height:1.25; }}
.stButton button, .stDownloadButton button {{ height:auto; min-height:44px; padding-top:.4rem; padding-bottom:.4rem; }}
.stButton button > div, .stButton button [data-testid="stMarkdownContainer"] {{ overflow:visible !important; }}

/* Transiciones y movimiento */
@keyframes m3k-entra {{ from {{ opacity:0; transform:translateY(12px); }} to {{ opacity:1; transform:none; }} }}
@keyframes m3k-brillo {{ 0%,100% {{ box-shadow:0 0 0 0 rgba(184,245,58,.0); }} 50% {{ box-shadow:0 0 22px 2px rgba(184,245,58,.22); }} }}
.block-container {{ animation:m3k-entra .5s cubic-bezier(.2,.7,.2,1) both; }}
.stButton button, .stDownloadButton button, .stFormSubmitButton button {{ transition:transform .15s ease, box-shadow .2s ease, background-color .2s ease, border-color .2s ease; }}
.stButton button:hover, .stDownloadButton button:hover, .stFormSubmitButton button:hover {{ transform:translateY(-2px); box-shadow:0 6px 18px rgba(0,0,0,.45); }}
.stButton button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {{ box-shadow:0 0 22px rgba(184,245,58,.45); }}
.stButton button:active {{ transform:scale(.98); }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {{ transition:background-color .2s ease, padding-left .2s ease; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{ padding-left:1.1rem; }}
.m3k-cab {{ animation:m3k-entra .55s cubic-bezier(.2,.7,.2,1) both; }}
.m3k-kpi.heroe {{ animation:m3k-subir .5s cubic-bezier(.2,.7,.2,1) both, m3k-brillo 3.5s ease-in-out 1s infinite; }}
.m3k-modo {{ transition:transform .2s ease, border-color .2s ease, box-shadow .2s ease; }}
.m3k-modo:hover {{ transform:translateY(-3px); border-color:#B8F53A; box-shadow:0 8px 22px rgba(0,0,0,.45); }}
.m3k-tabla tbody tr {{ transition:background-color .15s ease; }}
[data-testid="stExpander"] {{ transition:border-color .2s ease; }} [data-testid="stExpander"]:hover {{ border-color:#4A4A4F; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ transition:border-color .2s ease, box-shadow .2s ease; }}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{ box-shadow:0 0 24px rgba(184,245,58,.06); }}

/* Acceso: tarjeta central con marca y tres razones para entrar */
.m3k-login {{ max-width:460px; margin:1.2rem auto .8rem; text-align:center; position:relative; }}
.m3k-login::before {{ content:''; position:absolute; left:50%; top:-60px; width:520px; height:360px; transform:translateX(-50%); z-index:-1;
  background:radial-gradient(ellipse at center, rgba(214,165,40,.34), rgba(184,245,58,.10) 48%, transparent 68%); pointer-events:none; }}
.m3k-login .logo-img {{ width:170px; height:170px; display:block; margin:0 auto .6rem; position:relative; }}
.m3k-login .logo {{ width:76px; height:76px; border-radius:22px; background:#B8F53A; color:#0A1A05; font-size:2.3rem;
  display:flex; align-items:center; justify-content:center; margin:0 auto 1rem; box-shadow:0 0 0 8px rgba(184,245,58,.12); }}
.m3k-login .marca {{ font-size:.74rem; letter-spacing:.16em; color:#B8F53A; font-weight:700; }}
.m3k-login h1 {{ font-size:2rem; margin:.25rem 0 .3rem; color:#F4F4F2; }}
.m3k-login p {{ color:var(--suave); margin:0 0 1.1rem; }}
.m3k-login .pasos {{ display:grid; grid-template-columns:repeat(3,1fr); gap:.6rem; margin:0 0 1rem; }}
.m3k-login .pasos div {{ background:#161617; border:1px solid var(--borde); border-radius:12px; padding:.7rem .4rem; font-size:.78rem; color:#D4D4D8; }}
.m3k-login .pasos span {{ display:block; font-size:1.4rem; margin-bottom:.2rem; }}
@keyframes m3k-logo-in {{ from {{ opacity:0; transform:translateY(10px) scale(.92); }} to {{ opacity:1; transform:none; }} }}
@keyframes m3k-glow-in {{ from {{ opacity:0; transform:translateX(-50%) scale(.6); }} to {{ opacity:1; transform:translateX(-50%) scale(1); }} }}
@keyframes m3k-respira {{ 0%,100% {{ opacity:.35; transform:translateX(-50%) scale(.82); }} 50% {{ opacity:1; transform:translateX(-50%) scale(1.2); }} }}
@keyframes m3k-logo-luz {{ 0%,100% {{ filter:drop-shadow(0 0 4px rgba(214,165,40,.15)) brightness(.94); }} 50% {{ filter:drop-shadow(0 0 30px rgba(255,205,70,.85)) brightness(1.12); }} }}
@keyframes m3k-orbita {{ from {{ transform:translateX(-50%) rotate(0deg); }} to {{ transform:translateX(-50%) rotate(360deg); }} }}
.m3k-login::before {{ animation:m3k-glow-in 1.1s cubic-bezier(.2,.8,.2,1) both, m3k-respira 3.2s 1.1s ease-in-out infinite; }}
.m3k-login .logo-img {{ animation:m3k-logo-in .7s cubic-bezier(.2,.8,.2,1) both, m3k-logo-luz 3.2s .8s ease-in-out infinite; }}
.m3k-login .marca {{ animation:m3k-entra .6s .3s cubic-bezier(.2,.8,.2,1) both; }}
.m3k-login h1 {{ animation:m3k-entra .6s .4s cubic-bezier(.2,.8,.2,1) both; }}
.m3k-login p {{ animation:m3k-entra .6s .5s cubic-bezier(.2,.8,.2,1) both; }}
.m3k-login .pasos div:nth-child(1) {{ animation:m3k-entra .6s .6s cubic-bezier(.2,.8,.2,1) both; }}
.m3k-login .pasos div:nth-child(2) {{ animation:m3k-entra .6s .72s cubic-bezier(.2,.8,.2,1) both; }}
.m3k-login .pasos div:nth-child(3) {{ animation:m3k-entra .6s .84s cubic-bezier(.2,.8,.2,1) both; }}
@media (prefers-reduced-motion: reduce) {{ .m3k-login *, .m3k-login::before, .m3k-login::after {{ animation:none !important; }} }}
.st-key-acceso_form {{ max-width:460px; margin:0 auto; }}

/* Modalidades: tarjetas con icono y ejemplo */
.m3k-modos {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:.7rem; margin:.2rem 0 1rem; }}
.m3k-modo {{ background:var(--fondo); border:1px solid var(--borde); border-radius:12px; padding:.85rem 1rem; }}
.m3k-modo.sel {{ border:1.5px solid #B8F53A; background:#1F1F21; }}
.m3k-modo .ico {{ width:40px; height:40px; border-radius:11px; background:#252527; display:flex; align-items:center; justify-content:center; font-size:1.3rem; margin-bottom:.5rem; }}
.m3k-modo.sel .ico {{ background:#B8F53A; }}
.m3k-modo b {{ font-size:1.02rem; }} .m3k-modo .sub {{ color:var(--suave); font-size:.8rem; margin:.1rem 0 .5rem; }}
.m3k-modo ul {{ list-style:none; margin:0; padding:0; font-size:.84rem; color:#D4D4D8; line-height:1.7; }}
.m3k-modo .ej {{ margin-top:.5rem; padding-top:.45rem; border-top:1px dashed var(--borde); font-size:.8rem; color:var(--suave); }}
.m3k-modo .ej strong {{ color:#B8F53A; }}

/* Barra lateral: panel con marca arriba, secciones en mayúsculas, iconos en fichas y la página activa como tarjeta con acento lima */
html body .stApp [data-testid="stSidebar"], html body .stApp [data-testid="stSidebarContent"] {{ background:linear-gradient(180deg,#151516 0%,#0E0E0F 100%) !important;
  border-right:1px solid #2A2A2D !important; }}
html body .stApp [data-testid="stSidebarHeader"] {{ display:flex; align-items:center; gap:.7rem; padding:1.1rem 1rem .9rem !important; border-bottom:1px solid #2A2A2D; margin-bottom:.4rem; }}
html body .stApp [data-testid="stSidebarHeader"] img {{ height:42px !important; width:auto !important; max-width:none; }}
html body .stApp [data-testid="stSidebarHeader"]::after {{ content:"Préstamos"; order:1; flex:1; font-weight:700; font-size:1.02rem; color:#F4F4F2; letter-spacing:.01em; }}
html body .stApp [data-testid="stSidebarCollapseButton"] {{ order:2; }}
html body .stApp [data-testid="stSidebarNav"] [data-testid="stNavSectionHeader"], html body .stApp [data-testid="stSidebarNav"] [data-testid="stNavSectionHeader"] span, html body .stApp [data-testid="stSidebarNav"] ul li > div > span {{
  text-transform:uppercase; letter-spacing:.14em; font-size:.68rem !important; font-weight:700; color:#77777C !important; padding:.9rem .9rem .25rem; }}
html body .stApp [data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {{ border-radius:12px !important; margin:3px 10px !important; padding:.42rem .6rem !important;
  gap:.7rem !important; border:1px solid transparent; color:#D4D4D8 !important; background:transparent !important;
  transition:background-color .2s ease, border-color .2s ease, transform .2s ease !important; }}
html body .stApp [data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{ background:#1E1E20 !important; border-color:#2A2A2D; padding-left:.6rem !important; transform:translateX(2px); }}
html body .stApp [data-testid="stSidebar"] [data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {{ width:32px; height:32px; border-radius:10px;
  display:inline-flex !important; align-items:center; justify-content:center; font-size:1.1rem !important; flex:none;
  background:linear-gradient(180deg,#2A2A2D,#1E1E20); border:1px solid #333336; color:#A8A8AD !important; }}
html body .stApp [data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {{ position:relative; }}
html body .stApp [data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {{
  background:linear-gradient(100deg, rgba(184,245,58,.30) 0%, rgba(86,92,70,.95) 30%, #38383A 100%) !important; border-color:rgba(184,245,58,.55);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.14), 0 6px 16px rgba(0,0,0,.45); font-weight:700; }}
html body .stApp [data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"]::before {{ content:''; position:absolute; left:-10px; top:50%; transform:translateY(-50%);
  width:5px; height:62%; background:#B8F53A; border-radius:0 5px 5px 0; box-shadow:0 0 12px rgba(184,245,58,.7); }}
html body .stApp [data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"], html body .stApp [data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] * {{ color:#FFFFFF !important; text-shadow:0 1px 2px rgba(0,0,0,.5); }}
html body .stApp [data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"], html body .stApp [data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"] * {{ background:linear-gradient(180deg,#3A3C33,#26271F); border-color:rgba(184,245,58,.5); color:#B8F53A !important; text-shadow:none; }}
html body .stApp [data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"]::after {{ content:"›"; margin-left:auto; font-size:1.3rem; line-height:1; color:#D4D4D8; }}
.m3k-liq {{ background:linear-gradient(180deg,#242426,#171718); border:1px solid #2A2A2D; border-radius:14px; padding:.85rem .95rem; margin:.4rem 0 .7rem; }}
.m3k-liq .et {{ font-size:.66rem; letter-spacing:.14em; text-transform:uppercase; color:#77777C; font-weight:700; }}
.m3k-liq .val {{ font-size:1.5rem; font-weight:700; color:#B8F53A; margin:.15rem 0 .35rem; }}
.m3k-liq .est {{ display:flex; align-items:center; gap:.45rem; font-size:.76rem; color:#9A9AA0; }}
.m3k-liq .pt {{ width:8px; height:8px; border-radius:50%; background:#7EDC6A; box-shadow:0 0 8px #7EDC6A; flex:none; }}
.m3k-liq .pt.off {{ background:#F2B84B; box-shadow:0 0 8px #F2B84B; }}
html body .stApp [data-testid="stSidebar"] .stButton button {{ width:100%; background:transparent !important; border:1px solid #38383C !important; color:#D4D4D8 !important; border-radius:12px; }}
html body .stApp [data-testid="stSidebar"] .stButton button:hover {{ border-color:#B8F53A !important; color:#B8F53A !important; }}

/* Encabezado con foto de billetes difuminada a la derecha, que se desvanece hacia el texto */
.m3k-cab {{ position:relative; overflow:hidden; min-height:158px; align-items:center; }}
.m3k-cab::before {{ content:''; position:absolute; top:0; right:0; bottom:0; left:auto; width:auto; height:100%; aspect-ratio:962 / 317;
  background-image:{_BANNER}; background-size:100% 100%; background-position:center; pointer-events:none; z-index:0;
  -webkit-mask-image:linear-gradient(90deg, rgba(0,0,0,0) 0%, rgba(0,0,0,.03) 10%, rgba(0,0,0,.10) 20%, rgba(0,0,0,.22) 30%, rgba(0,0,0,.38) 40%, rgba(0,0,0,.56) 50%, rgba(0,0,0,.74) 60%, rgba(0,0,0,.88) 70%, rgba(0,0,0,.96) 80%, #000 92%); mask-image:linear-gradient(90deg, rgba(0,0,0,0) 0%, rgba(0,0,0,.03) 10%, rgba(0,0,0,.10) 20%, rgba(0,0,0,.22) 30%, rgba(0,0,0,.38) 40%, rgba(0,0,0,.56) 50%, rgba(0,0,0,.74) 60%, rgba(0,0,0,.88) 70%, rgba(0,0,0,.96) 80%, #000 92%); }}
.m3k-cab > * {{ position:relative; z-index:1; }}
.m3k-cab.cont::before {{ background-image:{_BANNER_CONT}; }}
.m3k-cab.ctrl::before {{ background-image:{_BANNER_CTRL}; }}
.m3k-cab.app::before {{ background-image:{_BANNER_APP}; }}
@media (max-width:640px) {{ .m3k-cab::before {{ width:100%; opacity:.35; }} }}
/* lima suavizado: relleno translúcido, borde fino y texto claro (menos intensidad que el lima sólido) */
html body .stApp .stButton button[kind="primary"], html body .stApp button[data-testid="stBaseButton-primary"], html body .stApp [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"], html body .stApp [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primaryFormSubmit"],
html body .stApp [class*="st-key-nc_"] button:not(:disabled), html body .stApp [data-testid="stFileUploaderDropzone"] button {{ background:rgba(184,245,58,.14) !important; border:1px solid rgba(184,245,58,.5) !important; color:#D6F58C !important; font-weight:600; }}
html body .stApp .stButton button[kind="primary"] *, html body .stApp button[data-testid="stBaseButton-primary"] *, html body .stApp [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] *, html body .stApp [class*="st-key-nc_"] button:not(:disabled) *, html body .stApp [data-testid="stFileUploaderDropzone"] button * {{ color:#D6F58C !important; background:transparent !important; }}
html body .stApp .stButton button[kind="primary"]:hover, html body .stApp button[data-testid="stBaseButton-primary"]:hover, html body .stApp [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:hover, html body .stApp [class*="st-key-nc_"] button:not(:disabled):hover {{ background:rgba(184,245,58,.24) !important; border-color:rgba(184,245,58,.8) !important; }}
html body .stApp [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {{ background:rgba(184,245,58,.14) !important; border-color:rgba(184,245,58,.5) !important; box-shadow:none !important; }}
html body .stApp [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked), html body .stApp [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) * {{ color:#D6F58C !important; }}
html body .stApp [data-testid="stNumberInputContainer"] button {{ background:rgba(184,245,58,.14) !important; color:#D6F58C !important; }}
html body .stApp [data-testid="stNumberInputContainer"] button * {{ color:#D6F58C !important; fill:#D6F58C !important; background:transparent !important; }}
html body .stApp [data-baseweb="select"] > div > div:last-child {{ background:rgba(184,245,58,.14) !important; }}
html body .stApp [data-baseweb="select"] svg {{ fill:#D6F58C !important; color:#D6F58C !important; }}
html body .stApp .m3k-paso span {{ background:rgba(184,245,58,.14) !important; border:1px solid rgba(184,245,58,.55); color:#D6F58C !important; box-shadow:none; }}
html body .stApp [data-testid="stSidebar"] [data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {{ font-weight:400 !important; font-variation-settings:'FILL' 0, 'wght' 400 !important; }}
/* alertas: el borde va solo en el contenedor externo (si no, se ve una marca doble) */
html body .stApp [data-testid="stAlert"] [data-testid="stAlertContainer"], html body .stApp [data-testid="stAlert"] [data-baseweb="notification"], html body .stApp [data-testid="stAlert"] [role="alert"] {{ border:none !important; border-left:none !important; border-radius:0 !important; background:transparent !important; box-shadow:none !important; }}
/* iconos Material: trazo normal aunque el texto de al lado esté en negrita */
html body .stApp [data-testid="stIconMaterial"], html body .stApp [data-testid="stIconMaterial"] *, html body .stApp [data-testid="stRadio"] label span[class*="material"], html body .stApp button span[data-testid="stIconMaterial"] {{ font-weight:400 !important; font-variation-settings:'FILL' 0, 'wght' 300 !important; }}
html body .stApp [data-testid="stRadio"] label[data-baseweb="radio"] p {{ font-size:.92rem; word-break:normal; overflow-wrap:normal; hyphens:none; }}
/* botones de enlace (st.link_button): mismo aspecto oscuro que los demás */
html body .stApp [data-testid="stLinkButton"] a, html body .stApp [data-testid="stLinkButton"] a:visited {{ background:#161617 !important; border:1px solid #38383C !important; color:#F4F4F2 !important; text-decoration:none !important; }}
html body .stApp [data-testid="stLinkButton"] a *, html body .stApp [data-testid="stLinkButton"] a p {{ color:#F4F4F2 !important; background:transparent !important; }}
html body .stApp [data-testid="stLinkButton"] a:hover {{ border-color:#B8F53A !important; background:#1F1F21 !important; }}
/* logos de Yape, Plin y WhatsApp en los botones correspondientes */
[class*="st-key-nc_entrega__1"] button p::before, [class*="st-key-mp_"][class*="__1"] button p::before {{ content:''; display:inline-block; width:22px; height:22px; margin-right:.5rem; vertical-align:-6px; background:{_LOGO_YAPE} center / contain no-repeat; }}
[class*="st-key-nc_entrega__2"] button p::before, [class*="st-key-mp_"][class*="__2"] button p::before {{ content:''; display:inline-block; width:22px; height:22px; margin-right:.5rem; vertical-align:-6px; background:{_LOGO_PLIN} center / contain no-repeat; }}
[class*="st-key-wa_chat"] p::before {{ content:''; display:inline-block; width:22px; height:22px; margin-right:.5rem; vertical-align:-6px; background:{_LOGO_WA} center / contain no-repeat; }}
/* botones de método (Efectivo, Yape, Plin, Transferencia): el texto no se parte por la mitad */
html body .stApp [class*="st-key-nc_entrega__"] button, html body .stApp [class*="st-key-mp_"][class*="__"] button {{ padding-left:.25rem !important; padding-right:.25rem !important; }}
html body .stApp [class*="st-key-nc_entrega__"] button p, html body .stApp [class*="st-key-mp_"][class*="__"] button p {{ white-space:nowrap !important; word-break:normal !important; overflow-wrap:normal !important; hyphens:none !important; font-size:.8rem !important; }}
html body .stApp [class*="st-key-nc_entrega__"] button [data-testid="stIconMaterial"], html body .stApp [class*="st-key-mp_"][class*="__"] button [data-testid="stIconMaterial"] {{ font-size:1.05rem !important; margin-right:.1rem; }}
html body .stApp [class*="st-key-nc_entrega__"] button > div, html body .stApp [class*="st-key-mp_"][class*="__"] button > div {{ gap:.25rem; flex-wrap:nowrap; }}
/* accesos directos de Inicio: solo en el celular */
html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-qa_"]) {{ display:none !important; }}
/* barra inferior: solo en el celular */
html body .stApp [class*="st-key-barra_movil"] {{ display:none !important; }}
/* móvil: encabezado compacto y filas de botones que NO se apilan (solo las filas de botones; el resto de columnas sí se apila) */
@media (max-width: 640px) {{
  html body .stApp .m3k-cab {{ min-height:108px; padding:.7rem .8rem; gap:.7rem; }}
  html body .stApp .m3k-cab .ico {{ width:42px; height:42px; font-size:1.3rem; border-radius:12px; }}
  html body .stApp .m3k-cab .marca {{ font-size:.62rem; letter-spacing:.08em; }}
  html body .stApp [data-testid="stToolbarActions"] {{ display:none !important; }}
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-nc_entrega__"]),
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-nc_modalidad__"]),
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-nc_meses__"]),
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-nc_cuando__"]),
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-mp_"]),
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-vc_"]) {{ flex-direction:row !important; flex-wrap:nowrap !important; gap:.4rem !important; }}
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-nc_entrega__"]) > [data-testid="stColumn"],
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-nc_modalidad__"]) > [data-testid="stColumn"],
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-nc_meses__"]) > [data-testid="stColumn"],
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-nc_cuando__"]) > [data-testid="stColumn"],
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-mp_"]) > [data-testid="stColumn"],
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-vc_"]) > [data-testid="stColumn"] {{ min-width:0 !important; width:auto !important; flex:1 1 0 !important; }}
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-nc_rapido_"]) {{ flex-direction:row !important; flex-wrap:wrap !important; gap:.4rem !important; }}
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-nc_rapido_"]) > [data-testid="stColumn"] {{ min-width:0 !important; width:auto !important; flex:1 1 30% !important; }}
  html body .stApp [class*="st-key-nc_"] button p, html body .stApp [class*="st-key-mp_"] button p, html body .stApp [class*="st-key-vc_"] button p {{ font-size:.8rem !important; white-space:normal; }}
  html body .stApp [class*="st-key-ficha_"] {{ margin-bottom:.8rem; }}
  html body .stApp .f-panel b {{ font-size:.95rem; }}
  /* la animación de entrada del contenido impedía que la barra inferior quedara fija a la pantalla */
  html body .stApp, html body .stApp [data-testid="stAppViewContainer"], html body .stApp [data-testid="stMain"], html body .stApp [data-testid="stMainBlockContainer"], html body .stApp .block-container {{ animation:none !important; transform:none !important; filter:none !important; will-change:auto !important; contain:none !important; perspective:none !important; }}
  /* celular: sin barra lateral ni cabecera; la navegación va en la barra inferior */
  html body .stApp [data-testid="stSidebar"], html body .stApp [data-testid="stSidebarCollapsedControl"], html body .stApp [data-testid="stExpandSidebarButton"], html body .stApp [data-testid="collapsedControl"], html body .stApp [data-testid="stHeader"] {{ display:none !important; }}
  html body .stApp [data-testid="stMainBlockContainer"], html body .stApp .block-container {{ padding-top:1rem !important; padding-bottom:7rem !important; }}
  html body .stApp [class*="st-key-barra_movil"] {{ display:block !important; position:fixed !important; left:0; right:0; bottom:0; width:100% !important; z-index:999990; background:#121213; border-top:1px solid #2A2A2D; padding:.25rem .3rem calc(.3rem + env(safe-area-inset-bottom)); box-sizing:border-box; }}
  html body .stApp [class*="st-key-barra_movil"] [data-testid="stHorizontalBlock"] {{ flex-direction:row !important; flex-wrap:nowrap !important; gap:0 !important; align-items:stretch; }}
  html body .stApp [class*="st-key-barra_movil"] [data-testid="stColumn"] {{ min-width:0 !important; width:auto !important; flex:1 1 0 !important; }}
  html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"], html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] button {{ flex-direction:column !important; justify-content:center; align-items:center; gap:2px !important; padding:.3rem 0 !important; min-height:52px; background:transparent !important; border:0 !important; box-shadow:none !important; color:#9A9AA0 !important; width:100%; }}
  html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"] > div, html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] button > div {{ flex-direction:column !important; align-items:center; gap:2px !important; justify-content:center; }}
  html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"] p, html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] button p {{ font-size:.68rem !important; margin:0; color:inherit !important; white-space:nowrap; }}
  html body .stApp [class*="st-key-barra_movil"] [data-testid="stIconMaterial"] {{ font-size:1.4rem !important; color:inherit !important; margin:0 !important; }}
  html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] button [data-testid="stIconMaterial"]:last-child:not(:first-child) {{ display:none !important; }}
  html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"][aria-current="page"] {{ color:#B8F53A !important; background:rgba(184,245,58,.10) !important; border-radius:12px; }}
  html body .stApp [data-testid="stPopoverBody"] {{ min-width:min(260px,90vw); }}
  html body .stApp [class*="st-key-barra_movil"] [data-testid="stIconEmoji"] {{ font-size:1.65rem !important; line-height:1.1 !important; margin:0 !important; }}
  /* barra inferior: iconos más grandes, texto completo y claro, pestaña activa marcada */
  html body .stApp [class*="st-key-barra_movil"] {{ background:#141416 !important; border-top:1px solid #2F2F33 !important; box-shadow:0 -8px 20px rgba(0,0,0,.5); padding:.35rem .25rem calc(.35rem + env(safe-area-inset-bottom)) !important; }}
  html body .stApp [class*="st-key-barra_movil"] [data-testid="stColumn"], html body .stApp [class*="st-key-barra_movil"] [data-testid="stElementContainer"], html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] {{ overflow:visible !important; min-width:0 !important; }}
  html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"], html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] button {{ position:relative; min-height:58px; gap:3px !important; color:#C4C4CA !important; border-radius:14px !important; padding:.35rem 0 !important; }}
  html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] button div, html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"] div {{ display:flex !important; flex-direction:column !important; align-items:center !important; justify-content:center !important; gap:3px !important; width:auto !important; min-width:0 !important; }}
  html body .stApp [class*="st-key-barra_movil"] [data-testid="stIconMaterial"] {{ font-size:1.7rem !important; line-height:1 !important; font-weight:400; }}
  html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"] p, html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] button p {{ font-size:.74rem !important; font-weight:600 !important; line-height:1.1 !important; letter-spacing:.01em; overflow:visible !important; text-overflow:clip !important; }}
  html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"][aria-current="page"], html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] button[aria-expanded="true"] {{ color:#B8F53A !important; background:rgba(184,245,58,.13) !important; }}
  html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"][aria-current="page"]::before, html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] button[aria-expanded="true"]::before {{ content:""; position:absolute; top:-.35rem; left:28%; right:28%; height:3px; border-radius:0 0 4px 4px; background:#B8F53A; }}
  html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"][aria-current="page"] [data-testid="stIconMaterial"] {{ font-variation-settings:'FILL' 1, 'wght' 500 !important; }}
  /* barra inferior: el icono y el texto cada uno en su propio renglón, sin encimarse */
  html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"], html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] button {{ min-height:66px !important; height:auto !important; padding:.4rem .1rem .35rem !important; gap:.2rem !important; overflow:visible !important; }}
  html body .stApp [class*="st-key-barra_movil"] [data-testid="stIconEmoji"], html body .stApp [class*="st-key-barra_movil"] [data-testid="stIconMaterial"] {{ display:block !important; flex:none !important; width:auto !important; height:auto !important; min-height:0 !important; font-size:1.5rem !important; line-height:1.3 !important; margin:0 0 .15rem !important; padding:0 !important; }}
  html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"] p, html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] button p {{ display:block !important; flex:none !important; margin:0 !important; padding:0 !important; font-size:.72rem !important; line-height:1.25 !important; height:auto !important; white-space:nowrap !important; }}
  html body .stApp [class*="st-key-barra_movil"] a[data-testid="stPageLink-NavLink"] > div, html body .stApp [class*="st-key-barra_movil"] [data-testid="stPopover"] button > div {{ gap:.15rem !important; height:auto !important; }}
  /* Nuevo crédito: solo la modalidad elegida, compacta (los botones de arriba cambian de una a otra) */
  html body .stApp .m3k-modos {{ display:block; margin:.2rem 0 .8rem; }}
  html body .stApp .m3k-modo:not(.sel) {{ display:none; }}
  html body .stApp .m3k-modo {{ padding:.7rem .85rem; transform:none !important; }}
  html body .stApp .m3k-modo .ico {{ width:34px; height:34px; font-size:1.1rem; border-radius:10px; margin-bottom:.35rem; }}
  html body .stApp .m3k-modo ul {{ font-size:.8rem; line-height:1.45; }}
  html body .stApp .m3k-modo .sub {{ margin:.05rem 0 .35rem; }}
  /* accesos directos de Inicio: 2 por línea */
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-qa_"]) {{ display:flex !important; flex-direction:row !important; flex-wrap:wrap !important; gap:.4rem !important; }}
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-qa_"]) > [data-testid="stColumn"] {{ min-width:0 !important; width:auto !important; flex:1 1 calc(50% - .4rem) !important; }}
  html body .stApp [class*="st-key-qa_"] button p {{ font-size:.85rem !important; white-space:nowrap; }}
  /* tablas anchas (opción apilar): en el celular cada fila es una tarjeta con sus datos etiquetados */
  html body .stApp .m3k-scroll:has(.m3k-tabla.apilar) {{ overflow:visible; max-height:none; border:0; background:none; }}
  html body .stApp .m3k-tabla.apilar, html body .stApp .m3k-tabla.apilar tbody, html body .stApp .m3k-tabla.apilar tfoot,
  html body .stApp .m3k-tabla.apilar tr, html body .stApp .m3k-tabla.apilar td {{ display:block; width:100%; box-sizing:border-box; }}
  html body .stApp .m3k-tabla.apilar thead {{ display:none; }}
  html body .stApp .m3k-tabla.apilar tbody tr, html body .stApp .m3k-tabla.apilar tfoot tr {{ border:1px solid #2A2A2D; border-radius:14px; background:#161617; margin:0 0 .6rem; padding:.35rem 0; }}
  html body .stApp .m3k-tabla.apilar tfoot tr {{ border-color:rgba(184,245,58,.5); }}
  html body .stApp .m3k-tabla.apilar td, html body .stApp .m3k-tabla.apilar tbody tr:nth-child(even) td, html body .stApp .m3k-tabla.apilar tbody tr:hover td {{ display:flex; justify-content:space-between; align-items:center; gap:.8rem; border-top:0; padding:.28rem .8rem; text-align:right; white-space:normal; background:transparent; }}
  html body .stApp .m3k-tabla.apilar td::before {{ content:attr(data-label); color:#9A9AA0; font-size:.7rem; text-transform:uppercase; letter-spacing:.05em; text-align:left; flex:0 0 auto; }}
  html body .stApp .m3k-tabla.apilar td.nw, html body .stApp .m3k-tabla.apilar td.n {{ white-space:normal; }}
  html body .stApp .m3k-tabla.apilar td .m3k-barra {{ width:55%; min-width:90px; flex:0 1 55%; }}
  /* cabecera con fondo sólido: el logo y el botón del menú ya no se encimen con el contenido al hacer scroll */
  html body .stApp [data-testid="stHeader"] {{ background:#0B0B0C !important; }}
  /* filtros y vistas: botones en fila (2 por línea como mínimo), no uno debajo de otro */
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-filtro_prestamo__"]),
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-filtro_cliente__"]),
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-filtro_caja__"]),
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-vista_prestamos__"]) {{ flex-direction:row !important; flex-wrap:wrap !important; gap:.4rem !important; }}
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-filtro_prestamo__"]) > [data-testid="stColumn"],
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-filtro_cliente__"]) > [data-testid="stColumn"],
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-filtro_caja__"]) > [data-testid="stColumn"],
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-vista_prestamos__"]) > [data-testid="stColumn"] {{ min-width:0 !important; width:auto !important; flex:1 1 calc(50% - .4rem) !important; }}
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-filtro_prestamo__"]) > [data-testid="stColumn"]:not(:has(button)),
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-filtro_cliente__"]) > [data-testid="stColumn"]:not(:has(button)),
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-filtro_caja__"]) > [data-testid="stColumn"]:not(:has(button)),
  html body .stApp [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [class*="st-key-vista_prestamos__"]) > [data-testid="stColumn"]:not(:has(button)) {{ display:none !important; }}
  html body .stApp [class*="st-key-filtro_"] button p, html body .stApp [class*="st-key-vista_prestamos__"] button p {{ font-size:.8rem !important; white-space:normal; }}
}}
</style>
"""


def aplicar() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# icono y color de cada pantalla (el color agrupa por sección: operación lima, contabilidad celeste, control ámbar)
SECCIONES = {
    "Control de cartera": ("🏠", "#B8F53A"), "Registrar cobro": ("💵", "#B8F53A"), "Préstamos": ("💰", "#B8F53A"), "Clientes": ("👥", "#B8F53A"),
    "Resultados": ("📊", "#6CC4E8"), "Cuentas por cobrar": ("🧾", "#6CC4E8"), 
    "Caja": ("🏦", "#F2B84B"), "Recibos": ("🧾", "#F2B84B"), "Configuración": ("⚙️", "#9A9AA0"),
}


def encabezado(titulo: str, subtitulo: str = "") -> None:
    sub = f"<p>{esc(subtitulo)}</p>" if subtitulo else ""
    icono, color = SECCIONES.get(titulo, ("💼", ACENTO))
    clase = "m3k-cab cont" if titulo in SECCIONES_CONTABILIDAD else "m3k-cab ctrl" if titulo in SECCIONES_CONTROL else "m3k-cab app" if titulo in SECCIONES_APLICACION else "m3k-cab"
    st.markdown(f'<div class="{clase}" style="--sec:{color}"><div class="ico">{icono}</div><div><div class="marca">M3K · Préstamos personales</div>'
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


ICONOS_KPI = (("hoy", "📅"), ("vencido", "⚠️"), ("atraso", "⚠️"), ("calle", "💰"), ("prestado", "💰"), ("caja", "🏦"), ("disponible", "🏦"), ("liquidez", "🏦"),
              ("ganancia", "📈"), ("cobrad", "💵"), ("cobrar", "💵"), ("cuota", "🗓️"), ("saldo", "🧮"), ("cliente", "👥"), ("entrado", "📥"),
              ("salido", "📤"), ("crédito", "💳"), ("capital", "🏛️"), ("interés", "📈"), ("total", "🧮"))


def _icono_kpi(etiqueta: str, icono: str | None = None) -> str:
    if icono:
        return icono
    e = etiqueta.lower()
    return next((i for clave, i in ICONOS_KPI if clave in e), "📌")


def kpis(items: list[dict]) -> None:
    """items: dicts con etiqueta, valor, nota (opcional), tono (ok/aviso/malo/info) y heroe (opcional)."""
    tarjetas = []
    for it in items:
        tono = TONOS.get(it.get("tono", ""), BORDE)
        clase = "m3k-kpi heroe" if it.get("heroe") else "m3k-kpi"
        nota = f'<div class="nota">{esc(it["nota"])}</div>' if it.get("nota") else ""
        tarjetas.append(f'<div class="{clase}" style="--tono:{tono}"><div class="ic">{_icono_kpi(it["etiqueta"], it.get("icono"))}</div><div class="e">{esc(it["etiqueta"])}</div>'
                        f'<div class="v">{esc(it["valor"])}</div>{nota}</div>')
    st.markdown(f'<div class="m3k-kpis">{"".join(tarjetas)}</div>', unsafe_allow_html=True)


def tabla(columnas: list[str], filas: list, numericas: tuple[int, ...] = (), etiqueta: str = "", pie: list | None = None,
          sin_corte: tuple[int, ...] = (), apilar: bool = False) -> None:
    """Tabla HTML con cabecera fija, desplazamiento propio y fila de totales opcional.

    Cada fila es una lista de celdas, o un dict {"celdas": [...], "clase": "cab"|"sub"} para filas de agrupación.
    Si una fila trae menos celdas que columnas, su última celda ocupa el resto del ancho (útil para títulos de asiento).
    Las celdas se escapan salvo que sean `Raw`. Una celda que empieza con dos espacios se muestra con sangría.
    `sin_corte` lista las columnas cuyo texto nunca se parte en dos líneas (fechas, números, cuentas).
    `apilar` hace que en pantallas pequeñas cada fila se vea como una tarjeta con sus datos etiquetados.
    """
    def celda(i: int, valor, ancho: int = 1) -> str:
        clases = []
        if i in numericas:
            clases.append("n")
        if i in sin_corte and ancho == 1:  # los títulos que ocupan varias columnas sí deben poder partirse
            clases.append("nw")
        texto = esc(valor)
        if isinstance(valor, str) and valor.startswith("  ") and not isinstance(valor, Raw):
            clases.append("sangria")
            texto = esc(valor.strip())
        span = f' colspan="{ancho}"' if ancho > 1 else ""
        etiqueta_col = f' data-label="{html.escape(columnas[i])}"' if i < len(columnas) else ""
        return f'<td class="{" ".join(clases)}"{span}{etiqueta_col}>{texto}</td>'

    cab = "".join(f'<th class="{"n" if i in numericas else ""}">{esc(c)}</th>' for i, c in enumerate(columnas))
    cuerpo = []
    for fila in filas:
        celdas, clase = (fila["celdas"], fila.get("clase", "")) if isinstance(fila, dict) else (fila, "")
        resto = len(columnas) - len(celdas) + 1
        partes = [celda(i, c, resto if i == len(celdas) - 1 else 1) for i, c in enumerate(celdas)]
        cuerpo.append(f'<tr class="{clase}">' + "".join(partes) + "</tr>")
    tfoot = ""
    if pie:
        tfoot = "<tfoot><tr>" + "".join(f'<td class="{"n" if i in numericas else ""}" data-label="{html.escape(columnas[i])}">{esc(c)}</td>' for i, c in enumerate(pie)) + "</tr></tfoot>"
    aria = f' aria-label="{html.escape(etiqueta)}"' if etiqueta else ""
    st.markdown(f'<div class="m3k-scroll" role="region" tabindex="0"{aria}><table class="m3k-tabla{" apilar" if apilar else ""}">'
                f'<thead><tr>{cab}</tr></thead><tbody>{"".join(cuerpo)}</tbody>{tfoot}</table></div>', unsafe_allow_html=True)


def barra(avance: float) -> Raw:
    ancho = max(0, min(100, round(avance * 100)))
    return Raw(f'<div class="m3k-barra" role="img" aria-label="{ancho} % cobrado"><i style="width:{ancho}%"></i></div>')


def vacio(titulo: str, ayuda: str, icono: str = "📭") -> None:
    st.markdown(f'<div class="m3k-vacio"><div class="gran">{icono}</div><b>{esc(titulo)}</b>{esc(ayuda)}</div>', unsafe_allow_html=True)


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


def _logo_html() -> str:
    """Logo M3K con los bordes difuminados para que se funda con el fondo; si falta el archivo se usa la ficha con el icono."""
    import base64
    from pathlib import Path
    ruta = Path(__file__).parent / "assets" / "logo_m3k.png"
    try:
        datos = base64.b64encode(ruta.read_bytes()).decode()
    except OSError:
        return '<div class="logo">💰</div>'
    return f'<img class="logo-img" alt="M3K" src="data:image/png;base64,{datos}">'


def saludo_del_dia() -> str:
    """«Buenos días» / «Buenas tardes» / «Buenas noches» según la hora de Lima."""
    hora = datetime.now(calc.LIMA).hour
    return "Buenos días" if hora < 12 else "Buenas tardes" if hora < 19 else "Buenas noches"


def acceso_cabecera() -> None:
    """Marca y saludo de bienvenida, sobre el formulario de la clave."""
    st.markdown(f'<div class="m3k-login">{_logo_html()}<div class="marca">M3K · PRÉSTAMOS</div>'
                f'<h1>{saludo_del_dia()}, <span>Monthy</span></h1>'
                '<p>Monthy Paifa Del Aguila · M3K Préstamos<br>Acceso privado. Ingresa tu clave.</p>'
                '<div class="pasos"><div><span>💵</span>Cobros del día</div><div><span>📒</span>Cartera y clientes</div>'
                '<div><span>🧾</span>Recibos</div></div></div>', unsafe_allow_html=True)


def tarjeta_caja(liquidez: float, respaldo: bool) -> None:
    """Tarjeta de liquidez al pie de la barra lateral, con el estado del respaldo."""
    estado = "Respaldo en Google Drive activo" if respaldo else "Sin respaldo: datos solo en este equipo"
    st.markdown(f'<div class="m3k-liq"><div class="et">Liquidez en caja</div><div class="val num">{soles(liquidez)}</div>'
                f'<div class="est"><span class="pt{"" if respaldo else " off"}"></span>{estado}</div></div>', unsafe_allow_html=True)


def barra_movil(paginas: dict) -> None:
    """Barra de navegación inferior (solo se ve en el celular, el CSS la oculta en pantallas grandes)."""
    # iconos a color (los mismos de las cabeceras de cada pantalla)
    principales = (("inicio", "Inicio", "🏠"), ("cobros", "Cobrar", "💵"), ("prestamos", "Créditos", "💰"), ("clientes", "Clientes", "👥"))
    mas = (("resumen", "Resultados", "📊"), ("cxc", "Cuentas por cobrar", "📒"), ("caja", "Caja", "🏦"),
           ("recibos", "Recibos", "🧾"), ("config", "Configuración", "⚙️"))
    with st.container(key="barra_movil"):
        columnas = st.columns(5)
        for col, (clave, etiqueta, icono) in zip(columnas, principales):
            with col:
                st.page_link(paginas[clave], label=etiqueta, icon=icono)
        with columnas[4]:
            with st.popover("Más", icon="🗂️", use_container_width=True):
                for clave, etiqueta, icono in mas:
                    st.page_link(paginas[clave], label=etiqueta, icon=icono, use_container_width=True)
                if st.button("Cerrar sesión", icon=":material/logout:", key="salir_movil", use_container_width=True):
                    st.session_state.clear()
                    st.rerun()


def ocultar_barra_lateral() -> None:
    """Sin sesión no se muestra el menú: Streamlit conserva en pantalla el de la sesión anterior si la app se detiene antes de definirlo."""
    st.markdown("<style>[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'], [data-testid='collapsedControl'], "
                "[data-testid='stSidebarNav'] {display:none !important;}</style>", unsafe_allow_html=True)
