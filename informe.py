from docx import Document

def generar_word_informe(ruta_plantilla, datos, ruta_salida):
    doc = Document(ruta_plantilla)
    
    # Mapeo y reemplazo de variables clave dentro de la plantilla de Word
    reemplazos = {
        "{{GRUPO}}": str(datos.get("GRUPO DE TUBERÍAS", "")),
        "{{UNIDAD}}": str(datos.get("UNIDAD", "")),
        "{{COD_INFORME}}": str(datos.get("CODIGO DE INFORME", "")),
        "{{SAP}}": str(datos.get("SAP", "")),
        "{{LINEAS}}": str(datos.get("LINEAS", "")),
        "{{INSPECTOR}}": str(datos.get("ISNPECTOR", "")),
        "{{OBSERVACION}}": str(datos.get("OBSERVACIÓN", ""))
    }
    
    # Reemplazar en párrafos
    for p in doc.paragraphs:
        for clave, valor in reemplazos.items():
            if clave in p.text:
                p.text = p.text.replace(clave, valor)
                
    # Reemplazar en tablas si las hubiera en la plantilla
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                for clave, valor in reemplazos.items():
                    if clave in celda.text:
                        celda.text = celda.text.replace(clave, valor)
                        
    doc.save(ruta_salida)
