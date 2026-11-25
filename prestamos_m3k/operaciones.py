"""Operaciones que modifican la base de datos (un diccionario) con sus validaciones.

Cada función valida, cambia `db`, deja una línea en la auditoría y devuelve el registro
creado. Quien las llama es responsable de guardar con `datos.guardar(db)`. Nada se borra
de verdad salvo clientes sin historial: lo demás se anula y conserva su folio.
"""

from __future__ import annotations

import re
import uuid

import calculos as calc
import contabilidad as cont


def _nuevo_id() -> str:
    return uuid.uuid4().hex[:8]


def _folio(db: dict, clave: str, prefijo: str) -> str:
    db["contadores"][clave] = db["contadores"].get(clave, 0) + 1
    return f"M3K-{prefijo}-{db['contadores'][clave]:05d}"


def _auditar(db: dict, accion: str, detalle: str) -> None:
    db["auditoria"].append({"ts": calc.ahora(), "accion": accion, "detalle": detalle})


def periodo_de(valor) -> str:
    d = calc.fecha(valor)
    return f"{d.year}-{d.month:02d}"


def verificar_abierto(db: dict, valor) -> None:
    """No se registran operaciones con fecha dentro de un mes ya cerrado."""
    periodo = periodo_de(valor)
    if periodo in db.get("cierres", {}):
        anio, mes = periodo.split("-")
        raise ValueError(f"El mes {mes}/{anio} está cerrado. Usa una fecha de un mes abierto o reabre el cierre.")


def verificar_no_futura(valor, hoy_=None, que: str = "La fecha") -> None:
    if calc.fecha(valor) > calc.fecha(hoy_ or calc.hoy()):
        raise ValueError(f"{que} no puede ser futura.")


def buscar(lista: list[dict], id_: str) -> dict | None:
    return next((x for x in lista if x["id"] == id_), None)


# ───────────────────────── clientes ─────────────────────────

def _validar_cliente(db: dict, nombre: str, dni: str, telefono: str, propio: str | None = None) -> tuple[str, str, str]:
    nombre, dni, telefono = nombre.strip(), dni.strip(), re.sub(r"[\s-]", "", telefono)
    if len(nombre) < 3:
        raise ValueError("Escribe el nombre completo del cliente.")
    if not re.fullmatch(r"\d{8}", dni):
        raise ValueError("El DNI debe tener 8 dígitos.")
    if telefono and not re.fullmatch(r"\+?\d{7,12}", telefono):
        raise ValueError("El teléfono debe tener solo números (7 a 12 dígitos).")
    if any(c["dni"] == dni and c["id"] != propio for c in db["clientes"]):
        raise ValueError("Ya existe un cliente con ese DNI.")
    return nombre, dni, telefono


def crear_cliente(db: dict, nombre: str, dni: str, telefono: str = "", direccion: str = "") -> dict:
    nombre, dni, telefono = _validar_cliente(db, nombre, dni, telefono)
    cliente = {"id": _nuevo_id(), "nombre": nombre, "dni": dni, "telefono": telefono,
               "direccion": direccion.strip(), "activo": True, "creado": calc.ahora()}
    db["clientes"].append(cliente)
    _auditar(db, "Cliente creado", f"{nombre} (DNI {dni})")
    return cliente


def editar_cliente(db: dict, cliente_id: str, nombre: str, dni: str, telefono: str = "", direccion: str = "") -> dict:
    cliente = buscar(db["clientes"], cliente_id)
    if not cliente:
        raise ValueError("El cliente no existe.")
    nombre, dni, telefono = _validar_cliente(db, nombre, dni, telefono, propio=cliente_id)
    cliente.update(nombre=nombre, dni=dni, telefono=telefono, direccion=direccion.strip())
    _auditar(db, "Cliente editado", f"{nombre} (DNI {dni})")
    return cliente


def cambiar_estado_cliente(db: dict, cliente_id: str, activo: bool) -> dict:
    cliente = buscar(db["clientes"], cliente_id)
    if not cliente:
        raise ValueError("El cliente no existe.")
    cliente["activo"] = activo
    _auditar(db, "Cliente activado" if activo else "Cliente desactivado", cliente["nombre"])
    return cliente


def eliminar_cliente(db: dict, cliente_id: str) -> None:
    cliente = buscar(db["clientes"], cliente_id)
    if not cliente:
        raise ValueError("El cliente no existe.")
    if any(p["cliente_id"] == cliente_id for p in db["prestamos"]):
        raise ValueError("El cliente tiene créditos registrados: desactívalo en vez de eliminarlo.")
    db["clientes"].remove(cliente)
    _auditar(db, "Cliente eliminado", cliente["nombre"])


# ───────────────────────── préstamos ─────────────────────────

def crear_prestamo(db: dict, cliente_id: str, monto: float, tasa_pct: float, modalidad: str,
                   fecha_desembolso, entrega: str = "Efectivo", n_cuotas: int | None = None, hoy_=None, meses: int | None = None, fin_de_mes: bool = False) -> dict:
    cliente = buscar(db["clientes"], cliente_id)
    if not cliente or not cliente.get("activo", True):
        raise ValueError("Elige un cliente activo.")
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    if tasa_pct < 0:
        raise ValueError("El interés no puede ser negativo.")
    if modalidad not in calc.MODALIDADES:
        raise ValueError("Modalidad no válida.")
    f0 = calc.fecha(fecha_desembolso)
    verificar_no_futura(f0, hoy_, "La fecha de desembolso")
    verificar_abierto(db, f0)
    cuotas = calc.generar_cronograma(monto, tasa_pct, modalidad, f0, n_cuotas, meses, fin_de_mes)  # valida cuotas y meses
    meses_credito = (calc.MESES_MENSUAL[0] if meses is None else meses) if modalidad == "mensual" else 1
    prestamo = {
        "id": _nuevo_id(),
        "numero": db["contadores"].get("prestamo", 0) + 1,
        "cliente_id": cliente_id,
        "monto": round(float(monto), 2),
        "tasa": float(tasa_pct),
        "modalidad": modalidad,
        "fecha_desembolso": f0.isoformat(),
        "entrega": entrega,
        "meses": meses_credito,
        "fin_de_mes": bool(fin_de_mes and modalidad == "mensual"),
        "total": calc.de_centimos(sum(calc.a_centimos(q["monto"]) for q in cuotas)),
        "cuotas": cuotas,
        "anulado": False,
        "creado": calc.ahora(),
    }
    db["contadores"]["prestamo"] = prestamo["numero"]
    prestamo["folio_desembolso"] = _folio(db, "desembolso", "D")
    db["prestamos"].append(prestamo)
    _auditar(db, "Crédito creado",
             f"Préstamo {prestamo['numero']:04d} a {cliente['nombre']}: S/ {prestamo['monto']:.2f} ({modalidad})")
    return prestamo


def anular_prestamo(db: dict, prestamo_id: str, motivo: str, hoy_=None) -> dict:
    prestamo = buscar(db["prestamos"], prestamo_id)
    if not prestamo or prestamo.get("anulado"):
        raise ValueError("El préstamo no existe o ya está anulado.")
    if not motivo.strip():
        raise ValueError("Escribe el motivo de la anulación.")
    if any(p["prestamo_id"] == prestamo_id and not p.get("anulado") for p in db["pagos"]):
        raise ValueError("Tiene cobros registrados: anúlalos primero en Recibos.")
    prestamo["anulado"] = True
    prestamo["motivo_anulacion"] = motivo.strip()
    prestamo["fecha_anulacion"] = calc.fecha(hoy_ or calc.hoy()).isoformat()
    _auditar(db, "Crédito anulado", f"Préstamo {prestamo['numero']:04d}: {motivo.strip()}")
    return prestamo


# ───────────────────────── cobros ─────────────────────────

def registrar_pago(db: dict, prestamo_id: str, fecha_pago, monto: float, metodo: str = "Efectivo",
                   nota: str = "", hoy_=None) -> dict:
    """Registra un cobro. Primero cubre la mora pendiente y el resto va a las cuotas más antiguas."""
    prestamo = buscar(db["prestamos"], prestamo_id)
    if not prestamo or prestamo.get("anulado"):
        raise ValueError("El préstamo no existe o está anulado.")
    f_pago = calc.fecha(fecha_pago)
    if f_pago > calc.fecha(hoy_ or calc.hoy()):
        raise ValueError("La fecha del cobro no puede ser futura.")
    if f_pago < calc.fecha(prestamo["fecha_desembolso"]):
        raise ValueError("La fecha del cobro no puede ser anterior al desembolso.")
    verificar_abierto(db, f_pago)

    mora_pct = float(db["config"].get("mora_diaria_pct", 0) or 0)
    pagos = [p for p in db["pagos"] if not p.get("anulado")]
    antes = calc.evaluar_prestamo(prestamo, pagos, f_pago, mora_pct)

    monto_c = calc.a_centimos(monto)
    mora_c = calc.a_centimos(antes["mora_pendiente"])
    saldo_c = calc.a_centimos(antes["saldo"])
    if monto_c <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    if monto_c > mora_c + saldo_c:
        raise ValueError(f"El monto supera la deuda pendiente (S/ {(mora_c + saldo_c) / 100:.2f}).")

    a_mora = min(monto_c, mora_c)
    a_cuotas = monto_c - a_mora
    pago = {
        "id": _nuevo_id(),
        "folio": _folio(db, "pago", "P"),
        "prestamo_id": prestamo_id,
        "fecha": f_pago.isoformat(),
        "monto_cuota": calc.de_centimos(a_cuotas),
        "monto_mora": calc.de_centimos(a_mora),
        "metodo": metodo,
        "nota": nota.strip(),
        "anulado": False,
        "creado": calc.ahora(),
    }
    despues = calc.evaluar_prestamo(prestamo, pagos + [pago], f_pago, mora_pct)
    antes_pagadas = {c["n"] for c in antes["cuotas"] if c["estado"] == "pagada"}
    pago["cuotas_cubiertas"] = [c["n"] for c in despues["cuotas"] if c["estado"] == "pagada" and c["n"] not in antes_pagadas]
    pago["saldo_despues"] = despues["saldo"]
    pago["cancelo_prestamo"] = calc.a_centimos(despues["saldo"]) == 0 and calc.a_centimos(despues.get("mora_pendiente", 0)) == 0
    db["pagos"].append(pago)
    cliente = buscar(db["clientes"], prestamo["cliente_id"]) or {}
    _auditar(db, "Cobro registrado", f"{pago['folio']} · {cliente.get('nombre', '—')} · S/ {monto_c / 100:.2f}")
    return pago


def anular_pago(db: dict, pago_id: str, motivo: str, hoy_=None) -> dict:
    pago = buscar(db["pagos"], pago_id)
    if not pago or pago.get("anulado"):
        raise ValueError("El cobro no existe o ya está anulado.")
    if not motivo.strip():
        raise ValueError("Escribe el motivo de la anulación.")
    pago["anulado"] = True
    pago["motivo_anulacion"] = motivo.strip()
    pago["fecha_anulacion"] = calc.fecha(hoy_ or calc.hoy()).isoformat()  # la reversión se registra hoy
    _auditar(db, "Cobro anulado", f"{pago['folio']}: {motivo.strip()}")
    return pago


# ───────────────────────── caja ─────────────────────────

TIPOS_MOVIMIENTO = {
    "aporte": "Aporte de capital (entra dinero)",
    "retiro": "Retiro de capital (sale dinero)",
    "gasto": "Gasto (sale dinero)",
    "servicio": "Pago de servicio (sale dinero)",
}


def registrar_movimiento(db: dict, tipo: str, monto: float, fecha_mov, detalle: str = "", hoy_=None) -> dict:
    if tipo not in TIPOS_MOVIMIENTO:
        raise ValueError("Tipo de movimiento no válido.")
    if monto <= 0:
        raise ValueError("El monto debe ser mayor a cero.")
    verificar_no_futura(fecha_mov, hoy_, "La fecha del movimiento")
    verificar_abierto(db, fecha_mov)
    mov = {"id": _nuevo_id(), "tipo": tipo, "monto": round(float(monto), 2),
           "fecha": calc.fecha(fecha_mov).isoformat(), "detalle": detalle.strip(), "anulado": False}
    db["movimientos"].append(mov)
    _auditar(db, "Movimiento de caja", f"{tipo} S/ {mov['monto']:.2f} {mov['detalle']}".strip())
    return mov


def anular_movimiento(db: dict, mov_id: str, hoy_=None) -> None:
    mov = buscar(db["movimientos"], mov_id)
    if not mov or mov.get("anulado"):
        raise ValueError("El movimiento no existe o ya está anulado.")
    mov["anulado"] = True
    mov["fecha_anulacion"] = calc.fecha(hoy_ or calc.hoy()).isoformat()
    _auditar(db, "Movimiento anulado", f"{mov['tipo']} S/ {mov['monto']:.2f}")


def cambiar_capital_base(db: dict, nuevo: float, motivo: str) -> None:
    if nuevo < 0:
        raise ValueError("El capital base no puede ser negativo.")
    if not motivo.strip():
        raise ValueError("Escribe el motivo del cambio: queda en la auditoría.")
    anterior = db["config"].get("capital_base", 0)
    db["config"]["capital_base"] = round(float(nuevo), 2)
    _auditar(db, "Capital base cambiado", f"de S/ {anterior:.2f} a S/ {nuevo:.2f}: {motivo.strip()}")


def guardar_config(db: dict, tasa_default: float, mora_diaria_pct: float) -> None:
    if not (0 <= tasa_default <= 100 and 0 <= mora_diaria_pct <= 5):
        raise ValueError("Revisa los valores: interés 0 a 100 %, mora diaria 0 a 5 %.")
    db["config"].update(tasa_default=float(tasa_default), mora_diaria_pct=float(mora_diaria_pct))
    _auditar(db, "Configuración cambiada", f"interés {tasa_default} %, mora diaria {mora_diaria_pct} %")


# ───────────────────────── cierre mensual ─────────────────────────

def cerrar_mes(db: dict, periodo: str, hoy_=None) -> dict:
    """Cierra un mes: guarda sus cifras y bloquea nuevas operaciones con fecha en ese mes."""
    hoy_ = calc.fecha(hoy_ or calc.hoy())
    fila = next((f for f in cont.estado_periodos(db, hoy_) if f["periodo"] == periodo), None)
    if not fila:
        raise ValueError("Ese mes está fuera del rango de la contabilidad.")
    if fila["estado"] == "cerrado":
        raise ValueError("Ese mes ya está cerrado.")
    if fila["estado"] == "en curso":
        raise ValueError("El mes aún no termina: se puede cerrar desde el día siguiente a su último día.")
    if not fila["puede_cerrar"]:
        raise ValueError("Cierra primero los meses anteriores.")
    cierre = {"cerrado": calc.ahora(), "cifras": cont.instantanea(db, periodo, hoy_)}
    db.setdefault("cierres", {})[periodo] = cierre
    _auditar(db, "Mes cerrado", cont.nombre_mes(periodo))
    return cierre


def reabrir_mes(db: dict, periodo: str, motivo: str) -> None:
    cierres = db.get("cierres", {})
    if periodo not in cierres:
        raise ValueError("Ese mes no está cerrado.")
    if any(p > periodo for p in cierres):
        raise ValueError("Solo se puede reabrir el último mes cerrado.")
    if not motivo.strip():
        raise ValueError("Escribe el motivo: queda en la auditoría.")
    del cierres[periodo]
    _auditar(db, "Mes reabierto", f"{cont.nombre_mes(periodo)}: {motivo.strip()}")
