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

RE_FECHA_RANGO = re.compile(r"\d{2}/\d{2}/\d{4}\s+al\s+\d{2}/\d{2}/\d{4}")
RE_EXAMINADOR = re.compile(r"Examinador Nivel II", re.IGNORECASE)


def insertar_foto_unidad_segura(ruta_word, ruta_foto):
    """Inserta o reemplaza la foto de la unidad en el documento Word de forma segura."""
    try:
        doc = Document(ruta_word)
        for para in doc.paragraphs:
            if "FOTO" in para.text.upper() or "IMAGEN" in para.text.upper():
                para.text = ""
                run = para.add_run()
                run.add_picture(str(ruta_foto), width=Inches(4.5))
                doc.save(ruta_word)
                return

        doc.add_paragraph("Fotografía de la Unidad / Grupo:")
        doc.add_picture(str(ruta_foto), width=Inches(5.0))
        doc.save(ruta_word)
    except Exception as e:
        print(f"[!] Aviso al insertar la foto: {e}")


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
            "item": str(ln.get("item") or i),
            "sap": str(ln.get("sap") or "SIN DATO"),
            "unidad": str(ln.get("unidad") or "SIN DATO"),
            "tag": tag,
            **datos_tecnicos,
        })

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

    fecha_ini, fecha_fin, examinadores = inventario.derivar_fecha_y_examinadores(
        lineas_alcance, elaborador
    )
    fecha_ini_txt = fecha_ini or "PENDIENTE"
    fecha_fin_txt = fecha_fin or "PENDIENTE"

    # -- Tabla 2: encabezado (cliente/grupo/fechas) -------------------------
    if len(doc.tables) > 2:
        tabla_header = doc.tables[2]
        try:
            docxlib.set_cell_text(tabla_header.cell(2, 1)._tc, grupo_buscado)
            docxlib.set_cell_text(tabla_header.cell(4, 2)._tc, f"{fecha_ini_txt} al {fecha_fin_txt}")
            docxlib.set_cell_text(
                tabla_header.cell(4, 3)._tc, datetime.date.today().strftime("%d/%m/%Y")
            )
        except IndexError:
            avisos.append("La tabla de encabezado de la plantilla no tiene la estructura esperada.")

    _reemplazar_fecha_inspeccion_parrafo(doc, fecha_ini_txt, fecha_fin_txt)
    _reemplazar_bloque_examinadores(doc, examinadores)

    n = len(tags_ordenados)

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

    # -- Tabla 1: recomendación técnica por línea (del checklist VT) --------
    if len(doc.tables) > 1:
        filas1 = docxlib.clone_table_to_n_rows(doc.tables[1], n, header_rows=1)
        for tr, fila in zip(filas1, filas_tecnicas):
            items_chk = hallazgos_por_tag.get(fila["tag"])
            if items_chk:
                recomendacion = "\n".join(info["recomendacion"] for info in items_chk if info["recomendacion"])
            elif ruta_checklist:
                recomendacion = "Sin hallazgos relevantes registrados en el checklist VT."
            else:
                recomendacion = "PENDIENTE (falta checklist VT para redactar hallazgo/recomendación)"
            docxlib.fill_row(tr, [fila["item"], fila["tag"], recomendacion])

    # -- Tabla 7: hallazgos relevantes en VT y UT por línea ------------------
    if len(doc.tables) > 7:
        filas7 = docxlib.clone_table_to_n_rows(doc.tables[7], n, header_rows=1)
        for tr, fila in zip(filas7, filas_tecnicas):
            partes = []
            p = psaim_por_tag.get(fila["tag"])
            if p:
                rate = psaim.rate_corrosion_mm_anio(p["rcr_mpy"])
                vida = psaim.vida_util_display(p["vida_util_anios"], fila.get("clase", ""))
                partes.append(f"Rate de corrosión {rate:g} mm/año, con una vida remanente {vida} años.")
            items_chk = hallazgos_por_tag.get(fila["tag"])
            if items_chk:
                partes.extend(info["hallazgo"] for info in items_chk if info["hallazgo"])
            texto = " ".join(partes) if partes else "PENDIENTE (línea aún sin inspección de campo)"
            docxlib.fill_row(tr, [fila["item"], fila["unidad"], fila["tag"], texto])

    ruta_word_salida = os.path.join(dir_salida, f"Informe_{grupo_buscado}.docx")
    doc.save(ruta_word_salida)
    print(f"[✔] Informe Word generado con éxito en: {ruta_word_salida}")

    if ruta_foto and os.path.exists(str(ruta_foto)):
        insertar_foto_unidad_segura(ruta_word_salida, ruta_foto)
        print("[✔] Foto de la unidad procesada e insertada en el informe.")

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
    }
