import compartir
import recibo_imagen

D = {"titulo": "Recibo de cobro", "folio": "M3K-P-00005", "anulado": False, "motivo": "", "cronograma": None,
     "bloque1": [("Fecha", "Sáb 21/11/2026"), ("Cliente", "Katia Giovana")],
     "bloque2": [("TOTAL COBRADO", "S/ 75.00", True), ("Saldo del crédito tras este cobro", "S/ 225.00", False)]}


def test_telefono_peru_y_internacional():
    assert compartir.telefono_wa("991 874 021") == "51991874021"
    assert compartir.telefono_wa("+51 923 580 997") == "51923580997"
    assert compartir.telefono_wa("") is None and compartir.telefono_wa("123") is None


def test_mensaje_y_enlace():
    m = compartir.mensaje(D, "KATIA GIOVANA GONZALES")
    assert "Katia" in m and "S/ 75.00" in m and "M3K-P-00005" in m
    assert compartir.enlace_chat("991874021", m).startswith("https://wa.me/51991874021?text=")
    assert compartir.enlace_chat(None, m) is None


def test_imagen_png_valida_y_anulado():
    assert recibo_imagen.generar(D)[:8] == b"\x89PNG\r\n\x1a\n"
    assert recibo_imagen.generar(dict(D, anulado=True, motivo="error de monto"))[:4] == b"\x89PNG"
