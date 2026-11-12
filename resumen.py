"""Resumen y balance total de los dos planes (sin Streamlit)."""

import io

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# (clave en kpis, etiqueta). Todas cuentan informes salvo las de líneas.
FILAS = [
    ("informes", "Informes totales"),
    ("finalizados", "Informes finalizados"),
    ("pend_elaborar", "Pendientes de elaborar"),
    ("pend_inspeccion", "Campo · pend. inspección"),
    ("por_elaborar", "Gabinete · por elaborar"),
    ("en_proceso", "Gabinete · en elaboración"),
    ("por_revisar", "Especialista · por revisar"),
    ("revisados", "Especialista · revisados"),
    ("en_revision", "Cliente · en revisión"),
    ("valorizados", "Cliente · valorizados"),
    ("lineas", "Líneas activas"),
    ("lineas_retiradas", "Líneas retiradas"),
]
# Pendientes que requieren acción, por responsable de la etapa.
ALERTAS = [
    ("pend_inspeccion", "Pend. inspección (campo)"),
    ("por_elaborar", "Por elaborar (gabinete)"),
    ("por_revisar", "Por revisar (especialista)"),
    ("en_revision", "En revisión (cliente)"),
]


def kpis_adicionales(kp):
    """Adapta los KPIs de planes.py (TOTAL) a las mismas claves del plan de líneas."""
    return {
        "informes": kp["informes"],
        "finalizados": kp["finalizados"],
        "pend_elaborar": kp["pend_elaborar"],
        "lineas": kp["puntos"],
        "lineas_retiradas": kp["retirados"],
        "pend_inspeccion": kp["pend_inspeccion"],
        "por_elaborar": kp["pend_elaboracion"],
        "en_proceso": kp["en_proceso"],
        "por_revisar": kp["por_revisar"],
        "revisados": kp["revisados"],
        "en_revision": kp["en_revision"],
        "valorizados": kp["valorizados"],
    }


def total(*ks):
    claves = set().union(*ks)
    return {k: sum(x.get(k, 0) for x in ks) for k in claves}


def avance(k):
    return (k["finalizados"] / k["informes"] * 100) if k["informes"] else 0.0


def comparativo(planes_k):
    """planes_k: dict nombre del plan -> KPIs. Agrega la columna TOTAL."""
    kt = total(*planes_k.values())
    filas = []
    for c, et in FILAS:
        fila = {"INDICADOR": et}
        fila.update({n.upper(): k[c] for n, k in planes_k.items()})
        fila["TOTAL"] = kt[c]
        filas.append(fila)
    av = {"INDICADOR": "% avance (finalizados)"}
    av.update({n.upper(): f"{avance(k):.1f}%" for n, k in planes_k.items()})
    av["TOTAL"] = f"{avance(kt):.1f}%"
    filas.append(av)
    tabla = pd.DataFrame(filas)
    tabla.index = range(1, len(tabla) + 1)
    return tabla


def alertas(planes_k):
    """Pendientes críticos (solo los mayores que cero), de mayor a menor."""
    filas = []
    for c, et in ALERTAS:
        for plan, k in planes_k.items():
            if k[c] > 0:
                filas.append({"PLAN": plan, "PENDIENTE": et, "INFORMES": k[c]})
    filas.sort(key=lambda f: -f["INFORMES"])
    tabla = pd.DataFrame(filas, columns=["PLAN", "PENDIENTE", "INFORMES"])
    tabla.index = range(1, len(tabla) + 1)
    return tabla


def excel_resumen(planes_k, extra=None):
    hojas = {"RESUMEN": comparativo(planes_k), "ALERTAS": alertas(planes_k)}
    hojas.update(extra or {})
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as w:
        for nombre, tabla in hojas.items():
            tabla.to_excel(w, index=False, sheet_name=nombre)
            hoja = w.book[nombre]
            hoja.freeze_panes = "A2"
            relleno = PatternFill("solid", fgColor="0E2A47")
            for c in hoja[1]:
                c.font = Font(color="FFFFFF", bold=True)
                c.fill = relleno
                c.alignment = Alignment(horizontal="center", vertical="center",
                                        wrap_text=True)
            for col in hoja.columns:
                ancho = max(len(str(c.value if c.value is not None else "")) for c in col)
                hoja.column_dimensions[get_column_letter(col[0].column)].width = \
                    min(max(ancho + 2, 12), 40)
    salida.seek(0)
    return salida.getvalue()


ORDEN_PLANES = ["Plan de líneas", "Planes adicionales", "Pescantes y trolleys"]
ORDEN_MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
               "AGOSTO", "SETIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]


def listas_adicionales(res, plan="Planes adicionales", unidad="línea"):
    """Informes de planes adicionales pendientes de inspección / por elaborar.

    ``res`` es el resultado de planes.procesar_planes. Mismo formato que
    lineas_kpis.listas().
    """
    import planes

    informes, activos = res["informes"], res["activos"]

    def armar(estado):
        salida = []
        for _, inf in informes[informes["ESTADO"] == estado].iterrows():
            x = activos[activos["CLAVE"] == inf["CLAVE"]]
            lineas = x[["LINEAS", "SAP", planes.COL_ESTADO, "NOTAS"]].copy()
            lineas.columns = ["LINEAS", "SAP", "ESTADO - ELABORACIÓN ", "NOTAS"]
            lineas["_PEND"] = x[planes.COL_ESTADO].map(
                lambda e: "PENDIENTE INSPECCION" in planes.texto_normalizado(e)
            ).values
            codigo = inf["CODIGO DE INFORME"]
            salida.append({
                "PLAN": plan,
                "UNIT": unidad,
                "ALCANCE": inf["PLAN"],
                "MES": inf["MES"],
                "INFORME": "Sin código de informe" if planes.es_codigo_provisional(codigo) else codigo,
                "IDENTIFICACIÓN": inf["GRUPO DE TUBERÍAS"],
                "RESPONSABLE": inf["RESPONSABLE"] or "Sin asignar",
                "N_LINEAS": len(x),
                "N_PEND": int(lineas["_PEND"].sum()),
                "lineas": lineas.reset_index(drop=True),
            })
        return salida

    return armar(planes.PEND_INSPECCION), armar(planes.PEND_ELABORACION)


def ordenar(items):
    """Plan de líneas primero y, dentro de cada plan, por mes."""
    def clave(i):
        mes = ORDEN_MESES.index(i["MES"]) if i["MES"] in ORDEN_MESES else 99
        return (ORDEN_PLANES.index(i["PLAN"]) if i["PLAN"] in ORDEN_PLANES else 9, mes)
    return sorted(items, key=clave)


def tabla_lista(items, inspeccion):
    """DataFrame para mostrar y lista de detalles (líneas) en el mismo orden."""
    filas, detalles = [], []
    for i in items:
        if inspeccion:
            lineas = f"{i['N_PEND']} de {i['N_LINEAS']} por inspeccionar"
        else:
            u = i.get("UNIT", "línea")
            lineas = f"{i['N_LINEAS']} {u}{'' if i['N_LINEAS'] == 1 else 's'}"
        filas.append({
            "PLAN": i["PLAN"], "MES": i["MES"], "INFORME": i["INFORME"],
            "IDENTIFICACIÓN": i["IDENTIFICACIÓN"], "LÍNEAS": lineas,
            "RESPONSABLE": i["RESPONSABLE"],
        })
        detalles.append(i["lineas"])
    tabla = pd.DataFrame(filas, columns=["PLAN", "MES", "INFORME", "IDENTIFICACIÓN",
                                         "LÍNEAS", "RESPONSABLE"])
    tabla.index = range(1, len(tabla) + 1)
    return tabla, detalles


def filtrar(items, plan, consulta):
    def texto(i):
        return " ".join([i["PLAN"], i["MES"], i["INFORME"], i["IDENTIFICACIÓN"],
                         i["RESPONSABLE"], " ".join(i["lineas"]["LINEAS"].astype(str)),
                         " ".join(i["lineas"]["SAP"].astype(str))])
    q = consulta.strip().upper()
    return [i for i in items
            if (plan == "Todos" or i["PLAN"] == plan) and (not q or q in texto(i).upper())]
