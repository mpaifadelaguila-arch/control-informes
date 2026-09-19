"""
checklist.py — lee y parcha el VT-CHECK LIST real (formato estándar fijo
AD-UN05-TL-TUB-VT, una hoja por línea inspeccionada). Este formato NO se
modifica: no se agregan columnas, filas ni hojas. Layout de cada hoja:

    Q9  -> TAG de la línea inspeccionada (identifica la hoja).
    E9  -> TAG del circuito/grupo.
    E10 -> Unidad.
    Q10 -> Examinador(es).

    A partir de la fila 15: una fila por cada uno de los 17 ítems fijos del
    checklist (Recubrimientos, Componentes, Uniones Soldadas, Bridas...,
    Placas orificio, Puntos de inyección, Soportes, Abrazaderas,
    Instrumentación, Válvulas, Protección Catódica, Juntas dieléctricas,
    Vibraciones, Verticalidad, Reparaciones, Inspección Bajo Aislamiento,
    Otros). Cuando un ítem tiene más de un hallazgo, el propio archivo ya
    trae filas adicionales para ese ítem (mismo N° de ítem repetido, o la
    fila fusionada más alta) — nunca se insertan filas nuevas.

        B = Ítem (N°)          C = Categoría
        G/H/I/J = A/O/R/NA     K (fusionada K:R) = Comentario (texto libre)
        S en adelante = fotografías incrustadas

El inspector ya escribe en "Comentario" tanto hallazgos (frases
descriptivas: "Se evidencia...", "Deterioro...", "Presencia de...") como,
cuando corresponde, la recomendación (frases imperativas: "Realizar...",
"Instalar...", "Reemplazar..."). `parchar_checklist_vt` detecta —por el
verbo inicial, sin ningún modelo de lenguaje— cuáles filas ya son
recomendación; para los ítems marcados O/R que tienen hallazgo pero ninguna
recomendación, intenta sugerir una (recomendaciones.sugerir_caso_desde_texto,
basado en palabras clave del COMPENDIO) y, SOLO si el propio ítem ya tiene
una celda de Comentario vacía disponible (respetando el formato fijo), la
escribe ahí, marcada como "[SUGERENCIA AUTOMÁTICA - VALIDAR]". Si no hay
celda disponible o no hay sugerencia confiable, no se toca el archivo y se
reporta un aviso para redacción manual.
"""
import re

import openpyxl
from openpyxl.cell.cell import MergedCell

import recomendaciones

# --- Layout fijo del formato AD-UN05-TL-TUB-VT ------------------------------
CELDA_LINEA = "Q9"
CELDA_GRUPO = "E9"
CELDA_UNIDAD = "E10"
CELDA_EXAMINADORES = "Q10"

FILA_INICIO_ITEMS = 15
COL_ITEM = 2       # B
COL_CATEGORIA = 3  # C
COLS_MARCA = {7: "A", 8: "O", 9: "R", 10: "NA"}  # G/H/I/J
COL_COMENTARIO = 11  # K (celda ancla de la fusión K:R)
ULTIMO_ITEM_ESPERADO = 17  # "Otros:" -- fin real de la tabla fija

VERBOS_RECOMENDACION = (
    "realizar", "instalar", "reemplazar", "aplicar", "efectuar", "retirar",
    "reparar", "limpiar", "corregir", "reforzar", "verificar", "solicitar",
    "programar", "colocar", "restablecer", "adecuar", "ejecutar", "recomendar",
    "recomendación",
)

TEXTO_PENDIENTE_MANUAL = (
    "PENDIENTE — requiere redacción manual del especialista "
    "(hallazgo VT sin recomendación registrada)."
)


def _clasificar(texto):
    t = texto.strip().lower()
    if t.startswith(VERBOS_RECOMENDACION):
        return "RECOMENDACION"
    return "HALLAZGO"


# Correcciones ortográficas frecuentes en el texto libre de campo (tildes
# omitidas y typos recurrentes observados en el VT-CHECK LIST real). Es una
# normalización determinística (diccionario fijo), no una reescritura ni
# reinterpretación del contenido: nunca cambia el significado del hallazgo,
# solo prolijidad de redacción antes de volcarlo al informe.
CORRECCIONES_TEXTO = {
    "corrosion": "corrosión", "corrsoion": "corrosión",
    "atmosferica": "atmosférica",
    "proteccion": "protección", "ingnifuca": "ignífuga", "ignifuca": "ignífuga",
    "diametro": "diámetro",
    "esparrago": "espárrago", "esparragos": "espárragos",
    "valvula": "válvula", "valvulas": "válvulas",
    "instrumentacion": "instrumentación",
    "recubirmiento": "recubrimiento",
    "condicion": "condición",
    "seccion": "sección",
    "ademas": "además",
    "polucion": "polución", "adhrencia": "adherencia",
    "ubicacion": "ubicación",
    "evaluacion": "evaluación",
    "inspeccion": "inspección",
    "reparacion": "reparación",
    "instalacion": "instalación",
    "identificacion": "identificación",
    "posicion": "posición",
}
_RE_PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]+")


def _mejorar_texto(texto):
    """Normaliza tildes/typos frecuentes y puntuación de un hallazgo de
    campo, sin alterar su contenido técnico. Se usa para lo que pasa al
    informe Word (no reescribe la celda original del checklist)."""
    if not texto:
        return texto

    def _reemplazar(m):
        palabra = m.group(0)
        correcta = CORRECCIONES_TEXTO.get(palabra.lower())
        if correcta is None:
            return palabra
        return correcta[0].upper() + correcta[1:] if palabra[0].isupper() else correcta

    resultado = _RE_PALABRA.sub(_reemplazar, texto.strip())
    resultado = re.sub(r"\s{2,}", " ", resultado)
    if resultado:
        resultado = resultado[0].upper() + resultado[1:]
        if resultado[-1] not in ".!?":
            resultado += "."
    return resultado


def _bloques_por_item(ws):
    """Agrupa las filas de la hoja en bloques (item, categoría, fila_ini,
    fila_fin), respetando exactamente las filas que ya trae el archivo
    (nunca se insertan ni eliminan filas)."""
    bloques = []
    item_actual = None
    cat_actual = None
    inicio_actual = None
    fila = FILA_INICIO_ITEMS

    while fila <= ws.max_row:
        b = ws.cell(row=fila, column=COL_ITEM).value
        c = ws.cell(row=fila, column=COL_CATEGORIA).value
        k = ws.cell(row=fila, column=COL_COMENTARIO).value
        marca_presente = any(
            ws.cell(row=fila, column=col).value == "X" for col in COLS_MARCA
        )

        if b is None and c is None and k is None and not marca_presente:
            # Fila completamente vacía: si ya pasamos el último ítem
            # esperado, se terminó la tabla real (el resto son filas fuera
            # del área impresa que python-docx/openpyxl a veces reporta de
            # más). Si aún no llegamos al último ítem, puede ser solo un
            # hueco dentro de un bloque fusionado -> seguimos.
            if item_actual == ULTIMO_ITEM_ESPERADO:
                break
            fila += 1
            continue

        if b is not None:
            if item_actual is not None:
                bloques.append((item_actual, cat_actual, inicio_actual, fila - 1))
            item_actual = b
            cat_actual = c if c is not None else cat_actual
            inicio_actual = fila
        elif c is not None:
            cat_actual = c

        fila += 1

    if item_actual is not None:
        bloques.append((item_actual, cat_actual, inicio_actual, min(fila - 1, ws.max_row)))

    return bloques


def _filas_del_bloque(ws, fila_ini, fila_fin):
    filas = []
    for r in range(fila_ini, fila_fin + 1):
        celda = ws.cell(row=r, column=COL_COMENTARIO)
        if isinstance(celda, MergedCell) or celda.value in (None, ""):
            continue
        texto = str(celda.value)
        marca = None
        for col, m in COLS_MARCA.items():
            if ws.cell(row=r, column=col).value == "X":
                marca = m
                break
        filas.append({"fila": r, "texto": texto, "marca": marca, "tipo": _clasificar(texto)})
    return filas


def _procesar_bloque(ws, item, categoria, fila_ini, fila_fin):
    """Resuelve el hallazgo (mejorado) y la recomendación de un ítem del
    checklist -- exista ya en el archivo o haya que sugerirla -- SIN escribir
    nada todavía. Devuelve None si el ítem no tiene un hallazgo real (marca
    A/NA, o sin comentario) o si no tiene ninguna fotografía de respaldo: una
    observación O/R sin foto no lleva recomendación ni pasa al informe."""
    filas = _filas_del_bloque(ws, fila_ini, fila_fin)
    if not filas or not any(f["marca"] in ("O", "R") for f in filas):
        return None
    if not imagenes_del_bloque(ws, fila_ini, fila_fin):
        return None

    hallazgo = " ".join(_mejorar_texto(f["texto"]) for f in filas if f["tipo"] == "HALLAZGO")
    recomendacion_existente = " ".join(f["texto"] for f in filas if f["tipo"] == "RECOMENDACION")
    filas_hallazgo = [f["fila"] for f in filas if f["tipo"] == "HALLAZGO"]
    fila_ultimo_hallazgo = filas_hallazgo[-1] if filas_hallazgo else filas[-1]["fila"]

    if not hallazgo and recomendacion_existente:
        # El inspector solo escribió la frase de acción (ningún renglón
        # descriptivo aparte): se usa esa misma frase también como hallazgo,
        # para que la tabla de Hallazgos y la de Recomendaciones queden con
        # la misma cantidad de ítems y la misma numeración por hallazgo.
        hallazgo = _mejorar_texto(recomendacion_existente)

    if recomendacion_existente:
        return {
            "item": item, "categoria": categoria,
            "hallazgo": hallazgo, "recomendacion": recomendacion_existente,
            "sugerida": False, "fila_ultimo_hallazgo": fila_ultimo_hallazgo,
        }

    sugerido = recomendaciones.sugerir_caso_desde_texto(categoria, hallazgo)
    recomendacion = sugerido.recomendacion if sugerido else TEXTO_PENDIENTE_MANUAL
    return {
        "item": item, "categoria": categoria,
        "hallazgo": hallazgo, "recomendacion": recomendacion,
        "sugerida": True, "fila_ultimo_hallazgo": fila_ultimo_hallazgo,
    }


def parchar_checklist_vt(ruta_original, contexto_ignorado, ruta_salida):
    """Recorre las hojas del VT-CHECK LIST real (una por línea). Para cada
    ítem con hallazgo real (marca O/R) resuelve su Hallazgo (mejorado) y su
    Recomendación -- si ya estaba escrita por el inspector, se usa tal cual;
    si no, se sugiere con recomendaciones.sugerir_caso_desde_texto y, SOLO
    si el propio ítem ya tiene una celda de Comentario vacía disponible, se
    escribe ahí (el formato fijo nunca se altera: no se agregan filas).

    Cuando no hay celda disponible, la recomendación sugerida NO se pierde:
    de todas formas viaja en `hallazgos_por_tag` para que el informe Word y
    los anexos la incluyan, y se reporta como aviso para que quede además en
    el checklist en la próxima revisión manual.

    Devuelve (avisos, hallazgos_por_tag), con
    hallazgos_por_tag[tag] = [{"item","categoria","hallazgo","recomendacion",
    "sugerida","escrita_en_excel"}, ...].
    """
    wb = openpyxl.load_workbook(ruta_original)
    avisos = []
    hallazgos_por_tag = {}

    for nombre_hoja in wb.sheetnames:
        ws = wb[nombre_hoja]
        tag = ws[CELDA_LINEA].value
        tag = str(tag).strip() if tag else None
        if not tag:
            avisos.append(f"Hoja '{nombre_hoja}': no se encontró el TAG de línea en {CELDA_LINEA}.")
            continue

        for item, categoria, fila_ini, fila_fin in _bloques_por_item(ws):
            info = _procesar_bloque(ws, item, categoria, fila_ini, fila_fin)
            if info is None:
                continue

            if info["sugerida"]:
                # El hallazgo de campo ya quedó capturado en info["hallazgo"]
                # (para la tabla de Hallazgos del informe); en el propio
                # checklist, esa misma celda de Comentario se REEMPLAZA por
                # la recomendación (no se agregan filas ni columnas).
                ws.cell(row=info["fila_ultimo_hallazgo"], column=COL_COMENTARIO).value = (
                    info["recomendacion"]
                )
                info["escrita_en_excel"] = True
                avisos.append(
                    f"Hoja '{nombre_hoja}' (línea {tag}), ítem {item} [{categoria}]: "
                    f"recomendación sugerida automáticamente y parchada en el checklist: "
                    f"{info['recomendacion']}"
                )
            else:
                info["escrita_en_excel"] = True

            hallazgos_por_tag.setdefault(tag, []).append(info)

    wb.save(ruta_salida)
    print(f"[✔] Checklist parchado y guardado con éxito en: {ruta_salida}")
    if avisos:
        print("[!] Avisos durante el parchado del checklist:")
        for a in avisos:
            print("    -", a)
    return avisos, hallazgos_por_tag


def extraer_hallazgos_por_tag(ruta_checklist):
    """Lector independiente: recorre un VT-CHECK LIST (parchado o no) y
    resuelve, por TAG de línea, el mismo Hallazgo/Recomendación que produce
    parchar_checklist_vt (incluida la sugerencia automática cuando falte),
    sin modificar el archivo. Útil para reconstruir el informe sin tener que
    volver a ejecutar el parchado."""
    wb = openpyxl.load_workbook(ruta_checklist, data_only=True)
    resultado = {}

    for nombre_hoja in wb.sheetnames:
        ws = wb[nombre_hoja]
        tag = ws[CELDA_LINEA].value
        tag = str(tag).strip() if tag else None
        if not tag:
            continue

        for item, categoria, fila_ini, fila_fin in _bloques_por_item(ws):
            info = _procesar_bloque(ws, item, categoria, fila_ini, fila_fin)
            if info is None:
                continue
            resultado.setdefault(tag, []).append(info)

    return resultado


def tiene_foto_en_fila(ws, fila_num):
    """Valida si en una fila específica del checklist existe una imagen
    incrustada (ancla en esa fila)."""
    if not hasattr(ws, "_images") or not ws._images:
        return False

    for img in ws._images:
        celda_anclaje = img.anchor
        if hasattr(celda_anclaje, "_from"):
            row_idx = celda_anclaje._from.row + 1
            if row_idx == fila_num:
                return True
        elif isinstance(celda_anclaje, str):
            match = re.search(r"\d+", celda_anclaje)
            if match and int(match.group()) == fila_num:
                return True
    return False


def imagenes_del_bloque(ws, fila_ini, fila_fin):
    """Devuelve las imágenes incrustadas cuya ancla cae dentro de
    [fila_ini, fila_fin] (rango de filas de un ítem del checklist)."""
    imagenes = []
    for img in getattr(ws, "_images", []):
        fr = getattr(img.anchor, "_from", None)
        fila_img = (fr.row + 1) if fr is not None else None
        if fila_img is not None and fila_ini <= fila_img <= fila_fin:
            imagenes.append(img)
    return imagenes
