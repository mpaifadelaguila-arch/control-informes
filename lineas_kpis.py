"""KPIs del plan de líneas para el resumen general (sin Streamlit).

Replica el criterio del panel de plan_de_lineas.py (procesar_agrupaciones_y_kpis)
para poder leer los mismos números desde otra página sin ejecutar esa app.
Si cambia el criterio allí, debe cambiarse aquí.
"""

import json
import os
import re

import pandas as pd

COLUMNAS = [
    "ITEM POR MES", "IT2", "UNIDAD", "MES", "LINEAS", "CODIGO DE INFORME",
    "GRUPO DE TUBERÍAS", "SAP", "ALCANCE DEL SERVICIO", "NOTAS",
    "ESTADO - ELABORACIÓN ", "RESPONSABLE", "OBSERVACIÓN", "VALORIZACIÓN",
]
PATRON_ANEXO = re.compile(r"^(.*-RLP-\d+)-\d+-(\d{4})$", flags=re.IGNORECASE)


def norm(valor):
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return ""
    return str(valor).strip().upper().translate(str.maketrans("ÁÉÍÓÚÜÑ", "AEIOUUN"))


def limpio(valor):
    if valor is None or (not isinstance(valor, str) and pd.isna(valor)):
        return ""
    texto = str(valor).strip()
    return texto[:-2] if texto.endswith(".0") else texto


def es_anexo(codigo):
    return bool(PATRON_ANEXO.match(limpio(codigo)))


def es_provisional(codigo):
    c = norm(codigo)
    return c in {"", "-"} or any(
        t in c for t in ("PENDIENTE ASIGNAR", "PENDIENTE DE ASIGNAR", "POR ASIGNAR")
    )


def es_revision_fiabilidad(obs):
    o = norm(obs)
    return "FIABILIDAD" in o and "REVISION" in o


def es_pendiente_inspeccion(fila):
    estado = norm(fila.get("ESTADO - ELABORACIÓN ", ""))
    notas = norm(fila.get("NOTAS", ""))
    obs = norm(fila.get("OBSERVACIÓN", ""))
    return any(
        t in estado or t in notas or t in obs
        for t in ("PENDIENTE COMPLETAR INSPECCION", "PENDIENTE INSPECCION",
                  "FALTA CARPETA", "COMPLETAR INSPECCION")
    )


def cargar(ruta):
    """Lee database_informes.json (la misma base que usa el plan de líneas)."""
    if not os.path.exists(ruta):
        return pd.DataFrame(columns=COLUMNAS)
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            df = pd.DataFrame(json.load(f))
    except Exception:
        return pd.DataFrame(columns=COLUMNAS)
    return preparar(df)


def preparar(df):
    df = df.copy()
    for c in COLUMNAS:
        if c not in df.columns:
            df[c] = ""
    df = df[COLUMNAS].fillna("")
    for c in COLUMNAS:
        df[c] = df[c].map(limpio)
    # «FlAB» (con l minúscula) se escribe FIAB.
    df["CODIGO DE INFORME"] = df["CODIGO DE INFORME"].map(
        lambda c: re.sub(r"(?i)(?<=-)FLAB(?=-)", "FIAB", c)
    )
    return df


def calcular(df):
    """KPIs de informes (únicos) y líneas del plan de líneas."""
    vacio = {k: 0 for k in (
        "informes", "finalizados", "pend_elaborar", "lineas", "lineas_retiradas",
        "pend_inspeccion", "por_elaborar", "en_proceso", "por_revisar",
        "revisados", "en_revision", "valorizados")}
    if df.empty:
        return vacio
    retirado = (
        df["OBSERVACIÓN"].map(lambda v: "RETIRADO" in norm(v))
        | df["NOTAS"].map(lambda v: "RETIRADO" in norm(v))
        | df["VALORIZACIÓN"].map(lambda v: norm(v) == "RETIRADO")
    )
    act = df[~retirado].copy()
    act["CLAVE"] = act.apply(
        lambda f: f"{limpio(f['MES'])}|SIN-CODIGO-GRUPO|{norm(f['GRUPO DE TUBERÍAS'])}"
        if es_provisional(f["CODIGO DE INFORME"])
        else f"{limpio(f['MES'])}|{limpio(f['CODIGO DE INFORME'])}", axis=1)
    act["TIPO"] = act["CODIGO DE INFORME"].map(
        lambda c: "Anexo" if es_anexo(c) else "Principal")
    princ = act[act["TIPO"] == "Principal"]
    estado = act["ESTADO - ELABORACIÓN "].map(norm)
    pend_insp = act.apply(es_pendiente_inspeccion, axis=1)
    claves_pend_insp = set(act.loc[pend_insp, "CLAVE"])
    por_elab = act[estado.str.contains("PENDIENTE ELABORACION")]
    en_proc = act[estado.str.contains("EN PROCESO") & ~act["CLAVE"].isin(claves_pend_insp)]

    unicos, finalizados = set(), set()
    val, fiab, esp_pend, esp_rev = 0, 0, 0, 0
    for _, f in princ.iterrows():
        if not limpio(f["MES"]) or not limpio(f["GRUPO DE TUBERÍAS"]):
            continue
        clave = f["CLAVE"]
        if clave in unicos:
            continue
        unicos.add(clave)
        est = norm(f["ESTADO - ELABORACIÓN "])
        if "FINALIZADO" in est or "100%" in est:
            finalizados.add(clave)
        if norm(f["VALORIZACIÓN"]) == "SI":
            val += 1
            continue
        o = norm(f["OBSERVACIÓN"])
        if es_revision_fiabilidad(o):
            fiab += 1
        if "PENDIENTE REVISION POR EL ESPECIALISTA" in o:
            esp_pend += 1
        if ("REV. POR EL ESPECIALISTA" in o or "REVISION POR EL ESPECIALISTA" in o
                or "REVISADO POR ESPECIALISTA" in o) and "PENDIENTE" not in o:
            esp_rev += 1

    def n_princ(d):
        return d[d["TIPO"] == "Principal"]["CLAVE"].nunique()

    return {
        "informes": len(unicos),
        "finalizados": len(finalizados),
        "pend_elaborar": max(0, len(unicos) - len(finalizados)),
        "lineas": len(act),
        "lineas_retiradas": int(retirado.sum()),
        "pend_inspeccion": n_princ(act[pend_insp]),
        "por_elaborar": n_princ(por_elab),
        "en_proceso": n_princ(en_proc),
        "por_revisar": esp_pend,
        "revisados": esp_rev,
        "en_revision": fiab,
        "valorizados": val,
    }
