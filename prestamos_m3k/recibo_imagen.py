"""Recibo como imagen PNG (para mandarlo por WhatsApp). Usa los mismos datos que la pantalla y el PDF."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_FUENTES = Path(__file__).parent / "assets" / "fuentes"
ANCHO, MARGEN, BORDE = 960, 72, 6
FONDO, TINTA, SUAVE, LIMA, LINEA, ROJO, VERDE = "#F4F4F2", "#0A1A05", "#4A4F45", "#B8F53A", "#8C9488", "#B3261E", "#1F6B4F"


def _fuente(peso: str, tam: int) -> ImageFont.FreeTypeFont:
    for nombre in (f"Inter-{peso}.otf",):
        try:
            return ImageFont.truetype(str(_FUENTES / nombre), tam)
        except OSError:
            pass
    try:  # por si la fuente incluida no cargara
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if peso == "Bold" else "DejaVuSans.ttf", tam)
    except OSError:
        return ImageFont.load_default()


def _ajustar(dib: ImageDraw.ImageDraw, texto: str, fuente, ancho: int) -> list[str]:
    """Parte el texto en líneas que quepan en `ancho`."""
    lineas, actual = [], ""
    for palabra in str(texto).split():
        prueba = f"{actual} {palabra}".strip()
        if dib.textlength(prueba, font=fuente) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas or [""]


def generar(d: dict) -> bytes:
    """PNG del recibo. `d` es el diccionario de `_datos_recibo` (titulo, folio, bloque1, bloque2, cronograma...)."""
    f_marca, f_tit, f_txt, f_fuerte, f_tabla = _fuente("Bold", 22), _fuente("Bold", 58), _fuente("Regular", 30), _fuente("Bold", 36), _fuente("Regular", 29)
    f_tabla_b = _fuente("Bold", 29)
    util = ANCHO - 2 * MARGEN
    medida = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    def filas(items, fuerte_por_fila: bool):
        """Calcula las líneas de cada fila (etiqueta a la izquierda, valor alineado a la derecha)."""
        res = []
        for it in items:
            etq, val = it[0], it[1]
            fuerte = it[2] if fuerte_por_fila else False
            fnt = f_fuerte if fuerte else f_txt
            ancho_etq = medida.textlength(etq, font=fnt)
            lineas = _ajustar(medida, val, fnt, max(120, int(util - ancho_etq - 36)))
            res.append((etq, lineas, fnt, fuerte))
        return res

    b1, b2 = filas(d["bloque1"], False), filas(d["bloque2"], True)
    alto_fila = lambda fnt, n: int(fnt.size * 1.5) * n + 10
    cuerpo = 40 + 60 + 70 + 40 + (60 if d["anulado"] else 0) + (96 if d.get("cancelado") else 0)
    cuerpo += 34 + sum(alto_fila(f, len(l)) for _, l, f, _ in b1) + 34 + sum(alto_fila(f, len(l)) for _, l, f, _ in b2) + 34
    if d["cronograma"]:
        cuerpo += 56 + 64 * (len(d["cronograma"]) + 1) + 30
    alto = cuerpo + 2 * 40

    img = Image.new("RGB", (ANCHO + 48, alto + 48), "#FFFFFF")
    dib = ImageDraw.Draw(img)
    dib.rounded_rectangle((24, 24, 24 + ANCHO, 24 + alto), radius=40, fill=FONDO, outline=LIMA, width=BORDE)
    x0, x1, y = 24 + MARGEN, 24 + ANCHO - MARGEN, 24 + 64

    dib.text((x0, y), "M3K · PRÉSTAMOS PERSONALES", font=f_marca, fill="#3F7A00")
    y += 44
    dib.text((x0, y), d["titulo"], font=f_tit, fill=TINTA)
    y += 84
    dib.text((x0, y), d["folio"], font=f_txt, fill=SUAVE)
    y += 52
    if d["anulado"]:
        dib.text((x0, y), "ANULADO" + (f" — {d['motivo']}" if d["motivo"] else ""), font=f_fuerte, fill=ROJO)
        y += 60
    if d.get("cancelado"):
        texto = "PRÉSTAMO CANCELADO"
        ancho_t = dib.textlength(texto, font=f_fuerte)
        dib.rounded_rectangle((x0, y, x1, y + 76), radius=18, fill="#E4F5D2", outline=VERDE, width=4)
        dib.text((x0 + (x1 - x0 - ancho_t) / 2, y + 16), texto, font=f_fuerte, fill=VERDE)
        y += 96

    def punteada(yy):
        xx = x0
        while xx < x1:
            dib.line((xx, yy, min(xx + 10, x1), yy), fill=LINEA, width=2)
            xx += 18

    def bloque(items, yy):
        for etq, lineas, fnt, fuerte in items:
            dib.text((x0, yy), etq, font=fnt, fill=TINTA if fuerte else TINTA)
            for ln in lineas:
                dib.text((x1 - dib.textlength(ln, font=fnt), yy), ln, font=fnt, fill=TINTA)
                yy += int(fnt.size * 1.5)
            yy += 10
        return yy

    punteada(y)
    y = bloque(b1, y + 22) + 12
    punteada(y)
    y = bloque(b2, y + 22) + 12
    if d["cronograma"]:
        punteada(y)
        y += 26
        dib.text((x0, y), "Cronograma", font=f_fuerte, fill=TINTA)
        y += 56
        cols = [x0, x0 + 110, x0 + 110 + 470, x1]
        filas_t = [("N.º", "Vence", "Cuota")] + list(d["cronograma"])
        for i, (n, fch, monto) in enumerate(filas_t):
            top, bot = y + i * 64, y + (i + 1) * 64
            if i == 0:
                dib.rectangle((cols[0], top, cols[3], bot), fill="#E3E8DF")
            dib.rectangle((cols[0], top, cols[3], bot), outline=LINEA, width=2)
            for cx in cols[1:3]:
                dib.line((cx, top, cx, bot), fill=LINEA, width=2)
            fnt = f_tabla_b if i == 0 else f_tabla
            ty = top + (64 - fnt.size) // 2 - 4
            dib.text((cols[0] + 18, ty), n, font=fnt, fill=TINTA)
            dib.text((cols[1] + 18, ty), fch, font=fnt, fill=TINTA)
            dib.text((cols[3] - 18 - dib.textlength(monto, font=fnt), ty), monto, font=fnt, fill=TINTA)

    salida = io.BytesIO()
    img.save(salida, format="PNG", optimize=True)
    return salida.getvalue()
