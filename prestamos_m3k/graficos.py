"""Gráficos en HTML, SVG y CSS puros: se ven igual en cualquier despliegue, no necesitan librerías y se animan con CSS.

Cada función devuelve un texto HTML de una sola línea (Markdown trata las líneas en blanco como fin de bloque).
Las animaciones están en estilos.py y se desactivan solas si el sistema pide «reducir movimiento».
"""

from __future__ import annotations

import math

import estilos as ui

DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
# de «al día» (verde) a «muy atrasado» (rojo)
COLORES_GRAVEDAD = ["#1E7B4B", "#C48A1A", "#A8600A", "#C2571A", "#B3261E", "#7A1712"]


def _una_linea(html: str) -> str:
    return "".join(linea.strip() for linea in html.splitlines())


def _corto(valor: float) -> str:
    """S/ 1,250 -> «1.3 mil»; los montos chicos se muestran completos."""
    if abs(valor) >= 10000:
        return f"{valor / 1000:.0f} mil"
    if abs(valor) >= 1000:
        return f"{valor / 1000:.1f} mil"
    return f"{valor:,.0f}"


def _dm(dia) -> str:
    return f"{dia.day} {MESES[dia.month - 1]}"


def panel(titulo: str, cuerpo: str, pie: str = "") -> str:
    pie_html = f'<div class="pie">{ui.esc(pie)}</div>' if pie else ""
    return _una_linea(f'<div class="m3k-panel"><div class="t">{ui.esc(titulo)}</div>{cuerpo}{pie_html}</div>')


def avance(cobrado: float, esperado: float, mes: str = "", detalle: str | None = None) -> str:
    """Barra de avance: «S/ 360 cobrados de S/ 540 que vencen en noviembre» (o con el `detalle` que se indique)."""
    detalle = detalle if detalle is not None else f"que vencen en {mes}"
    pct = 0 if not esperado else min(100.0, cobrado / esperado * 100)
    return _una_linea(f'''
      <div class="m3k-avance">
        <div class="cab"><div><b class="num">{ui.soles(cobrado)}</b> cobrados de <span class="num">{ui.soles(esperado)}</span> {ui.esc(detalle)}</div>
        <strong class="num">{pct:.0f} %</strong></div>
        <div class="pista" role="img" aria-label="{pct:.0f} % cobrado"><i style="width:{pct:.1f}%"></i></div>
      </div>''')


def proximos_dias(dias: list[dict], hoy) -> str:
    """Una tarjeta por día de trabajo con lo que vence; la altura de la barrita compara un día con otro."""
    mayor = max((d["monto"] for d in dias), default=0)
    tarjetas = []
    for i, d in enumerate(dias):
        if d["fecha"] == hoy:
            rotulo = "Hoy"
        elif (d["fecha"] - hoy).days == 1:
            rotulo = "Mañana"
        else:
            rotulo = DIAS[d["fecha"].weekday()].capitalize()
        clase = "m3k-dia" + (" hoy" if d["fecha"] == hoy else "") + ("" if d["monto"] else " vacio")
        nivel = (d["monto"] / mayor * 100) if mayor else 0
        detalle = f'{d["cuotas"]} cuota(s)' if d["cuotas"] else "Sin cobros"
        tarjetas.append(
            f'<div class="{clase}" style="animation-delay:{i * 0.06:.2f}s"><div class="d">{ui.esc(rotulo)} · {_dm(d["fecha"])}</div>'
            f'<div class="m num">{ui.soles(d["monto"]) if d["monto"] else "—"}</div><div class="n">{detalle}</div>'
            f'<div class="nivel"><i style="width:{nivel:.0f}%"></i></div></div>')
    return f'<div class="m3k-dias">{"".join(tarjetas)}</div>'


def semanas(datos: list[dict]) -> str:
    """Barras por semana: lo que vencía (gris) frente a lo ya cobrado (verde)."""
    mayor = max((s["esperado"] for s in datos), default=0) or 1
    cols = []
    for i, s in enumerate(datos):
        h_esp = max(3, s["esperado"] / mayor * 100) if s["esperado"] else 0
        h_cob = max(3, s["cobrado"] / mayor * 100) if s["cobrado"] else 0
        titulo = f'Semana del {_dm(s["desde"])}: vencían {ui.soles(s["esperado"])}, cobrado {ui.soles(s["cobrado"])}'
        cols.append(
            f'<div class="c{" act" if s["actual"] else ""}" title="{ui.esc(titulo)}"><div class="barras">'
            f'<i class="esp" style="height:{h_esp:.0f}%;animation-delay:{i * 0.07:.2f}s"></i>'
            f'<i class="cob" style="height:{h_cob:.0f}%;animation-delay:{i * 0.07 + 0.12:.2f}s"></i></div>'
            f'<span class="rot">{"Esta sem." if s["actual"] else _dm(s["desde"])}</span>'
            f'<span class="val num">{_corto(s["cobrado"])} / {_corto(s["esperado"])}</span></div>')
    leyenda = '<div class="leyenda"><span><i class="esp"></i>Vencía</span><span><i class="cob"></i>Cobrado</span></div>'
    return f'<div class="m3k-sem" style="grid-template-columns:repeat({max(1, len(datos))},minmax(0,1fr))">{"".join(cols)}</div>{leyenda}'


def dona(segmentos: list[dict], centro: str, centro_sub: str) -> str:
    """Anillo con la cartera por antigüedad, más la lista de cada tramo con su monto y porcentaje."""
    total = sum(s["monto"] for s in segmentos) or 1
    r = 46
    c = 2 * math.pi * r
    aros, acum, items = [], 0.0, []
    for i, s in enumerate(segmentos):
        largo = s["monto"] / total * c
        color = s.get("color") or COLORES_GRAVEDAD[min(s.get("gravedad", 0), len(COLORES_GRAVEDAD) - 1)]
        aros.append(f'<circle class="seg" cx="60" cy="60" r="{r}" fill="none" stroke="{color}" stroke-width="16" transform="rotate(-90 60 60)" '
                    f'style="stroke-dasharray:{largo:.2f} {c - largo:.2f};stroke-dashoffset:{-acum:.2f};--c:{c:.2f};animation-delay:{i * 0.12:.2f}s"/>')
        acum += largo
        etiqueta = s.get("etiqueta") or (s["nombre"] if s.get("gravedad", 0) == 0 else f'Atraso {s["nombre"]}')
        items.append(f'<li><i style="background:{color}"></i><span>{ui.esc(etiqueta)}</span><b class="num">{ui.soles(s["monto"])}</b>'
                     f'<em>{s["monto"] / total * 100:.0f} %</em></li>')
    svg = (f'<svg viewBox="0 0 120 120" width="150" height="150" role="img" aria-label="Cartera por antigüedad">'
           f'<circle cx="60" cy="60" r="{r}" fill="none" stroke="#E6ECE8" stroke-width="16"/>{"".join(aros)}'
           f'<text x="60" y="58" text-anchor="middle" class="dc">{ui.esc(centro)}</text>'
           f'<text x="60" y="73" text-anchor="middle" class="ds">{ui.esc(centro_sub)}</text></svg>')
    return f'<div class="m3k-dona">{svg}<ul>{"".join(items)}</ul></div>'


def linea(serie: list[tuple]) -> str:
    """Línea del saldo de caja día a día. Sin ejes ni números sueltos: se leen los extremos debajo."""
    valores = [v for _, v in serie]
    menor, mayor = min(valores), max(valores)
    rango = (mayor - menor) or 1
    n = max(1, len(serie) - 1)
    pts = [(i / n * 600, 125 - (v - menor) / rango * 105 if mayor != menor else 70) for i, (_, v) in enumerate(serie)]
    trazo = " ".join(f'{"M" if i == 0 else "L"}{x:.1f} {y:.1f}' for i, (x, y) in enumerate(pts))
    area = f"{trazo} L600 140 L0 140 Z"
    rejilla = "".join(f'<line x1="0" x2="600" y1="{y}" y2="{y}" stroke="#E6ECE8" stroke-width="1" vector-effect="non-scaling-stroke"/>' for y in (20, 70, 125))
    svg = (f'<svg class="lin" viewBox="0 0 600 140" preserveAspectRatio="none" role="img" aria-label="Saldo de caja de los últimos días">{rejilla}'
           f'<g class="revela"><path d="{area}" fill="#1E7B4B" fill-opacity=".10"/>'
           f'<path d="{trazo}" fill="none" stroke="#1E7B4B" stroke-width="2.2" stroke-linejoin="round" vector-effect="non-scaling-stroke"/></g></svg>')
    ini, fin = serie[0], serie[-1]
    pie = (f'<div class="extremos"><span>{_dm(ini[0])}<b class="num">{ui.soles(ini[1])}</b></span>'
           f'<span class="mm">Mín {ui.soles(menor)} · Máx {ui.soles(mayor)}</span>'
           f'<span class="der">Hoy<b class="num">{ui.soles(fin[1])}</b></span></div>')
    return f"{svg}{pie}"


def reparto(partes: list[tuple[str, float, str]]) -> str:
    """Una sola barra dividida en partes (nombre, monto, color), con la lista de cada parte debajo."""
    total = sum(m for _, m, _ in partes) or 1
    trozos = "".join(f'<i style="width:{m / total * 100:.2f}%;background:{c}" title="{ui.esc(n)}"></i>' for n, m, c in partes if m)
    leyenda = "".join(
        f'<li><i style="background:{c}"></i><span>{ui.esc(n)}</span><b class="num">{ui.soles(m)}</b><em>{m / total * 100:.0f} %</em></li>' for n, m, c in partes)
    return f'<div class="m3k-reparto"><div class="barra" role="img" aria-label="Reparto de lo cobrado">{trozos}</div><ul>{leyenda}</ul></div>'


def columnas(datos: list[tuple[str, float, bool]], vacio_txt: str = "") -> str:
    """Una columna por periodo (rótulo, monto, resaltada). El monto va sobre la columna, así una sola barra no parece un bloque sin sentido."""
    mayor = max((v for _, v, _ in datos), default=0) or 1
    cols = []
    for i, (rotulo, valor, resaltar) in enumerate(datos):
        alto = max(3, valor / mayor * 100) if valor else 0
        cols.append(
            f'<div class="c{" act" if resaltar else ""}" title="{ui.esc(rotulo)}: {ui.soles(valor)}"><div class="barras">'
            f'{f'<div class="col" style="height:{alto:.0f}%"><span class="val num">{_corto(valor)}</span><i class="cob" style="animation-delay:{i * 0.06:.2f}s"></i></div>' if valor else ""}'
            f'</div><span class="rot">{ui.esc(rotulo)}</span></div>')
    return f'<div class="m3k-sem una" style="grid-template-columns:repeat({max(1, len(datos))},minmax(0,1fr))">{"".join(cols)}</div>'


def cascada(filas: list[tuple[str, float, str]]) -> str:
    """Cómo se formó un saldo: filas (nombre, monto, tipo) con tipo «mas», «menos» o «total»; la longitud de cada barra compara los montos."""
    mayor = max((abs(m) for _, m, _ in filas), default=0) or 1
    colores = {"mas": ui.TONOS["ok"], "menos": ui.TONOS["aviso"], "total": ui.TONOS["info"]}
    out = []
    for i, (nombre, monto, tipo) in enumerate(filas):
        ancho = max(1.5, abs(monto) / mayor * 100) if monto else 0
        signo = {"mas": "+ ", "menos": "− ", "total": ""}[tipo]
        out.append(
            f'<div class="fila {tipo}"><span class="n">{ui.esc(nombre)}</span>'
            f'<div class="pista"><i style="width:{ancho:.1f}%;background:{colores[tipo]};animation-delay:{i * 0.07:.2f}s"></i></div>'
            f'<b class="num">{signo}{ui.soles(abs(monto))}</b></div>')
    return f'<div class="m3k-cascada">{"".join(out)}</div>'


def cuotas(lista: list[dict]) -> str:
    """Una tarjeta por cuota (n, vence, monto, pagado, estado, atraso), con el color de su estado y lo pagado como barra."""
    tarjetas = []
    for i, c in enumerate(lista):
        nombre, tono = ui.ESTADOS_CUOTA.get(c["estado"], (c["estado"], "neutro"))
        color = ui.TONOS[tono]
        pct = min(100.0, c["pagado"] / c["monto"] * 100) if c["monto"] else 0
        if c["estado"] == "vencida" and c.get("atraso"):
            nota = f'{c["atraso"]} días de atraso'
        elif c["estado"] == "parcial":
            nota = f'Pagado {ui.soles(c["pagado"])}'
        else:
            nota = nombre
        tarjetas.append(
            f'<div class="m3k-dia" style="border-top:3px solid {color};animation-delay:{min(i * 0.025, 0.5):.2f}s"><div class="d">Cuota {c["n"]}</div>'
            f'<div class="m num">{ui.soles(c["monto"])}</div><div class="n">{ui.esc(ui.fecha_dia(c["vence"]))}</div>'
            f'<div class="n" style="color:{color};font-weight:600">{ui.esc(nota)}</div>'
            f'<div class="nivel"><i style="width:{pct:.0f}%;background:{color}"></i></div></div>')
    return f'<div class="m3k-dias cuotas">{"".join(tarjetas)}</div>'
