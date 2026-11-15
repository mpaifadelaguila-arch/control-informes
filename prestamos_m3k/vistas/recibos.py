"""Recibos de desembolso y de cobro, con anulación de abonos registrados por error."""

import html

import streamlit as st

import calculos as calc
import datos
import estilos as ui
import operaciones as ops
from vistas import comun


def _fila(etq: str, valor: str, fuerte: bool = False) -> str:
    clase = ' class="f t"' if fuerte else ' class="f"'
    return f"<div{clase}><span>{html.escape(etq)}</span><span>{html.escape(valor)}</span></div>"


def _cuerpo_recibo(db: dict, tipo: str, r: dict) -> str:
    """HTML interno del recibo (todo el texto va escapado)."""
    if tipo == "pago":
        pr = ops.buscar(db["prestamos"], r["prestamo_id"])
        cli = ops.buscar(db["clientes"], pr["cliente_id"]) or {}
        cubiertas = ", ".join(str(n) for n in r.get("cuotas_cubiertas", [])) or "abono parcial"
        partes = [
            "<h3>Recibo de cobro</h3>", f"<div>{html.escape(r['folio'])}</div>",
            '<div class="anul">ANULADO — ' + html.escape(r.get("motivo_anulacion", "")) + "</div>" if r.get("anulado") else "",
            "<hr>", _fila("Fecha", ui.fecha_txt(r["fecha"])), _fila("Cliente", cli.get("nombre", "—")), _fila("DNI", cli.get("dni", "—")),
            _fila("Crédito", f"Préstamo {pr['numero']:04d} ({comun.nombre_modalidad(pr['modalidad'])})"),
            _fila("Medio de pago", r["metodo"]), _fila("Cuotas canceladas", cubiertas), "<hr>",
            _fila("Aplicado a cuotas", ui.soles(r["monto_cuota"])),
        ]
        if r.get("monto_mora"):
            partes.append(_fila("Aplicado a mora", ui.soles(r["monto_mora"])))
        partes += [_fila("TOTAL COBRADO", ui.soles(r["monto_cuota"] + r.get("monto_mora", 0)), True),
                   _fila("Saldo del crédito tras este cobro", ui.soles(r.get("saldo_despues", 0))),
                   '<hr><div style="margin-top:1.6rem">Firma de quien recibe: ______________________</div>']
        if r.get("nota"):
            partes.insert(-1, _fila("Nota", r["nota"]))
        return "".join(partes)
    cli = ops.buscar(db["clientes"], r["cliente_id"]) or {}
    cuotas = "".join(
        f"<tr><td>{q['n']}</td><td>{ui.fecha_txt(q['vence'])}</td><td style='text-align:right'>{html.escape(ui.soles(q['monto']))}</td></tr>"
        for q in r["cuotas"]
    )
    return "".join([
        "<h3>Recibo de desembolso</h3>", f"<div>{html.escape(r['folio_desembolso'])}</div>",
        '<div class="anul">ANULADO — ' + html.escape(r.get("motivo_anulacion", "")) + "</div>" if r.get("anulado") else "",
        "<hr>", _fila("Fecha", ui.fecha_txt(r["fecha_desembolso"])), _fila("Cliente", cli.get("nombre", "—")), _fila("DNI", cli.get("dni", "—")),
        _fila("Crédito", f"Préstamo {r['numero']:04d}"), _fila("Forma de entrega", r["entrega"]), "<hr>",
        _fila("Capital entregado", ui.soles(r["monto"]), True), _fila("Interés total", f"{r['tasa']:g} % = {ui.soles(r['total'] - r['monto'])}"),
        _fila("Total a pagar", ui.soles(r["total"])), _fila("Modalidad", f"{comun.nombre_modalidad(r['modalidad'])} · {len(r['cuotas'])} cuota(s)"),
        "<hr><b>Cronograma</b>", f"<table style='width:100%;border-collapse:collapse'>{cuotas}</table>",
        '<div style="margin-top:1.6rem">Firma del cliente: ______________________</div>',
    ])


def _html_descargable(cuerpo: str) -> bytes:
    estilo = ("body{font-family:Arial,sans-serif;max-width:520px;margin:2rem auto;color:#1B2A22}"
              ".f{display:flex;justify-content:space-between;gap:1rem;padding:.18rem 0}.t{font-size:1.2rem;font-weight:700}"
              ".anul{color:#9B2C22;font-weight:700}hr{border:0;border-top:1px dashed #999;margin:.8rem 0}td{padding:.15rem .3rem}")
    return f'<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>Recibo M3K</title><style>{estilo}</style></head><body>{cuerpo}</body></html>'.encode("utf-8")


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
    lista.sort(key=lambda r: (r["fecha"], r["folio"]), reverse=True)
    if not lista:
        ui.vacio("Sin resultados", "Cambia el tipo o la búsqueda.")
        return

    ui.tabla(["Folio", "Fecha", "Cliente", "Crédito", "Monto", "Estado"],
             [[r["folio"], ui.fecha_txt(r["fecha"]), r["cliente"], r["detalle"], ui.soles(r["monto"]),
               ui.chip("Anulado", "neutro") if r["anulado"] else ui.chip("Vigente", "ok")] for r in lista[:150]],
             numericas=(4,), etiqueta="Recibos")
    if len(lista) > 150:
        st.caption(f"Se muestran los 150 más recientes de {len(lista)}. Usa la búsqueda para encontrar uno anterior.")

    ids = [r["id"] for r in lista]
    if st.session_state.get("recibo_sel") not in ids:
        st.session_state.pop("recibo_sel", None)
    por_id = {r["id"]: r for r in lista}
    sel = st.selectbox("Abrir recibo", ids, format_func=lambda i: f"{por_id[i]['folio']} · {por_id[i]['cliente']} · {ui.soles(por_id[i]['monto'])}", key="recibo_sel")
    reg = por_id[sel]
    cuerpo = _cuerpo_recibo(db, reg["tipo"], reg["r"])
    st.markdown(f'<div class="m3k-recibo">{cuerpo}</div>', unsafe_allow_html=True)
    st.download_button("Descargar recibo para imprimir", _html_descargable(cuerpo), file_name=f"{reg['folio']}.html", mime="text/html",
                       icon=":material/download:")

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
