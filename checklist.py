import openpyxl
import re

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
        
        for fila in range(1, ws.max_row + 1):
            # Obtener el identificador o tag de la línea/ítem desde la columna correspondiente (ej. Columna B)
            item_id = ws.cell(row=fila, column=2).value
            
            if item_id:
                item_id_str = str(item_id).strip()
                # Verificar si el ítem está registrado en el diccionario y posee una imagen adjunta
                if item_id_str in recomendaciones_dict and tiene_foto_en_fila(ws, fila):
                    # Asignar la recomendación o dato técnico en la celda de destino (ej. Columna H)
                    ws.cell(row=fila, column=8).value = recomendaciones_dict[item_id_str]

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
            match = re.search(r'\d+', celda_anclaje)
            if match and int(match.group()) == fila_num:
                return True
    return False
