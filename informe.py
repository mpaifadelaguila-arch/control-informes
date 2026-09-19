from docx import Document

def generar_word_informe(ruta_plantilla, datos, ruta_salida):
    """
    Lee una plantilla de Word (.docx) y reemplaza las etiquetas (placeholders) 
    con la información combinada del Excel Maestro y la Base de Datos de Líneas.
    """
    doc = Document(ruta_plantilla)
    
    # Mapeo de las etiquetas que están en tu plantilla de Word con los campos del Excel
    reemplazos = {
        "{{GRUPO}}": str(datos.get("GRUPO DE TUBERÍAS", "")),
        "{{UNIDAD}}": str(datos.get("UNIDAD", "")),
        "{{COD_INFORME}}": str(datos.get("CODIGO DE INFORME", "")),
        "{{SAP}}": str(datos.get("SAP", "")),
        "{{LINEAS}}": str(datos.get("LINEAS", "")),
        "{{INSPECTOR}}": str(datos.get("RESPONSABLE", "")),
        "{{OBSERVACION}}": str(datos.get("OBSERVACIÓN", ""))
    }
    
    # 1. Reemplazar etiquetas en los párrafos normales del documento
    for p in doc.paragraphs:
        for clave, valor in reemplazos.items():
            if clave in p.text:
                p.text = p.text.replace(clave, valor)
                
    # 2. Reemplazar etiquetas en las tablas que contenga la plantilla de Word
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                for clave, valor in reemplazos.items():
                    if clave in celda.text:
                        celda.text = celda.text.replace(clave, valor)
                        
    # Guardar el documento final generado para el grupo
    doc.save(ruta_salida)
    print(f"[✔] Informe Word generado con éxito en: {ruta_salida}")
