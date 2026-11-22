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
from datetime import date

import streamlit as st

import calculos as calc

# Paleta oscura: negro verdoso con lima como acento; los estados usan tonos claros que se leen sobre fondo oscuro.
PAGINA, FONDO, PAPEL, BORDE = "#050D07", "#0C1C10", "#0F2412", "#1E3A1F"
TEXTO, TEXTO_SUAVE, ACENTO, CABECERA_TABLA = "#F2FBE8", "#9DB58A", "#B8F53A", "#0F2412"
SOBRE_ACENTO = "#0A1A05"  # texto sobre fondos lima
TONOS = {"ok": "#7EDC6A", "aviso": "#F2B84B", "malo": "#FF7A6B", "info": "#6CC4E8", "neutro": "#9DB58A"}


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
  color:var(--c); background:color-mix(in srgb, var(--c) 16%, #0C1C10); border:1px solid color-mix(in srgb, var(--c) 40%, #0C1C10); }}

/* Tablas tipo libro */
.m3k-scroll {{ overflow-x:auto; border:1px solid var(--borde); border-radius:6px; margin:.3rem 0 1rem; max-height:70vh; }}
.m3k-tabla {{ width:100%; border-collapse:collapse; font-size:.84rem; }}
.m3k-tabla th {{ text-align:left; background:{CABECERA_TABLA}; color:var(--suave); font-weight:600; font-size:.72rem;
  letter-spacing:.04em; text-transform:uppercase; padding:.45rem .65rem; white-space:nowrap; position:sticky; top:0; z-index:1;
  border-bottom:1px solid var(--borde); }}
.m3k-tabla td {{ padding:.38rem .65rem; border-top:1px solid #1E3A1F; vertical-align:middle; }}
.m3k-tabla tbody tr:nth-child(even) td {{ background:#0A160C; }}
.m3k-tabla td.n, .m3k-tabla th.n {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
.m3k-tabla tr.cab td {{ background:var(--papel) !important; font-weight:600; border-top:1px solid var(--borde); }}
.m3k-tabla tr.sub td {{ font-weight:600; background:var(--papel) !important; }}
.m3k-tabla td.sangria {{ padding-left:1.6rem; color:var(--texto); }}
.m3k-tabla td.nw, .m3k-tabla th.nw {{ white-space:nowrap; }}
.m3k-tabla tr.cab td {{ border-top:2px solid var(--borde); }}
.m3k-tabla tfoot td {{ font-weight:700; background:{CABECERA_TABLA}; border-top:2px solid var(--borde); padding:.45rem .65rem;
  font-variant-numeric:tabular-nums; }}
.m3k-tabla tfoot td.n {{ text-align:right; }}
.m3k-tabla tbody tr:hover td {{ background:#14301A; }}
.m3k-barra {{ height:6px; background:#1E3A1F; border-radius:99px; min-width:70px; overflow:hidden; }}
.m3k-barra i {{ display:block; height:100%; background:var(--ok); border-radius:99px; }}

/* Fila de cobranza y estados vacíos */
.m3k-fila {{ background:var(--fondo); border:1px solid var(--borde); border-left:4px solid var(--tono, var(--borde));
  border-radius:6px; padding:.6rem .85rem; display:flex; justify-content:space-between; gap:1rem; align-items:center; }}
.m3k-fila b {{ display:block; }} .m3k-fila small {{ color:var(--suave); }}
.m3k-vacio {{ border:1px dashed var(--borde); border-radius:8px; padding:1.3rem; text-align:center; color:var(--suave); background:var(--papel); }}
.m3k-vacio b {{ color:var(--texto); display:block; margin-bottom:.25rem; }}
.m3k-verif {{ display:flex; justify-content:space-between; gap:1rem; padding:.45rem .1rem; border-bottom:1px solid #1E3A1F; font-size:.9rem; }}

/* Recibo imprimible */
.m3k-recibo {{ background:#F2FBE8; color:#0A1A05; border:1px solid #B8F53A; border-radius:8px; padding:1.3rem 1.5rem; max-width:520px;
  margin:.5rem 0 1rem; font-variant-numeric:tabular-nums; }}
.m3k-recibo h3 {{ margin:0 0 .2rem; color:#0A1A05; }} .m3k-recibo hr {{ border:0; border-top:1px dashed #9aa79f; margin:.8rem 0; }}
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
.m3k-avance .pista {{ height:12px; background:#1E3A1F; border-radius:99px; overflow:hidden; }}
.m3k-avance .pista i {{ display:block; height:100%; background:linear-gradient(90deg,#4FA84A,var(--ok)); border-radius:99px; transform-origin:left;
  animation:m3k-ancho 1s cubic-bezier(.2,.7,.2,1) .15s both; }}
.m3k-dias {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(125px,1fr)); gap:.6rem; }}
.m3k-dia {{ border:1px solid var(--borde); border-radius:8px; padding:.6rem .75rem; background:var(--fondo); animation:m3k-subir .5s ease both;
  transition:transform .2s ease, box-shadow .2s ease; }}
.m3k-dia:hover {{ transform:translateY(-2px); box-shadow:0 5px 14px rgba(0,0,0,.4); }}
.m3k-dia.hoy {{ border-color:var(--acento); background:#12281A; }} .m3k-dia.vacio {{ opacity:.6; }}
.m3k-dia .d {{ font-size:.74rem; text-transform:uppercase; letter-spacing:.03em; color:var(--suave); }}
.m3k-dia .m {{ font-size:1.12rem; font-weight:700; margin:.1rem 0; }} .m3k-dia .n {{ font-size:.76rem; color:var(--suave); }}
.m3k-dia .nivel {{ height:4px; background:#1E3A1F; border-radius:99px; margin-top:.5rem; overflow:hidden; }}
.m3k-dia .nivel i {{ display:block; height:100%; background:var(--info); border-radius:99px; transform-origin:left; animation:m3k-ancho .8s ease .2s both; }}
.m3k-sem {{ display:grid; grid-template-columns:repeat(6,1fr); gap:.5rem; align-items:start; }}
.m3k-sem .c {{ display:flex; flex-direction:column; align-items:center; gap:.25rem; min-width:0; }}
.m3k-sem .barras {{ height:120px; width:100%; display:flex; align-items:flex-end; justify-content:center; gap:3px; border-bottom:1px solid var(--borde); }}
.m3k-sem .barras i {{ display:block; width:36%; max-width:34px; border-radius:3px 3px 0 0; transform-origin:bottom; animation:m3k-alto .75s cubic-bezier(.2,.7,.2,1) both;
  transition:filter .2s ease; }}
.m3k-sem .c:hover .barras i {{ filter:brightness(.92); }}
.m3k-sem i.esp, .leyenda i.esp {{ background:#2F5A33; }} .m3k-sem i.cob, .leyenda i.cob {{ background:var(--ok); }}
.m3k-sem .rot {{ font-size:.72rem; color:var(--suave); white-space:nowrap; }} .m3k-sem .act .rot {{ color:var(--texto); font-weight:700; }}
.m3k-sem .val {{ font-size:.7rem; color:var(--suave); white-space:nowrap; }}
.leyenda {{ display:flex; gap:1rem; margin-top:.6rem; font-size:.76rem; color:var(--suave); }}
.leyenda i {{ display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:.35rem; vertical-align:-1px; }}
.m3k-dona {{ display:flex; align-items:center; gap:1.1rem; flex-wrap:wrap; }}
.m3k-dona svg {{ flex:none; }} .m3k-dona .dc {{ font-size:13px; font-weight:700; fill:var(--texto); }} .m3k-dona .ds {{ font-size:8px; fill:var(--suave); }}
.m3k-dona .seg {{ animation:m3k-aro 1s cubic-bezier(.3,.7,.2,1) both; }}
.m3k-dona ul {{ list-style:none; margin:0; padding:0; flex:1; min-width:170px; max-width:380px; }}
.m3k-dona li {{ display:grid; grid-template-columns:12px 1fr auto 38px; gap:.5rem; align-items:center; padding:.3rem 0; border-bottom:1px solid #1E3A1F; font-size:.85rem; }}
.m3k-dona li:last-child {{ border-bottom:0; }} .m3k-dona li i {{ width:10px; height:10px; border-radius:50%; }}
.m3k-dona li em {{ font-style:normal; color:var(--suave); text-align:right; font-size:.78rem; }}
.m3k-panel svg.lin {{ width:100%; height:150px; display:block; }} .m3k-panel .revela {{ animation:m3k-revela 1.3s cubic-bezier(.4,.1,.2,1) both; }}
.extremos {{ display:flex; justify-content:space-between; align-items:flex-start; gap:.5rem; font-size:.76rem; color:var(--suave); margin-top:.35rem; flex-wrap:wrap; }}
.extremos b {{ display:block; color:var(--texto); font-size:.9rem; }} .extremos .der {{ text-align:right; }} .extremos .mm {{ align-self:center; }}

.m3k-sem.una .barras {{ height:140px; }}
.m3k-sem.una .col {{ width:70%; max-width:46px; display:flex; flex-direction:column; align-items:center; }}
.m3k-sem.una .col i {{ width:100%; max-width:none; flex:1; border-radius:3px 3px 0 0; }}
.m3k-sem.una .col .val {{ font-weight:600; color:var(--texto); font-size:.74rem; white-space:nowrap; line-height:1.5; animation:m3k-subir .6s ease .3s both; }}
.m3k-reparto .barra {{ display:flex; height:22px; border-radius:99px; overflow:hidden; background:#1E3A1F; animation:m3k-revela 1s cubic-bezier(.4,.1,.2,1) both; }}
.m3k-reparto .barra i {{ display:block; height:100%; }}
.m3k-reparto ul {{ list-style:none; margin:.7rem 0 0; padding:0; display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:.2rem 1.5rem; }}
.m3k-reparto li {{ display:grid; grid-template-columns:12px 1fr auto 38px; gap:.5rem; align-items:center; padding:.3rem 0; font-size:.88rem; border-bottom:1px solid #1E3A1F; }}
.m3k-reparto li i {{ width:10px; height:10px; border-radius:50%; }} .m3k-reparto li em {{ font-style:normal; color:var(--suave); text-align:right; font-size:.78rem; }}

.m3k-cascada .fila {{ display:grid; grid-template-columns:minmax(120px,190px) 1fr auto; gap:.8rem; align-items:center; padding:.38rem 0; border-bottom:1px solid #1E3A1F; font-size:.9rem; }}
.m3k-cascada .fila:last-child {{ border-bottom:0; }} .m3k-cascada .fila.total {{ border-top:2px solid var(--borde); margin-top:.2rem; font-weight:700; }}
.m3k-cascada .pista {{ height:12px; background:#16301A; border-radius:99px; overflow:hidden; }}
.m3k-cascada .pista i {{ display:block; height:100%; border-radius:99px; transform-origin:left; animation:m3k-ancho .9s cubic-bezier(.2,.7,.2,1) both; }}
.m3k-cascada b {{ text-align:right; min-width:92px; }}
@media (max-width: 640px) {{ .m3k-cascada .fila {{ grid-template-columns:1fr auto; }} .m3k-cascada .pista {{ grid-column:1 / -1; grid-row:2; }} }}

[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"]) {{ border-color:var(--borde) !important; background:var(--fondo); border-radius:8px; }}

.m3k-dias.cuotas {{ grid-template-columns:repeat(auto-fill,minmax(118px,1fr)); gap:.5rem; }}
.m3k-dias.cuotas .m3k-dia {{ padding:.5rem .65rem; }} .m3k-dias.cuotas .m {{ font-size:1rem; }}
.m3k-cliente {{ display:grid; grid-template-columns:44px minmax(160px,1.3fr) 190px minmax(190px,1fr); gap:.9rem; align-items:center; margin-bottom:.9rem; }}
.m3k-cliente .est {{ display:flex; gap:.35rem; justify-content:flex-end; flex-wrap:wrap; }}
.m3k-cliente .av {{ width:40px; height:40px; border-radius:50%; background:#16301A; color:var(--acento); font-weight:700; display:flex; align-items:center; justify-content:center; }}
.m3k-cliente .dat b {{ display:block; }} .m3k-cliente small {{ color:var(--suave); }}
.m3k-cliente .monto {{ text-align:right; }} .m3k-cliente .monto b {{ display:block; font-size:1.05rem; }}
.m3k-cliente .m3k-barra {{ margin-top:.35rem; }}
@media (max-width: 760px) {{ .m3k-cliente {{ grid-template-columns:44px 1fr; }} .m3k-cliente .est, .m3k-cliente .monto {{ grid-column:1 / -1; text-align:left; }} }}

.m3k-sem .val b {{ color:var(--texto); font-weight:600; }} .m3k-sem .val.f {{ color:var(--aviso); font-weight:600; }} .m3k-sem .val.ok {{ color:var(--ok); font-weight:600; }}
.m3k-aldia b {{ display:block; font-size:1.8rem; color:var(--ok); }} .m3k-aldia span {{ color:var(--suave); }} .m3k-aldia strong {{ color:var(--texto); }}

/* Selectores horizontales (st.radio) con aspecto de navegación: píldoras, la opción activa en verde.
   Si Streamlit cambia su estructura interna, estas reglas simplemente dejan de aplicarse y quedan los botones de opción normales. */
[data-testid="stRadio"] [role="radiogroup"] {{ gap:.45rem; flex-wrap:wrap; }}
[data-testid="stRadio"] label[data-baseweb="radio"] {{ background:var(--fondo); border:1px solid var(--borde); border-radius:999px; padding:.28rem .95rem; margin:0;
  cursor:pointer; transition:background .15s ease, border-color .15s ease, box-shadow .15s ease; }}
[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child:not(:has(p)) {{ display:none; }}
[data-testid="stRadio"] label[data-baseweb="radio"]:hover {{ border-color:var(--acento); background:#12281A; }}
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {{ background:var(--acento); border-color:var(--acento); box-shadow:0 2px 8px rgba(184,245,58,.25); }}
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p {{ color:#0A1A05 !important; font-weight:600; }}
[data-testid="stRadio"] label[data-baseweb="radio"] p {{ font-size:.9rem; margin:0; }}
/* selector principal de cada pantalla (st.container(key="nav_principal")): más grande, con una línea que lo separa del contenido */
.st-key-nav_principal {{ border-bottom:1px solid var(--borde); padding-bottom:.7rem; margin-bottom:.3rem; }}
.st-key-nav_principal [data-testid="stRadio"] label[data-baseweb="radio"] {{ padding:.5rem 1.25rem; border-radius:10px; }}
.st-key-nav_principal [data-testid="stRadio"] label[data-baseweb="radio"] p {{ font-size:1rem; }}

/* Encabezado con ícono y fondo de color por sección; tarjetas con ícono y tinte */
.m3k-cab {{ justify-content:flex-start; background:linear-gradient(100deg, color-mix(in srgb, var(--sec, var(--acento)) 16%, #0C1C10) 0%, #0C1C10 75%); border:1px solid var(--borde);
  border-bottom:3px solid var(--sec, var(--acento)); border-radius:12px; padding:.9rem 1.1rem; align-items:center; gap:1rem; }}
.m3k-cab .ico {{ width:54px; height:54px; border-radius:14px; background:color-mix(in srgb, var(--sec, var(--acento)) 20%, #0C1C10); font-size:1.7rem;
  display:flex; align-items:center; justify-content:center; flex:none; box-shadow:inset 0 0 0 1px color-mix(in srgb, var(--sec, var(--acento)) 35%, #0C1C10); }}
.m3k-cab .marca {{ color:var(--sec, var(--acento)); }}
.m3k-kpi {{ background:linear-gradient(135deg, color-mix(in srgb, var(--tono, #9DB58A) 12%, #0C1C10), #0C1C10 70%); position:relative; padding-right:3.4rem; }}
.m3k-kpi.heroe {{ background:linear-gradient(135deg, color-mix(in srgb, var(--tono, #9DB58A) 22%, #0C1C10), #0C1C10 80%); }}
.m3k-kpi .ic {{ position:absolute; top:.7rem; right:.7rem; width:38px; height:38px; border-radius:50%; font-size:1.2rem;
  background:color-mix(in srgb, var(--tono, #9DB58A) 22%, #0C1C10); display:flex; align-items:center; justify-content:center; }}
[data-testid="stSidebar"] {{ background:linear-gradient(180deg, #07140A 0%, #050D07 100%) !important; }}

.m3k-pagadas {{ background:#12281A; border:1px solid #2A4A2C; color:#B8F53A; border-radius:8px; padding:.45rem .8rem; font-size:.85rem; margin:.2rem 0 .6rem; }}

.m3k-paso {{ display:flex; align-items:center; gap:.65rem; margin:.1rem 0 .6rem; font-size:1.15rem; }}
.m3k-paso span {{ width:30px; height:30px; border-radius:50%; background:var(--acento); color:#0A1A05; font-weight:700; font-size:.95rem;
  display:flex; align-items:center; justify-content:center; flex:none; box-shadow:0 0 0 3px rgba(184,245,58,.15); }}
.m3k-simula {{ background:linear-gradient(135deg,#12281A,#0C1C10 70%); border:1px dashed #2F5A33; border-radius:12px; padding:1.6rem 1.4rem; }}
.m3k-simula .gran {{ font-size:2.6rem; line-height:1; margin-bottom:.4rem; }}
.m3k-simula b {{ font-size:1.15rem; }} .m3k-simula p {{ color:var(--suave); margin:.4rem 0 .3rem; }} .m3k-simula ul {{ margin:0; padding-left:1.1rem; line-height:1.9; }}

/* Tema oscuro forzado: Streamlit Cloud usa la configuración de la raíz del repositorio, así que los colores base se fijan aquí
   para que esta app se vea igual en cualquier despliegue. */
:root {{ color-scheme: dark; }}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] {{ background-color:#050D07 !important; color:var(--texto) !important; }}
/* Fondo: resplandor lima en las esquinas y textura fina de puntos, como en las referencias */
[data-testid="stAppViewContainer"] {{ background-image:
  radial-gradient(ellipse 60% 45% at 100% 0%, rgba(184,245,58,.16), transparent 70%),
  radial-gradient(ellipse 50% 40% at 0% 100%, rgba(120,220,60,.10), transparent 70%),
  radial-gradient(rgba(184,245,58,.07) 1px, transparent 1px) !important;
  background-size:auto, auto, 22px 22px !important; background-attachment:fixed !important; }}
[data-testid="stHeader"] {{ background:transparent !important; }}
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {{ background-image:radial-gradient(ellipse 120% 40% at 0% 0%, rgba(184,245,58,.10), transparent 70%) !important; }}
[data-testid="stSidebar"], [data-testid="stSidebarContent"], [data-testid="stSidebarNav"] {{ background:#07140A !important; border-right:1px solid var(--borde); }}
.stApp, .stApp p, .stApp li, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stWidgetLabel"], .stApp [data-testid="stCaptionContainer"] {{ color:var(--texto); }}
.stApp [data-testid="stCaptionContainer"], .stApp small {{ color:var(--suave) !important; }}
[data-testid="stSidebar"] a, [data-testid="stSidebar"] [data-testid="stSidebarNavLink"] span, [data-testid="stSidebarNavSeparator"] span,
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {{ color:#CFE8B8 !important; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {{ background:#B8F53A !important; font-weight:700; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"], [data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] * {{ color:#0A1A05 !important; }}
[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{ background:#12281A !important; }}
[data-testid="stSidebar"] hr {{ border-color:var(--borde) !important; }}
[data-testid="stSidebarNav"] header span, [data-testid="stSidebarNav"] [data-testid="stNavSectionHeader"], [data-testid="stSidebarNav"] ul li > div > span {{ color:var(--suave) !important; }}
.stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea, div[data-baseweb="select"] > div,
div[data-baseweb="input"], div[data-baseweb="base-input"], [data-testid="stNumberInputContainer"] {{ background:#0C1C10 !important; color:var(--texto) !important; border-color:#2A4A2C !important; }}
[data-testid="stNumberInputContainer"] button {{ background:#12281A !important; color:var(--texto) !important; }}
div[data-baseweb="popover"] ul, div[data-baseweb="menu"], div[data-baseweb="popover"] li, div[data-baseweb="calendar"] {{ background:#0C1C10 !important; color:var(--texto) !important; }}
div[data-baseweb="popover"] li:hover {{ background:#16301A !important; }}
::placeholder {{ color:#6F8A5E !important; opacity:1; }}
.stButton button, .stDownloadButton button, .stFormSubmitButton button {{ background:#0C1C10; color:#CFE8B8; border:1px solid #2A4A2C; }}
.stButton button p, .stButton button span, .stDownloadButton button p, .stFormSubmitButton button p {{ color:inherit !important; }}
button[data-testid^="stBaseButton-secondary"], [data-testid="stFormSubmitButton"] button, [data-testid="stDownloadButton"] button {{ background:#0C1C10 !important; color:#CFE8B8 !important; border:1px solid #2A4A2C !important; }}
button[data-testid^="stBaseButton-secondary"] *, [data-testid="stFormSubmitButton"] button *, [data-testid="stDownloadButton"] button * {{ color:#CFE8B8 !important; }}
button[data-testid^="stBaseButton-secondary"]:hover, [data-testid="stFormSubmitButton"] button:hover, [data-testid="stDownloadButton"] button:hover {{ border-color:var(--acento) !important; background:#12281A !important; }}
.stButton button[kind="primary"], button[data-testid="stBaseButton-primary"], .stFormSubmitButton button[kind="primary"],
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"], [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primaryFormSubmit"] {{
  background:#B8F53A !important; border-color:#B8F53A !important; color:#0A1A05 !important; font-weight:700; }}
.stButton button[kind="primary"] *, button[data-testid="stBaseButton-primary"] *, .stFormSubmitButton button[kind="primary"] *,
[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"] *, [data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primaryFormSubmit"] * {{ color:#0A1A05 !important; }}
.stButton button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]:hover {{ background:#D9FB8C !important; border-color:#D9FB8C !important; }}
.stButton button:disabled {{ opacity:.45; }}
[data-testid="stExpander"] {{ background:#0C1C10; border:1px solid var(--borde); }}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {{ color:var(--texto) !important; }}
[data-baseweb="tab-list"] button, [data-baseweb="tab-list"] button * {{ color:var(--suave) !important; }}
[data-baseweb="tab-list"] button[aria-selected="true"], [data-baseweb="tab-list"] button[aria-selected="true"] * {{ color:var(--acento) !important; font-weight:700; }}
[data-testid="stRadio"] label, [data-testid="stRadio"] label * {{ color:var(--texto) !important; }}
[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked), [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) * {{ color:#0A1A05 !important; }}
[data-testid="stForm"] {{ border:1px solid var(--borde); background:var(--fondo); }}
[data-testid="stAlert"] {{ border:1px solid #2A4A2C; background:#0F2412 !important; }}
[data-testid="stAlert"], [data-testid="stAlert"] * {{ color:var(--texto) !important; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-color:var(--borde) !important; }}
hr {{ border-color:var(--borde) !important; }}
code {{ background:#16301A !important; color:#D9FB8C !important; }}

.stApp .m3k-recibo, .stApp .m3k-recibo * {{ color:#0A1A05; }} .stApp .m3k-recibo .anul {{ color:#B3261E; }} .stApp .m3k-recibo small {{ color:#3E5A2A !important; }}

/* ---- Correcciones de visibilidad: todo control con fondo oscuro y texto claro ---- */
div[data-baseweb="select"], div[data-baseweb="select"] * {{ background-color:#0C1C10 !important; color:#F2FBE8 !important; border-color:#2A4A2C !important; }}
div[data-baseweb="select"] svg {{ fill:#B8F53A !important; }}
div[data-baseweb="select"] > div:hover {{ border-color:#B8F53A !important; }}
[data-testid="stDateInput"] *, [data-testid="stDateInputField"], [data-baseweb="datepicker"] * {{ background-color:#0C1C10 !important; color:#F2FBE8 !important; border-color:#2A4A2C !important; }}
[data-testid="stDateInput"] svg {{ fill:#B8F53A !important; }}
[data-testid="stDateInput"] input::placeholder {{ color:#9DB58A !important; }}
[data-baseweb="popover"], [data-baseweb="popover"] > div, [data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="calendar"], [data-baseweb="calendar"] * {{ background-color:#0C1C10 !important; color:#F2FBE8 !important; }}
[data-baseweb="popover"] {{ border:1px solid #2A4A2C; border-radius:10px; }}
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] li[aria-selected="true"] {{ background-color:#16301A !important; color:#B8F53A !important; }}
[data-baseweb="calendar"] [aria-selected="true"], [data-baseweb="calendar"] [aria-selected="true"] * {{ background-color:#B8F53A !important; color:#0A1A05 !important; }}
[data-testid="stFileUploaderDropzone"], [data-testid="stFileUploaderDropzone"] * {{ background-color:#0C1C10 !important; color:#CFE8B8 !important; }}
[data-testid="stFileUploaderDropzone"] {{ border:1.5px dashed #2F5A33 !important; border-radius:12px; transition:border-color .2s ease, box-shadow .2s ease; }}
[data-testid="stFileUploaderDropzone"]:hover {{ border-color:#B8F53A !important; box-shadow:0 0 18px rgba(184,245,58,.12); }}
[data-testid="stFileUploaderDropzone"] button {{ background-color:#B8F53A !important; color:#0A1A05 !important; }}
[data-testid="stFileUploaderDropzone"] button * {{ background-color:transparent !important; color:#0A1A05 !important; }}
[data-testid="stAlert"], [data-testid="stAlertContainer"], [data-baseweb="notification"], [role="alert"] {{ background-color:#0F2412 !important; color:#F2FBE8 !important; border:1px solid #2F5A33 !important; border-left:4px solid #B8F53A !important; border-radius:10px; }}
[data-testid="stAlert"] *, [data-baseweb="notification"] * {{ background-color:transparent !important; color:#F2FBE8 !important; }}
[data-testid="stAlert"] svg {{ fill:#B8F53A !important; }}
[data-testid="stException"], [data-testid="stNotification"] {{ background:#0F2412 !important; }}

/* Iconos: fichas claras para que se vean sobre fondo oscuro */
.m3k-cab .ico {{ background:#B8F53A !important; box-shadow:0 0 0 4px rgba(184,245,58,.14), 0 0 22px rgba(184,245,58,.25) !important; }}
.m3k-kpi .ic {{ background:#DDF7A8 !important; box-shadow:0 0 0 3px rgba(184,245,58,.14); }}
.m3k-modo .ico {{ background:#DDF7A8 !important; }} .m3k-modo.sel .ico {{ background:#B8F53A !important; }}
.m3k-cliente .av {{ background:#B8F53A !important; color:#0A1A05 !important; }}
.m3k-simula .gran {{ display:inline-flex; width:64px; height:64px; border-radius:18px; background:#DDF7A8; align-items:center; justify-content:center; font-size:2rem; }}

/* Barras y pistas: más contraste sobre las tarjetas */
.m3k-barra, .m3k-avance .pista, .m3k-dia .nivel, .m3k-cascada .pista, .m3k-reparto .barra {{ background:#2F5A33 !important; }}
.m3k-sem i.esp, .leyenda i.esp {{ background:#5E9B4A !important; }}
.m3k-sem .barras {{ border-bottom:1px solid #4A7A44 !important; }}
.m3k-dona circle[stroke="#1E3A1F"] {{ stroke:#2F5A33; }}
.m3k-panel svg line {{ stroke:#2F5A33 !important; }}

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
[data-testid="stExpander"] {{ transition:border-color .2s ease; }} [data-testid="stExpander"]:hover {{ border-color:#2F5A33; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ transition:border-color .2s ease, box-shadow .2s ease; }}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{ box-shadow:0 0 24px rgba(184,245,58,.06); }}

/* Acceso: tarjeta central con marca y tres razones para entrar */
.m3k-login {{ max-width:460px; margin:1.2rem auto .8rem; text-align:center; position:relative; }}
.m3k-login::before {{ content:''; position:absolute; left:50%; top:-60px; width:520px; height:360px; transform:translateX(-50%); z-index:-1;
  background:radial-gradient(ellipse at center, rgba(184,245,58,.28), transparent 65%); pointer-events:none; }}
.m3k-login .logo {{ width:76px; height:76px; border-radius:22px; background:#B8F53A; color:#0A1A05; font-size:2.3rem;
  display:flex; align-items:center; justify-content:center; margin:0 auto 1rem; box-shadow:0 0 0 8px rgba(184,245,58,.12); }}
.m3k-login .marca {{ font-size:.74rem; letter-spacing:.16em; color:#B8F53A; font-weight:700; }}
.m3k-login h1 {{ font-size:2rem; margin:.25rem 0 .3rem; color:#F2FBE8; }}
.m3k-login p {{ color:var(--suave); margin:0 0 1.1rem; }}
.m3k-login .pasos {{ display:grid; grid-template-columns:repeat(3,1fr); gap:.6rem; margin:0 0 1rem; }}
.m3k-login .pasos div {{ background:#0C1C10; border:1px solid var(--borde); border-radius:12px; padding:.7rem .4rem; font-size:.78rem; color:#CFE8B8; }}
.m3k-login .pasos span {{ display:block; font-size:1.4rem; margin-bottom:.2rem; }}
.st-key-acceso_form {{ max-width:460px; margin:0 auto; }}

/* Modalidades: tarjetas con icono y ejemplo */
.m3k-modos {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:.7rem; margin:.2rem 0 1rem; }}
.m3k-modo {{ background:var(--fondo); border:1px solid var(--borde); border-radius:12px; padding:.85rem 1rem; }}
.m3k-modo.sel {{ border:1.5px solid #B8F53A; background:#12281A; }}
.m3k-modo .ico {{ width:40px; height:40px; border-radius:11px; background:#16301A; display:flex; align-items:center; justify-content:center; font-size:1.3rem; margin-bottom:.5rem; }}
.m3k-modo.sel .ico {{ background:#B8F53A; }}
.m3k-modo b {{ font-size:1.02rem; }} .m3k-modo .sub {{ color:var(--suave); font-size:.8rem; margin:.1rem 0 .5rem; }}
.m3k-modo ul {{ list-style:none; margin:0; padding:0; font-size:.84rem; color:#CFE8B8; line-height:1.7; }}
.m3k-modo .ej {{ margin-top:.5rem; padding-top:.45rem; border-top:1px dashed var(--borde); font-size:.8rem; color:var(--suave); }}
.m3k-modo .ej strong {{ color:#B8F53A; }}
</style>
"""


def aplicar() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# icono y color de cada pantalla (el color agrupa por sección: operación lima, contabilidad celeste, control ámbar)
SECCIONES = {
    "Control de cartera": ("🏠", "#B8F53A"), "Registrar cobro": ("💵", "#B8F53A"), "Préstamos": ("💰", "#B8F53A"), "Clientes": ("👥", "#B8F53A"),
    "Resultados": ("📊", "#6CC4E8"), "Cuentas por cobrar": ("🧾", "#6CC4E8"), 
    "Caja": ("🏦", "#F2B84B"), "Recibos": ("🧾", "#F2B84B"), "Configuración": ("⚙️", "#9DB58A"),
}


def encabezado(titulo: str, subtitulo: str = "") -> None:
    sub = f"<p>{esc(subtitulo)}</p>" if subtitulo else ""
    icono, color = SECCIONES.get(titulo, ("💼", ACENTO))
    st.markdown(f'<div class="m3k-cab" style="--sec:{color}"><div class="ico">{icono}</div><div><div class="marca">M3K · Préstamos personales</div>'
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
          sin_corte: tuple[int, ...] = ()) -> None:
    """Tabla HTML con cabecera fija, desplazamiento propio y fila de totales opcional.

    Cada fila es una lista de celdas, o un dict {"celdas": [...], "clase": "cab"|"sub"} para filas de agrupación.
    Si una fila trae menos celdas que columnas, su última celda ocupa el resto del ancho (útil para títulos de asiento).
    Las celdas se escapan salvo que sean `Raw`. Una celda que empieza con dos espacios se muestra con sangría.
    `sin_corte` lista las columnas cuyo texto nunca se parte en dos líneas (fechas, números, cuentas).
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
        return f'<td class="{" ".join(clases)}"{span}>{texto}</td>'

    cab = "".join(f'<th class="{"n" if i in numericas else ""}">{esc(c)}</th>' for i, c in enumerate(columnas))
    cuerpo = []
    for fila in filas:
        celdas, clase = (fila["celdas"], fila.get("clase", "")) if isinstance(fila, dict) else (fila, "")
        resto = len(columnas) - len(celdas) + 1
        partes = [celda(i, c, resto if i == len(celdas) - 1 else 1) for i, c in enumerate(celdas)]
        cuerpo.append(f'<tr class="{clase}">' + "".join(partes) + "</tr>")
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


def acceso_cabecera() -> None:
    """Marca y razones para entrar, sobre el formulario de la clave."""
    st.markdown('<div class="m3k-login"><div class="logo">💰</div><div class="marca">M3K · PRÉSTAMOS</div>'
                '<h1>Tu cartera, clara y al día</h1><p>Ingresa tu clave para continuar.</p>'
                '<div class="pasos"><div><span>💵</span>Cobros del día</div><div><span>📒</span>Cartera y clientes</div>'
                '<div><span>🧾</span>Recibos</div></div></div>', unsafe_allow_html=True)
