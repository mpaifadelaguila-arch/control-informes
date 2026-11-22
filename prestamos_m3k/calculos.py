"""Reglas de negocio de M3K Préstamos: cronogramas, estado de cada crédito, mora,
costo efectivo y caja.

Son funciones puras sobre diccionarios (el contenido de data/prestamos.json); no usan
Streamlit, así que se pueden probar con pytest. Los importes se guardan en soles con
2 decimales y se operan internamente en céntimos (enteros) para evitar errores de
redondeo.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

# Lima no tiene horario de verano: UTC-5 fijo.
LIMA = timezone(timedelta(hours=-5))

PLAZO_DIAS = 24

# Los domingos no se trabaja ni se cobra: el plazo de 24 días son 24 días de trabajo (lunes a sábado).
# Semanal: siempre 4 cuotas iguales, una cada 7 días.
# Mensual: de 1 a 3 meses; el interés (la tasa) es POR MES. Los primeros meses se paga solo el interés y en el último
# mes el interés más todo el capital. Cada cuota vence el mismo día de cada mes.
CUOTAS_SEMANALES = (4, range(4, 5))  # (por defecto, permitidas)
MESES_MENSUAL = (1, 2, 3)
MODALIDADES = {
    "diario": {"nombre": "Diario", "texto": "24 cuotas, una por día de trabajo (lunes a sábado)"},
    "semanal": {"nombre": "Semanal", "texto": "4 cuotas iguales, una cada 7 días"},
    "mensual": {"nombre": "Mensual", "texto": "Cada mes se paga solo el interés; en el último mes, el interés y todo el capital"},
    # «Pago único» ya no se ofrece, pero los créditos antiguos con esa modalidad se siguen mostrando y cobrando.
    "final": {"nombre": "Pago único", "texto": "1 solo pago al día de trabajo 24", "oculta": True},
}
ENTREGAS = ("Efectivo", "Yape", "Plin", "Transferencia")
METODOS_COBRO = ("Efectivo", "Yape", "Plin", "Transferencia")

# Tramos de antigüedad de la deuda vencida: (etiqueta, desde, hasta) en días de atraso.
TRAMOS_MORA = (
    ("1 a 7 días", 1, 7),
    ("8 a 15 días", 8, 15),
    ("16 a 30 días", 16, 30),
    ("31 a 60 días", 31, 60),
    ("Más de 60 días", 61, 10**6),
)


# ───────────────────────── utilidades ─────────────────────────

def hoy() -> date:
    return datetime.now(LIMA).date()


def ahora() -> str:
    return datetime.now(LIMA).isoformat(timespec="seconds")


def fecha(valor) -> date:
    """Acepta date, datetime o texto ISO (AAAA-MM-DD...)."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor)[:10])


def a_centimos(importe) -> int:
    return int((Decimal(str(importe)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def de_centimos(centimos: int) -> float:
    return round(centimos / 100, 2)


def modalidades_ofrecidas() -> list[str]:
    return [k for k, v in MODALIDADES.items() if not v.get("oculta")]


def total_a_pagar(monto, tasa_pct, meses: int = 1) -> float:
    """Capital más interés total. La tasa es plana sobre el periodo; en la modalidad mensual se cobra por cada mes."""
    total = Decimal(str(monto)) * (Decimal(100) + Decimal(str(tasa_pct)) * int(meses)) / 100
    return float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def trasladar_domingo(dia: date) -> date:
    """Los domingos no se cobra: el vencimiento pasa al lunes."""
    return dia + timedelta(days=1) if dia.weekday() == 6 else dia


def sumar_habiles(desde: date, n: int) -> date:
    """Fecha del día de trabajo número n después de `desde` (se salta los domingos)."""
    d, contados = desde, 0
    while contados < n:
        d += timedelta(days=1)
        if d.weekday() != 6:
            contados += 1
    return d


def sumar_meses(desde: date, n: int) -> date:
    """El mismo día n meses después; si ese mes no tiene el día (31, 29...), el último día del mes."""
    indice = desde.year * 12 + (desde.month - 1) + n
    anio, mes = divmod(indice, 12)
    return date(anio, mes + 1, min(desde.day, monthrange(anio, mes + 1)[1]))


def fechas_vencimiento(modalidad: str, fecha_desembolso, n_cuotas: int | None = None, meses: int | None = None) -> list[date]:
    f0 = fecha(fecha_desembolso)
    if modalidad == "mensual":
        m = MESES_MENSUAL[0] if meses is None else meses
        if m not in MESES_MENSUAL:
            raise ValueError("La modalidad mensual admite de 1 a 3 meses.")
        return [trasladar_domingo(sumar_meses(f0, i)) for i in range(1, m + 1)]
    if modalidad == "diario":
        return [sumar_habiles(f0, i) for i in range(1, PLAZO_DIAS + 1)]
    if modalidad == "final":
        return [sumar_habiles(f0, PLAZO_DIAS)]
    if modalidad == "semanal":
        n = n_cuotas or CUOTAS_SEMANALES[0]
        if n not in CUOTAS_SEMANALES[1]:
            raise ValueError("La modalidad semanal es de 4 cuotas.")
        return [trasladar_domingo(f0 + timedelta(days=7 * i)) for i in range(1, n + 1)]
    raise ValueError("Modalidad no válida.")


# ───────────────────────── cronograma y costo ─────────────────────────

def generar_cronograma(monto, tasa_pct, modalidad: str, fecha_desembolso, n_cuotas: int | None = None,
                       meses: int | None = None) -> list[dict]:
    vencimientos = fechas_vencimiento(modalidad, fecha_desembolso, n_cuotas, meses)
    if modalidad == "mensual":
        m = len(vencimientos)
        capital_c = a_centimos(monto)
        interes_mes_c = a_centimos(total_a_pagar(monto, tasa_pct, 1)) - capital_c
        total_m_c = a_centimos(total_a_pagar(monto, tasa_pct, m))
        cuotas = [{"n": i, "vence": v.isoformat(), "monto": de_centimos(interes_mes_c), "capital": 0.0}
                  for i, v in enumerate(vencimientos[:-1], start=1)]
        cuotas.append({"n": m, "vence": vencimientos[-1].isoformat(), "monto": de_centimos(total_m_c - interes_mes_c * (m - 1)),
                       "capital": de_centimos(capital_c)})
        return cuotas
    total_c = a_centimos(total_a_pagar(monto, tasa_pct))
    n = len(vencimientos)
    base = total_c // n
    resto = total_c - base * n  # la última cuota absorbe los céntimos sobrantes
    return [
        {"n": i, "vence": v.isoformat(), "monto": de_centimos(base + (resto if i == n else 0))}
        for i, v in enumerate(vencimientos, start=1)
    ]


def capital_recuperado_c(prestamo: dict, pagado_c: int) -> int:
    """Parte del capital que ya volvió con lo cobrado (en céntimos). En el mensual, las cuotas de solo interés no devuelven capital;
    en los demás créditos cada cobro devuelve capital e interés en la misma proporción que el total."""
    cuotas = prestamo["cuotas"]
    if all("capital" in q for q in cuotas):
        restante, capital = pagado_c, 0.0
        for q in cuotas:
            monto_c = a_centimos(q["monto"])
            aplicado = min(restante, monto_c)
            restante -= aplicado
            if monto_c:
                capital += aplicado * a_centimos(q["capital"]) / monto_c
        return round(capital)
    total_c, monto_c = a_centimos(prestamo["total"]), a_centimos(prestamo["monto"])
    return round(pagado_c * monto_c / total_c) if total_c else 0


def capital_por_pago(db: dict) -> dict[str, float]:
    """Capital que devolvió cada cobro vigente (el resto de la cuota es interés), aplicando los cobros de más antiguo a más nuevo."""
    resultado: dict[str, float] = {}
    for pr in db["prestamos"]:
        acumulado_c, capital_previo_c = 0, 0
        for p in sorted((p for p in db["pagos"] if p["prestamo_id"] == pr["id"] and not p.get("anulado")),
                        key=lambda p: (p["fecha"], p["folio"])):
            acumulado_c += a_centimos(p["monto_cuota"])
            capital_c = capital_recuperado_c(pr, acumulado_c)
            resultado[p["id"]] = de_centimos(capital_c - capital_previo_c)
            capital_previo_c = capital_c
    return resultado


def costo_efectivo(monto, cuotas: list[dict], fecha_desembolso) -> dict:
    """Tasa interna de retorno del crédito, expresada por día, a 30 días y anual (TCEA).

    Con interés plano y cuotas que devuelven capital poco a poco, el costo real es
    mucho mayor que el porcentaje nominal; por eso se muestra siempre al cliente.
    """
    f0 = fecha(fecha_desembolso)
    flujos = [((fecha(q["vence"]) - f0).days, float(q["monto"])) for q in cuotas]
    capital = float(monto)
    total = sum(m for _, m in flujos)
    if capital <= 0 or total <= capital:
        return {"tir_diaria": 0.0, "tem": 0.0, "tea": 0.0, "costo_periodo": 0.0}

    def valor_presente(r: float) -> float:
        return sum(m / (1 + r) ** d for d, m in flujos) - capital

    bajo, alto = 0.0, 1.0
    while valor_presente(alto) > 0 and alto < 1e6:
        alto *= 2
    for _ in range(200):
        medio = (bajo + alto) / 2
        if valor_presente(medio) > 0:
            bajo = medio
        else:
            alto = medio
    r = (bajo + alto) / 2
    return {
        "tir_diaria": r,
        "tem": (1 + r) ** 30 - 1,
        "tea": (1 + r) ** 365 - 1,
        "costo_periodo": total / capital - 1,
    }


# ───────────────────────── estado de un crédito ─────────────────────────

def evaluar_prestamo(prestamo: dict, pagos: list[dict], al_dia, mora_diaria_pct: float = 0.0) -> dict:
    """Reparte lo cobrado entre las cuotas (de la más antigua a la más reciente) y calcula
    saldos, atraso, mora y la parte de capital e interés ya recuperada."""
    al_dia = fecha(al_dia)
    validos = [p for p in pagos if p["prestamo_id"] == prestamo["id"] and not p.get("anulado")]
    pagado_c = sum(a_centimos(p["monto_cuota"]) for p in validos)
    mora_pagada_c = sum(a_centimos(p.get("monto_mora", 0)) for p in validos)

    restante = pagado_c
    cuotas, mora_acumulada = [], 0.0
    for q in prestamo["cuotas"]:
        monto_c = a_centimos(q["monto"])
        aplicado = min(restante, monto_c)
        restante -= aplicado
        saldo_c = monto_c - aplicado
        vence = fecha(q["vence"])
        atraso = (al_dia - vence).days if saldo_c > 0 and vence < al_dia else 0
        if saldo_c == 0:
            estado = "pagada"
        elif atraso > 0:
            estado = "vencida"
        elif aplicado > 0:
            estado = "parcial"
        else:
            estado = "pendiente"
        mora_acumulada += (saldo_c / 100) * (mora_diaria_pct / 100) * atraso
        cuotas.append({
            "n": q["n"], "vence": vence, "monto": q["monto"],
            "pagado": de_centimos(aplicado), "saldo": de_centimos(saldo_c),
            "estado": estado, "atraso": atraso,
        })

    total_c = a_centimos(prestamo["total"])
    monto_c = a_centimos(prestamo["monto"])
    saldo_c = sum(a_centimos(c["saldo"]) for c in cuotas)
    vencido_c = sum(a_centimos(c["saldo"]) for c in cuotas if c["estado"] == "vencida")
    capital_rec_c = capital_recuperado_c(prestamo, pagado_c)
    mora_pendiente = max(0.0, round(mora_acumulada - mora_pagada_c / 100, 2))
    vencidas = [c for c in cuotas if c["estado"] == "vencida"]

    if prestamo.get("anulado"):
        estado = "anulado"
    elif saldo_c == 0:
        estado = "cancelado"
    elif vencidas:
        estado = "vencido"
    else:
        estado = "vigente"

    return {
        "estado": estado,
        "cuotas": cuotas,
        "proxima": next((c for c in cuotas if c["saldo"] > 0), None),
        "total": prestamo["total"],
        "pagado": de_centimos(pagado_c),
        "saldo": de_centimos(saldo_c),
        "vencido": de_centimos(vencido_c),
        "mora_pendiente": mora_pendiente,
        "mora_cobrada": de_centimos(mora_pagada_c),
        "capital_recuperado": de_centimos(capital_rec_c),
        "interes_cobrado": de_centimos(pagado_c - capital_rec_c),
        "capital_pendiente": de_centimos(monto_c - capital_rec_c),
        "cuotas_vencidas": len(vencidas),
        "cuotas_con_saldo": sum(1 for c in cuotas if c["saldo"] > 0),
        "atraso_max": max((c["atraso"] for c in cuotas), default=0),
        "avance": (pagado_c / total_c) if total_c else 0.0,
    }


def evaluar_cartera(db: dict, al_dia) -> dict[str, dict]:
    pagos = [p for p in db["pagos"] if not p.get("anulado")]
    mora = float(db["config"].get("mora_diaria_pct", 0) or 0)
    return {pr["id"]: evaluar_prestamo(pr, pagos, al_dia, mora) for pr in db["prestamos"]}


# ───────────────────────── indicadores de cartera y caja ─────────────────────────

def indicadores(db: dict, evals: dict[str, dict], al_dia) -> dict:
    al_dia = fecha(al_dia)
    activos = [pr for pr in db["prestamos"] if evals[pr["id"]]["estado"] in ("vigente", "vencido")]
    vigentes_no_anulados = [pr for pr in db["prestamos"] if not pr.get("anulado")]

    capital_en_calle = sum(evals[p["id"]]["capital_pendiente"] for p in activos)
    por_cobrar = sum(evals[p["id"]]["saldo"] for p in activos)
    vencido = sum(evals[p["id"]]["vencido"] for p in activos)
    cuotas_vencidas = sum(evals[p["id"]]["cuotas_vencidas"] for p in activos)

    cobros_hoy_monto, cobros_hoy_n = 0.0, 0
    for p in activos:
        for c in evals[p["id"]]["cuotas"]:
            if c["saldo"] > 0 and c["vence"] == al_dia:
                cobros_hoy_monto += c["saldo"]
                cobros_hoy_n += 1

    ganancia_proyectada = sum(p["total"] - p["monto"] for p in vigentes_no_anulados)
    ganancia_realizada = sum(
        evals[p["id"]]["interes_cobrado"] + evals[p["id"]]["mora_cobrada"] for p in vigentes_no_anulados
    )
    return {
        "capital_en_calle": round(capital_en_calle, 2),
        "por_cobrar": round(por_cobrar, 2),
        "vencido": round(vencido, 2),
        "mora_pendiente": round(sum(evals[p["id"]]["mora_pendiente"] for p in activos), 2),
        "prestamos_activos": len(activos),
        "cuotas_vencidas": cuotas_vencidas,
        "morosidad": (vencido / por_cobrar) if por_cobrar else 0.0,
        "cobros_hoy_monto": round(cobros_hoy_monto, 2),
        "cobros_hoy_n": cobros_hoy_n,
        "ganancia_proyectada": round(ganancia_proyectada, 2),
        "ganancia_realizada": round(ganancia_realizada, 2),
    }


def cola_cobranza(db: dict, evals: dict[str, dict], al_dia) -> list[dict]:
    """Créditos con deuda vencida o con cuota que vence hoy, de mayor a menor atraso."""
    al_dia = fecha(al_dia)
    clientes = {c["id"]: c for c in db["clientes"]}
    cola = []
    for pr in db["prestamos"]:
        ev = evals[pr["id"]]
        if ev["estado"] not in ("vigente", "vencido"):
            continue
        hoy_monto = sum(c["saldo"] for c in ev["cuotas"] if c["saldo"] > 0 and c["vence"] == al_dia)
        if ev["vencido"] > 0 or hoy_monto > 0:
            cola.append({
                "prestamo": pr, "cliente": clientes.get(pr["cliente_id"], {}),
                "atraso": ev["atraso_max"], "vencido": ev["vencido"],
                "hoy": round(hoy_monto, 2), "cuotas_vencidas": ev["cuotas_vencidas"],
            })
    cola.sort(key=lambda x: (-x["atraso"], -x["hoy"]))
    return cola


def antiguedad_mora(evals: dict[str, dict]) -> list[dict]:
    """Saldo vencido agrupado por días de atraso de cada cuota."""
    filas = [{"tramo": t, "cuotas": 0, "monto": 0.0} for t, _, _ in TRAMOS_MORA]
    for ev in evals.values():
        if ev["estado"] not in ("vigente", "vencido"):
            continue
        for c in ev["cuotas"]:
            if c["estado"] != "vencida":
                continue
            for fila, (_, desde, hasta) in zip(filas, TRAMOS_MORA):
                if desde <= c["atraso"] <= hasta:
                    fila["cuotas"] += 1
                    fila["monto"] = round(fila["monto"] + c["saldo"], 2)
                    break
    return filas


def _suma_movimientos(db: dict, ingreso: bool) -> float:
    return sum(
        m["monto"] for m in db["movimientos"]
        if not m.get("anulado") and (m["tipo"] in ("aporte",)) == ingreso
    )


def resumen_caja(db: dict) -> dict:
    base = float(db["config"].get("capital_base", 0))
    desembolsado = sum(p["monto"] for p in db["prestamos"] if not p.get("anulado"))
    cobrado = sum(p["monto_cuota"] + p.get("monto_mora", 0) for p in db["pagos"] if not p.get("anulado"))
    aportes = _suma_movimientos(db, True)
    salidas = _suma_movimientos(db, False)
    return {
        "capital_base": base,
        "desembolsado": round(desembolsado, 2),
        "cobrado": round(cobrado, 2),
        "aportes": round(aportes, 2),
        "salidas": round(salidas, 2),
        "liquidez": round(base - desembolsado + cobrado + aportes - salidas, 2),
    }


def movimientos_caja(db: dict) -> list[dict]:
    """Historial único de caja (desembolsos, cobros y movimientos manuales), del más reciente al más antiguo."""
    clientes = {c["id"]: c["nombre"] for c in db["clientes"]}
    prestamos = {p["id"]: p for p in db["prestamos"]}
    filas = []
    for pr in db["prestamos"]:
        if not pr.get("anulado"):
            filas.append({"fecha": fecha(pr["fecha_desembolso"]), "tipo": "Desembolso",
                          "detalle": f"{clientes.get(pr['cliente_id'], '—')} · préstamo {pr['numero']:04d}",
                          "monto": -pr["monto"], "folio": pr["folio_desembolso"]})
    for p in db["pagos"]:
        if not p.get("anulado"):
            pr = prestamos.get(p["prestamo_id"], {})
            filas.append({"fecha": fecha(p["fecha"]), "tipo": "Cobro",
                          "detalle": f"{clientes.get(pr.get('cliente_id'), '—')} · préstamo {pr.get('numero', 0):04d}",
                          "monto": round(p["monto_cuota"] + p.get("monto_mora", 0), 2), "folio": p["folio"]})
    etiquetas = {"aporte": "Aporte de capital", "retiro": "Retiro", "gasto": "Gasto", "servicio": "Pago de servicio"}
    for m in db["movimientos"]:
        if not m.get("anulado"):
            signo = 1 if m["tipo"] == "aporte" else -1
            filas.append({"fecha": fecha(m["fecha"]), "tipo": etiquetas.get(m["tipo"], m["tipo"]),
                          "detalle": m.get("detalle", ""), "monto": signo * m["monto"], "folio": ""})
    filas.sort(key=lambda f: (f["fecha"], f["monto"] < 0, f["folio"]))  # el más antiguo primero; en un mismo día, primero lo que entra
    return filas


def movimientos_con_saldo(db: dict) -> list[dict]:
    """El historial de caja con el saldo que quedaba después de cada movimiento (parte del capital base)."""
    saldo_c = a_centimos(db["config"].get("capital_base", 0))
    filas = movimientos_caja(db)
    for f in filas:
        saldo_c += a_centimos(f["monto"])
        f["saldo"] = de_centimos(saldo_c)
    return filas


# ───────────────────────── series para los gráficos del inicio ─────────────────────────

def _cuotas_de_creditos(db: dict, evals: dict[str, dict]):
    for pr in db["prestamos"]:
        if not pr.get("anulado"):
            yield from evals[pr["id"]]["cuotas"]


def cuotas_por_semana(db: dict, evals: dict[str, dict], al_dia, atras: int = 4, adelante: int = 1) -> list[dict]:
    """Por semana (de lunes a sábado): lo que vencía y lo que ya se cobró de esas cuotas."""
    al_dia = fecha(al_dia)
    lunes = al_dia - timedelta(days=al_dia.weekday())
    semanas = [{"desde": lunes + timedelta(days=7 * k), "esperado_c": 0, "cobrado_c": 0, "actual": k == 0} for k in range(-atras, adelante + 1)]
    for c in _cuotas_de_creditos(db, evals):
        for s in semanas:
            if s["desde"] <= c["vence"] <= s["desde"] + timedelta(days=6):
                s["esperado_c"] += a_centimos(c["monto"])
                s["cobrado_c"] += a_centimos(c["pagado"])
                break
    return [{"desde": s["desde"], "actual": s["actual"], "esperado": de_centimos(s["esperado_c"]), "cobrado": de_centimos(s["cobrado_c"])} for s in semanas]


def avance_mes(db: dict, evals: dict[str, dict], al_dia) -> dict:
    """De las cuotas que vencen en el mes de `al_dia`: cuánto era y cuánto se lleva cobrado."""
    al_dia = fecha(al_dia)
    esperado = cobrado = 0
    for c in _cuotas_de_creditos(db, evals):
        if (c["vence"].year, c["vence"].month) == (al_dia.year, al_dia.month):
            esperado += a_centimos(c["monto"])
            cobrado += a_centimos(c["pagado"])
    return {"esperado": de_centimos(esperado), "cobrado": de_centimos(cobrado), "pct": (cobrado / esperado) if esperado else 0.0}


def proximos_cobros(db: dict, evals: dict[str, dict], al_dia, n: int = 6) -> list[dict]:
    """Los próximos `n` días de trabajo (sin domingos), desde hoy, con lo que vence cada día."""
    dia = fecha(al_dia)
    dias = []
    while len(dias) < n:
        if dia.weekday() != 6:
            dias.append({"fecha": dia, "monto_c": 0, "cuotas": 0})
        dia += timedelta(days=1)
    por_fecha = {d["fecha"]: d for d in dias}
    for c in _cuotas_de_creditos(db, evals):
        d = por_fecha.get(c["vence"])
        if d and c["saldo"] > 0:
            d["monto_c"] += a_centimos(c["saldo"])
            d["cuotas"] += 1
    return [{"fecha": d["fecha"], "monto": de_centimos(d["monto_c"]), "cuotas": d["cuotas"]} for d in dias]


def composicion_cartera(db: dict, evals: dict[str, dict]) -> list[dict]:
    """Lo que te deben, separado en «al día» y en cada tramo de atraso. `gravedad` va de 0 (al día) a 5."""
    nombres = ["Al día"] + [t for t, _, _ in TRAMOS_MORA]
    montos = [0] * len(nombres)
    for pr in db["prestamos"]:
        ev = evals[pr["id"]]
        if pr.get("anulado") or ev["estado"] not in ("vigente", "vencido"):
            continue
        for c in ev["cuotas"]:
            if c["saldo"] <= 0:
                continue
            idx = 0
            if c["estado"] == "vencida":
                idx = 1 + next(i for i, (_, d1, d2) in enumerate(TRAMOS_MORA) if d1 <= c["atraso"] <= d2)
            montos[idx] += a_centimos(c["saldo"])
    return [{"nombre": n, "monto": de_centimos(m), "gravedad": i} for i, (n, m) in enumerate(zip(nombres, montos)) if m]
