"""La selección de cuotas del cobro debe coincidir con cómo se aplica el pago (de la más antigua a la más nueva)."""

import sys
import types
from datetime import date

import calculos as calc
import datos
import operaciones as ops

HOY = date(2026, 11, 15)


def _vista():
    sys.modules.setdefault("streamlit", types.ModuleType("streamlit"))  # en las pruebas puede no estar instalado
    from vistas import cobros
    falso = types.SimpleNamespace(session_state={})
    cobros.st = falso  # la vista solo usa session_state en las funciones de selección
    return cobros, falso


def _escenario():
    """Crédito semanal de 4 cuotas desembolsado el 19/10: al 15/11 hay 3 vencidas (26/10, 2/11, 9/11) y 1 por vencer (16/11)."""
    db = datos.vacio()
    db["config"]["capital_base"] = 2000.0
    c = ops.crear_cliente(db, "Ana Torres Quispe", "00000001")
    pr = ops.crear_prestamo(db, c["id"], 600, 20, "semanal", date(2026, 10, 19), n_cuotas=4, hoy_=HOY)
    e = calc.evaluar_prestamo(pr, [], HOY, 0.0)
    return db, pr, [q for q in e["cuotas"] if q["saldo"] > 0.004]


def _marcadas(cobros, st, pr, pend):
    return [c["n"] for c in pend if st.session_state.get(cobros._clave(pr["id"], c["n"]))]


def test_al_marcar_una_cuota_se_marcan_las_anteriores_y_al_desmarcar_las_posteriores():
    cobros, st = _vista()
    _, pr, pend = _escenario()
    assert len(pend) == 4
    st.session_state[cobros._clave(pr["id"], 3)] = True
    cobros._al_marcar(pr["id"], pend, 3)
    assert _marcadas(cobros, st, pr, pend) == [1, 2, 3]
    st.session_state[cobros._clave(pr["id"], 2)] = False
    cobros._al_marcar(pr["id"], pend, 2)
    assert _marcadas(cobros, st, pr, pend) == [1]


def test_propuesta_inicial_son_las_vencidas_y_el_total_es_lo_que_se_registra():
    cobros, st = _vista()
    db, pr, pend = _escenario()
    cobros._inicializar_seleccion(pr["id"], pend)
    assert _marcadas(cobros, st, pr, pend) == [1, 2, 3]  # las 3 vencidas; la de mañana no
    total = round(sum(c["saldo"] for c in pend if c["n"] in (1, 2, 3)), 2)
    assert total == 540.0
    pago = ops.registrar_pago(db, pr["id"], HOY, total, hoy_=HOY)
    assert pago["cuotas_cubiertas"] == [1, 2, 3]


def test_atajos_y_limpieza():
    cobros, st = _vista()
    _, pr, pend = _escenario()
    cobros._atajo(pr["id"], pend, "proxima")
    assert _marcadas(cobros, st, pr, pend) == [1]
    cobros._atajo(pr["id"], pend, "todas")
    assert _marcadas(cobros, st, pr, pend) == [1, 2, 3, 4]
    cobros._atajo(pr["id"], pend, "vencidas")
    assert _marcadas(cobros, st, pr, pend) == [1, 2, 3]
    cobros._limpiar_seleccion(pr["id"])
    assert not any(str(k).startswith("cq_") for k in st.session_state)
    # al volver a un crédito sin casillas guardadas se vuelve a proponer la selección
    cobros._inicializar_seleccion(pr["id"], pend)
    assert _marcadas(cobros, st, pr, pend) == [1, 2, 3]
