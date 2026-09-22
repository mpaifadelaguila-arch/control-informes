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
import posixpath
import re
import zipfile

import openpyxl
from lxml import etree
from openpyxl.cell.cell import MergedCell
from openpyxl.utils import get_column_letter

import recomendaciones

_NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS_XDR = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"

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
    "apra": "para",
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


def _leer_rels(zf, ruta_rels):
    """Devuelve {Id: Target} de un archivo .rels del paquete OOXML, o {}
    si no existe."""
    if ruta_rels not in zf.namelist():
        return {}
    root = etree.fromstring(zf.read(ruta_rels))
    return {
        el.get("Id"): el.get("Target")
        for el in root.iter(f"{{{_NS_PKG_REL}}}Relationship")
    }


def _fotos_por_hoja(ruta_xlsx):
    """Lee, directamente del XML del .xlsx (sin pasar por ws._images de
    openpyxl), qué fotografías hay ancladas en cada fila de cada hoja.

    openpyxl NO reconoce una foto agrupada junto con una anotación (círculo
    o flecha) que el inspector dibuja encima de la imagen: en ese caso
    Excel guarda un grupo de dibujo DENTRO de otro grupo, y openpyxl
    descarta ese anclaje en silencio (se comprobó con el archivo real:
    varios hallazgos con foto quedaban marcados como "sin foto" solo por
    esto). Recorrer el XML de cada `drawingN.xml` a mano, con `.iter()`
    sobre `a:blip` sin importar la profundidad de anidamiento, evita ese
    problema por completo.

    Devuelve {nombre_hoja: {fila_excel_1indexed: [bytes_imagen, ...]}}."""
    resultado = {}
    with zipfile.ZipFile(ruta_xlsx) as zf:
        wb_root = etree.fromstring(zf.read("xl/workbook.xml"))
        wb_rels = _leer_rels(zf, "xl/_rels/workbook.xml.rels")

        for sheet_el in wb_root.iter(f"{{{_NS_MAIN}}}sheet"):
            nombre_hoja = sheet_el.get("name")
            resultado[nombre_hoja] = {}
            rid = sheet_el.get(f"{{{_NS_R}}}id")
            target = wb_rels.get(rid)
            if not target:
                continue

            sheet_path = posixpath.normpath(f"xl/{target}")
            sheet_rels_path = posixpath.join(
                posixpath.dirname(sheet_path), "_rels",
                posixpath.basename(sheet_path) + ".rels",
            )
            sheet_rels = _leer_rels(zf, sheet_rels_path)
            drawing_target = next(
                (t for rid2, t in sheet_rels.items() if t and "drawing" in t.lower()),
                None,
            )
            if not drawing_target:
                continue
            drawing_path = posixpath.normpath(
                posixpath.join(posixpath.dirname(sheet_path), drawing_target)
            )
            if drawing_path not in zf.namelist():
                continue
            drawing_rels_path = posixpath.join(
                posixpath.dirname(drawing_path), "_rels",
                posixpath.basename(drawing_path) + ".rels",
            )
            drawing_rels = _leer_rels(zf, drawing_rels_path)

            drawing_root = etree.fromstring(zf.read(drawing_path))
            for anchor in drawing_root:
                if etree.QName(anchor).localname not in ("twoCellAnchor", "oneCellAnchor"):
                    continue
                from_el = anchor.find(f"{{{_NS_XDR}}}from")
                row_el = from_el.find(f"{{{_NS_XDR}}}row") if from_el is not None else None
                if row_el is None or row_el.text is None:
                    continue
                fila_excel = int(row_el.text) + 1

                blobs = []
                for blip in anchor.iter(f"{{{_NS_A}}}blip"):
                    rid_img = blip.get(f"{{{_NS_R}}}embed")
                    target_img = drawing_rels.get(rid_img) if rid_img else None
                    if not target_img:
                        continue
                    media_path = posixpath.normpath(
                        posixpath.join(posixpath.dirname(drawing_path), target_img)
                    )
                    if media_path in zf.namelist():
                        blobs.append(zf.read(media_path))
                if blobs:
                    resultado[nombre_hoja].setdefault(fila_excel, []).extend(blobs)
    return resultado


def _mapa_hoja_a_sheet_path(zf):
    """Devuelve {nombre_hoja: 'xl/worksheets/sheetN.xml'} a partir del
    propio workbook.xml (mismo mapeo que usa _fotos_por_hoja)."""
    wb_root = etree.fromstring(zf.read("xl/workbook.xml"))
    wb_rels = _leer_rels(zf, "xl/_rels/workbook.xml.rels")
    mapa = {}
    for sheet_el in wb_root.iter(f"{{{_NS_MAIN}}}sheet"):
        nombre_hoja = sheet_el.get("name")
        rid = sheet_el.get(f"{{{_NS_R}}}id")
        target = wb_rels.get(rid)
        if target:
            mapa[nombre_hoja] = posixpath.normpath(f"xl/{target}")
    return mapa


def _patch_celdas_en_sheet_xml(sheet_xml_bytes, parches):
    """Reemplaza, dentro del XML crudo de una hoja, el valor de las celdas
    indicadas en `parches` ({(fila, columna_letra): texto_nuevo}) por un
    string en línea (inlineStr) -- sin tocar ningún otro nodo del XML
    (estilos, fusiones, dibujos, fórmulas de otras celdas...). Devuelve los
    bytes del XML modificado."""
    root = etree.fromstring(sheet_xml_bytes)
    for (fila, col), texto in parches.items():
        ref = f"{col}{fila}"
        celda = root.find(f".//{{{_NS_MAIN}}}row[@r='{fila}']/{{{_NS_MAIN}}}c[@r='{ref}']")
        if celda is None:
            continue
        for hijo in list(celda):
            celda.remove(hijo)
        celda.set("t", "inlineStr")
        is_el = etree.SubElement(celda, f"{{{_NS_MAIN}}}is")
        t_el = etree.SubElement(is_el, f"{{{_NS_MAIN}}}t")
        t_el.text = texto
        t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def _reescribir_xlsx_con_parches(ruta_original, ruta_salida, parches_por_hoja):
    """Copia el .xlsx original entrada por entrada, byte a byte, y SOLO en
    las hojas con parches reemplaza el valor de las celdas indicadas (vía
    XML crudo). openpyxl NUNCA se usa para volver a escribir el archivo:
    su Workbook.save() no sabe representar una foto agrupada junto con una
    anotación (círculo/flecha) que el inspector dibuja encima -- una vez
    reconstruye el paquete .xlsx desde su propio modelo de imágenes,
    simplemente las pierde (comprobado con el archivo real: TODAS las
    fotografías de TODAS las hojas desaparecían tras un wb.save(), no solo
    las agrupadas). Reescribir solo el XML de la celda puntual evita por
    completo ese problema: dibujos, estilos, fusiones y todo lo demás
    quedan exactamente como en el archivo original."""
    with zipfile.ZipFile(ruta_original) as zf_in:
        hoja_a_path = _mapa_hoja_a_sheet_path(zf_in)
        path_a_hoja = {v: k for k, v in hoja_a_path.items()}

        with zipfile.ZipFile(ruta_salida, "w", zipfile.ZIP_DEFLATED) as zf_out:
            for item in zf_in.infolist():
                data = zf_in.read(item.filename)
                nombre_hoja = path_a_hoja.get(item.filename)
                if nombre_hoja and nombre_hoja in parches_por_hoja:
                    data = _patch_celdas_en_sheet_xml(data, parches_por_hoja[nombre_hoja])
                zf_out.writestr(item, data)


def extraer_hoja_a_xlsx(ruta_original, nombre_hoja, ruta_salida):
    """Copia el .xlsx original entero, pero deja en workbook.xml SOLO la
    hoja `nombre_hoja` en la lista de hojas -- remapeando/filtrando los
    nombres definidos (p.ej. Print_Area) que están fijados por
    localSheetId a esa hoja -- todo lo demás (estilos, dibujos, fotos,
    formato) queda exactamente igual que en _reescribir_xlsx_con_parches:
    nunca se pasa por openpyxl para no perder las fotografías agrupadas
    con anotación. Se usa para exportar a PDF una sola hoja (una línea)
    del VT-CHECK LIST con su formato y fotos originales intactos, sin
    arrastrar las demás hojas del checklist completo (Anexo B)."""
    with zipfile.ZipFile(ruta_original) as zf_in:
        wb_root = etree.fromstring(zf_in.read("xl/workbook.xml"))
        sheets_el = wb_root.find(f"{{{_NS_MAIN}}}sheets")
        hojas = list(sheets_el)
        idx_objetivo = next(
            (i for i, el in enumerate(hojas) if el.get("name") == nombre_hoja), None
        )
        if idx_objetivo is None:
            raise ValueError(f"Hoja «{nombre_hoja}» no encontrada en {ruta_original}")

        for el in hojas:
            if el.get("name") != nombre_hoja:
                sheets_el.remove(el)

        defined_names_el = wb_root.find(f"{{{_NS_MAIN}}}definedNames")
        if defined_names_el is not None:
            for dn in list(defined_names_el):
                local_id = dn.get("localSheetId")
                if local_id is None:
                    continue
                if int(local_id) == idx_objetivo:
                    dn.set("localSheetId", "0")
                else:
                    defined_names_el.remove(dn)

        workbook_xml_nuevo = etree.tostring(
            wb_root, xml_declaration=True, encoding="UTF-8", standalone=True
        )

        with zipfile.ZipFile(ruta_salida, "w", zipfile.ZIP_DEFLATED) as zf_out:
            for item in zf_in.infolist():
                data = (
                    workbook_xml_nuevo if item.filename == "xl/workbook.xml"
                    else zf_in.read(item.filename)
                )
                zf_out.writestr(item, data)


def _bloques_por_item(ws):
    """Agrupa las filas de la hoja en bloques (item, categoría, marca,
    fila_ini, fila_fin), respetando exactamente las filas que ya trae el
    archivo (nunca se insertan ni eliminan filas).

    La marca O/A/R/NA se lee UNA sola vez por bloque (igual que Ítem y
    Categoría, la celda está fusionada para todo el ítem, aunque dentro de
    él haya más de una observación de campo con su propio comentario y su
    propia foto) -- nunca por fila individual: si se leyera por fila, las
    filas de continuación de la fusión devuelven vacío (MergedCell) y una
    segunda observación del mismo ítem perdería su marca y se descartaría
    por error."""
    bloques = []
    item_actual = None
    cat_actual = None
    marca_actual = None
    inicio_actual = None
    fila = FILA_INICIO_ITEMS

    while fila <= ws.max_row:
        b = ws.cell(row=fila, column=COL_ITEM).value
        c = ws.cell(row=fila, column=COL_CATEGORIA).value
        k = ws.cell(row=fila, column=COL_COMENTARIO).value
        marca_fila = next(
            (m for col, m in COLS_MARCA.items() if ws.cell(row=fila, column=col).value == "X"),
            None,
        )

        if b is None and c is None and k is None and marca_fila is None:
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
                bloques.append((item_actual, cat_actual, marca_actual, inicio_actual, fila - 1))
            item_actual = b
            cat_actual = c if c is not None else cat_actual
            marca_actual = marca_fila
            inicio_actual = fila
        else:
            if c is not None:
                cat_actual = c
            if marca_fila is not None and marca_actual is None:
                marca_actual = marca_fila

        fila += 1

    if item_actual is not None:
        bloques.append((item_actual, cat_actual, marca_actual, inicio_actual, min(fila - 1, ws.max_row)))

    return bloques


def _filas_del_bloque(ws, fila_ini, fila_fin):
    filas = []
    for r in range(fila_ini, fila_fin + 1):
        celda = ws.cell(row=r, column=COL_COMENTARIO)
        if isinstance(celda, MergedCell) or celda.value in (None, ""):
            continue
        texto = str(celda.value)
        filas.append({"fila": r, "texto": texto, "tipo": _clasificar(texto)})
    return filas


def _sub_hallazgos_del_bloque(ws, fotos_hoja, fila_ini, fila_fin):
    """Un mismo ítem puede traer más de una observación de campo
    independiente -- cada una con su propio comentario y su propia foto (o
    par general+detalle, que sigue siendo UNA sola foto/observación) --,
    p.ej. 'Bridas...' con dos tramos distintos inspeccionados, cada uno con
    su propio hallazgo y su propia recomendación. La unidad real de una
    observación es LA FOTO, no la clasificación gramatical del texto: cada
    fila de Comentario que tiene su propia fotografía anclada abre una
    observación nueva, exista o no un verbo imperativo al inicio (un
    inspector puede escribir directamente "Realizar..." como el hallazgo
    de una observación fotografiada aparte, sin que eso la convierta en la
    recomendación de la fila anterior). Una fila sin foto propia se suma
    como texto adicional (hallazgo o recomendación) de la observación
    fotografiada más cercana hacia arriba. Cada grupo queda delimitado
    hasta la fila anterior al siguiente grupo (o el fin del bloque, si es
    el último) -- ese es el rango donde se busca SU propia fotografía."""
    filas = _filas_del_bloque(ws, fila_ini, fila_fin)
    grupos = []
    for f in filas:
        tiene_foto_propia = f["fila"] in fotos_hoja
        if tiene_foto_propia or not grupos:
            grupos.append({"hallazgo_filas": [], "recomendacion_filas": [], "fila_ini": f["fila"]})
        if f["tipo"] == "HALLAZGO":
            grupos[-1]["hallazgo_filas"].append(f)
        else:
            grupos[-1]["recomendacion_filas"].append(f)

    for i, g in enumerate(grupos):
        siguiente = grupos[i + 1]["fila_ini"] if i + 1 < len(grupos) else fila_fin + 1
        g["fila_fin_sub"] = siguiente - 1
    return grupos


def _procesar_bloque(ws, fotos_hoja, item, categoria, marca, fila_ini, fila_fin, tag=None, overrides=None):
    """Resuelve, para un ítem del checklist, cada observación de campo
    independiente que trae -- uno o más pares comentario+foto dentro del
    mismo ítem (p.ej. dos tramos distintos de 'Bridas...') -- su Hallazgo
    (mejorado) y su Recomendación, sin escribir nada todavía. Si el ítem no
    está marcado O/R, se descarta entero; si una observación puntual no
    tiene ninguna fotografía propia de respaldo, esa observación puntual se
    descarta (una observación O/R sin foto no lleva recomendación ni pasa
    al informe), pero las demás observaciones del mismo ítem que sí tengan
    foto se conservan. Devuelve una lista (puede tener más de un elemento
    por ítem, o ninguno).

    `overrides`, si se provee, es un dict {(tag, fila_ultimo_hallazgo):
    caso_id} -- cuando sugerir_caso_desde_texto() no encuentra ninguna
    regla (PENDIENTE), se prueba con recomendaciones.aplicar_caso_manual()
    usando el caso_id elegido explícitamente para esa fila (por una
    persona o por un agente de IA que leyó el catálogo), en vez de
    redactar nada nuevo."""
    resultados = []
    if marca not in ("O", "R"):
        return resultados

    for grupo in _sub_hallazgos_del_bloque(ws, fotos_hoja, fila_ini, fila_fin):
        sub_ini, sub_fin = grupo["fila_ini"], grupo["fila_fin_sub"]
        if not imagenes_del_bloque(fotos_hoja, sub_ini, sub_fin):
            continue

        hallazgo = " ".join(_mejorar_texto(f["texto"]) for f in grupo["hallazgo_filas"])
        recomendacion_existente = " ".join(f["texto"] for f in grupo["recomendacion_filas"])
        filas_hallazgo = [f["fila"] for f in grupo["hallazgo_filas"]]
        fila_ultimo_hallazgo = (
            filas_hallazgo[-1] if filas_hallazgo else grupo["recomendacion_filas"][-1]["fila"]
        )

        if not hallazgo and recomendacion_existente:
            # El inspector solo escribió la frase de acción (ningún renglón
            # descriptivo aparte): se usa esa misma frase también como hallazgo,
            # para que la tabla de Hallazgos y la de Recomendaciones queden con
            # la misma cantidad de ítems y la misma numeración por hallazgo.
            hallazgo = _mejorar_texto(recomendacion_existente)

        if recomendacion_existente:
            resultados.append({
                "item": item, "categoria": categoria,
                "hallazgo": hallazgo, "recomendacion": recomendacion_existente,
                "sugerida": False, "fila_ultimo_hallazgo": fila_ultimo_hallazgo,
                "fila_ini_sub": sub_ini, "fila_fin_sub": sub_fin,
            })
            continue

        sugerido = recomendaciones.sugerir_caso_desde_texto(categoria, hallazgo)
        aviso_override = None
        if sugerido is None and overrides:
            caso_manual = overrides.get((tag, fila_ultimo_hallazgo))
            if caso_manual:
                try:
                    sugerido = recomendaciones.aplicar_caso_manual(caso_manual, hallazgo)
                except ValueError as e:
                    aviso_override = str(e)
        recomendacion = sugerido.recomendacion if sugerido else TEXTO_PENDIENTE_MANUAL
        info = {
            "item": item, "categoria": categoria,
            "hallazgo": hallazgo, "recomendacion": recomendacion,
            "sugerida": True, "fila_ultimo_hallazgo": fila_ultimo_hallazgo,
            "fila_ini_sub": sub_ini, "fila_fin_sub": sub_fin,
        }
        if aviso_override:
            info["aviso_override"] = aviso_override
        resultados.append(info)
    return resultados


def parchar_checklist_vt(ruta_original, contexto_ignorado, ruta_salida, overrides=None):
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

    `overrides`, si se provee, es un dict {(tag, fila_ultimo_hallazgo):
    caso_id} para los hallazgos que sugerir_caso_desde_texto() no pudo
    resolver por palabras clave -- ver _procesar_bloque().

    Devuelve (avisos, hallazgos_por_tag), con
    hallazgos_por_tag[tag] = [{"item","categoria","hallazgo","recomendacion",
    "sugerida","escrita_en_excel"}, ...].
    """
    # Lectura únicamente -- openpyxl JAMÁS vuelve a escribir este archivo:
    # su Workbook.save() no sabe representar una foto agrupada junto con
    # una anotación (círculo/flecha) que el inspector dibuja encima, y al
    # reconstruir el paquete .xlsx desde su propio modelo de imágenes
    # simplemente las pierde (comprobado con el archivo real: TODAS las
    # fotografías de TODAS las hojas desaparecían, no solo las agrupadas).
    # El parchado real se hace más abajo, celda por celda, directamente
    # sobre el XML crudo (_reescribir_xlsx_con_parches), lo que deja el
    # resto del archivo -- dibujos incluidos -- intacto.
    wb = openpyxl.load_workbook(ruta_original)
    fotos_por_hoja = _fotos_por_hoja(ruta_original)
    col_comentario_letra = get_column_letter(COL_COMENTARIO)
    avisos = []
    hallazgos_por_tag = {}
    parches_por_hoja = {}

    for nombre_hoja in wb.sheetnames:
        ws = wb[nombre_hoja]
        fotos_hoja = fotos_por_hoja.get(nombre_hoja, {})
        tag = ws[CELDA_LINEA].value
        tag = str(tag).strip() if tag else None
        if not tag:
            avisos.append(f"Hoja '{nombre_hoja}': no se encontró el TAG de línea en {CELDA_LINEA}.")
            continue

        for item, categoria, marca, fila_ini, fila_fin in _bloques_por_item(ws):
            for info in _procesar_bloque(
                ws, fotos_hoja, item, categoria, marca, fila_ini, fila_fin,
                tag=tag, overrides=overrides,
            ):
                if info.get("aviso_override"):
                    avisos.append(
                        f"Hoja '{nombre_hoja}' (línea {tag}), ítem {item} [{categoria}]: "
                        f"el caso manual indicado para la fila {info['fila_ultimo_hallazgo']} "
                        f"no existe en el catálogo ({info['aviso_override']}); se dejó PENDIENTE."
                    )
                if info["sugerida"] and info["recomendacion"] != TEXTO_PENDIENTE_MANUAL:
                    # El hallazgo de campo ya quedó capturado en info["hallazgo"]
                    # (para la tabla de Hallazgos del informe); en el propio
                    # checklist, esa misma celda de Comentario se REEMPLAZA por
                    # la recomendación (no se agregan filas ni columnas).
                    parches_por_hoja.setdefault(nombre_hoja, {})[
                        (info["fila_ultimo_hallazgo"], col_comentario_letra)
                    ] = info["recomendacion"]
                    info["escrita_en_excel"] = True
                    avisos.append(
                        f"Hoja '{nombre_hoja}' (línea {tag}), ítem {item} [{categoria}]: "
                        f"recomendación sugerida automáticamente y parchada en el checklist: "
                        f"{info['recomendacion']}"
                    )
                elif info["sugerida"]:
                    # Ninguna regla del motor calzó con confianza: el
                    # hallazgo de campo original del inspector NUNCA se
                    # pierde (se conserva completo), pero la celda SÍ se
                    # marca -- se le agrega, a continuación del texto
                    # original, un aviso explícito de que falta la
                    # recomendación y debe redactarse a mano. Así ningún
                    # hallazgo queda sin ninguna recomendación asociada: o
                    # la sugiere el motor, o queda marcado para que el
                    # especialista la complete.
                    texto_original = ws.cell(
                        row=info["fila_ultimo_hallazgo"], column=COL_COMENTARIO
                    ).value or ""
                    parches_por_hoja.setdefault(nombre_hoja, {})[
                        (info["fila_ultimo_hallazgo"], col_comentario_letra)
                    ] = (
                        f"{texto_original}\n\n"
                        f"⚠ PENDIENTE: falta la recomendación técnica -- "
                        f"completar manualmente."
                    )
                    info["escrita_en_excel"] = True
                    avisos.append(
                        f"Hoja '{nombre_hoja}' (línea {tag}), ítem {item} [{categoria}]: "
                        f"PENDIENTE — sin regla de sugerencia confiable; el hallazgo de campo "
                        f"se conservó intacto en el checklist y se marcó para redacción manual "
                        f"del especialista: {info['hallazgo']}"
                    )
                else:
                    info["escrita_en_excel"] = True

                hallazgos_por_tag.setdefault(tag, []).append(info)

    _reescribir_xlsx_con_parches(ruta_original, ruta_salida, parches_por_hoja)
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
    fotos_por_hoja = _fotos_por_hoja(ruta_checklist)
    resultado = {}

    for nombre_hoja in wb.sheetnames:
        ws = wb[nombre_hoja]
        fotos_hoja = fotos_por_hoja.get(nombre_hoja, {})
        tag = ws[CELDA_LINEA].value
        tag = str(tag).strip() if tag else None
        if not tag:
            continue

        for item, categoria, marca, fila_ini, fila_fin in _bloques_por_item(ws):
            for info in _procesar_bloque(ws, fotos_hoja, item, categoria, marca, fila_ini, fila_fin):
                resultado.setdefault(tag, []).append(info)

    return resultado


def imagenes_del_bloque(fotos_hoja, fila_ini, fila_fin):
    """Devuelve las fotografías (bytes) cuya ancla cae dentro de
    [fila_ini, fila_fin] (rango de filas de una observación del
    checklist), según el mapeo fila->fotos que arma _fotos_por_hoja."""
    imagenes = []
    for fila, blobs in fotos_hoja.items():
        if fila_ini <= fila <= fila_fin:
            imagenes.extend(blobs)
    return imagenes
