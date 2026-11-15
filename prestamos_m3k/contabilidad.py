"""Contabilidad de M3K: libro diario, mayor, balance de comprobación, estados financieros,
cuentas por cobrar y cierres mensuales.

Todo se deriva de los registros operativos (créditos, cobros y movimientos de caja): no hay
una segunda base de datos que pueda descuadrarse. Los importes se operan en céntimos (enteros).

Método (interés plano, devengado en el tiempo):
- Desembolso:   Debe 121 Cartera (capital + interés)   Haber 101 Caja (capital)   Haber 129 Intereses no devengados (interés)
- Cobro:        Debe 101 Caja                           Haber 121 Cartera (cuota)  Haber 702 Mora
- Devengo (fin de mes): Debe 129 Intereses no devengados  Haber 701 Ingresos por intereses.
  El interés de cada crédito se reconoce en forma lineal entre el desembolso y su última cuota; si el cliente
  cancela antes, el interés restante se reconoce al cancelar.
- Una anulación no borra nada: genera un asiento de reversión con la fecha en que se anuló.
No incluye estimaciones por incobrabilidad (provisiones) ni impuestos.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta

import calculos as calc

# código: (nombre, naturaleza "D" deudora / "A" acreedora, rubro)
CUENTAS = {
    "101": ("Caja y bancos", "D", "activo"),
    "121": ("Cartera de créditos", "D", "activo"),
    "129": ("Intereses no devengados", "A", "activo"),  # se resta de la cartera
    "301": ("Capital aportado", "A", "patrimonio"),
    "302": ("Retiros de capital", "D", "patrimonio"),
    "601": ("Gastos operativos", "D", "gasto"),
    "701": ("Ingresos por intereses", "A", "ingreso"),
    "702": ("Ingresos por mora", "A", "ingreso"),
}
ORDEN_TIPO = {"apertura": 0, "desembolso": 1, "cobro": 2, "movimiento": 3, "devengo": 4, "reversion": 5}


# ───────────────────────── periodos ─────────────────────────

def periodo_de(valor) -> str:
    d = calc.fecha(valor)
    return f"{d.year}-{d.month:02d}"


def primer_dia(periodo: str) -> date:
    anio, mes = periodo.split("-")
    return date(int(anio), int(mes), 1)


def ultimo_dia(periodo: str) -> date:
    d = primer_dia(periodo)
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def siguiente(periodo: str) -> str:
    return periodo_de(ultimo_dia(periodo) + timedelta(days=1))


def anterior(periodo: str) -> str:
    return periodo_de(primer_dia(periodo) - timedelta(days=1))


def meses(desde: str, hasta: str) -> list[str]:
    lista, p = [], desde
    while p <= hasta:
        lista.append(p)
        p = siguiente(p)
    return lista


def nombre_mes(periodo: str) -> str:
    nombres = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
               "setiembre", "octubre", "noviembre", "diciembre")
    d = primer_dia(periodo)
    return f"{nombres[d.month - 1].capitalize()} {d.year}"


# ───────────────────────── devengo de intereses ─────────────────────────

def _cancelacion(prestamo: dict, pagos: list[dict]) -> date | None:
    """Fecha en que los cobros vigentes completan el total del crédito (None si sigue con saldo)."""
    total_c = calc.a_centimos(prestamo["total"])
    acumulado = 0
    for p in sorted((p for p in pagos if p["prestamo_id"] == prestamo["id"] and not p.get("anulado")),
                    key=lambda p: (p["fecha"], p["folio"])):
        acumulado += calc.a_centimos(p["monto_cuota"])
        if acumulado >= total_c:
            return calc.fecha(p["fecha"])
    return None


def _devengado_c(prestamo: dict, f_corte: date, cancelacion: date | None) -> int:
    interes_c = calc.a_centimos(prestamo["total"]) - calc.a_centimos(prestamo["monto"])
    f0 = calc.fecha(prestamo["fecha_desembolso"])
    final = calc.fecha(prestamo["cuotas"][-1]["vence"])
    if f_corte <= f0:
        return 0
    if f_corte >= final or (cancelacion and f_corte >= cancelacion):
        return interes_c
    return round(interes_c * (f_corte - f0).days / (final - f0).days)


# ───────────────────────── libro diario ─────────────────────────

def fecha_apertura(db: dict, hoy_=None) -> date:
    configurada = db["config"].get("fecha_apertura")
    if configurada:
        return calc.fecha(configurada)
    fechas = ([calc.fecha(p["fecha_desembolso"]) for p in db["prestamos"]]
              + [calc.fecha(p["fecha"]) for p in db["pagos"]]
              + [calc.fecha(m["fecha"]) for m in db["movimientos"]])
    return min(fechas) if fechas else calc.fecha(hoy_ or calc.hoy())


def _asiento(f: date, glosa: str, ref: str, tipo: str, categoria: str, lineas: list[tuple[str, int, int]],
             provisional: bool = False) -> dict:
    lineas = [(c, d, h) for c, d, h in lineas if d or h]
    assert sum(d for _, d, _ in lineas) == sum(h for _, _, h in lineas), f"Asiento descuadrado: {glosa}"
    return {"fecha": f, "glosa": glosa, "ref": ref, "tipo": tipo, "categoria": categoria,
            "lineas": lineas, "provisional": provisional}


def _invertir(a: dict, f: date) -> dict:
    return _asiento(f, "Reversión: " + a["glosa"], a["ref"] + " (anulado)", "reversion", a["categoria"],
                    [(c, h, d) for c, d, h in a["lineas"]])


def asientos(db: dict, hasta=None, hoy_=None) -> list[dict]:
    """Libro diario completo hasta `hasta` (por defecto hoy), numerado de forma estable."""
    hoy_ = calc.fecha(hoy_ or calc.hoy())
    hasta = calc.fecha(hasta or hoy_)
    clientes = {c["id"]: c["nombre"] for c in db["clientes"]}
    prestamos = {p["id"]: p for p in db["prestamos"]}
    lista: list[dict] = []

    base_c = calc.a_centimos(db["config"].get("capital_base", 0))
    if base_c > 0:
        lista.append(_asiento(fecha_apertura(db, hoy_), "Capital base inicial", "APERTURA", "apertura", "aporte",
                              [("101", base_c, 0), ("301", 0, base_c)]))

    for pr in db["prestamos"]:
        total_c, monto_c = calc.a_centimos(pr["total"]), calc.a_centimos(pr["monto"])
        a = _asiento(calc.fecha(pr["fecha_desembolso"]),
                     f"Desembolso préstamo {pr['numero']:04d} · {clientes.get(pr['cliente_id'], '—')}",
                     pr["folio_desembolso"], "desembolso", "desembolso",
                     [("121", total_c, 0), ("101", 0, monto_c), ("129", 0, total_c - monto_c)])
        lista.append(a)
        if pr.get("anulado"):
            lista.append(_invertir(a, calc.fecha(pr.get("fecha_anulacion") or pr["fecha_desembolso"])))

    for p in db["pagos"]:
        pr = prestamos.get(p["prestamo_id"])
        if not pr:
            continue
        cuota_c, mora_c = calc.a_centimos(p["monto_cuota"]), calc.a_centimos(p.get("monto_mora", 0))
        a = _asiento(calc.fecha(p["fecha"]),
                     f"Cobro préstamo {pr['numero']:04d} · {clientes.get(pr['cliente_id'], '—')}",
                     p["folio"], "cobro", "cobro",
                     [("101", cuota_c + mora_c, 0), ("121", 0, cuota_c), ("702", 0, mora_c)])
        lista.append(a)
        if p.get("anulado"):
            lista.append(_invertir(a, calc.fecha(p.get("fecha_anulacion") or p["fecha"])))

    for m in db["movimientos"]:
        monto_c = calc.a_centimos(m["monto"])
        detalle = m.get("detalle") or ""
        if m["tipo"] == "aporte":
            lineas, glosa, cat = [("101", monto_c, 0), ("301", 0, monto_c)], "Aporte de capital", "aporte"
        elif m["tipo"] == "retiro":
            lineas, glosa, cat = [("302", monto_c, 0), ("101", 0, monto_c)], "Retiro de capital", "retiro"
        else:
            etiqueta = "Pago de servicio" if m["tipo"] == "servicio" else "Gasto"
            lineas, glosa, cat = [("601", monto_c, 0), ("101", 0, monto_c)], etiqueta, "gasto"
        a = _asiento(calc.fecha(m["fecha"]), f"{glosa}{' · ' + detalle if detalle else ''}", "MOV-" + m["id"], "movimiento", cat, lineas)
        lista.append(a)
        if m.get("anulado"):
            lista.append(_invertir(a, calc.fecha(m.get("fecha_anulacion") or m["fecha"])))

    lista += _devengos(db, hoy_)
    lista.sort(key=lambda a: (a["fecha"], ORDEN_TIPO[a["tipo"]], a["ref"]))
    for i, a in enumerate(lista, start=1):
        a["numero"] = f"A-{i:05d}"
    return [a for a in lista if a["fecha"] <= hasta]


def _devengos(db: dict, hoy_: date) -> list[dict]:
    activos = [p for p in db["prestamos"] if not p.get("anulado")]
    if not activos:
        return []
    pagos = [p for p in db["pagos"] if not p.get("anulado")]
    cancel = {p["id"]: _cancelacion(p, pagos) for p in activos}
    previo = {p["id"]: 0 for p in activos}
    resultado = []
    for periodo in meses(periodo_de(min(calc.fecha(p["fecha_desembolso"]) for p in activos)), periodo_de(hoy_)):
        fin_mes = ultimo_dia(periodo)
        punto = min(fin_mes, hoy_)
        incremento = 0
        for p in activos:
            actual = _devengado_c(p, punto, cancel[p["id"]])
            incremento += actual - previo[p["id"]]
            previo[p["id"]] = actual
        if incremento > 0:
            prov = fin_mes > hoy_
            resultado.append(_asiento(punto, f"Devengo de intereses de {calc.fecha(punto).strftime('%m/%Y')}"
                                      + (" (provisional, al día de hoy)" if prov else ""),
                                      f"DEV-{periodo}", "devengo", "devengo", [("129", incremento, 0), ("701", 0, incremento)], prov))
    return resultado


# ───────────────────────── mayor, balance de comprobación y estados ─────────────────────────

def importe(c: int) -> float:
    return calc.de_centimos(c)


def _saldo_natural(cuenta: str, debe: int, haber: int) -> int:
    return debe - haber if CUENTAS[cuenta][1] == "D" else haber - debe


def mayor(lista: list[dict], cuenta: str) -> list[dict]:
    filas, corrido = [], 0
    for a in lista:
        for c, d, h in a["lineas"]:
            if c == cuenta:
                corrido += _saldo_natural(cuenta, d, h)
                filas.append({"fecha": a["fecha"], "numero": a["numero"], "glosa": a["glosa"], "ref": a["ref"],
                              "debe": importe(d), "haber": importe(h), "saldo": importe(corrido)})
    return filas


def sumas(lista: list[dict], desde=None, hasta=None) -> dict[str, tuple[int, int]]:
    """Total debe y haber por cuenta dentro del periodo (en céntimos)."""
    desde = calc.fecha(desde) if desde else None
    hasta = calc.fecha(hasta) if hasta else None
    tot = {c: [0, 0] for c in CUENTAS}
    for a in lista:
        if (desde and a["fecha"] < desde) or (hasta and a["fecha"] > hasta):
            continue
        for c, d, h in a["lineas"]:
            tot[c][0] += d
            tot[c][1] += h
    return {c: (d, h) for c, (d, h) in tot.items()}


def balance_comprobacion(lista: list[dict]) -> dict:
    tot = sumas(lista)
    filas = []
    for c, (nombre, _, _) in CUENTAS.items():
        d, h = tot[c]
        filas.append({"cuenta": c, "nombre": nombre, "debe": importe(d), "haber": importe(h),
                      "deudor": importe(max(d - h, 0)), "acreedor": importe(max(h - d, 0))})
    total = {k: round(sum(f[k] for f in filas), 2) for k in ("debe", "haber", "deudor", "acreedor")}
    return {"filas": filas, "total": total, "cuadra": total["debe"] == total["haber"] and total["deudor"] == total["acreedor"]}


def saldo(lista: list[dict], cuenta: str, hasta=None) -> float:
    d, h = sumas(lista, hasta=hasta)[cuenta]
    return importe(_saldo_natural(cuenta, d, h))


def estado_resultados(lista: list[dict], desde, hasta) -> dict:
    t = sumas(lista, desde, hasta)
    intereses, mora = (t["701"][1] - t["701"][0]), (t["702"][1] - t["702"][0])
    gastos = t["601"][0] - t["601"][1]
    return {"intereses": importe(intereses), "mora": importe(mora), "ingresos": importe(intereses + mora),
            "gastos": importe(gastos), "utilidad": importe(intereses + mora - gastos)}


def balance_general(lista: list[dict], hasta=None) -> dict:
    t = sumas(lista, hasta=hasta)
    caja = t["101"][0] - t["101"][1]
    cartera = t["121"][0] - t["121"][1]
    no_dev = t["129"][1] - t["129"][0]
    capital = t["301"][1] - t["301"][0]
    retiros = t["302"][0] - t["302"][1]
    resultados = (t["701"][1] - t["701"][0]) + (t["702"][1] - t["702"][0]) - (t["601"][0] - t["601"][1])
    activo, patrimonio = caja + cartera - no_dev, capital - retiros + resultados
    return {"caja": importe(caja), "cartera": importe(cartera), "no_devengados": importe(no_dev),
            "cartera_neta": importe(cartera - no_dev), "activo": importe(activo),
            "capital": importe(capital), "retiros": importe(retiros), "resultados": importe(resultados),
            "patrimonio": importe(patrimonio), "cuadra": activo == patrimonio}


CATEGORIAS_FLUJO = (("cobro", "Cobros de cuotas y mora"), ("aporte", "Aportes de capital"), ("desembolso", "Desembolsos de créditos"),
                    ("retiro", "Retiros de capital"), ("gasto", "Gastos y servicios"))


def flujo_caja(lista: list[dict], desde, hasta) -> dict:
    desde, hasta = calc.fecha(desde), calc.fecha(hasta)
    inicial = sum(d - h for a in lista if a["fecha"] < desde for c, d, h in a["lineas"] if c == "101")
    mov = {k: 0 for k, _ in CATEGORIAS_FLUJO}
    for a in lista:
        if desde <= a["fecha"] <= hasta and a["categoria"] in mov:  # el devengo no mueve caja
            mov[a["categoria"]] += sum(d - h for c, d, h in a["lineas"] if c == "101")
    final = inicial + sum(mov.values())
    return {"inicial": importe(inicial), "movimientos": {k: importe(v) for k, v in mov.items()},
            "entradas": importe(sum(v for v in mov.values() if v > 0)), "salidas": importe(sum(v for v in mov.values() if v < 0)),
            "final": importe(final)}


# ───────────────────────── cuentas por cobrar ─────────────────────────

def cuentas_por_cobrar(db: dict, evals: dict[str, dict], al_dia) -> dict:
    """Saldo por cliente con antigüedad, intereses no devengados y conciliación con el mayor."""
    al_dia = calc.fecha(al_dia)
    pagos = [p for p in db["pagos"] if not p.get("anulado")]
    clientes = {c["id"]: c for c in db["clientes"]}
    por_cliente: dict[str, dict] = {}
    for pr in db["prestamos"]:
        if pr.get("anulado"):
            continue
        ev = evals[pr["id"]]
        fila = por_cliente.setdefault(pr["cliente_id"], {
            "cliente": clientes.get(pr["cliente_id"], {}).get("nombre", "—"), "dni": clientes.get(pr["cliente_id"], {}).get("dni", ""),
            "creditos": 0, "por_cobrar": 0, "vencido": 0, "tramos": [0] * len(calc.TRAMOS_MORA), "no_devengado": 0})
        fila["creditos"] += 1 if ev["estado"] in ("vigente", "vencido") else 0
        fila["por_cobrar"] += calc.a_centimos(ev["saldo"])
        fila["vencido"] += calc.a_centimos(ev["vencido"])
        for c in ev["cuotas"]:
            if c["estado"] == "vencida":
                for i, (_, d1, d2) in enumerate(calc.TRAMOS_MORA):
                    if d1 <= c["atraso"] <= d2:
                        fila["tramos"][i] += calc.a_centimos(c["saldo"])
                        break
        interes_c = calc.a_centimos(pr["total"]) - calc.a_centimos(pr["monto"])
        fila["no_devengado"] += interes_c - _devengado_c(pr, al_dia, _cancelacion(pr, pagos))

    filas = sorted(por_cliente.values(), key=lambda f: -f["vencido"])
    for f in filas:
        f["por_vencer"] = f["por_cobrar"] - f["vencido"]
        f["cartera_neta"] = f["por_cobrar"] - f["no_devengado"]
    total = {k: sum(f[k] for f in filas) for k in ("creditos", "por_cobrar", "vencido", "por_vencer", "no_devengado", "cartera_neta")}
    total["tramos"] = [sum(f["tramos"][i] for f in filas) for i in range(len(calc.TRAMOS_MORA))]

    lib = asientos(db, al_dia, al_dia)
    conciliacion = []
    for cuenta, etiqueta, valor in (("121", "Cartera de créditos", total["por_cobrar"]), ("129", "Intereses no devengados", total["no_devengado"])):
        en_mayor = calc.a_centimos(saldo(lib, cuenta))
        conciliacion.append({"cuenta": cuenta, "nombre": etiqueta, "auxiliar": importe(valor), "mayor": importe(en_mayor),
                             "diferencia": importe(valor - en_mayor)})
    return {"filas": filas, "total": total, "conciliacion": conciliacion,
            "cuadra": all(c["diferencia"] == 0 for c in conciliacion)}


# ───────────────────────── cierre mensual ─────────────────────────

def instantanea(db: dict, periodo: str, hoy_=None) -> dict:
    """Cifras del mes, para guardarlas al cerrar y compararlas después."""
    fin = ultimo_dia(periodo)
    lib = asientos(db, fin, hoy_)
    res = estado_resultados(lib, primer_dia(periodo), fin)
    bal = balance_general(lib, fin)
    return {"caja": bal["caja"], "cartera": bal["cartera"], "no_devengados": bal["no_devengados"],
            "ingresos": res["ingresos"], "gastos": res["gastos"], "utilidad": res["utilidad"], "asientos": len(lib)}


def estado_periodos(db: dict, hoy_=None) -> list[dict]:
    """Cada mes desde la apertura hasta el actual: cerrado, abierto o en curso, y si se puede cerrar."""
    hoy_ = calc.fecha(hoy_ or calc.hoy())
    cierres = db.get("cierres", {})
    filas, previo_cerrado = [], True
    for p in meses(periodo_de(fecha_apertura(db, hoy_)), periodo_de(hoy_)):
        if p in cierres:
            estado = "cerrado"
        elif ultimo_dia(p) >= hoy_:
            estado = "en curso"
        else:
            estado = "abierto"
        filas.append({"periodo": p, "estado": estado, "puede_cerrar": estado == "abierto" and previo_cerrado, "cierre": cierres.get(p)})
        previo_cerrado = estado == "cerrado"
    return filas


def diferencias_con_cierre(db: dict, hoy_=None) -> list[dict]:
    """Meses cerrados cuyas cifras de hoy ya no coinciden con las que se guardaron al cerrar."""
    difs = []
    for periodo, cierre in sorted(db.get("cierres", {}).items()):
        actual = instantanea(db, periodo, hoy_)
        cambios = {k: (cierre["cifras"][k], actual[k]) for k in ("caja", "cartera", "no_devengados", "ingresos", "gastos")
                   if abs(cierre["cifras"][k] - actual[k]) > 0.004}
        if cambios:
            difs.append({"periodo": periodo, "cambios": cambios})
    return difs
