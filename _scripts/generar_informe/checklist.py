"""
checklist.py — parser y patch del checklist VT (formato AD-UN05-TL-TUB-VT,
17 ítems según API RP 574, una hoja por línea).

REGLA DE ORO (sección 7 y 9.1): el checklist original del usuario NUNCA se
reabre ni regraba con openpyxl.save() — eso corrompe/pierde las fotos
incrustadas (probado: 16.5MB -> 4.6MB, se perdieron 17 de 24 fotos). Todo
patch se hace editando el XML de la hoja (`xl/worksheets/sheetN.xml`)
directamente, byte a byte, sin tocar `sharedStrings.xml`, `xl/media/` ni
`xl/drawings/` — verificado con hash byte a byte que las fotos quedan
idénticas tras el patch.

⚠️ NOTA IMPORTANTE PARA EL USUARIO: esta versión se reconstruyó (15/09/2026)
a partir de la documentación del proyecto, SIN tener a mano un checklist VT
ya lleno para probar contra un caso real (el de GT-010 todavía no había
llegado). El patch de celda (`patch_cell_inline_str`, la parte que evita
perder fotos) sí está probado con un .xlsx sintético con imagen incrustada.
El PARSER (`parse_hoja`) usa una heurística razonable sobre el layout
descrito en la documentación, pero conviene revisar/ajustar sus supuestos
de columnas la primera vez que se corra contra un checklist real lleno.
"""
import re
import zipfile
import shutil
import os
import openpyxl

CONDICIONES = ["A", "O", "R", "NA"]
N_ITEMS_ESPERADOS = 17

HEADER_LABELS = {
    "tag_circuito": ["TAG", "TAG CIRCUITO", "CIRCUITO"],
    "linea_inspeccionada": ["LÍNEA INSPECCIONADA", "LINEA INSPECCIONADA", "LÍNEA"],
    "unidad": ["UNIDAD"],
    "fecha_inspeccion": ["FECHA DE INSPECCIÓN", "FECHA DE INSPECCION"],
    "examinadores": ["EXAMINADOR", "EXAMINADORES", "EXAMINADOR(ES)"],
}


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().upper()


def _find_label_value(ws, labels, max_row=25, max_col=20):
    """Busca en las primeras filas/columnas una celda cuyo texto coincida
    con alguna de `labels` y devuelve el valor de la celda contigua (misma
    fila, siguiente columna no vacía) — patrón típico de cabecera
    'Etiqueta: Valor' en estos checklists."""
    for row in ws.iter_rows(min_row=1, max_row=max_row, max_col=max_col):
        for cell in row:
            val = _norm(cell.value)
            if not val:
                continue
            for lab in labels:
                if lab in val:
                    # buscar el siguiente valor no vacío en la misma fila
                    for c2 in row[cell.column - 1 + 1:]:
                        if c2.value not in (None, ""):
                            return c2.value, cell.coordinate, c2.coordinate
                    # o en la celda inmediatamente a la derecha aunque esté
                    # vacía por ahora (para saber dónde escribir si falta)
                    return None, cell.coordinate, None
    return None, None, None


def parse_hoja(ws):
    """Extrae de una hoja del checklist: datos de cabecera + lista de
    ítems (17 esperados, pero escaneado dinámicamente por si hay filas
    extra insertadas sin renumerar — corrección de la sección 7)."""
    header = {}
    for key, labels in HEADER_LABELS.items():
        val, _, _ = _find_label_value(ws, labels)
        header[key] = val

    # localizar la fila de encabezado de la tabla de ítems: la que tiene
    # una celda "Comentario" (o "COMENTARIO")
    header_row = None
    col_comentario = None
    col_item = None
    cond_cols = {}
    for row in ws.iter_rows(min_row=1, max_row=40):
        for cell in row:
            v = _norm(cell.value)
            if v.startswith("COMENTARIO"):
                header_row = cell.row
                col_comentario = cell.column
        if header_row:
            break

    if header_row is None:
        raise ValueError("No se encontró la columna 'Comentario' en la hoja "
                          f"'{ws.title}' — layout no reconocido.")

    # en la misma fila de encabezado, ubicar columna de ítem/descripción y
    # las columnas de condición A/O/R/NA
    for cell in ws[header_row]:
        v = _norm(cell.value)
        if v in ("ÍTEM", "ITEM", "N°", "N", "DESCRIPCIÓN", "DESCRIPCION", "ELEMENTO"):
            if col_item is None:
                col_item = cell.column
        if v in CONDICIONES:
            cond_cols[v] = cell.column

    items = []
    r = header_row + 1
    empty_streak = 0
    while r <= ws.max_row and empty_streak < 3:
        row_vals = [ws.cell(row=r, column=c).value for c in range(1, ws.max_column + 1)]
        if all(v in (None, "") for v in row_vals):
            empty_streak += 1
            r += 1
            continue
        empty_streak = 0

        descripcion = ws.cell(row=r, column=col_item).value if col_item else None
        comentario = ws.cell(row=r, column=col_comentario).value if col_comentario else None
        condicion = None
        for cond, col in cond_cols.items():
            v = ws.cell(row=r, column=col).value
            if v not in (None, ""):
                condicion = cond
                break

        if descripcion or comentario or condicion:
            items.append({
                "fila": r,
                "descripcion": descripcion,
                "condicion": condicion,
                "comentario": comentario,
                "col_comentario": col_comentario,
            })
        r += 1

    return {"hoja": ws.title, "header": header, "items": items}


def parse_checklist(path):
    """Devuelve {nombre_hoja: resultado_de_parse_hoja} para TODAS las hojas
    del checklist (una hoja por línea del grupo). Se abre en modo
    read_only=True SOLO PARA LEER — nunca se llama .save() sobre este
    Workbook (regla de oro, ver docstring del módulo)."""
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    out = {}
    for name in wb.sheetnames:
        ws = wb[name]
        try:
            out[name] = parse_hoja(ws)
        except ValueError as e:
            out[name] = {"hoja": name, "error": str(e)}
    return out


def items_observados_o_rechazados(hoja_parseada):
    """Filtra los ítems marcados O (observado) o R (rechazado) — los que sí
    necesitan Hallazgo/Recomendación (sección 3 del checklist de insumos)."""
    return [it for it in hoja_parseada.get("items", [])
            if it.get("condicion") in ("O", "R")]


# ---------------------------------------------------------------------------
# PATCH: reemplazo de celda por XML directo, sin tocar fotos.
# ---------------------------------------------------------------------------

XML_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _col_letter_to_index(letter):
    idx = 0
    for ch in letter:
        idx = idx * 26 + (ord(ch.upper()) - ord("A") + 1)
    return idx


def _split_cell_ref(ref):
    m = re.match(r"([A-Z]+)(\d+)", ref.upper())
    return m.group(1), int(m.group(2))


def _sheet_xml_path_for_name(z, sheet_name):
    """Resuelve el nombre de hoja visible (ej. 'Hoja1' o el nombre real de
    la línea) al archivo xl/worksheets/sheetN.xml correspondiente, pasando
    por workbook.xml + workbook.xml.rels (los nombres de hoja NO son el
    nombre de archivo)."""
    import xml.etree.ElementTree as ET

    wb_xml = z.read("xl/workbook.xml")
    ns = {"m": XML_NS, "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    root = ET.fromstring(wb_xml)
    rid = None
    for sheet in root.findall(".//m:sheets/m:sheet", ns):
        if sheet.get("name") == sheet_name:
            rid = sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            break
    if rid is None:
        raise ValueError(f"Hoja '{sheet_name}' no encontrada en workbook.xml")

    rels_xml = z.read("xl/_rels/workbook.xml.rels")
    rroot = ET.fromstring(rels_xml)
    rel_ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
    for rel in rroot.findall("r:Relationship", rel_ns):
        if rel.get("Id") == rid:
            target = rel.get("Target").lstrip("/")
            return target if target.startswith("xl/") else "xl/" + target
    raise ValueError(f"No se resolvió el rId {rid} en workbook.xml.rels")


def patch_cells_inline_str(src_path, dst_path, sheet_name, cell_updates):
    """Reemplaza el valor de una o más celdas de una hoja por texto plano
    (`t="inlineStr"`), editando el XML de esa hoja directamente dentro del
    zip, SIN pasar por openpyxl.save() y SIN tocar sharedStrings.xml,
    xl/media/ ni xl/drawings/ — así las fotos incrustadas quedan
    byte-idénticas.

    `cell_updates`: dict {"F12": "texto nuevo", ...}

    IMPORTANTE (bug real detectado y corregido el 17/09/2026, grupo
    GT-010): la celda original casi siempre trae un atributo `s="N"`
    (referencia de estilo -- en los checklists VT reales, ese estilo es
    justamente el que aplica wrapText=1 y vertical=center a la celda de
    "Comentario"). Las primeras versiones de esta función reconstruían el
    `<c>` sin ese atributo, perdiendo el wrap/centrado y dejando el texto
    nuevo cortado/desalineado visualmente aunque el contenido fuera
    correcto. Ahora se conserva el `s="N"` de la celda original (si
    existía) al reconstruir el `<c>`.

    Técnica confirmada en la sección 9.1 (`patch_checklist.py` original) y
    en la 12.2 (celdas de cabecera vacías)."""
    import re as _re

    if os.path.abspath(src_path) != os.path.abspath(dst_path):
        shutil.copyfile(src_path, dst_path)
    tmp_path = dst_path + ".tmp"

    with zipfile.ZipFile(src_path, "r") as zin:
        sheet_path = _sheet_xml_path_for_name(zin, sheet_name)
        sheet_xml = zin.read(sheet_path).decode("utf-8")

        for cell_ref, new_text in cell_updates.items():
            escaped = (
                new_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )

            # 1) Caso: la celda YA existe como elemento <c r="F12" ...>...</c>
            #    (con o sin contenido interno, self-closing o no) -- se
            #    conserva su atributo s="N" si lo trae.
            pattern_full = re.compile(
                rf'<c r="{re.escape(cell_ref)}"([^>]*?)(/>|>.*?</c>)', re.DOTALL
            )
            m_full = pattern_full.search(sheet_xml)
            if m_full:
                attrs_originales = m_full.group(1)
                sm = re.search(r'\bs="(\d+)"', attrs_originales)
                style_attr = f' s="{sm.group(1)}"' if sm else ""
                new_cell_xml = (
                    f'<c r="{cell_ref}"{style_attr} t="inlineStr">'
                    f'<is><t xml:space="preserve">{escaped}</t></is></c>'
                )
                sheet_xml = pattern_full.sub(lambda _m: new_cell_xml, sheet_xml, count=1)
                continue

            new_cell_xml = f'<c r="{cell_ref}" t="inlineStr"><is><t xml:space="preserve">{escaped}</t></is></c>'

            # 2) Caso: la celda no existe todavía en esa fila -> insertarla
            #    en la posición correcta dentro del <row r="12">...</row>
            col_letters, row_num = _split_cell_ref(cell_ref)
            col_idx = _col_letter_to_index(col_letters)
            row_pattern = re.compile(
                rf'(<row r="{row_num}"[^>]*>)(.*?)(</row>)', re.DOTALL
            )
            m = row_pattern.search(sheet_xml)
            if not m:
                # La fila tampoco existe todavía (ej. hoja casi vacía) ->
                # crearla en la posición correcta dentro de <sheetData>.
                new_row_xml = f'<row r="{row_num}">{new_cell_xml}</row>'
                existing_rows = list(re.finditer(r'<row r="(\d+)"', sheet_xml))
                insert_at = None
                for er in existing_rows:
                    if int(er.group(1)) > row_num:
                        insert_at = er.start()
                        break
                if insert_at is not None:
                    sheet_xml = sheet_xml[:insert_at] + new_row_xml + sheet_xml[insert_at:]
                else:
                    close_tag = "</sheetData>"
                    pos = sheet_xml.index(close_tag)
                    sheet_xml = sheet_xml[:pos] + new_row_xml + sheet_xml[pos:]
                continue
            row_open, row_body, row_close = m.groups()
            existing_cells = list(re.finditer(r'<c r="([A-Z]+)(\d+)"', row_body))
            insert_pos = len(row_body)
            for ec in existing_cells:
                if _col_letter_to_index(ec.group(1)) > col_idx:
                    insert_pos = ec.start()
                    break
            new_body = row_body[:insert_pos] + new_cell_xml + row_body[insert_pos:]
            sheet_xml = sheet_xml[:m.start()] + row_open + new_body + row_close + sheet_xml[m.end():]

    with zipfile.ZipFile(src_path, "r") as zin, zipfile.ZipFile(
        tmp_path, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == sheet_path:
                data = sheet_xml.encode("utf-8")
            zout.writestr(item, data)

    os.replace(tmp_path, dst_path)


def verify_media_untouched(path_a, path_b):
    """Utilidad de verificación: compara xl/media/* y xl/drawings/* entre
    dos .xlsx byte a byte. Devuelve lista de diferencias (vacía = OK)."""
    import hashlib

    def hashes(path, prefix):
        with zipfile.ZipFile(path) as z:
            return {
                n: hashlib.sha256(z.read(n)).hexdigest()
                for n in z.namelist()
                if n.startswith(prefix)
            }

    diffs = []
    for prefix in ("xl/media/", "xl/drawings/"):
        ha = hashes(path_a, prefix)
        hb = hashes(path_b, prefix)
        if ha.keys() != hb.keys():
            diffs.append(f"{prefix}: archivos distintos {set(ha) ^ set(hb)}")
        for k in ha:
            if k in hb and ha[k] != hb[k]:
                diffs.append(f"{prefix}{k}: hash distinto")
    return diffs
