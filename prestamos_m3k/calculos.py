"""Reglas de negocio de M3K Préstamos: cronogramas, estado de cada crédito, mora,
costo efectivo y caja.

Son funciones puras sobre diccionarios (el contenido de data/prestamos.json); no usan
Streamlit, así que se pueden probar con pytest. Los importes se guardan en soles con
2 decimales y se operan internamente en céntimos (enteros) para evitar errores de
redondeo.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

# Lima no tiene horario de verano: UTC-5 fijo.
LIMA = timezone(timedelta(hours=-5))

PLAZO_DIAS = 24

# Los domingos no se trabaja ni se cobra: el plazo de 24 días son 24 días de trabajo (lunes a sábado).
# En la modalidad semanal el número de cuotas lo elige quien presta (de 1 a 8; por defecto 4) y vencen
# cada 7 días.
CUOTAS_SEMANALES = (4, range(1, 9))  # (por defecto, permitidas)
MODALIDADES = {
    "diario": {"nombre": "Diario", "texto": "24 cuotas, una por día de trabajo (lunes a sábado)"},
    "semanal": {"nombre": "Semanal", "texto": "Cuotas iguales cada 7 días (eliges de 1 a 8)"},
    "final": {"nombre": "Pago único", "texto": "1 solo pago al día de trabajo 24"},
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


def total_a_pagar(monto, tasa_pct) -> float:
    """Capital más interés total (tasa plana sobre el periodo, sin importar la modalidad)."""
    total = Decimal(str(monto)) * (Decimal(100) + Decimal(str(tasa_pct))) / 100
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


def fechas_vencimiento(modalidad: str, fecha_desembolso, n_cuotas: int | None = None) -> list[date]:
    f0 = fecha(fecha_desembolso)
    if modalidad == "diario":
        return [sumar_habiles(f0, i) for i in range(1, PLAZO_DIAS + 1)]
    if modalidad == "final":
        return [sumar_habiles(f0, PLAZO_DIAS)]
    if modalidad == "semanal":
        n = n_cuotas or CUOTAS_SEMANALES[0]
        if n not in CUOTAS_SEMANALES[1]:
            raise ValueError("La modalidad semanal admite de 1 a 8 cuotas.")
        return [trasladar_domingo(f0 + timedelta(days=7 * i)) for i in range(1, n + 1)]
    raise ValueError("Modalidad no válida.")


# ───────────────────────── cronograma y costo ─────────────────────────

def generar_cronograma(monto, tasa_pct, modalidad: str, fecha_desembolso, n_cuotas: int | None = None) -> list[dict]:
    vencimientos = fechas_vencimiento(modalidad, fecha_desembolso, n_cuotas)
    total_c = a_centimos(total_a_pagar(monto, tasa_pct))
    n = len(vencimientos)
    base = total_c // n
    resto = total_c - base * n  # la última cuota absorbe los céntimos sobrantes
    return [
        {"n": i, "vence": v.isoformat(), "monto": de_centimos(base + (resto if i == n else 0))}
        for i, v in enumerate(vencimientos, start=1)
    ]


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
    capital_rec_c = round(pagado_c * monto_c / total_c) if total_c else 0
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
    filas.sort(key=lambda f: (f["fecha"], f["folio"]))  # el más antiguo primero
    return filas
