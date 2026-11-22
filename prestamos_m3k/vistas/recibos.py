"""Recibos de desembolso y de cobro, con anulación de abonos registrados por error."""

import html

import streamlit as st

import calculos as calc
import datos
import estilos as ui
import operaciones as ops
from vistas import comun


def _datos_recibo(db: dict, tipo: str, r: dict) -> dict:
    """Contenido del recibo, una sola vez, para pantalla y PDF: título, folio, líneas, cronograma y firma."""
    if tipo == "pago":
        pr = ops.buscar(db["prestamos"], r["prestamo_id"])
        cli = ops.buscar(db["clientes"], pr["cliente_id"]) or {}
        cubiertas = ", ".join(str(n) for n in r.get("cuotas_cubiertas", [])) or "abono parcial"
        bloque1 = [("Fecha", ui.fecha_dia(r["fecha"])), ("Cliente", cli.get("nombre", "—")), ("DNI", cli.get("dni", "—")),
                   ("Crédito", f"Préstamo {pr['numero']:04d} ({comun.nombre_modalidad(pr['modalidad'])})"),
                   ("Medio de pago", r["metodo"]), ("Cuotas canceladas", cubiertas)]
        bloque2 = [("Aplicado a cuotas", ui.soles(r["monto_cuota"]), False)]
        if r.get("monto_mora"):
            bloque2.append(("Aplicado a mora", ui.soles(r["monto_mora"]), False))
        bloque2 += [("TOTAL COBRADO", ui.soles(r["monto_cuota"] + r.get("monto_mora", 0)), True),
                    ("Saldo del crédito tras este cobro", ui.soles(r.get("saldo_despues", 0)), False)]
        if r.get("nota"):
            bloque2.append(("Nota", r["nota"], False))
        return {"titulo": "Recibo de cobro", "folio": r["folio"], "anulado": r.get("anulado", False), "motivo": r.get("motivo_anulacion", ""),
                "bloque1": bloque1, "bloque2": bloque2, "cronograma": None, "firma": "Firma de quien recibe"}
    cli = ops.buscar(db["clientes"], r["cliente_id"]) or {}
    bloque1 = [("Fecha", ui.fecha_dia(r["fecha_desembolso"])), ("Cliente", cli.get("nombre", "—")), ("DNI", cli.get("dni", "—")),
               ("Crédito", f"Préstamo {r['numero']:04d}"), ("Forma de entrega", r["entrega"])]
    bloque2 = [("Capital entregado", ui.soles(r["monto"]), True), ("Interés total", (f"{r['tasa']:g} % por mes × {r['meses']} meses = {ui.soles(r['total'] - r['monto'])}" if r.get("meses", 1) > 1 else f"{r['tasa']:g} % = {ui.soles(r['total'] - r['monto'])}"), False),
               ("Total a pagar", ui.soles(r["total"]), False),
               ("Modalidad", f"{comun.nombre_modalidad(r['modalidad'])} · {len(r['cuotas'])} cuota(s)", False)]
    return {"titulo": "Recibo de desembolso", "folio": r["folio_desembolso"], "anulado": r.get("anulado", False), "motivo": r.get("motivo_anulacion", ""),
            "bloque1": bloque1, "bloque2": bloque2,
            "cronograma": [(str(q["n"]), ui.fecha_dia(q["vence"]), ui.soles(q["monto"])) for q in r["cuotas"]], "firma": "Firma del cliente"}


def _fila(etq: str, valor: str, fuerte: bool = False) -> str:
    clase = ' class="f t"' if fuerte else ' class="f"'
    return f"<div{clase}><span>{html.escape(etq)}</span><span>{html.escape(valor)}</span></div>"


def _html_recibo(d: dict) -> str:
    """HTML del recibo para mostrarlo en pantalla (todo el texto va escapado)."""
    partes = [f"<h3>{html.escape(d['titulo'])}</h3>", f"<div>{html.escape(d['folio'])}</div>"]
    if d["anulado"]:
        partes.append('<div class="anul">ANULADO — ' + html.escape(d["motivo"]) + "</div>")
    partes += ["<hr>"] + [_fila(e, v) for e, v in d["bloque1"]] + ["<hr>"] + [_fila(e, v, f) for e, v, f in d["bloque2"]]
    if d["cronograma"]:
        filas = "".join(f"<tr><td>{html.escape(n)}</td><td>{html.escape(f)}</td><td style='text-align:right'>{html.escape(m)}</td></tr>" for n, f, m in d["cronograma"])
        partes += ["<hr><b>Cronograma</b>", f"<table style='width:100%;border-collapse:collapse'>{filas}</table>"]
    else:
        partes.append("<hr>")
    partes.append(f'<div style="margin-top:1.6rem">{html.escape(d["firma"])}: ______________________</div>')
    return "".join(partes)


def _pdf_recibo(d: dict) -> bytes:
    """Recibo en PDF (media hoja A4 vertical, listo para imprimir)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    verde, gris = colors.HexColor("#1F6B4F"), colors.HexColor("#5A6B62")
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=10, leading=13)
    fuerte = ParagraphStyle("fuerte", parent=base, fontName="Helvetica-Bold", fontSize=12, leading=15)
    der = ParagraphStyle("der", parent=base, alignment=2)
    der_f = ParagraphStyle("der_f", parent=fuerte, alignment=2)
    esc = lambda t: html.escape(str(t))

    def linea():
        return HRFlowable(width="100%", thickness=0.6, color=gris, dash=(2, 2), spaceBefore=4, spaceAfter=6)

    def bloque(filas):
        datos_ = [[Paragraph(esc(e), fuerte if f else base), Paragraph(esc(v), der_f if f else der)] for e, v, f in filas]
        t = Table(datos_, colWidths=[62 * mm, 62 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        return t

    elementos = [Paragraph("M3K · PRÉSTAMOS PERSONALES", ParagraphStyle("m", parent=base, fontSize=8, textColor=verde, fontName="Helvetica-Bold")),
                 Paragraph(esc(d["titulo"]), ParagraphStyle("t", parent=base, fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=verde)),
                 Paragraph(esc(d["folio"]), ParagraphStyle("f", parent=base, textColor=gris))]
    if d["anulado"]:
        elementos.append(Paragraph("ANULADO — " + esc(d["motivo"]), ParagraphStyle("a", parent=fuerte, textColor=colors.HexColor("#B3261E"))))
    elementos += [linea(), bloque([(e, v, False) for e, v in d["bloque1"]]), linea(), bloque(d["bloque2"])]
    if d["cronograma"]:
        elementos += [linea(), Paragraph("<b>Cronograma</b>", base), Spacer(1, 3)]
        filas = [["N.º", "Vence", "Cuota"]] + [list(f) for f in d["cronograma"]]
        t = Table(filas, colWidths=[16 * mm, 70 * mm, 38 * mm])
        t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 10), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                               ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEEA")), ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                               ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9AA79F")), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        elementos.append(t)
    elementos += [Spacer(1, 22 * mm), Paragraph(esc(d["firma"]) + ": ______________________________", base)]

    import io
    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=A5, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                      title=f"{d['titulo']} {d['folio']}", author="M3K Préstamos").build(elementos)
    return buffer.getvalue()


def mostrar() -> None:
    db = datos.cargar()
    ui.encabezado("Recibos", "Abre un recibo para guardarlo o imprimirlo. Si un cobro fue un error, anúlalo: la cuota, el saldo y la caja se recalculan.")

    registros = []
    for p in db["pagos"]:
        pr = ops.buscar(db["prestamos"], p["prestamo_id"]) or {}
        registros.append({"id": p["id"], "tipo": "pago", "folio": p["folio"], "fecha": p["fecha"], "cliente": comun.nombre_cliente(db, pr.get("cliente_id", "")),
                          "monto": round(p["monto_cuota"] + p.get("monto_mora", 0), 2), "anulado": p.get("anulado", False), "r": p,
                          "detalle": f"Préstamo {pr.get('numero', 0):04d}"})
    for pr in db["prestamos"]:
        registros.append({"id": pr["id"], "tipo": "desembolso", "folio": pr["folio_desembolso"], "fecha": pr["fecha_desembolso"],
                          "cliente": comun.nombre_cliente(db, pr["cliente_id"]), "monto": pr["monto"], "anulado": pr.get("anulado", False), "r": pr,
                          "detalle": f"Préstamo {pr['numero']:04d}"})
    if not registros:
        ui.vacio("Aún no hay recibos", "Se generan solos al registrar un desembolso o un cobro.")
        return

    c1, c2 = st.columns([1, 2])
    tipo = c1.selectbox("Tipo", ["Todos", "Cobros", "Desembolsos"])
    buscar = c2.text_input("Buscar", placeholder="Cliente o folio").strip().lower()
    lista = [r for r in registros
             if (tipo == "Todos" or (tipo == "Cobros") == (r["tipo"] == "pago"))
             and (not buscar or buscar in r["cliente"].lower() or buscar in r["folio"].lower())]
    lista.sort(key=lambda r: (r["fecha"], r["folio"]))  # el más antiguo primero
    if not lista:
        ui.vacio("Sin resultados", "Cambia el tipo o la búsqueda.")
        return

    ui.tabla(["Folio", "Fecha", "Cliente", "Crédito", "Monto", "Estado"],
             [[r["folio"], ui.fecha_dia(r["fecha"]), r["cliente"], r["detalle"], ui.soles(r["monto"]),
               ui.chip("Anulado", "neutro") if r["anulado"] else ui.chip("Vigente", "ok")] for r in lista[-150:]],
             numericas=(4,), sin_corte=(0, 1, 2, 3), etiqueta="Recibos")
    if len(lista) > 150:
        st.caption(f"Se muestran los 150 más recientes (los anteriores quedan fuera de la lista) de {len(lista)}. Usa la búsqueda para encontrar uno anterior.")

    ids = [r["id"] for r in lista]
    if st.session_state.get("recibo_sel") not in ids:
        st.session_state.pop("recibo_sel", None)
    por_id = {r["id"]: r for r in lista}
    sel = st.selectbox("Abrir recibo", ids, format_func=lambda i: f"{por_id[i]['folio']} · {por_id[i]['cliente']} · {ui.soles(por_id[i]['monto'])}", key="recibo_sel")
    reg = por_id[sel]
    datos_recibo = _datos_recibo(db, reg["tipo"], reg["r"])
    st.markdown(f'<div class="m3k-recibo">{_html_recibo(datos_recibo)}</div>', unsafe_allow_html=True)
    st.download_button("Descargar recibo (PDF)", _pdf_recibo(datos_recibo), file_name=f"{reg['folio']}.pdf", mime="application/pdf",
                       icon=":material/picture_as_pdf:")

    if reg["tipo"] == "pago" and not reg["anulado"]:
        with st.expander("Anular este cobro"):
            st.caption("El folio se conserva como anulado. El saldo del crédito y la caja se recalculan solos.")
            motivo = st.text_input("Motivo de la anulación", key=f"mot_{sel}")
            if st.button("Anular cobro", key=f"anular_{sel}"):
                try:
                    ops.anular_pago(db, sel, motivo)
                except ValueError as e:
                    st.error(str(e))
                else:
                    datos.guardar(db)
                    if st.session_state.get("ultimo_pago", {}).get("id") == sel:
                        st.session_state.pop("ultimo_pago")
                    ui.avisar("ok", f"Cobro {reg['folio']} anulado.")
                    st.rerun()
