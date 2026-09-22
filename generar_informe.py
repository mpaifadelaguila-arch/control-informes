"""
generar_informe.py — orquesta la generación REAL del informe Word y del
VT-CHECK LIST parchado para un grupo de tuberías, conectando los motores ya
existentes en el repo:

    inventario.py  -> cruce técnico contra BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx
    psaim.py       -> cálculo de rate de corrosión / vida útil (PSAIM)
    checklist.py   -> parche del VT-CHECK LIST con el motor de reglas
                       recomendaciones.py (hallazgo + recomendación, sin IA)
    docxlib.py     -> llenado real de las tablas de la plantilla Word
                       (clonado de filas, preservando fotos/formato)

`plantilla_base.docx` no tiene placeholders {{...}}: es un informe real que
sirve de "molde" de tablas (una fila de ejemplo por línea). Por eso el
llenado se hace clonando/recortando filas a la cantidad real de líneas del
grupo y sobrescribiendo cada celda con el dato correspondiente.
"""
import copy
import os
import re
import datetime
import openpyxl
from docx import Document
from docx.shared import Inches

import inventario
import psaim
import docxlib
import checklist as checklist_mod
import recomendaciones

RE_FECHA_RANGO = re.compile(r"\d{2}/\d{2}/\d{4}\s+al\s+\d{2}/\d{2}/\d{4}")
RE_EXAMINADOR = re.compile(r"Examinador Nivel II", re.IGNORECASE)


NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_W = docxlib.W_NS


def _reemplazar_foto_portada(doc, ruta_foto):
    """Reemplaza los BYTES de la foto panorámica de portada (la de la
    unidad/grupo que ya trae la plantilla-molde) por la foto real subida en
    la interfaz, conservando el tamaño/posición del marco original.

    El documento trae más de una imagen incrustada (el logo de la empresa,
    ~173x169 casi cuadrado, y la foto panorámica, ~712x533 apaisada) -- se
    identifica la correcta por tamaño de área y relación de aspecto
    apaisada (misma regla que docxlib.find_portada_photo, pero usando el
    lector de imágenes propio de python-docx en vez de PIL, que no es una
    dependencia del proyecto). Nunca se toca el logo. Devuelve True si
    encontró una imagen candidata para reemplazar."""
    candidatos = []
    for p in doc.paragraphs:
        for blip in p._p.findall(f".//{{{NS_A}}}blip"):
            rId = blip.get(f"{{{NS_R}}}embed")
            if not rId:
                continue
            try:
                image_part = doc.part.related_parts[rId]
                w, h = image_part.image.px_width, image_part.image.px_height
            except (KeyError, Exception):
                continue
            if not w or not h:
                continue
            ratio = w / h
            if 1.1 < ratio < 1.6:
                candidatos.append((w * h, image_part))

    if not candidatos:
        return False

    candidatos.sort(key=lambda c: c[0], reverse=True)
    _, image_part = candidatos[0]
    with open(ruta_foto, "rb") as f:
        image_part._blob = f.read()
    return True


def insertar_foto_unidad_segura(doc, ruta_foto):
    """Inserta la foto de la unidad en el documento (en memoria, antes de
    guardar): reemplaza la foto de portada que ya trae la plantilla si
    existe; si no, la agrega al final como respaldo."""
    try:
        if _reemplazar_foto_portada(doc, ruta_foto):
            return
        doc.add_paragraph("Fotografía de la Unidad / Grupo:")
        doc.add_picture(str(ruta_foto), width=Inches(5.0))
    except Exception as e:
        print(f"[!] Aviso al insertar la foto: {e}")


def _primer_texto_cuadro_texto(doc):
    """Devuelve el texto del primer cuadro de texto (txbxContent) no vacío
    del cuerpo -- en la plantilla-molde es donde vive el código de informe
    de muestra, que python-docx no expone vía doc.paragraphs."""
    for cuadro in doc.element.body.iter(f"{{{NS_W}}}txbxContent"):
        texto = "".join(t.text or "" for t in cuadro.iter(f"{{{NS_W}}}t"))
        if texto.strip():
            return texto.strip()
    return None


def _reemplazar_en_cuadros_texto(doc, buscar, reemplazar):
    """Reemplaza, dentro de cualquier cuadro de texto (txbxContent) del
    cuerpo, toda ocurrencia literal de `buscar` por `reemplazar` (p.ej. el
    código de informe de muestra, que vive en un cuadro de texto y no en un
    párrafo normal)."""
    if not buscar or buscar == reemplazar:
        return
    for cuadro in doc.element.body.iter(f"{{{NS_W}}}txbxContent"):
        for p_el in cuadro.iter(f"{{{NS_W}}}p"):
            texto_parrafo = "".join(t.text or "" for t in p_el.iter(f"{{{NS_W}}}t"))
            if buscar in texto_parrafo:
                docxlib.set_para_content(p_el, texto_parrafo.replace(buscar, reemplazar))


def _normalizar_tag_para_match(texto):
    """Normaliza un TAG SOLO para comparar (nunca para mostrar): unifica
    mayúsculas, espacios (incluye NBSP) y comillas tipográficas de pulgada
    a una comilla recta -- la diferencia más común entre cómo un TAG queda
    escrito en el Detalle de grupo y en el nombre de una hoja de Excel."""
    texto = str(texto or "").strip().upper().replace("\xa0", " ")
    texto = re.sub(r"\s+", " ", texto)
    for comilla in ("”", "“", "″", "’", "‘", "'"):
        texto = texto.replace(comilla, '"')
    return texto


def _leer_psaim_por_linea(ruta_psaim, tags):
    """Intenta asociar el Excel PSAIM subido a las líneas del grupo.

    Caso normal: el archivo trae una hoja por línea, nombrada igual (o muy
    parecido) al TAG. Caso de respaldo: el archivo trae una sola hoja/línea
    y el grupo tiene exactamente una línea -> se aplica directo."""
    avisos = []
    resultados = {}
    try:
        wb = openpyxl.load_workbook(ruta_psaim, data_only=True)
    except Exception as e:
        avisos.append(f"No se pudo abrir el archivo PSAIM: {e}")
        return resultados, avisos

    tags_por_norm = {t.strip().upper(): t for t in tags}

    for nombre_hoja in wb.sheetnames:
        norm = nombre_hoja.strip().upper()
        tag_real = tags_por_norm.get(norm)
        if tag_real is None:
            # Reintento tolerante a comillas tipográficas/espacios (p.ej.
            # el nombre de la hoja quedó con ” en vez de ") antes de
            # probar la coincidencia parcial, más arriesgada.
            norm_tol = _normalizar_tag_para_match(nombre_hoja)
            for tnorm, torig in tags_por_norm.items():
                if _normalizar_tag_para_match(tnorm) == norm_tol:
                    tag_real = torig
                    break
        if tag_real is None:
            for tnorm, torig in tags_por_norm.items():
                if tnorm and (tnorm in norm or norm in tnorm):
                    tag_real = torig
                    break
        if tag_real is None:
            continue
        try:
            resultados[tag_real] = psaim.leer_psaim_hoja(wb[nombre_hoja])
        except psaim.PSAIMFaltaDetalle as e:
            avisos.append(str(e))

    if not resultados and len(tags) == 1:
        try:
            resultados[tags[0]] = psaim.leer_psaim(ruta_psaim)
        except psaim.PSAIMFaltaDetalle as e:
            avisos.append(str(e))

    if not resultados:
        avisos.append(
            "No se pudo asociar el archivo PSAIM a ninguna línea del grupo "
            "(se espera una hoja por línea, nombrada igual al TAG)."
        )
    return resultados, avisos


def _reemplazar_fecha_inspeccion_parrafo(doc, fecha_ini, fecha_fin):
    for p in doc.paragraphs:
        if RE_FECHA_RANGO.search(p.text):
            nuevo_texto = RE_FECHA_RANGO.sub(f"{fecha_ini} al {fecha_fin}", p.text)
            docxlib.set_para_content(p._p, nuevo_texto)
            return True
    return False


def _reemplazar_bloque_examinadores(doc, lista_examinadores):
    candidatos = [p for p in doc.paragraphs if RE_EXAMINADOR.search(p.text)]
    if not candidatos:
        return False
    anchor_el = candidatos[0]._p
    for p in candidatos[1:]:
        p._p.getparent().remove(p._p)
    if lista_examinadores:
        docxlib.clone_paragraph_block(anchor_el, lista_examinadores)
    return True


def _reemplazar_texto_literal_parrafos(doc, buscar, reemplazar):
    """Reemplaza, en todos los párrafos del cuerpo, cualquier ocurrencia
    literal de `buscar` por `reemplazar` (usado para el nombre de grupo de
    muestra de la plantilla, que aparece repetido en varios párrafos
    narrativos, no solo en la tabla de encabezado)."""
    if not buscar or buscar == reemplazar:
        return
    for p in doc.paragraphs:
        if buscar in p.text:
            docxlib.set_para_content(p._p, p.text.replace(buscar, reemplazar))


def _es_retirada(observacion):
    return bool(observacion) and "retirad" in str(observacion).strip().lower()


def _lista_espanol(numeros):
    numeros = [str(n) for n in numeros]
    if not numeros:
        return ""
    if len(numeros) == 1:
        return numeros[0]
    return ", ".join(numeros[:-1]) + " y " + numeros[-1]


def _es_pendiente_anexo(fila):
    return bool(fila.get("entrega_anexo"))


def _agregar_nota_pendiente_anexo(doc, filas_tecnicas):
    """Agrega, como viñeta(s) NUEVA(S) dentro de la misma lista de notas de
    "1.0 Sumario de Inspección" (justo debajo de la nota de "solo se
    realizó inspección visual", con el mismo estilo de lista), un aviso
    por cada texto distinto que el usuario haya escrito en la columna "SE
    ENTREGARA COMO INFORME ANEXO" del Detalle de grupo. Esas líneas NO
    llevan hallazgo, ni recomendación, ni checklist, ni Anexo en ESTE
    informe -- se inspeccionarán después y se entregarán como Informe
    Complementario / Anexo Adicional aparte.

    Cuando dos o más líneas describen EL MISMO motivo (el mismo texto, sin
    contar la referencia a "Línea N°..." que cada una trae con su propio
    número), se unifican en una sola viñeta con la lista de líneas al
    inicio; si el motivo es distinto entre líneas, cada una conserva su
    propia viñeta -- nunca se inventa una frase genérica que mezcle
    motivos distintos."""
    pendientes = [f for f in filas_tecnicas if _es_pendiente_anexo(f)]
    if not pendientes:
        return False

    # Se quita el "Línea N° X" (o "Líneas N° X") que el propio texto trae
    # al inicio, si lo trae, para comparar solo el MOTIVO real -- dos
    # textos que solo difieren en el número de línea SÍ deben unificarse.
    _RE_PREFIJO_LINEA = re.compile(
        r"^l[íi]neas?\s*n[°ºo]?\.?\s*\d+(?:\s*[,y]\s*\d+)*\s*[:,\-–]?\s*",
        re.IGNORECASE,
    )

    grupos = {}
    orden_grupos = []
    for f in pendientes:
        texto = str(f["entrega_anexo"]).strip()
        motivo = _RE_PREFIJO_LINEA.sub("", texto).strip() or texto
        clave = motivo.lower()
        if clave not in grupos:
            grupos[clave] = {"motivo": motivo, "items": []}
            orden_grupos.append(clave)
        grupos[clave]["items"].append(f["item"])

    anchor = None
    for p in doc.paragraphs:
        if "solo se realizó inspección visual" in p.text:
            anchor = p._p
            break
    if anchor is None:
        return False

    punto_insercion = anchor
    for clave in orden_grupos:
        grupo = grupos[clave]
        etiqueta = "Línea" if len(grupo["items"]) == 1 else "Líneas"
        texto_nota = f"{etiqueta} N° {_lista_espanol(grupo['items'])}: {grupo['motivo']}"
        nuevo_p = copy.deepcopy(anchor)
        punto_insercion.addnext(nuevo_p)
        docxlib.set_para_content(nuevo_p, texto_nota)
        punto_insercion = nuevo_p
    return True


def _reemplazar_nota_solo_vt(doc, filas_activas):
    """Actualiza el párrafo NOTA de la tabla 0 ("En las líneas N°... solo
    se realizó inspección visual...") con los ítems cuyo alcance del
    servicio NO incluye medición de espesores (UT) -- se excluyen las
    líneas retiradas, que no llevan ninguna inspección."""
    solo_vt = [
        f["item"] for f in filas_activas
        if str(f.get("alcance") or "").strip().upper() != "LINEAS"
    ]
    for p in doc.paragraphs:
        if "solo se realizó inspección visual" in p.text:
            if solo_vt:
                nuevo = (
                    f"En las líneas N° {_lista_espanol(solo_vt)}, solo se realizó "
                    "inspección visual, tal como se especifica en los alcances del "
                    "servicio. "
                )
            else:
                nuevo = (
                    "Todas las líneas del grupo cuentan con inspección visual y "
                    "medición de espesores (UT), según los alcances del servicio. "
                )
            docxlib.set_para_content(p._p, nuevo)
            return True
    return False


# Frecuencia de inspección UT-VT por Clase API 570 (tabla de referencia
# fija proporcionada por el usuario) -- solo se usa el intervalo de años de
# cada clase, el texto ya está definido, no se redacta de nuevo.
SENTENCIA_INTERVALO_POR_CLASE = {
    "clase 1": (
        "Programar la próxima inspección visual y Medición de espesores en "
        "un periodo no mayor a 5 años, como lo indica API 570, tabla 1."
    ),
    "clase 2": (
        "Programar la próxima inspección visual en un periodo no mayor a 5 "
        "años y Medición de espesores en un intervalo máximo de 10 años, "
        "como lo indica API 570, tabla 1."
    ),
    "clase 3": (
        "Programar la próxima inspección visual y Medición de espesores en "
        "un periodo no mayor a 10 años, como lo indica API 570, tabla 1."
    ),
    "clase 4": (
        "Programar la próxima medición de espesores en un periodo no mayor "
        "a 10 años y la próxima inspección externa en un periodo no mayor "
        "a 5 años, como lo indica API 570, tabla 1. (opcional por ser "
        "tubería clase 04)."
    ),
    "punto de inyeccion": (
        "Programar la próxima inspección visual y Medición de espesores en "
        "un periodo no mayor a 3 años, como lo indica API 570, tabla 1."
    ),
}


def _normalizar_clase(clase):
    t = str(clase or "").strip().lower()
    t = t.replace("í", "i").replace("ó", "o")
    return t


def _construir_bloque_recomendaciones_por_clase(filas_activas):
    """Agrupa las líneas activas por Clase API 570 y arma un párrafo por
    clase presente en el grupo: qué N° de líneas son de esa clase, seguido
    del intervalo de inspección UT/VT ya definido para esa clase (tabla de
    referencia del usuario) -- nunca se redacta un intervalo nuevo."""
    por_clase = {}
    for f in filas_activas:
        clase_norm = _normalizar_clase(f.get("clase"))
        if clase_norm not in SENTENCIA_INTERVALO_POR_CLASE:
            continue
        por_clase.setdefault(clase_norm, []).append(f["item"])

    parrafos = []
    orden = ["clase 1", "clase 2", "clase 3", "clase 4", "punto de inyeccion"]
    for clase_norm in orden:
        items = por_clase.get(clase_norm)
        if not items:
            continue
        etiqueta = "Punto de inyección" if clase_norm == "punto de inyeccion" else clase_norm.capitalize()
        parrafos.append(
            f"Para las líneas N° {_lista_espanol(items)} ({etiqueta}): "
            + SENTENCIA_INTERVALO_POR_CLASE[clase_norm]
        )
    return parrafos


def _reemplazar_recomendaciones_por_clase(doc, filas_activas):
    """Reemplaza el párrafo único de RECOMENDACIONES de la plantilla-molde
    por uno o más párrafos (uno por Clase API 570 presente en el grupo)."""
    parrafos = _construir_bloque_recomendaciones_por_clase(filas_activas)
    if not parrafos:
        return False
    for p in doc.paragraphs:
        if "Programar la próxima inspección visual" in p.text:
            docxlib.clone_paragraph_block(p._p, parrafos)
            return True
    return False


def ejecutar_proceso_grupo(
    grupo_buscado,
    ruta_maestro,
    ruta_base_lineas,
    ruta_plantilla_word,
    dir_salida="salida_informes",
    ruta_foto=None,
    ruta_checklist=None,
    ruta_psaim=None,
    elaborador=None,
):
    print(f"[*] Iniciando procesamiento automático para el grupo: {grupo_buscado}")
    os.makedirs(dir_salida, exist_ok=True)
    avisos = []

    # 1. Detalle de grupo / líneas cargado en la interfaz (alcance del servicio)
    lineas_alcance = inventario.cargar_alcance(ruta_maestro)
    if not lineas_alcance:
        raise ValueError("El archivo de detalle de grupo/líneas no contiene líneas válidas.")
    tags_ordenados = [ln["tag"] for ln in lineas_alcance]
    print(f"[*] Líneas detectadas para el grupo {grupo_buscado}: {tags_ordenados}")

    # 2. Cruce técnico contra la Base Maestra FASE1 (datos de operación/diseño)
    inv = inventario.cargar_inventario(ruta_base_lineas)
    inv_por_norm = {k.strip().upper(): v for k, v in inv.items()}

    filas_tecnicas = []
    for i, ln in enumerate(lineas_alcance, start=1):
        tag = ln["tag"]
        inv_row = inv_por_norm.get(tag.strip().upper())
        datos_tecnicos, avisos_linea = inventario.cruzar_linea(tag, inv_row)
        avisos.extend(avisos_linea)
        filas_tecnicas.append({
            # Numeración SIEMPRE secuencial dentro del grupo (1, 2, 3...):
            # la columna "ITEM POR MES" del detalle es un contador mensual
            # cruzado entre grupos (p.ej. 158), no el N° de línea del informe.
            "item": str(i),
            "sap": str(ln.get("sap") or "SIN DATO"),
            "unidad": str(ln.get("unidad") or "SIN DATO"),
            "tag": tag,
            "alcance": ln.get("alcance"),
            "observacion": (str(ln["observacion"]).strip() if ln.get("observacion") else None),
            "entrega_anexo": (str(ln["entrega_anexo"]).strip() if ln.get("entrega_anexo") else None),
            **datos_tecnicos,
        })

    # Las líneas retiradas del plan (NOTAS/observación con "retirad...") y
    # las que el usuario marcó para entregarse como Informe Complementario
    # / Anexo Adicional aparte (columna "SE ENTREGARA COMO INFORME ANEXO")
    # solo se muestran en las tablas técnicas (0 y 5); nunca en
    # Recomendación (1) ni en Hallazgos (7), donde no corresponde ninguna
    # inspección todavía.
    filas_activas = [
        f for f in filas_tecnicas
        if not _es_retirada(f.get("observacion")) and not _es_pendiente_anexo(f)
    ]

    # 3. PSAIM: rate de corrosión y vida útil por línea (si se subió el archivo)
    psaim_por_tag = {}
    if ruta_psaim and os.path.exists(str(ruta_psaim)):
        print("[*] Procesando reporte PSAIM...")
        psaim_por_tag, avisos_psaim = _leer_psaim_por_linea(str(ruta_psaim), tags_ordenados)
        avisos.extend(avisos_psaim)

    # 4. Checklist VT: parchar con el motor de reglas (recomendaciones.py)
    hallazgos_por_tag = {}
    ruta_checklist_salida = os.path.join(dir_salida, f"Checklist_VT_{grupo_buscado}.xlsx")
    if ruta_checklist and os.path.exists(str(ruta_checklist)):
        print("[*] Procesando y parchando el Checklist VT...")
        avisos_chk, hallazgos_por_tag = checklist_mod.parchar_checklist_vt(
            str(ruta_checklist), {}, ruta_checklist_salida
        )
        avisos.extend(avisos_chk)
        print("[✔] Checklist parchado correctamente.")
    else:
        avisos.append(
            "No se cargó VT-CHECK LIST: la tabla de Recomendación y Hallazgos "
            "quedará como 'PENDIENTE' hasta que se suba el checklist."
        )

    # 5. Generar el informe Word real a partir de la plantilla-molde
    print("[*] Generando informe en Word...")
    doc = Document(str(ruta_plantilla_word))

    if not elaborador:
        elaborador = next(
            (str(ln["elaborador"]).strip() for ln in lineas_alcance if ln.get("elaborador")),
            None,
        )

    fecha_ini, fecha_fin, examinadores = inventario.derivar_fecha_y_examinadores(
        lineas_alcance, elaborador
    )
    fecha_ini_txt = fecha_ini or "PENDIENTE"
    fecha_fin_txt = fecha_fin or "PENDIENTE"

    # El nombre de grupo que se MUESTRA en el informe viene de la columna
    # "GRUPO DE TUBERÍAS" del detalle de grupo, no del nombre del archivo
    # subido (que puede traer prefijos como "GRUPO-" y duplicar la palabra
    # con la etiqueta fija de la plantilla, p.ej. "GRUPO GRUPO-22-...").
    nombre_grupo_real = next(
        (str(ln["grupo"]).strip() for ln in lineas_alcance if ln.get("grupo")), None
    ) or grupo_buscado

    # El nombre de grupo y el código de informe de muestra de la
    # plantilla-molde aparecen repetidos en varios párrafos narrativos y en
    # cuadros de texto -- se capturan ANTES de sobrescribirlos.
    grupo_muestra = doc.tables[2].cell(2, 1).text.strip() if len(doc.tables) > 2 else None
    codigo_muestra = _primer_texto_cuadro_texto(doc)
    codigo_informe = next(
        (str(ln["codigo_informe"]).strip() for ln in lineas_alcance if ln.get("codigo_informe")),
        None,
    )

    # -- Tabla 2: encabezado (cliente/grupo/fechas) -------------------------
    if len(doc.tables) > 2:
        tabla_header = doc.tables[2]
        try:
            docxlib.set_cell_text(tabla_header.cell(2, 1)._tc, nombre_grupo_real)
            docxlib.set_cell_text(tabla_header.cell(4, 2)._tc, f"{fecha_ini_txt} al {fecha_fin_txt}")
            docxlib.set_cell_text(
                tabla_header.cell(4, 3)._tc, datetime.date.today().strftime("%d/%m/%Y")
            )
        except IndexError:
            avisos.append("La tabla de encabezado de la plantilla no tiene la estructura esperada.")

    if codigo_muestra and codigo_informe:
        _reemplazar_en_cuadros_texto(doc, codigo_muestra, codigo_informe)

    _reemplazar_fecha_inspeccion_parrafo(doc, fecha_ini_txt, fecha_fin_txt)
    _reemplazar_bloque_examinadores(doc, examinadores)

    if grupo_muestra and grupo_muestra != nombre_grupo_real:
        _reemplazar_texto_literal_parrafos(doc, grupo_muestra, nombre_grupo_real)

    _agregar_nota_pendiente_anexo(doc, filas_tecnicas)
    _reemplazar_nota_solo_vt(doc, filas_activas)
    _reemplazar_recomendaciones_por_clase(doc, filas_activas)

    n = len(tags_ordenados)
    n_activas = len(filas_activas)

    # -- Tabla 0: N°, SAP, Línea, Rate Corrosión, Vida Útil ------------------
    if len(doc.tables) > 0:
        filas0 = docxlib.clone_table_to_n_rows(doc.tables[0], n, header_rows=1)
        for tr, fila in zip(filas0, filas_tecnicas):
            p = psaim_por_tag.get(fila["tag"])
            if p:
                rate = f"{psaim.rate_corrosion_mm_anio(p['rcr_mpy']):g}"
                vida = psaim.vida_util_display(p["vida_util_anios"], fila.get("clase", ""))
            else:
                rate, vida = "---", "---"
            docxlib.fill_row(tr, [fila["item"], fila["sap"], fila["tag"], rate, vida])

    # -- Tabla 5: datos técnicos completos (operación/diseño) ---------------
    if len(doc.tables) > 5:
        filas5 = docxlib.clone_table_to_n_rows(doc.tables[5], n, header_rows=2)
        for tr, fila in zip(filas5, filas_tecnicas):
            docxlib.fill_row(tr, [
                fila["item"], fila["sap"], fila["tag"],
                fila["pres_oper_psi"], fila["temp_oper_f"],
                fila["pres_dis_psi"], fila["temp_dis_f"],
                fila["schedule"], fila["material"],
                fila["inicio"], fila["termino"], fila["fluido"], fila["clase"],
            ])

    # -- Tabla 6: mecanismo de daño asociado (catálogo de 20, cruzado con --
    # -- los hallazgos reales de la inspección, sin IA) ----------------------
    if len(doc.tables) > 6:
        todos_los_hallazgos = [
            info["hallazgo"]
            for items_chk in hallazgos_por_tag.values()
            for info in items_chk
            if info["hallazgo"]
        ]
        fluidos_activos = [f.get("fluido") for f in filas_activas]
        mecanismos = recomendaciones.detectar_mecanismos_dano(todos_los_hallazgos, fluidos_activos)
        if mecanismos:
            filas6 = docxlib.clone_table_to_n_rows(doc.tables[6], len(mecanismos), header_rows=1)
            for i, (tr, mecanismo) in enumerate(zip(filas6, mecanismos), start=1):
                # La celda "Aplica" ya trae una viñeta Wingdings que se ve
                # como "✓" (numId=12, w:numFmt="bullet"); dejarla vacía de
                # texto para no duplicar el check.
                docxlib.fill_row(tr, [str(i), mecanismo, ""])
        elif not ruta_checklist:
            docxlib.fill_row(
                docxlib.clone_table_to_n_rows(doc.tables[6], 1, header_rows=1)[0],
                ["1", "PENDIENTE (falta checklist VT para determinar el mecanismo de daño)", ""],
            )
        else:
            docxlib.fill_row(
                docxlib.clone_table_to_n_rows(doc.tables[6], 1, header_rows=1)[0],
                ["1", "Sin mecanismos de daño identificados en los hallazgos registrados", ""],
            )

    # -- Tabla 1: recomendación técnica por línea (del checklist VT) --------
    # Las líneas retiradas del plan no llevan fila aquí (solo en tablas 0/5).
    # Cada recomendación va numerada (1, 2, 3...) en un párrafo propio --
    # misma numeración/orden que su hallazgo correspondiente en la tabla 7.
    if len(doc.tables) > 1:
        filas1 = docxlib.clone_table_to_n_rows(doc.tables[1], n_activas, header_rows=1)
        for tr, fila in zip(filas1, filas_activas):
            items_chk = hallazgos_por_tag.get(fila["tag"])
            if items_chk:
                recomendacion = [info["recomendacion"] for info in items_chk if info["recomendacion"]]
            elif fila.get("observacion"):
                recomendacion = fila["observacion"]
            elif ruta_checklist:
                recomendacion = "Sin hallazgos relevantes registrados en el checklist VT."
            else:
                recomendacion = "PENDIENTE (falta checklist VT para redactar hallazgo/recomendación)"
            docxlib.fill_row_multi(tr, [fila["item"], fila["tag"], recomendacion])

    # -- Tabla 7: hallazgos relevantes en VT y UT por línea ------------------
    # Las líneas retiradas del plan no llevan fila aquí (solo en tablas 0/5).
    # El resumen de PSAIM (UT) va SIN numerar, como prefijo; los hallazgos
    # de VT van numerados (1, 2, 3...) debajo, en el mismo orden que sus
    # recomendaciones correspondientes en la tabla 1.
    if len(doc.tables) > 7:
        filas7 = docxlib.clone_table_to_n_rows(doc.tables[7], n_activas, header_rows=1)
        for tr, fila in zip(filas7, filas_activas):
            prefijo_psaim = ""
            p = psaim_por_tag.get(fila["tag"])
            if p:
                rate = psaim.rate_corrosion_mm_anio(p["rcr_mpy"])
                vida = psaim.vida_util_display(p["vida_util_anios"], fila.get("clase", ""))
                prefijo_psaim = f"Rate de corrosión {rate:g} mm/año, con una vida remanente {vida} años."

            items_chk = hallazgos_por_tag.get(fila["tag"])
            lista_hallazgos = [info["hallazgo"] for info in items_chk if info["hallazgo"]] if items_chk else []

            if not prefijo_psaim and not lista_hallazgos:
                texto_pendiente = fila.get("observacion") or "PENDIENTE (línea aún sin inspección de campo)"
                tcs = tr.findall(docxlib.qn("w:tc"))
                docxlib.set_cell_text(tcs[0], fila["item"])
                docxlib.set_cell_text(tcs[1], fila["unidad"])
                docxlib.set_cell_text(tcs[2], fila["tag"])
                if len(docxlib.get_tc_paragraphs(tcs[3])) >= 2:
                    # Esta fila sí trae el párrafo de prefijo PSAIM (sin
                    # numerar) separado del párrafo de hallazgos VT
                    # (numerado, "1)..."): dejar cada "pendiente" en su
                    # párrafo correcto en vez de que ambos caigan juntos
                    # en el primer párrafo (sin numeración) por defecto.
                    docxlib.set_cell_text_prefijo_mas_lista(
                        tcs[3],
                        "PENDIENTE (falta reporte de ultrasonido / PSAIM).",
                        [texto_pendiente],
                    )
                else:
                    docxlib.set_cell_text(tcs[3], texto_pendiente)
                continue

            tcs = tr.findall(docxlib.qn("w:tc"))
            docxlib.set_cell_text(tcs[0], fila["item"])
            docxlib.set_cell_text(tcs[1], fila["unidad"])
            docxlib.set_cell_text(tcs[2], fila["tag"])
            docxlib.set_cell_text_prefijo_mas_lista(tcs[3], prefijo_psaim, lista_hallazgos)

    ruta_word_salida = os.path.join(dir_salida, f"Informe_{grupo_buscado}.docx")

    if ruta_foto and os.path.exists(str(ruta_foto)):
        insertar_foto_unidad_segura(doc, ruta_foto)
        print("[✔] Foto de la unidad procesada e insertada en el informe.")

    doc.save(ruta_word_salida)
    print(f"[✔] Informe Word generado con éxito en: {ruta_word_salida}")

    print(f"[✔] ¡Proceso completo finalizado para el grupo {grupo_buscado}!")
    if avisos:
        print("[!] Avisos del proceso:")
        for a in avisos:
            print("    -", a)

    return {
        "avisos": avisos,
        "ruta_word": ruta_word_salida,
        "ruta_checklist": ruta_checklist_salida if (ruta_checklist and os.path.exists(str(ruta_checklist))) else None,
        "tags": tags_ordenados,
        "unidad": filas_tecnicas[0]["unidad"] if filas_tecnicas else None,
        "lineas_alcance": lineas_alcance,
        "psaim_por_tag": psaim_por_tag,
        "hallazgos_por_tag": hallazgos_por_tag,
        "codigo_informe": codigo_informe,
    }


def _reemplazar_sumario_complementario(doc, sumario_texto):
    """Reemplaza el párrafo "1.0 SUMARIO DE INSPECCIÓN" de la plantilla
    complementaria por el texto libre escrito por el especialista (a
    diferencia del informe principal, esta narrativa es demasiado
    específica -- qué líneas puntuales presentan qué hallazgos -- para
    redactarla de forma confiable sin intervención humana)."""
    ancla = "Como resultado de la aplicación de las técnicas de inspección"
    for p in doc.paragraphs:
        if ancla in p.text:
            if sumario_texto and sumario_texto.strip():
                docxlib.set_para_content(p._p, sumario_texto.strip())
            return True
    return False


def _reemplazar_nota_anexo_complementario(doc, codigo_informe_principal, filas_activas):
    """Reemplaza la NOTA de la plantilla complementaria ("El presente
    documento es un anexo complementario al informe principal...") con el
    código del informe principal y el N° de las líneas efectivamente
    incluidas en este anexo (el N° ORIGINAL de cada línea, si el detalle
    de grupo lo trae; si no, el orden secuencial normal)."""
    ancla = "es un anexo complementario al informe principal"
    for p in doc.paragraphs:
        if ancla in p.text:
            codigo = (codigo_informe_principal or "").strip() or "PENDIENTE"
            lista = _lista_espanol([f["item"] for f in filas_activas])
            nuevo = (
                f"El presente documento es un anexo complementario al informe "
                f"principal {codigo}, referente a la inspección de la Línea "
                f"N° {lista}."
            )
            docxlib.set_para_content(p._p, nuevo)
            return True
    return False


def ejecutar_proceso_grupo_complementario(
    grupo_buscado,
    ruta_maestro,
    ruta_base_lineas,
    ruta_plantilla_word,
    dir_salida="salida_informes",
    ruta_foto=None,
    ruta_checklist=None,
    elaborador=None,
    codigo_informe_principal=None,
    sumario_texto=None,
):
    """Genera un Informe Complementario / Anexo Adicional: mismo flujo que
    ejecutar_proceso_grupo(), pero para el caso en que un subconjunto de
    líneas de un grupo YA CERRADO se inspecciona tiempo después y se
    entrega como anexo al informe principal. Diferencias clave, todas
    reflejadas en `plantilla_complementario.docx` (una plantilla-molde
    propia, con 6 tablas en vez de 8 -- sin PSAIM ni datos técnicos
    completos):
      - Nunca hay PSAIM/UT: la tabla 0 solo trae N°/SAP/Línea.
      - El N° de cada línea es el N° ORIGINAL del informe principal (si
        el detalle de grupo trae esa columna), no un recuento 1..n nuevo.
      - El Sumario de Inspección es texto libre (ver
        _reemplazar_sumario_complementario).
      - Se agrega la NOTA de "anexo complementario al informe principal
        [código]" en vez de la nota de "solo inspección visual".
      - La sección RECOMENDACIONES sigue el mismo mecanismo por Clase API
        570 que el informe principal (se reutiliza tal cual)."""
    print(f"[*] Iniciando procesamiento de informe complementario para el grupo: {grupo_buscado}")
    os.makedirs(dir_salida, exist_ok=True)
    avisos = []

    lineas_alcance = inventario.cargar_alcance(ruta_maestro)
    if not lineas_alcance:
        raise ValueError("El archivo de detalle de grupo/líneas no contiene líneas válidas.")
    tags_ordenados = [ln["tag"] for ln in lineas_alcance]
    print(f"[*] Líneas detectadas: {tags_ordenados}")

    inv = inventario.cargar_inventario(ruta_base_lineas)
    inv_por_norm = {k.strip().upper(): v for k, v in inv.items()}

    filas_tecnicas = []
    for i, ln in enumerate(lineas_alcance, start=1):
        tag = ln["tag"]
        inv_row = inv_por_norm.get(tag.strip().upper())
        datos_tecnicos, avisos_linea = inventario.cruzar_linea(tag, inv_row)
        avisos.extend(avisos_linea)
        numero_original = str(ln.get("numero_original") or "").strip()
        filas_tecnicas.append({
            "item": numero_original or str(i),
            "sap": str(ln.get("sap") or "SIN DATO"),
            "unidad": str(ln.get("unidad") or "SIN DATO"),
            "tag": tag,
            "alcance": ln.get("alcance"),
            "observacion": (str(ln["observacion"]).strip() if ln.get("observacion") else None),
            **datos_tecnicos,
        })

    filas_activas = [f for f in filas_tecnicas if not _es_retirada(f.get("observacion"))]

    hallazgos_por_tag = {}
    ruta_checklist_salida = os.path.join(dir_salida, f"Checklist_VT_{grupo_buscado}.xlsx")
    if ruta_checklist and os.path.exists(str(ruta_checklist)):
        print("[*] Procesando y parchando el Checklist VT...")
        avisos_chk, hallazgos_por_tag = checklist_mod.parchar_checklist_vt(
            str(ruta_checklist), {}, ruta_checklist_salida
        )
        avisos.extend(avisos_chk)
    else:
        avisos.append(
            "No se cargó VT-CHECK LIST: la tabla de Recomendación y Hallazgos "
            "quedará como 'PENDIENTE' hasta que se suba el checklist."
        )

    print("[*] Generando informe complementario en Word...")
    doc = Document(str(ruta_plantilla_word))

    if not elaborador:
        elaborador = next(
            (str(ln["elaborador"]).strip() for ln in lineas_alcance if ln.get("elaborador")),
            None,
        )

    fecha_ini, fecha_fin, examinadores = inventario.derivar_fecha_y_examinadores(
        lineas_alcance, elaborador
    )
    fecha_ini_txt = fecha_ini or "PENDIENTE"
    fecha_fin_txt = fecha_fin or "PENDIENTE"

    nombre_grupo_real = next(
        (str(ln["grupo"]).strip() for ln in lineas_alcance if ln.get("grupo")), None
    ) or grupo_buscado

    grupo_muestra = doc.tables[2].cell(2, 1).text.strip() if len(doc.tables) > 2 else None
    codigo_muestra = _primer_texto_cuadro_texto(doc)
    codigo_informe = next(
        (str(ln["codigo_informe"]).strip() for ln in lineas_alcance if ln.get("codigo_informe")),
        None,
    )

    if len(doc.tables) > 2:
        tabla_header = doc.tables[2]
        try:
            docxlib.set_cell_text(tabla_header.cell(2, 1)._tc, nombre_grupo_real)
            docxlib.set_cell_text(tabla_header.cell(4, 2)._tc, f"{fecha_ini_txt} al {fecha_fin_txt}")
            docxlib.set_cell_text(
                tabla_header.cell(4, 3)._tc, datetime.date.today().strftime("%d/%m/%Y")
            )
        except IndexError:
            avisos.append("La tabla de encabezado de la plantilla no tiene la estructura esperada.")

    if codigo_muestra and codigo_informe:
        _reemplazar_en_cuadros_texto(doc, codigo_muestra, codigo_informe)

    _reemplazar_fecha_inspeccion_parrafo(doc, fecha_ini_txt, fecha_fin_txt)
    _reemplazar_bloque_examinadores(doc, examinadores)

    if grupo_muestra and grupo_muestra != nombre_grupo_real:
        _reemplazar_texto_literal_parrafos(doc, grupo_muestra, nombre_grupo_real)

    _reemplazar_sumario_complementario(doc, sumario_texto)
    _reemplazar_nota_anexo_complementario(doc, codigo_informe_principal, filas_activas)
    _reemplazar_recomendaciones_por_clase(doc, filas_activas)

    n_activas = len(filas_activas)

    # -- Tabla 0: N°, SAP, Línea ---------------------------------------------
    if len(doc.tables) > 0:
        filas0 = docxlib.clone_table_to_n_rows(doc.tables[0], n_activas, header_rows=1)
        for tr, fila in zip(filas0, filas_activas):
            docxlib.fill_row(tr, [fila["item"], fila["sap"], fila["tag"]])

    # -- Tabla 4: características de la línea (datos técnicos operación/ ---
    # -- diseño, igual que la tabla 5 del informe principal) ----------------
    if len(doc.tables) > 4:
        filas4c = docxlib.clone_table_to_n_rows(doc.tables[4], n_activas, header_rows=2)
        for tr, fila in zip(filas4c, filas_activas):
            docxlib.fill_row(tr, [
                fila["item"], fila["sap"], fila["tag"],
                fila["pres_oper_psi"], fila["temp_oper_f"],
                fila["pres_dis_psi"], fila["temp_dis_f"],
                fila["schedule"], fila["material"],
                fila["inicio"], fila["termino"], fila["fluido"], fila["clase"],
            ])

    # -- Tabla 5: mecanismo de daño asociado ---------------------------------
    if len(doc.tables) > 5:
        todos_los_hallazgos = [
            info["hallazgo"]
            for items_chk in hallazgos_por_tag.values()
            for info in items_chk
            if info["hallazgo"]
        ]
        fluidos_activos = [f.get("fluido") for f in filas_activas]
        mecanismos = recomendaciones.detectar_mecanismos_dano(todos_los_hallazgos, fluidos_activos)
        if mecanismos:
            filas5 = docxlib.clone_table_to_n_rows(doc.tables[5], len(mecanismos), header_rows=1)
            for i, (tr, mecanismo) in enumerate(zip(filas5, mecanismos), start=1):
                docxlib.fill_row(tr, [str(i), mecanismo, ""])
        elif not ruta_checklist:
            docxlib.fill_row(
                docxlib.clone_table_to_n_rows(doc.tables[5], 1, header_rows=1)[0],
                ["1", "PENDIENTE (falta checklist VT para determinar el mecanismo de daño)", ""],
            )
        else:
            docxlib.fill_row(
                docxlib.clone_table_to_n_rows(doc.tables[5], 1, header_rows=1)[0],
                ["1", "Sin mecanismos de daño identificados en los hallazgos registrados", ""],
            )

    # -- Tabla 1: recomendación técnica por línea (del checklist VT) --------
    if len(doc.tables) > 1:
        filas1 = docxlib.clone_table_to_n_rows(doc.tables[1], n_activas, header_rows=1)
        for tr, fila in zip(filas1, filas_activas):
            items_chk = hallazgos_por_tag.get(fila["tag"])
            if items_chk:
                recomendacion = [info["recomendacion"] for info in items_chk if info["recomendacion"]]
            elif fila.get("observacion"):
                recomendacion = fila["observacion"]
            elif ruta_checklist:
                recomendacion = "Sin hallazgos relevantes registrados en el checklist VT."
            else:
                recomendacion = "PENDIENTE (falta checklist VT para redactar hallazgo/recomendación)"
            docxlib.fill_row_multi(tr, [fila["item"], fila["tag"], recomendacion])

    # -- Tabla 6: hallazgos relevantes en VT por línea (sin PSAIM/UT) -------
    if len(doc.tables) > 6:
        filas6 = docxlib.clone_table_to_n_rows(doc.tables[6], n_activas, header_rows=1)
        for tr, fila in zip(filas6, filas_activas):
            items_chk = hallazgos_por_tag.get(fila["tag"])
            lista_hallazgos = [info["hallazgo"] for info in items_chk if info["hallazgo"]] if items_chk else []
            if not lista_hallazgos:
                lista_hallazgos = [fila.get("observacion") or "PENDIENTE (línea aún sin inspección de campo)"]
            docxlib.fill_row_multi(tr, [fila["item"], fila["unidad"], fila["tag"], lista_hallazgos])

    ruta_word_salida = os.path.join(dir_salida, f"Informe_Complementario_{grupo_buscado}.docx")

    if ruta_foto and os.path.exists(str(ruta_foto)):
        insertar_foto_unidad_segura(doc, ruta_foto)
        print("[✔] Foto de la unidad procesada e insertada en el informe complementario.")

    doc.save(ruta_word_salida)
    print(f"[✔] Informe Complementario Word generado con éxito en: {ruta_word_salida}")

    if avisos:
        print("[!] Avisos del proceso:")
        for a in avisos:
            print("    -", a)

    return {
        "avisos": avisos,
        "ruta_word": ruta_word_salida,
        "ruta_checklist": ruta_checklist_salida if (ruta_checklist and os.path.exists(str(ruta_checklist))) else None,
        "tags": tags_ordenados,
        "lineas_alcance": lineas_alcance,
        "hallazgos_por_tag": hallazgos_por_tag,
        "codigo_informe": codigo_informe,
    }
