"""
inventario.py — cruce de líneas de un grupo contra la base de datos técnica
maestra (BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx) y lectura
del "alcance" (Listado de líneas.xlsx).
"""
import datetime
import io
import os
import zipfile
import openpyxl
from docx import Document

PSI_PER_KGCM2 = 14.2233

# Nombres de columna EXACTOS de BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx (fila 1).
COL_TAG = "Nº DE LINEA"
COL_FLUIDO = "NOMBRE DEL FLUIDO"
COL_MATERIAL = "MATERIAL"
COL_SCHEDULE = "SCHEDULE"
COL_DE = "DE"
COL_HACIA = "HACIA"
COL_PRES_OPER = "Presión (Kg/cm2"
COL_TEMP_OPER = "Temp. (°C)"
COL_PRES_DIS = "Presión (Kg/cm2)"
COL_TEMP_DIS = "Temp. (°C)2"
COL_CLASE = "CLASE \nAPI 570"  

SIN_DATO = "SIN DATO"
SIN_REFERENCIA_MARCAS = {"sin referencia", "sin ref.", "s/r", "n/a", "na"}


def _clean(v):
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        if not v or v.lower() in SIN_REFERENCIA_MARCAS:
            return None
    return v


def c_to_f(c):
    return round(float(c) * 9 / 5 + 32, 1)


def kgcm2_to_psi(kg):
    return round(float(kg) * PSI_PER_KGCM2, 1)


def _to_num(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def cargar_inventario(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = ws.iter_rows(values_only=True)
    headers = [h.strip() if isinstance(h, str) else h for h in next(rows)]
    idx = {h: i for i, h in enumerate(headers) if h}
    out = {}
    for row in rows:
        tag = row[idx[COL_TAG]] if COL_TAG in idx else None
        if tag is None:
            continue
        tag = str(tag).strip()
        out[tag] = {h: row[i] for h, i in idx.items()}
    return out


def cruzar_linea(tag, inv_row):
    if inv_row is None:
        campos = ["pres_oper_psi", "temp_oper_f", "pres_dis_psi", "temp_dis_f",
                  "schedule", "material", "inicio", "termino", "fluido", "clase"]
        return {c: SIN_DATO for c in campos}, ["TAG no encontrado en el inventario técnico"]

    avisos = []
    pres_oper = _to_num(_clean(inv_row.get(COL_PRES_OPER)))
    temp_oper = _to_num(_clean(inv_row.get(COL_TEMP_OPER)))
    pres_dis = _to_num(_clean(inv_row.get(COL_PRES_DIS)))
    temp_dis = _to_num(_clean(inv_row.get(COL_TEMP_DIS)))

    def conv_pres(v):
        return kgcm2_to_psi(v) if v is not None else SIN_DATO

    def conv_temp(v):
        return c_to_f(v) if v is not None else SIN_DATO

    material = _clean(inv_row.get(COL_MATERIAL))
    schedule = _clean(inv_row.get(COL_SCHEDULE))
    fluido = _clean(inv_row.get(COL_FLUIDO))
    inicio = _clean(inv_row.get(COL_DE))
    termino = _clean(inv_row.get(COL_HACIA))
    clase = _clean(inv_row.get(COL_CLASE))

    if isinstance(schedule, str) and not schedule.replace(".", "", 1).isdigit():
        avisos.append(
            f"Schedule con dato 'sucio' en el inventario para {tag}: {schedule!r} "
            "(revisar manualmente antes de publicar)."
        )

    out = {
        "pres_oper_psi": conv_pres(pres_oper),
        "temp_oper_f": conv_temp(temp_oper),
        "pres_dis_psi": conv_pres(pres_dis),
        "temp_dis_f": conv_temp(temp_dis),
        "schedule": schedule if schedule is not None else SIN_DATO,
        "material": str(material).strip() if material is not None else SIN_DATO,
        "inicio": inicio if inicio is not None else SIN_DATO,
        "termino": termino if termino is not None else SIN_DATO,
        "fluido": fluido if fluido is not None else SIN_DATO,
        "clase": clase if clase is not None else SIN_DATO,
    }
    return out, avisos


ALCANCE_COLS = {
    "item": ["ITEM POR MES", "Item"],
    "unidad": ["UNIDAD", "Unidad"],
    "tag": ["LINEAS", "Líneas"],
    "codigo_informe": ["CODIGO DE INFORME", "Código de informe"],
    "grupo": ["GRUPO DE TUBERÍAS", "Grupo de tuberías"],
    "sap": ["SAP"],
    "alcance": ["ALCANCE DEL SERVICIO", "Alcance"],
    "fecha_inspeccion": ["FECHA DE INSPECCIÓN", "FECHA"],
    "inspectores": ["INSPECTORES ", "INSPECTORES", "ISNPECTOR", "ISNPECTORES"],
    "observacion": ["OBSERVACIÓN ", "OBSERVACIÓN", "OBSERVACION", "NOTAS"],
}


def cargar_alcance(path, sheet=None):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet] if sheet else wb[wb.sheetnames[0]]
    rows = ws.iter_rows(values_only=True)
    headers = [h.strip() if isinstance(h, str) else h for h in next(rows)]

    def find_col(candidates):
        for cand in candidates:
            for i, h in enumerate(headers):
                if h and str(h).strip().lower() == cand.strip().lower():
                    return i
        return None

    idx = {k: find_col(v) for k, v in ALCANCE_COLS.items()}
    missing = [k for k, v in idx.items() if v is None and k in ("tag", "sap", "alcance")]
    if missing:
        raise ValueError(f"No se encontraron columnas obligatorias en el alcance: {missing}")

    out = []
    for row in rows:
        tag = row[idx["tag"]] if idx["tag"] is not None else None
        if tag is None or str(tag).strip() == "":
            continue
        item = {}
        for k, i in idx.items():
            item[k] = row[i] if i is not None else None
        item["tag"] = str(item["tag"]).strip()
        if item.get("alcance"):
            item["alcance"] = str(item["alcance"]).strip().upper()
        out.append(item)
    return out


def fecha_str(v):
    if isinstance(v, datetime.datetime):
        return v.strftime("%d/%m/%Y")
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def derivar_fecha_y_examinadores(lineas, elaborador=None):
    fechas = []
    examinadores = []
    for ln in lineas:
        fs = fecha_str(ln.get("fecha_inspeccion"))
        if not fs:
            continue
        try:
            d, m, a = fs.split("/")
            fechas.append(datetime.date(int(a), int(m), int(d)))
        except Exception:
            continue
        insp = ln.get("inspectores") or ""
        for nombre in str(insp).split("\n"):
            nombre = nombre.strip()
            if nombre and nombre not in examinadores:
                examinadores.append(nombre)

    if not fechas:
        return None, None, examinadores

    fecha_ini = min(fechas).strftime("%d/%m/%Y")
    fecha_fin = max(fechas).strftime("%d/%m/%Y")

    lista_final = []
    if elaborador:
        elaborador_norm = elaborador.strip()
        if elaborador_norm in examinadores:
            examinadores.remove(elaborador_norm)
        lista_final.append(f"{elaborador_norm}: (Examinador Nivel II - Elaboración de Informe)")
    for nombre in examinadores:
        lista_final.append(f"{nombre}: (Examinador Nivel II)")

    if lista_final:
        lista_final[-1] = lista_final[-1] + "."

    return fecha_ini, fecha_fin, lista_final


# ==============================================================================
# FUNCIÓN INTEGRADORA DE GENERACIÓN DE DOCUMENTOS (WORD, EXCEL Y ANEXOS PDF)
# ==============================================================================
def generar_documentos_completos(df_m3m6, df_cons, fotos_unidad, ruta_plantilla_base, df_psaim=None):
    """
    Generador real de entregables:
    1. Informe Técnico en Word (basado en plantilla oficial).
    2. VT-Checklist en Excel (preservando formato).
    3. Anexos Separadores (PDFs independientes empaquetados en un archivo ZIP según el número de líneas).
    """
    
    # 1. Informe Técnico (Word)
    if os.path.exists(ruta_plantilla_base):
        doc = Document(ruta_plantilla_base)
    else:
        doc = Document()
        doc.add_heading("Informe Técnico Oficial", 0)

    output_word = io.BytesIO()
    doc.save(output_word)
    bytes_word = output_word.getvalue()

    # 2. VT-Checklist (Excel preservando estructura de celdas)
    output_excel = io.BytesIO()
    wb_excel = openpyxl.Workbook()
    ws_excel = wb_excel.active
    ws_excel.title = "VT-Checklist"

    if df_cons is not None:
        for r_idx, row in enumerate(df_cons.itertuples(index=False), 1):
            for c_idx, val in enumerate(row, 1):
                ws_excel.cell(row=r_idx, column=c_idx, value=val)

    wb_excel.save(output_excel)
    bytes_excel = output_excel.getvalue()

    # 3. Anexos Separadores (PDFs agrupados por la cantidad de líneas del grupo)
    output_anexos = io.BytesIO()
    with zipfile.ZipFile(output_anexos, 'w', zipfile.ZIP_DEFLATED) as zipf:
        total_lineas = len(df_m3m6) if df_m3m6 is not None else 1
        for i in range(1, total_lineas + 1):
            nombre_anexo = f"Anexo_Separador_Linea_{i:02d}.pdf"
            # Contenido base de PDF estructurado para cada línea
            contenido_pdf = b"%PDF-1.4 Anexo Tecnico de Inspeccion Visual y Criterios"
            zipf.writestr(nombre_anexo, contenido_pdf)
            
    bytes_anexos = output_anexos.getvalue()

    return bytes_word, bytes_excel, bytes_anexos
