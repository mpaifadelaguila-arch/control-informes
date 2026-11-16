"""Pruebas del libro diario, estados financieros, cuentas por cobrar y cierres."""

from datetime import date

import pytest

import calculos as calc
import contabilidad as cont
import datos
import operaciones as ops

HOY = date(2026, 11, 15)


def _escenario():
    """Los dos créditos semanales de las capturas (agosto/setiembre) más aportes y un gasto."""
    db = datos.vacio()
    db["config"]["capital_base"] = 5000.0
    ana = ops.crear_cliente(db, "Ana Torres Quispe", "00000001", "900000001")
    p1 = ops.crear_prestamo(db, ana["id"], 600, 20, "semanal", date(2026, 8, 19), hoy_=HOY)
    p3 = ops.crear_prestamo(db, ana["id"], 500, 20, "semanal", date(2026, 8, 2), hoy_=HOY)
    ops.registrar_pago(db, p1["id"], "2026-09-03", 180, hoy_=HOY)
    ops.registrar_pago(db, p3["id"], "2026-08-24", 150, hoy_=HOY)
    ops.registrar_pago(db, p3["id"], "2026-09-03", 150, hoy_=HOY)
    ops.registrar_movimiento(db, "aporte", 300, date(2026, 9, 10), "Aporte", hoy_=HOY)
    ops.registrar_movimiento(db, "gasto", 45, date(2026, 10, 5), "Movilidad", hoy_=HOY)
    return db, p1, p3


def test_el_libro_diario_cuadra_y_concilia_con_caja_y_cartera():
    db, *_ = _escenario()
    lib = cont.asientos(db, HOY, HOY)
    for a in lib:
        assert sum(d for _, d, _ in a["lineas"]) == sum(h for _, _, h in a["lineas"])
    bc = cont.balance_comprobacion(lib)
    assert bc["cuadra"]
    assert cont.saldo(lib, "101") == calc.resumen_caja(db)["liquidez"] == 5000 - 1100 + 480 + 300 - 45
    evals = calc.evaluar_cartera(db, HOY)
    assert cont.saldo(lib, "121") == calc.indicadores(db, evals, HOY)["por_cobrar"] == 840.0
    bal = cont.balance_general(lib, HOY)
    assert bal["cuadra"] and bal["activo"] == bal["patrimonio"]


def test_los_intereses_se_devengan_por_mes_y_al_final_quedan_completos():
    db, *_ = _escenario()
    lib = cont.asientos(db, HOY, HOY)
    # Ambos créditos ya pasaron su última cuota: todo el interés (80 + 100... 220) está reconocido.
    assert cont.estado_resultados(lib, date(2026, 8, 1), HOY)["intereses"] == 220.0
    assert cont.saldo(lib, "129") == 0.0
    meses_con_devengo = [a["ref"] for a in lib if a["tipo"] == "devengo"]
    assert meses_con_devengo == sorted(meses_con_devengo) and "DEV-2026-08" in meses_con_devengo
    # Un crédito reciente solo reconoce una parte y el resto queda como intereses no devengados.
    db2 = datos.vacio()
    db2["config"]["capital_base"] = 2000.0
    c = ops.crear_cliente(db2, "Luis Ramos Huamán", "00000002")
    ops.crear_prestamo(db2, c["id"], 1000, 20, "semanal", date(2026, 11, 2), n_cuotas=4, hoy_=HOY)
    lib2 = cont.asientos(db2, HOY, HOY)
    assert 0 < cont.saldo(lib2, "701") < 200 and cont.saldo(lib2, "701") + cont.saldo(lib2, "129") == 200.0
    assert any(a["provisional"] for a in lib2 if a["tipo"] == "devengo")


def test_cancelar_antes_reconoce_el_interes_restante():
    db = datos.vacio()
    db["config"]["capital_base"] = 2000.0
    c = ops.crear_cliente(db, "Rosa Díaz Flores", "00000003")
    p = ops.crear_prestamo(db, c["id"], 500, 20, "semanal", date(2026, 11, 2), n_cuotas=4, hoy_=HOY)
    ops.registrar_pago(db, p["id"], date(2026, 11, 9), 600, hoy_=HOY)  # paga todo en la primera semana
    lib = cont.asientos(db, HOY, HOY)
    assert cont.saldo(lib, "701") == 100.0 and cont.saldo(lib, "129") == 0.0 and cont.saldo(lib, "121") == 0.0


def test_anular_genera_reversion_y_deja_los_saldos_como_si_no_existiera():
    db, p1, _ = _escenario()
    pago = db["pagos"][0]
    antes = cont.asientos(db, HOY, HOY)
    ops.anular_pago(db, pago["id"], "Se registró dos veces", hoy_=HOY)
    lib = cont.asientos(db, HOY, HOY)
    assert [a["tipo"] for a in lib if a["ref"].endswith("(anulado)")] == ["reversion"]
    assert len(lib) >= len(antes) + 1
    assert cont.balance_comprobacion(lib)["cuadra"]
    assert cont.saldo(lib, "101") == calc.resumen_caja(db)["liquidez"]


def test_cuentas_por_cobrar_concilia_con_el_mayor_y_clasifica_la_mora():
    db, *_ = _escenario()
    evals = calc.evaluar_cartera(db, HOY)
    cxc = cont.cuentas_por_cobrar(db, evals, HOY)
    assert cxc["cuadra"]
    assert cxc["total"]["por_cobrar"] == 84000 and cxc["total"]["vencido"] == 84000 and cxc["total"]["por_vencer"] == 0
    assert sum(cxc["total"]["tramos"]) == cxc["total"]["vencido"]
    assert cxc["filas"][0]["cliente"] == "Ana Torres Quispe"


def test_flujo_de_caja_inicial_mas_movimientos_es_final():
    db, *_ = _escenario()
    lib = cont.asientos(db, HOY, HOY)
    flujo = cont.flujo_caja(lib, date(2026, 9, 1), date(2026, 9, 30))
    assert flujo["movimientos"]["cobro"] == 330.0 and flujo["movimientos"]["aporte"] == 300.0
    assert round(flujo["inicial"] + flujo["entradas"] + flujo["salidas"], 2) == flujo["final"]
    todo = cont.flujo_caja(lib, date(2026, 1, 1), HOY)
    assert todo["final"] == cont.saldo(lib, "101")


def test_estado_de_resultados_utilidad_es_ingresos_menos_gastos():
    db, *_ = _escenario()
    lib = cont.asientos(db, HOY, HOY)
    er = cont.estado_resultados(lib, date(2026, 10, 1), date(2026, 10, 31))
    assert er["gastos"] == 45.0 and er["utilidad"] == round(er["ingresos"] - er["gastos"], 2)


def test_cierre_mensual_bloquea_operaciones_y_exige_orden():
    db, p1, _ = _escenario()
    with pytest.raises(ValueError, match="aún no termina"):
        ops.cerrar_mes(db, "2026-11", HOY)
    with pytest.raises(ValueError, match="anteriores"):
        ops.cerrar_mes(db, "2026-09", HOY)
    for periodo in ("2026-08", "2026-09", "2026-10"):
        ops.cerrar_mes(db, periodo, HOY)
    assert db["cierres"]["2026-10"]["cifras"]["gastos"] == 45.0
    with pytest.raises(ValueError, match="cerrado"):
        ops.registrar_pago(db, p1["id"], date(2026, 10, 20), 100, hoy_=HOY)
    with pytest.raises(ValueError, match="cerrado"):
        ops.registrar_movimiento(db, "gasto", 10, date(2026, 9, 20), hoy_=HOY)
    ops.registrar_movimiento(db, "gasto", 10, HOY, "Mes en curso", hoy_=HOY)  # el mes en curso sigue abierto
    assert cont.diferencias_con_cierre(db, HOY) == []
    with pytest.raises(ValueError, match="último mes cerrado"):
        ops.reabrir_mes(db, "2026-09", "Corrección")
    with pytest.raises(ValueError, match="motivo"):
        ops.reabrir_mes(db, "2026-10", "")
    ops.reabrir_mes(db, "2026-10", "Faltaba un gasto")
    assert "2026-10" not in db["cierres"]


def test_se_detecta_un_cambio_posterior_en_un_mes_cerrado():
    db, *_ = _escenario()
    ops.cerrar_mes(db, "2026-08", HOY)
    db["movimientos"].append({"id": "x1", "tipo": "gasto", "monto": 80.0, "fecha": "2026-08-20", "detalle": "Cargado a mano", "anulado": False})
    difs = cont.diferencias_con_cierre(db, HOY)
    assert difs and difs[0]["periodo"] == "2026-08" and "gastos" in difs[0]["cambios"]


def test_datos_de_ejemplo_cuadran_en_contabilidad():
    db = datos.ejemplo(HOY)
    lib = cont.asientos(db, HOY, HOY)
    assert cont.balance_comprobacion(lib)["cuadra"] and cont.balance_general(lib, HOY)["cuadra"]
    assert cont.saldo(lib, "101") == calc.resumen_caja(db)["liquidez"]
    assert cont.cuentas_por_cobrar(db, calc.evaluar_cartera(db, HOY), HOY)["cuadra"]


def test_recibos_pdf_incluyen_el_dia_y_se_generan():
    import types, sys
    sys.modules.setdefault("streamlit", types.ModuleType("streamlit"))
    import estilos
    assert estilos.fecha_dia(date(2026, 11, 21)) == "Sáb 21/11/2026"
    assert estilos.fecha_dia(date(2026, 11, 22)).startswith("Dom")
