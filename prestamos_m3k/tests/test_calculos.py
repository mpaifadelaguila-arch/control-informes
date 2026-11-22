"""Pruebas de las reglas de negocio con los mismos números que mostraba la app anterior."""

from datetime import date

import pytest

import calculos as calc
import datos
import operaciones as ops

HOY = date(2026, 11, 15)  # domingo


def _db_base():
    db = datos.vacio()
    db["config"]["capital_base"] = 5000.0
    ana = ops.crear_cliente(db, "Ana Torres Quispe", "00000001", "900000001")
    luis = ops.crear_cliente(db, "Luis Ramos Huamán", "00000002")
    return db, ana, luis


def test_total_y_cuotas_coinciden_con_la_app_anterior():
    assert calc.total_a_pagar(600, 20) == 720.0
    assert calc.total_a_pagar(500, 20) == 600.0
    sem = calc.generar_cronograma(600, 20, "semanal", date(2026, 8, 19))
    assert [c["monto"] for c in sem] == [180.0] * 4
    dia = calc.generar_cronograma(1000, 20, "diario", date(2026, 11, 15))
    assert len(dia) == 24 and sum(c["monto"] for c in dia) == 1200.0
    assert len(calc.generar_cronograma(1000, 20, "final", date(2026, 11, 15))) == 1


def test_la_ultima_cuota_absorbe_los_centimos():
    cuotas = calc.generar_cronograma(1000, 20, "semanal", date(2026, 11, 2))  # 1200 / 4 exacto
    assert sum(c["monto"] for c in cuotas) == 1200.0
    cuotas = calc.generar_cronograma(100, 17, "diario", date(2026, 11, 2))  # 117 / 24 no es exacto
    assert round(sum(c["monto"] for c in cuotas), 2) == 117.0


def test_los_domingos_no_cuentan_como_dia_de_cobro():
    assert calc.trasladar_domingo(date(2026, 11, 15)) == date(2026, 11, 16)  # domingo -> lunes
    assert calc.trasladar_domingo(date(2026, 11, 14)) == date(2026, 11, 14)  # sábado igual
    # Diario: 24 cuotas en 24 días de trabajo distintos (lunes a sábado), sin dos cuotas el mismo día.
    dia = calc.generar_cronograma(1000, 20, "diario", date(2026, 11, 1))
    fechas = [calc.fecha(q["vence"]) for q in dia]
    assert len(set(fechas)) == 24 and all(f.weekday() != 6 for f in fechas)
    assert fechas[0] == date(2026, 11, 2) and fechas[-1] == date(2026, 11, 28)  # 4 semanas de lunes a sábado
    # Pago único: día de trabajo 24, igual que la última cuota diaria.
    assert calc.fecha(calc.generar_cronograma(1000, 20, "final", date(2026, 11, 1))[0]["vence"]) == fechas[-1]
    # Semanal desembolsado un domingo: cada vencimiento cae en domingo y pasa al lunes.
    sem = calc.generar_cronograma(400, 20, "semanal", date(2026, 11, 15))
    assert [calc.fecha(q["vence"]) for q in sem] == [date(2026, 11, 23), date(2026, 11, 30), date(2026, 12, 7), date(2026, 12, 14)]


def test_cuadre_de_caja_y_cartera_de_las_capturas():
    """Caja 4,380 = 5,000 - 1,100 desembolsados + 480 cobrados; por cobrar 840; ganancia 220."""
    db, ana, _ = _db_base()
    p1 = ops.crear_prestamo(db, ana["id"], 600, 20, "semanal", date(2026, 8, 19), hoy_=HOY)
    p3 = ops.crear_prestamo(db, ana["id"], 500, 20, "semanal", date(2026, 8, 2), hoy_=HOY)
    ops.registrar_pago(db, p1["id"], "2026-09-03", 180, hoy_=HOY)
    ops.registrar_pago(db, p3["id"], "2026-08-24", 150, hoy_=HOY)
    ops.registrar_pago(db, p3["id"], "2026-09-03", 150, hoy_=HOY)

    assert calc.resumen_caja(db)["liquidez"] == 4380.0
    evals = calc.evaluar_cartera(db, HOY)
    ind = calc.indicadores(db, evals, HOY)
    assert ind["por_cobrar"] == 840.0
    assert ind["vencido"] == 840.0
    assert ind["ganancia_proyectada"] == 220.0
    assert ind["cuotas_vencidas"] == 5
    # El capital en calle ya descuenta lo recuperado (la app anterior mostraba 1,100).
    assert ind["capital_en_calle"] == pytest.approx(1100 - 480 * 1100 / 1320, abs=0.01)
    assert ind["capital_en_calle"] < 1100


def test_estados_de_cuota_y_antiguedad():
    db, ana, _ = _db_base()
    p = ops.crear_prestamo(db, ana["id"], 600, 20, "semanal", date(2026, 10, 1), hoy_=HOY)
    ops.registrar_pago(db, p["id"], "2026-10-07", 100, hoy_=HOY)  # abono parcial a la cuota 1
    ev = calc.evaluar_cartera(db, HOY)[p["id"]]
    assert ev["cuotas"][0]["estado"] == "vencida" and ev["cuotas"][0]["saldo"] == 80.0
    assert ev["estado"] == "vencido" and ev["atraso_max"] > 0
    antig = calc.antiguedad_mora(calc.evaluar_cartera(db, HOY))
    assert sum(f["monto"] for f in antig) == ev["vencido"]


def test_costo_efectivo_pago_unico_y_semanal():
    cuotas = calc.generar_cronograma(1000, 20, "final", date(2026, 11, 2))
    ce = calc.costo_efectivo(1000, cuotas, date(2026, 11, 2))
    dias = (calc.fecha(cuotas[0]["vence"]) - date(2026, 11, 2)).days
    assert ce["tea"] == pytest.approx(1.2 ** (365 / dias) - 1, rel=1e-6)
    semanal = calc.generar_cronograma(1000, 20, "semanal", date(2026, 11, 2))
    # Devolver capital poco a poco encarece el crédito frente al pago único.
    assert calc.costo_efectivo(1000, semanal, date(2026, 11, 2))["tea"] > ce["tea"]
    assert calc.costo_efectivo(1000, calc.generar_cronograma(1000, 0, "final", date(2026, 11, 2)), date(2026, 11, 2))["tea"] == 0


def test_mora_se_cobra_primero_y_no_se_cuenta_como_cuota():
    db, ana, _ = _db_base()
    db["config"]["mora_diaria_pct"] = 1.0
    p = ops.crear_prestamo(db, ana["id"], 1000, 20, "final", date(2026, 10, 1), hoy_=HOY)
    ev = calc.evaluar_cartera(db, HOY)[p["id"]]
    assert ev["mora_pendiente"] > 0
    mora = ev["mora_pendiente"]
    pago = ops.registrar_pago(db, p["id"], HOY, mora + 100, hoy_=HOY)
    assert pago["monto_mora"] == mora and pago["monto_cuota"] == 100.0
    assert calc.evaluar_cartera(db, HOY)[p["id"]]["saldo"] == 1100.0


def test_validaciones_de_cobro():
    db, ana, _ = _db_base()
    p = ops.crear_prestamo(db, ana["id"], 600, 20, "semanal", date(2026, 11, 1), hoy_=HOY)
    with pytest.raises(ValueError, match="mayor a cero"):
        ops.registrar_pago(db, p["id"], HOY, 0, hoy_=HOY)
    with pytest.raises(ValueError, match="supera la deuda"):
        ops.registrar_pago(db, p["id"], HOY, 721, hoy_=HOY)
    with pytest.raises(ValueError, match="futura"):
        ops.registrar_pago(db, p["id"], date(2026, 11, 20), 10, hoy_=HOY)
    with pytest.raises(ValueError, match="anterior al desembolso"):
        ops.registrar_pago(db, p["id"], date(2026, 10, 1), 10, hoy_=HOY)


def test_anular_cobro_recalcula_saldo_y_caja_y_conserva_folio():
    db, ana, _ = _db_base()
    p = ops.crear_prestamo(db, ana["id"], 600, 20, "semanal", date(2026, 11, 1), hoy_=HOY)
    pago = ops.registrar_pago(db, p["id"], HOY, 180, hoy_=HOY)
    assert calc.resumen_caja(db)["liquidez"] == 5000 - 600 + 180
    with pytest.raises(ValueError, match="motivo"):
        ops.anular_pago(db, pago["id"], " ")
    ops.anular_pago(db, pago["id"], "Se registró dos veces", hoy_=HOY)
    assert calc.resumen_caja(db)["liquidez"] == 5000 - 600
    assert calc.evaluar_cartera(db, HOY)[p["id"]]["saldo"] == 720.0
    assert pago["folio"] == "M3K-P-00001"
    assert ops.registrar_pago(db, p["id"], HOY, 180, hoy_=HOY)["folio"] == "M3K-P-00002"


def test_anular_prestamo_solo_sin_cobros():
    db, ana, _ = _db_base()
    p = ops.crear_prestamo(db, ana["id"], 600, 20, "semanal", date(2026, 11, 1), hoy_=HOY)
    pago = ops.registrar_pago(db, p["id"], HOY, 180, hoy_=HOY)
    with pytest.raises(ValueError, match="cobros registrados"):
        ops.anular_prestamo(db, p["id"], "Error de digitación")
    ops.anular_pago(db, pago["id"], "Prueba", hoy_=HOY)
    ops.anular_prestamo(db, p["id"], "Error de digitación", hoy_=HOY)
    assert calc.resumen_caja(db)["liquidez"] == 5000.0


def test_clientes_validaciones_y_eliminacion():
    db, ana, luis = _db_base()
    with pytest.raises(ValueError, match="8 dígitos"):
        ops.crear_cliente(db, "Carlos Pérez", "123")
    with pytest.raises(ValueError, match="Ya existe"):
        ops.crear_cliente(db, "Otra Persona", "00000001")
    ops.crear_prestamo(db, ana["id"], 100, 20, "final", date(2026, 11, 1), hoy_=HOY)
    with pytest.raises(ValueError, match="desactívalo"):
        ops.eliminar_cliente(db, ana["id"])
    ops.eliminar_cliente(db, luis["id"])
    assert len(db["clientes"]) == 1
    ops.cambiar_estado_cliente(db, ana["id"], False)
    with pytest.raises(ValueError, match="cliente activo"):
        ops.crear_prestamo(db, ana["id"], 100, 20, "final", date(2026, 11, 1), hoy_=HOY)


def test_capital_base_exige_motivo_y_queda_en_auditoria():
    db, _, _ = _db_base()
    with pytest.raises(ValueError, match="motivo"):
        ops.cambiar_capital_base(db, 6000, "")
    ops.cambiar_capital_base(db, 6000, "Aporte del socio")
    assert db["config"]["capital_base"] == 6000.0
    assert "Capital base cambiado" in db["auditoria"][-1]["accion"]


def test_movimientos_de_caja_y_historial():
    db, ana, _ = _db_base()
    ops.registrar_movimiento(db, "aporte", 500, HOY, "Aporte", hoy_=HOY)
    ops.registrar_movimiento(db, "gasto", 40, HOY, "Movilidad", hoy_=HOY)
    assert calc.resumen_caja(db)["liquidez"] == 5000 + 500 - 40
    historial = calc.movimientos_caja(db)
    assert {h["tipo"] for h in historial} == {"Aporte de capital", "Gasto"}


def test_respaldo_json_ida_y_vuelta_y_validaciones():
    db = datos.ejemplo(HOY)
    copia = datos.desde_bytes(datos.a_bytes(db))
    assert calc.resumen_caja(copia) == calc.resumen_caja(db)
    with pytest.raises(ValueError, match="no es JSON"):
        datos.desde_bytes(b"esto no es json")
    with pytest.raises(ValueError, match="lista"):
        datos.desde_bytes(b'{"clientes": 5}')


def test_datos_de_ejemplo_son_coherentes():
    db = datos.ejemplo(HOY)
    evals = calc.evaluar_cartera(db, HOY)
    estados = {e["estado"] for e in evals.values()}
    assert estados == {"vencido", "vigente", "cancelado"}
    ind = calc.indicadores(db, evals, HOY)
    assert ind["por_cobrar"] > 0 and ind["vencido"] > 0
    assert all("00000" in c["dni"] for c in db["clientes"])  # nada de datos reales
    assert calc.cola_cobranza(db, evals, HOY)


def test_semanal_es_siempre_de_4_cuotas():
    cuotas = calc.generar_cronograma(400, 20, "semanal", date(2026, 11, 16))
    assert len(cuotas) == 4 and all(q["monto"] == 120.0 for q in cuotas) and sum(q["monto"] for q in cuotas) == 480.0
    assert calc.fecha(cuotas[-1]["vence"]) == date(2026, 12, 14)
    for n in (1, 2, 3, 5, 8):
        with pytest.raises(ValueError, match="4 cuotas"):
            calc.generar_cronograma(200, 20, "semanal", date(2026, 11, 16), n)


def test_mensual_paga_solo_interes_y_el_capital_al_final():
    # S/ 500 al 20 % por mes
    for meses, esperado in ((1, [600.0]), (2, [100.0, 600.0]), (3, [100.0, 100.0, 600.0])):
        c = calc.generar_cronograma(500, 20, "mensual", date(2026, 11, 3), meses=meses)
        assert [q["monto"] for q in c] == esperado
        assert sum(q["monto"] for q in c) == calc.total_a_pagar(500, 20, meses) == 500 + 100 * meses
        assert [q["capital"] for q in c] == [0.0] * (meses - 1) + [500.0]
    c = calc.generar_cronograma(500, 20, "mensual", date(2026, 11, 3), meses=3)
    assert [calc.fecha(q["vence"]) for q in c] == [date(2026, 12, 3), date(2027, 1, 4), date(2027, 2, 3)]  # 3/1/2027 es domingo: pasa al lunes
    for m in (0, 4):
        with pytest.raises(ValueError, match="1 a 3"):
            calc.generar_cronograma(500, 20, "mensual", date(2026, 11, 3), meses=m)


def test_mensual_el_dia_31_y_los_domingos():
    c = calc.generar_cronograma(500, 20, "mensual", date(2026, 1, 31), meses=3)
    assert [calc.fecha(q["vence"]) for q in c] == [date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]  # el mes corto cae en su último día
    d = calc.generar_cronograma(500, 20, "mensual", date(2026, 10, 15))  # 15/11/2026 es domingo
    assert calc.fecha(d[0]["vence"]) == date(2026, 11, 16)


def test_mensual_el_capital_solo_vuelve_con_la_ultima_cuota():
    db = datos.vacio()
    db["config"]["capital_base"] = 2000.0
    c = ops.crear_cliente(db, "Ana Torres Quispe", "00000001")
    hoy = date(2027, 3, 1)
    pr = ops.crear_prestamo(db, c["id"], 500, 20, "mensual", date(2026, 11, 3), hoy_=date(2026, 11, 3), meses=3)
    assert pr["total"] == 800.0 and pr["meses"] == 3 and len(pr["cuotas"]) == 3
    ops.registrar_pago(db, pr["id"], date(2026, 12, 3), 100, hoy_=hoy)
    ops.registrar_pago(db, pr["id"], date(2027, 1, 3), 100, hoy_=hoy)
    e = calc.evaluar_prestamo(pr, db["pagos"], hoy)
    assert e["capital_recuperado"] == 0 and e["interes_cobrado"] == 200 and e["capital_pendiente"] == 500
    assert calc.indicadores(db, {pr["id"]: e}, hoy)["capital_en_calle"] == 500
    ops.registrar_pago(db, pr["id"], date(2027, 2, 3), 600, hoy_=hoy)
    e = calc.evaluar_prestamo(pr, db["pagos"], hoy)
    assert e["estado"] == "cancelado" and e["capital_recuperado"] == 500 and e["interes_cobrado"] == 300
    assert sorted(calc.capital_por_pago(db).values()) == [0.0, 0.0, 500.0]


def test_mensual_cuadra_en_contabilidad():
    import contabilidad as cont
    db = datos.vacio()
    db["config"]["capital_base"] = 2000.0
    c = ops.crear_cliente(db, "Ana Torres Quispe", "00000001")
    hoy = date(2027, 3, 1)
    pr = ops.crear_prestamo(db, c["id"], 500, 20, "mensual", date(2026, 11, 3), hoy_=date(2026, 11, 3), meses=2)
    ops.registrar_pago(db, pr["id"], date(2026, 12, 3), 100, hoy_=hoy)
    lib = cont.asientos(db, date(2026, 12, 20), date(2026, 12, 20))
    assert cont.balance_general(lib, date(2026, 12, 20))["cuadra"]
    lib = cont.asientos(db, hoy, hoy)
    assert cont.balance_general(lib, hoy)["cuadra"]
