"""Bloques de KPI en HTML con el estilo del tema (para las páginas adicionales)."""

from tema import ICONOS, TONOS, tinte


def estilo_tono(color):
    tono = TONOS[color]
    return (f"--tone:{tono};--tone-bg:{tinte(tono, 0.12)};"
            f"--tone-borde:{tinte(tono, 0.45)}")


def item_kpi(titulo, valor, color, alerta=False, lineas=None, unidad="informe"):
    clase = "kpi-item alerta" if alerta and valor else "kpi-item"
    if isinstance(valor, str):
        detalle = "del total"
    else:
        detalle = unidad + ("" if valor == 1 else "s")
    if lineas is not None:
        detalle += f" · {lineas} línea{'' if lineas == 1 else 's'}"
    return (
        f"<div class='{clase}' style='{estilo_tono(color)}'>"
        f"<div class='kpi-item-label'><span class='kpi-dot'></span>{titulo}</div>"
        f"<div class='kpi-item-value'>{valor}"
        f"<span class='kpi-item-lineas'>{detalle}</span></div></div>"
    )


def barra_avance(pct, color="verde"):
    tono = TONOS[color]
    return (
        f"<div style='height:8px;border-radius:6px;background:{tinte(tono, 0.18)};"
        f"margin:2px 4px 10px'><div style='height:8px;border-radius:6px;"
        f"width:{min(pct, 100):.1f}%;background:{tono}'></div></div>"
    )


def bloque_kpi(titulo, icono, color, items, extra_html=""):
    filas = "".join(item_kpi(*i) for i in items)
    return (
        "<div class='kpi-block-card'>"
        f"<div class='kpi-block-head' style='{estilo_tono(color)}'>"
        f"<div class='kpi-block-icon'>{ICONOS[icono]}</div>"
        f"<div class='kpi-block-title'>{titulo}</div></div>"
        f"<div class='kpi-items'>{extra_html}{filas}</div></div>"
    )
