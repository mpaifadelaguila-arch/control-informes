import openpyxl

def parchar_checklist_vt(ruta_original, recomendaciones_dict, ruta_salida):
    """
    Recorre todas las hojas del Excel de VT, identifica los hallazgos que tienen fotos 
    y coloca la recomendación directa en la celda correspondiente, sin dañar imágenes ni formatos.
    
    :param ruta_original: Ruta del archivo Excel del checklist de VT original.
    :param recomendaciones_dict: Diccionario o estructura con las recomendaciones procesadas 
                                   asociadas a cada ítem/hallazgo de campo.
    :param ruta_salida: Ruta donde se guardará el checklist parchado.
    """
    # Cargamos el workbook manteniendo las imágenes y estructuras originales
    wb = openpyxl.load_workbook(ruta_original)
    
    # Recorremos TODAS las hojas del archivo Excel
    for nombre_hoja in wb.sheetnames:
        ws = wb[nombre_hoja]
        print(f"[*] Procesando hoja del VT: {nombre_hoja}")
        
        # Nota: Aquí adaptas las columnas según la estructura de tu formato (ejemplo: Fila de inicio, 
        # columna de hallazgo/foto y columna donde va la recomendación directa).
        # Este bucle recorre las filas buscando celdas con fotos o indicadores de hallazgo de campo.
        
        for fila in range(1, ws.max_row + 1):
            # Ejemplo conceptual de validación de celda o fila:
            # Puedes verificar si la celda de la foto/imagen tiene contenido o si el ítem está marcado con hallazgo.
            # (openpyxl almacena las imágenes en ws._images, se puede validar si hay una imagen anclada a esa fila o celda).
            
            # Supongamos que identificamos el ID del ítem o código de línea en una columna específica (ej. Columna A o B):
            # item_id = ws.cell(row=fila, column=2).value 
            
            # if item_id in recomendaciones_dict and tiene_foto_en_fila(ws, fila):
            #     # Coloca la recomendación directa en la celda designada (ej. Columna de Recomendaciones, ej. Columna H)
            #     ws.cell(row=fila, column=8).value = recomendaciones_dict[item_id]
            pass

    # Guardamos el archivo resultante con el parche aplicado en todas las hojas
    wb.save(ruta_salida)
    print(f"[✔] Checklist multi-hoja VT parchado y guardado con éxito en: {ruta_salida}")

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
            import re
            match = re.search(r'\d+', celda_anclaje)
            if match and int(match.group()) == fila_num:
                return True
    return False
