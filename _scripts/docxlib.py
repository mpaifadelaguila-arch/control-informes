"""
docxlib.py — helpers de bajo nivel para editar el .docx real del informe
"Plan de Líneas de Proceso" sin perder fidelidad (fotos, formato, IDs válidos).

Se trabaja sobre el árbol lxml que python-docx ya expone (document._element),
nunca reconstruyendo el documento desde cero. Se verificó (14/09/2026, sesión
de reconstrucción) que Document.save() de python-docx preserva byte a byte
todo lo que no se toca explícitamente (word/media/*, styles, headers, etc.),
así que es seguro usarlo aquí — a diferencia de openpyxl con el checklist
.xlsx, que sí corrompe las fotos incrustadas (ver checklist.py).

Referencia: sección 11.1 y 13.6 de
`claude/analisis-estructura-informe-y-plan-automatizacion.md`.
"""
import copy
import random
import re

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W14_NS = "http://schemas.microsoft.com/office/word/2010/wordml"
NSMAP = {"w": W_NS, "w14": W14_NS}


def qn(tag):
    prefix, local = tag.split(":")
    uri = {"w": W_NS, "w14": W14_NS}[prefix]
    return f"{{{uri}}}{local}"


def _new_id():
    """Genera un w14:paraId/textId válido: debe ser < 0x80000000 (regla
    confirmada en la sección 8.2 — si no, la validación OOXML de Word falla)."""
    return format(random.getrandbits(31), "08X")


def regenerate_ids(element):
    """Regenera TODOS los w14:paraId/w14:textId del árbol, en CUALQUIER
    elemento que los tenga (no solo <w:p> — la propia fila <w:tr> también
    lleva su propio par, bug encontrado y corregido en la sección 13.6:
    si no se regenera el paraId de la fila, quedan duplicados aunque los
    párrafos de sus celdas sí se hayan regenerado)."""
    pid_attr = qn("w14:paraId")
    tid_attr = qn("w14:textId")
    for el in element.iter():
        if el.get(pid_attr) is not None:
            el.set(pid_attr, _new_id())
        if el.get(tid_attr) is not None:
            el.set(tid_attr, _new_id())
    return element


def get_tc_paragraphs(tc):
    return tc.findall(qn("w:p"))


def cell_text(tc):
    return "".join(t.text or "" for t in tc.findall(f'.//{qn("w:t")}'))


def set_para_content(paragraph_el, text, remove_highlight=True):
    """Reemplaza TODO el contenido de un párrafo por un único run con `text`,
    conservando el <w:pPr> (viñeta/numeración/alineación) y el <w:rPr> del
    primer run original (fuente/tamaño), quitando el resaltado amarillo si
    remove_highlight=True. Técnica confirmada en la sección 8.2/9.7b."""
    ppr = paragraph_el.find(qn("w:pPr"))
    runs = paragraph_el.findall(qn("w:r"))
    base_rpr = None
    if runs:
        rpr = runs[0].find(qn("w:rPr"))
        if rpr is not None:
            base_rpr = copy.deepcopy(rpr)
            if remove_highlight:
                hl = base_rpr.find(qn("w:highlight"))
                if hl is not None:
                    base_rpr.remove(hl)

    for r in runs:
        paragraph_el.remove(r)

    from lxml import etree

    new_r = etree.SubElement(paragraph_el, qn("w:r"))
    if base_rpr is not None:
        new_r.append(base_rpr)
    new_t = etree.SubElement(new_r, qn("w:t"))
    new_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    new_t.text = text

    # Reordenar: pPr siempre primero si existe
    if ppr is not None and paragraph_el.find(qn("w:pPr")) is None:
        paragraph_el.insert(0, ppr)
    return paragraph_el


def set_cell_text(tc, text):
    """Reemplaza el contenido del primer párrafo de una celda por `text`,
    preservando formato. Si la celda tiene varios párrafos vacíos extra,
    los deja intactos (no se borran, por si tienen formato de la plantilla)."""
    paras = get_tc_paragraphs(tc)
    if not paras:
        return tc
    set_para_content(paras[0], text)
    # Si hay párrafos adicionales vacíos en la celda, se limpian para no
    # dejar líneas en blanco sueltas.
    for p in paras[1:]:
        if not "".join(t.text or "" for t in p.findall(f'.//{qn("w:t")}')).strip():
            p.getparent().remove(p)
    return tc


def clone_table_to_n_rows(table, n, header_rows=1):
    """Generaliza una tabla con `header_rows` filas de encabezado + M filas
    de datos a exactamente `n` filas de datos, usando la ÚLTIMA fila de
    datos existente como molde (garantizado con formato válido).

    - Si M > n: se eliminan filas de datos sobrantes (se conservan las
      primeras n).
    - Si M < n: se clona el molde (n - M) veces, regenerando IDs.
    - Si M == n: no se toca nada.

    Devuelve la lista de las `n` filas de datos (objetos <w:tr> lxml), en
    orden, listas para que el llamador llene cada celda.

    Técnica: clonado de filas con regeneración de w14:paraId/w14:textId vía
    copy.deepcopy — sección 11.1 (clone_table_rows) y 13.6 (bug de paraId
    de fila corregido).
    """
    tbl = table._tbl
    all_trs = tbl.findall(qn("w:tr"))
    data_trs = all_trs[header_rows:]
    m = len(data_trs)

    if m == 0:
        raise ValueError(
            "La tabla no tiene ninguna fila de datos para usar como molde "
            "(se necesita al menos 1 fila de ejemplo con formato real)."
        )

    if n < m:
        for tr in data_trs[n:]:
            tbl.remove(tr)
        data_trs = data_trs[:n]
    elif n > m:
        molde = data_trs[-1]
        for _ in range(n - m):
            clone = copy.deepcopy(molde)
            regenerate_ids(clone)
            molde.addnext(clone)
            molde = clone
            data_trs.append(clone)

    # Filas con trHeight hRule="exact": cambiar a "atLeast" para que Word no
    # recorte contenido si el texto real es más largo que el de ejemplo
    # (regla de la sección 8.2).
    for tr in data_trs:
        for trh in tr.findall(f'.//{qn("w:trHeight")}'):
            if trh.get(qn("w:hRule")) == "exact":
                trh.set(qn("w:hRule"), "atLeast")

    return data_trs


def fill_row(tr, values):
    """Llena las celdas de una fila <w:tr> en orden con la lista `values`
    (strings). Si `values` es más corta que el número de celdas, las
    celdas sobrantes no se tocan."""
    tcs = tr.findall(qn("w:tc"))
    for tc, val in zip(tcs, values):
        if val is not None:
            set_cell_text(tc, str(val))
    return tr


def find_paragraph_by_id(document, para_id):
    """Ubica un párrafo del documento por su w14:paraId (más confiable que
    offsets numéricos — técnica de la sección 8.2)."""
    body = document.element.body
    for p in body.iter(qn("w:p")):
        if p.get(qn("w14:paraId")) == para_id:
            return p
    return None


def clone_paragraph_block(anchor_p, texts, remove_highlight=True):
    """A partir de un párrafo ancla (`anchor_p`), genera len(texts) párrafos
    clonados (uno por texto en `texts`), insertados justo después del ancla,
    conservando el <w:pPr> del ancla (viñeta/numeración) y regenerando IDs.
    El propio `anchor_p` se reutiliza como el primero de la lista.
    Usado para: Recomendación #1 con más de una Clase API 570 (sección 9.7b)
    y para el bloque de examinadores (sección 12.2)."""
    if not texts:
        return []
    set_para_content(anchor_p, texts[0], remove_highlight)
    result = [anchor_p]
    prev = anchor_p
    for t in texts[1:]:
        clone = copy.deepcopy(anchor_p)
        regenerate_ids(clone)
        set_para_content(clone, t, remove_highlight)
        prev.addnext(clone)
        prev = clone
        result.append(clone)
    return result


def replace_media_bytes(docx_zip_writer, original_zip, media_path, new_bytes):
    """Sustituye únicamente los bytes de un archivo en word/media/ al
    reempaquetar el .docx, conservando nombre y extensión (incluso si es
    '.tmp' registrada como image/png en Content_Types — regla de la
    sección 13.7: nunca renombrar). Se usa junto con `replace_media_in_docx`."""
    raise NotImplementedError("usar replace_media_in_docx")


def replace_media_in_docx(src_path, dst_path, media_name, new_bytes):
    """Copia el .docx de src_path a dst_path reemplazando SOLO
    word/media/<media_name> por new_bytes, byte a byte, sin tocar ninguna
    otra parte del zip (ni relaciones, ni Content_Types)."""
    import zipfile
    import shutil

    shutil.copyfile(src_path, dst_path)
    # zipfile no soporta "reemplazar en sitio" directamente: se reconstruye
    # el zip completo copiando todas las entradas salvo la reemplazada.
    tmp_path = dst_path + ".tmp"
    with zipfile.ZipFile(src_path, "r") as zin, zipfile.ZipFile(
        tmp_path, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        target = f"word/media/{media_name}"
        found = False
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == target:
                data = new_bytes
                found = True
            zout.writestr(item, data)
        if not found:
            raise FileNotFoundError(f"{target} no existe en el .docx original")
    import os

    os.replace(tmp_path, dst_path)


def find_portada_photo(docx_path):
    """Identifica la imagen de portada dentro de word/media/ por ser la
    única imagen 'grande' con relación de aspecto ~4:3 (regla de la
    sección 13.7 — no asumir el nombre de archivo, el logo y la firma
    escaneada son las otras imágenes típicas del docx)."""
    import zipfile
    from PIL import Image
    import io

    with zipfile.ZipFile(docx_path) as z:
        media = [n for n in z.namelist() if n.startswith("word/media/")]
        best = None
        best_area = 0
        for name in media:
            try:
                data = z.read(name)
                img = Image.open(io.BytesIO(data))
                w, h = img.size
                area = w * h
                ratio = w / h if h else 0
                if area > best_area and 1.1 < ratio < 1.6:
                    best_area = area
                    best = (name, w, h)
            except Exception:
                continue
        return best


def set_cell_text_multi(tc, texts):
    """Como set_cell_text, pero para varios ítems: usa el primer párrafo de
    la celda como ancla (conservando su w:pPr -- incluyendo w:numPr, es
    decir la numeración automática de Word tipo '1) 2) 3)...') y clona un
    párrafo por cada texto en `texts` con clone_paragraph_block, para que
    Word numere cada hallazgo/recomendación como ítem de lista aparte en
    vez de escribir '1) 2) 3)' a mano dentro de un solo párrafo (lo que
    duplicaba la numeración con la propia numeración automática de la
    plantilla, numId=13)."""
    paras = get_tc_paragraphs(tc)
    if not paras:
        return tc
    anchor = paras[0]
    clone_paragraph_block(anchor, list(texts))
    # limpiar párrafos vacíos adicionales de la plantilla (los que ya
    # existían en la celda antes del ancla clonado)
    for p in paras[1:]:
        if not "".join(t.text or "" for t in p.findall(f'.//{qn("w:t")}')).strip():
            p.getparent().remove(p)
    return tc


def set_cell_text_prefijo_mas_lista(tc, prefijo, items):
    """Para celdas de línea con Alcance=LINEAS: el molde real (fila 1 de la
    tabla 9.0 en la plantilla GT-010) trae DOS párrafos distintos: el
    primero SIN numeración (para la frase de rate/vida remanente del
    PSAIM) y el segundo YA con w:numPr propio (para el/los hallazgo(s),
    numerados 1), 2), 3)...). Se debe preservar esa separación: el primer
    párrafo se llena con `prefijo` tal cual (sin numerar) y el segundo
    párrafo (con su numPr real) se usa como ancla para clonar un párrafo
    numerado por cada elemento de `items`.

    El párrafo numerado molde nunca tuvo texto real en la plantilla (era
    un placeholder vacío sin ninguna fuente asignada, "SIN rPr"), así que
    al llenarlo Word cae a la fuente por defecto en vez de Cambria/22
    como el resto de la tabla -- se copia explícitamente el w:rPr del
    primer párrafo (que sí trae el formato correcto) para que ambos
    párrafos queden con la misma tipografía y tamaño.

    Si la celda no tiene esa estructura de 2 párrafos (por ejemplo si el
    grupo tiene más/menos líneas que la plantilla original y
    clone_table_to_n_rows tuvo que clonar/eliminar filas), cae de
    respaldo: escribe el prefijo pegado al primer hallazgo en un único
    párrafo con la numeración que tenga ese párrafo."""
    paras = get_tc_paragraphs(tc)
    if len(paras) >= 2:
        set_para_content(paras[0], prefijo or "")
        fallback_rpr = None
        primer_run = paras[0].find(qn("w:r"))
        if primer_run is not None:
            rpr0 = primer_run.find(qn("w:rPr"))
            if rpr0 is not None:
                fallback_rpr = copy.deepcopy(rpr0)
        anchor = paras[1]
        nuevos = clone_paragraph_block(anchor, list(items) if items else [""])
        if fallback_rpr is not None:
            for p in nuevos:
                r = p.find(qn("w:r"))
                if r is not None and r.find(qn("w:rPr")) is None:
                    r.insert(0, copy.deepcopy(fallback_rpr))
        for p in paras[2:]:
            if not "".join(t.text or "" for t in p.findall(f'.//{qn("w:t")}')).strip():
                p.getparent().remove(p)
        return tc
    # Respaldo: sin el segundo párrafo molde, todo en una lista simple.
    combinados = ([prefijo] + list(items)) if prefijo else list(items)
    return set_cell_text_multi(tc, combinados)


def fill_row_multi(tr, values):
    """Como fill_row, pero cada valor puede ser un string (una sola línea,
    comportamiento normal de set_cell_text) o una lista de strings (varios
    hallazgos/recomendaciones -> varios párrafos numerados automáticamente,
    ver set_cell_text_multi)."""
    tcs = tr.findall(qn("w:tc"))
    for tc, val in zip(tcs, values):
        if val is None:
            continue
        if isinstance(val, (list, tuple)):
            set_cell_text_multi(tc, val)
        else:
            set_cell_text(tc, str(val))
    return tr
