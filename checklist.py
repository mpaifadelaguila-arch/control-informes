import openpyxl

def parchar_checklist_vt(ruta_original, datos, ruta_salida):
    wb = openpyxl.load_workbook(ruta_original)
    ws = wb.active
    
    # Ejemplo de lógica para inyectar observaciones/recomendaciones en celdas clave del formato VT
    # (Puedes ajustar las coordenadas de las celdas según la estructura de tu formato de checklist)
    observacion_general = datos.get("OBSERVACIÓN", "Sin observaciones adicionales.")
    
    # Si la celda de comentarios general existe en el checklist, la actualizamos:
    # ws['B40'] = observacion_general 
    
    wb.save(ruta_salida)
    print(f"[✔] Checklist parchado guardado en: {ruta_salida}")
