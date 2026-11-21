"""Las series de los gráficos del inicio deben salir de las mismas cuentas que el resto de la app."""

import sys
import types
from datetime import date

sys.modules.setdefault("streamlit", types.ModuleType("streamlit"))  # en las pruebas puede no estar instalado

import calculos as calc
import contabilidad as cont
import datos
import graficos as g
import operaciones as ops

HOY = date(2026, 11, 15)  # domingo


def _escenario():
    """Semanal de 4 cuotas de 180 que vencen 26/10, 2/11, 9/11 y 16/11; se cobran las dos primeras."""
    db = datos.vacio()
    db["config"]["capital_base"] = 2000.0
    c = ops.crear_cliente(db, "Ana Torres Quispe", "00000001")
    pr = ops.crear_prestamo(db, c["id"], 600, 20, "semanal", date(2026, 10, 19), n_cuotas=4, hoy_=HOY)
    ops.registrar_pago(db, pr["id"], HOY, 360, hoy_=HOY)
    return db, calc.evaluar_cartera(db, HOY)


def test_semanas_comparan_lo_que_vencia_con_lo_cobrado():
    db, ev = _escenario()
    s = calc.cuotas_por_semana(db, ev, HOY)
    assert [x["desde"] for x in s][-2:] == [date(2026, 11, 9), date(2026, 11, 16)]
    assert [(x["esperado"], x["cobrado"]) for x in s] == [(0, 0), (0, 0), (180, 180), (180, 180), (180, 0), (180, 0)]
    assert [x["actual"] for x in s] == [False] * 4 + [True, False]


def test_avance_del_mes():
    db, ev = _escenario()
    assert calc.avance_mes(db, ev, HOY) == {"esperado": 540.0, "cobrado": 180.0, "pct": 180 / 540}


def test_proximos_cobros_saltan_domingos():
    db, ev = _escenario()
    dias = calc.proximos_cobros(db, ev, HOY)
    assert [d["fecha"].weekday() for d in dias] == [0, 1, 2, 3, 4, 5]  # el domingo de hoy no cuenta
    assert dias[0]["fecha"] == date(2026, 11, 16) and dias[0]["monto"] == 180.0 and dias[0]["cuotas"] == 1
    assert all(d["monto"] == 0 for d in dias[1:])


def test_composicion_suma_lo_que_te_deben():
    db, ev = _escenario()
    comp = calc.composicion_cartera(db, ev)
    assert [(c["nombre"], c["monto"]) for c in comp] == [("Al día", 180.0), ("1 a 7 días", 180.0)]
    assert sum(c["monto"] for c in comp) == calc.indicadores(db, ev, HOY)["por_cobrar"]


def test_serie_de_caja_termina_en_la_liquidez():
    db, _ = _escenario()
    serie = cont.serie_caja(cont.asientos(db, HOY, HOY), HOY, 30)
    assert len(serie) == 31 and serie[-1] == (HOY, calc.resumen_caja(db)["liquidez"])
    assert serie[0][1] == 0  # la caja se abre el día del capital base, después del inicio de la ventana


def test_graficos_generan_html_de_una_linea_sin_romperse():
    db, ev = _escenario()
    cuerpo = [g.avance(180, 540, "noviembre"), g.proximos_dias(calc.proximos_cobros(db, ev, HOY), HOY), g.semanas(calc.cuotas_por_semana(db, ev, HOY)),
              g.dona(calc.composicion_cartera(db, ev), "S/ 360", "te deben"),
              g.linea(cont.serie_caja(cont.asientos(db, HOY, HOY), HOY, 30)), g.panel("Título <b>", "<i>x</i>", "pie")]
    for html in cuerpo:
        assert "\n\n" not in html
    assert "&lt;b&gt;" in cuerpo[-1]  # el título se escapa


def test_reparto_y_columnas_de_reportes():
    r = g.reparto([("Capital", 150.0, "#1D5F9A"), ("Ganancia", 30.0, "#1E7B4B")])
    assert "83 %" in r and "17 %" in r and "\n\n" not in r
    c = g.columnas([("9/11", 180.0, False), ("16/11", 0.0, True)])
    assert c.count('class="col"') == 1 and "180" in c and "\n\n" not in c  # la semana sin cobros no dibuja columna
    assert g.columnas([]) and g.reparto([("Capital", 0.0, "#000")])  # sin datos no se rompe


def test_historial_de_caja_con_saldo_termina_en_la_liquidez():
    db, _ = _escenario()
    ops.registrar_movimiento(db, "gasto", 25, HOY, "Pasajes", hoy_=HOY)
    h = calc.movimientos_con_saldo(db)
    assert h[-1]["saldo"] == calc.resumen_caja(db)["liquidez"]
    assert h[0]["saldo"] == 2000.0 - 600.0  # primer movimiento: el desembolso sobre el capital base
    assert [x["tipo"] for x in h] == ["Desembolso", "Cobro", "Gasto"]


def test_cascada_html():
    html = g.cascada([("Capital base", 2000.0, "mas"), ("Créditos entregados", 600.0, "menos"), ("Saldo disponible", 1400.0, "total")])
    assert "+ S/ 2,000.00" in html and "− S/ 600.00" in html and "\n\n" not in html


def test_tarjetas_de_cuotas_por_estado():
    db, ev = _escenario()
    cuotas = next(iter(ev.values()))["cuotas"]
    html = g.cuotas(cuotas)
    assert html.count("Cuota ") == 4 and "Pagada" in html and "días de atraso" in html and "\n\n" not in html
    assert g.avance(180, 720, detalle="del total a pagar").count("del total a pagar") == 1


def test_semanas_con_palabras_y_todo_al_dia():
    db, ev = _escenario()
    html = g.semanas(calc.cuotas_por_semana(db, ev, HOY))
    assert "Faltan S/ 180.00" in html and "Por cobrar" in html and "Completo" in html and "Esta semana" in html
    assert "nada está vencido" in g.todo_al_dia(660.0) and "S/ 660.00" in g.todo_al_dia(660.0)
