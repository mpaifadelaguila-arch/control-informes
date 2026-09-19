"""
checklist.py — parcha el VT-CHECK LIST (Excel multihoja) escribiendo, en cada
fila con foto adjunta, el texto de "Hallazgo" y "Recomendación Técnica"
generado por el motor de reglas `recomendaciones.py` (sin IA), a partir de
columnas estructuradas que el inspector de campo llena por fila.

Columnas esperadas en cada hoja (encabezados en la fila 1, no importa el
orden ni si hay columnas extra — se buscan por nombre, tolerante a mayúsculas
y espacios, igual que en inventario.py):

    TAG / LINEA / ITEM      -> identificador de la línea/ítem (obligatoria)
    CASO                    -> id del catálogo de recomendaciones.CATALOGO
                                (ej. "BRIDA_TUERCA_FALTANTE") o su etiqueta
                                en español (obligatoria si hay foto)
    SEVERIDAD                -> LEVE PUNTUAL / LEVE GENERALIZADA / MODERADA / SEVERA
    ACCESIBLE                -> SI / NO (tramo alcanzable para VT de cerca)
    NPS                      -> diámetro nominal (ej. 4")
    LONGITUD                 -> longitud aprox. en metros
    CANTIDAD                 -> cantidad de elementos/uniones/juntas afectados
    UBICACION                -> referencia de ubicación / CML's
    TIPO                     -> tipo de válvula/soporte/aislamiento
    TAG_EQUIPO / MARCA        -> identificación de equipo (válvulas de control)
    COLOR_ACTUAL / COLOR_NORMA-> código de color detectado / reglamentario
    ELEMENTO                 -> tipo de accesorio/tubería/componente
    MATERIAL / SCHEDULE       -> datos del reemplazo (caso tuberías)

Columnas de salida (se escriben si existen encabezados con esos nombres; si
no existen se usa el respaldo histórico de la columna H para la
recomendación):

    HALLAZGO
    RECOMENDACION
"""
import openpyxl
import re

from recomendaciones import generar_hallazgo_y_recomendacion

COL_TAG_CANDIDATOS = ("tag", "linea", "línea", "item", "ítem")
COL_CASO_CANDIDATOS = ("caso",)
COL_SEVERIDAD_CANDIDATOS = ("severidad",)
COL_ACCESIBLE_CANDIDATOS = ("accesible",)
COL_HALLAZGO_SALIDA = ("hallazgo",)
COL_RECOMENDACION_SALIDA = ("recomendacion", "recomendación")

# Nombre de columna de entrada -> clave que espera recomendaciones.py.
COLUMNAS_VARIABLES = {
    "nps": "nps",
    "longitud": "longitud",
    "cantidad": "cantidad",
    "ubicacion": "ubicacion",
    "ubicación": "ubicacion",
    "tipo": "tipo",
    "tag_equipo": "tag",
    "marca": "tag",
    "color_actual": "color_actual",
    "color_norma": "color_norma",
    "elemento": "elemento",
    "material": "material",
    "schedule": "schedule",
}

FALLBACK_COL_TAG = 2  # columna B, respaldo histórico si no hay encabezado.
FALLBACK_COL_RECOMENDACION = 8  # columna H, respaldo histórico.


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _mapear_encabezados(ws):
    """Devuelve {nombre_normalizado: numero_de_columna} leyendo la fila 1."""
    encabezados = {}
    for celda in ws[1]:
        if celda.value is not None:
            encabezados[_norm(celda.value)] = celda.column
    return encabezados


def _buscar_columna(encabezados, candidatos):
    for cand in candidatos:
        if cand in encabezados:
            return encabezados[cand]
    return None


def parchar_checklist_vt(ruta_original, recomendaciones_dict, ruta_salida):
    """Recorre todas las hojas del VT-CHECK LIST, genera con
    `recomendaciones.generar_hallazgo_y_recomendacion` el texto de Hallazgo y
    Recomendación de cada fila que tenga foto adjunta y coloca ese texto en
    las columnas HALLAZGO/RECOMENDACION (o en la columna H, por compatibilidad,
    si el archivo no trae esos encabezados), sin dañar imágenes ni formatos.

    `recomendaciones_dict` se conserva por compatibilidad de firma pero ya no
    es la fuente del texto (ahora se genera por fila con el motor de reglas);
    solo se usa como filtro opcional: si se pasa un dict no vacío, únicamente
    se procesan los TAGs presentes en él.
    """
    wb = openpyxl.load_workbook(ruta_original)
    filtro_tags = set(recomendaciones_dict.keys()) if recomendaciones_dict else None
    avisos = []

    for nombre_hoja in wb.sheetnames:
        ws = wb[nombre_hoja]
        print(f"[*] Procesando hoja del VT: {nombre_hoja}")

        encabezados = _mapear_encabezados(ws)
        col_tag = _buscar_columna(encabezados, COL_TAG_CANDIDATOS) or FALLBACK_COL_TAG
        col_caso = _buscar_columna(encabezados, COL_CASO_CANDIDATOS)
        col_severidad = _buscar_columna(encabezados, COL_SEVERIDAD_CANDIDATOS)
        col_accesible = _buscar_columna(encabezados, COL_ACCESIBLE_CANDIDATOS)
        col_hallazgo_out = _buscar_columna(encabezados, COL_HALLAZGO_SALIDA)
        col_recomendacion_out = (
            _buscar_columna(encabezados, COL_RECOMENDACION_SALIDA)
            or FALLBACK_COL_RECOMENDACION
        )
        col_variables = {
            clave_destino: encabezados[nombre]
            for nombre, clave_destino in COLUMNAS_VARIABLES.items()
            if nombre in encabezados
        }

        if col_caso is None:
            avisos.append(
                f"Hoja '{nombre_hoja}': no se encontró la columna CASO — no se "
                "puede generar Hallazgo/Recomendación en esta hoja."
            )
            continue

        for fila in range(2, ws.max_row + 1):
            item_id = ws.cell(row=fila, column=col_tag).value
            if not item_id:
                continue
            item_id_str = str(item_id).strip()

            if filtro_tags is not None and item_id_str not in filtro_tags:
                continue
            if not tiene_foto_en_fila(ws, fila):
                continue

            caso_val = ws.cell(row=fila, column=col_caso).value
            if not caso_val or not str(caso_val).strip():
                continue

            datos_fila = {"caso": caso_val}
            if col_severidad:
                datos_fila["severidad"] = ws.cell(row=fila, column=col_severidad).value
            if col_accesible:
                datos_fila["accesible"] = ws.cell(row=fila, column=col_accesible).value
            for clave_destino, col_idx in col_variables.items():
                valor = ws.cell(row=fila, column=col_idx).value
                if valor is not None:
                    datos_fila[clave_destino] = valor

            try:
                resultado = generar_hallazgo_y_recomendacion(datos_fila)
            except ValueError as e:
                avisos.append(f"Hoja '{nombre_hoja}', fila {fila}: {e}")
                continue

            if resultado is None:
                # Regla crítica: leve puntual/localizada -> sin recomendación.
                continue

            if col_hallazgo_out:
                ws.cell(row=fila, column=col_hallazgo_out).value = resultado.hallazgo
            ws.cell(row=fila, column=col_recomendacion_out).value = resultado.recomendacion

    wb.save(ruta_salida)
    print(f"[✔] Checklist multi-hoja VT parchado y guardado con éxito en: {ruta_salida}")
    if avisos:
        print("[!] Avisos durante el parchado del checklist:")
        for a in avisos:
            print("    -", a)
    return avisos


def extraer_hallazgos_por_tag(ruta_checklist_parchado):
    """Relee un VT-CHECK LIST ya parchado por `parchar_checklist_vt` y agrupa,
    por TAG, la lista de pares (hallazgo, recomendacion) que se generaron
    (una entrada por fila con foto y caso reconocido). Se usa para volcar el
    mismo texto ya redactado en las tablas del informe Word, sin tener que
    volver a invocar el motor de reglas."""
    wb = openpyxl.load_workbook(ruta_checklist_parchado, data_only=True)
    resultado = {}

    for nombre_hoja in wb.sheetnames:
        ws = wb[nombre_hoja]
        encabezados = _mapear_encabezados(ws)
        col_tag = _buscar_columna(encabezados, COL_TAG_CANDIDATOS) or FALLBACK_COL_TAG
        col_hallazgo_out = _buscar_columna(encabezados, COL_HALLAZGO_SALIDA)
        col_recomendacion_out = (
            _buscar_columna(encabezados, COL_RECOMENDACION_SALIDA)
            or FALLBACK_COL_RECOMENDACION
        )

        for fila in range(2, ws.max_row + 1):
            item_id = ws.cell(row=fila, column=col_tag).value
            if not item_id:
                continue
            recomendacion = ws.cell(row=fila, column=col_recomendacion_out).value
            hallazgo = (
                ws.cell(row=fila, column=col_hallazgo_out).value
                if col_hallazgo_out
                else None
            )
            if not recomendacion and not hallazgo:
                continue
            tag = str(item_id).strip()
            resultado.setdefault(tag, []).append((hallazgo or "", recomendacion or ""))

    return resultado


def tiene_foto_en_fila(ws, fila_num):
    """
    Valida si en una fila específica del checklist existe una imagen incrustada
    (para asegurar que solo se parcheen los hallazgos que tienen fotos).
    """
    if not hasattr(ws, '_images') or not ws._images:
        return False

    for img in ws._images:
        # openpyxl guarda la celda de anclaje de la imagen (ej. 'E12')
        celda_anclaje = img.anchor
        if hasattr(celda_anclaje, '_from'):
            row_idx = celda_anclaje._from.row + 1  # Índice basado en 1
            if row_idx == fila_num:
                return True
        elif isinstance(celda_anclaje, str):
            # Si el anclaje viene como string (ej. 'E12')
            match = re.search(r'\d+', celda_anclaje)
            if match and int(match.group()) == fila_num:
                return True
    return False
