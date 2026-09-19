import os
import pandas as pd
from docx import Document
from docx.shared import Inches
from informe import generar_word_informe
from checklist import parchar_checklist_vt

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

def ejecutar_proceso_grupo(grupo_buscado, ruta_maestro, ruta_base_lineas, ruta_plantilla_word, dir_salida="salida_informes", ruta_foto=None, ruta_checklist=None):
    print(f"[*] Iniciando procesamiento automático para el grupo: {grupo_buscado}")
    
    # 1. Leer el archivo de detalle del grupo cargado en la interfaz
    df_maestro = pd.read_excel(ruta_maestro)
    
    # Identificar la columna de líneas de forma flexible
    col_lineas = None
    for c in df_maestro.columns:
        if any(term in str(c).lower() for term in ["linea", "tag", "tuberia"]):
            col_lineas = c
            break
    if not col_lineas:
        col_lineas = df_maestro.columns[5] if len(df_maestro.columns) > 5 else df_maestro.columns[0]
        
    lista_tags_lineas = df_maestro[col_lineas].dropna().astype(str).str.strip().tolist()
    print(f"[*] Tags de línea detectados para el grupo {grupo_buscado}: {lista_tags_lineas}")
    
    # 2. Leer la Base de Datos FASE 1 y cruzar los parámetros técnicos
    df_base_lineas = pd.read_excel(ruta_base_lineas)
    
    col_base_tag = None
    for c in df_base_lineas.columns:
        if any(term in str(c).lower() for term in ["linea", "tag"]):
            col_base_tag = c
            break
    if not col_base_tag:
        col_base_tag = df_base_lineas.columns[0]
    
    # Filtrado estricto asegurando limpieza de espacios y mayúsculas/minúsculas
    df_base_lineas['tag_clean'] = df_base_lineas[col_base_tag].astype(str).str.strip()
    lista_tags_clean = [t.upper() for t in lista_tags_lineas]
    
    df_filtrado_tecnico = df_base_lineas[df_base_lineas['tag_clean'].str.upper().isin(lista_tags_clean)]
    
    lista_datos_tecnicos = df_filtrado_tecnico.to_dict(orient="records") if not df_filtrado_tecnico.empty else []
    
    contexto = {
        "GRUPO DE TUBERÍAS": grupo_buscado,
        "LINEAS": ", ".join(lista_tags_lineas),
        "tabla_lineas": lista_datos_tecnicos
    }
    
    os.makedirs(dir_salida, exist_ok=True)
    
    # 3. Generar Informe Word base
    print("[*] Generando informe en Word...")
    ruta_word_salida = os.path.join(dir_salida, f"Informe_{grupo_buscado}.docx")
    generar_word_informe(ruta_plantilla_word, contexto, ruta_word_salida)
    
    if ruta_foto and os.path.exists(ruta_foto):
        insertar_foto_unidad_segura(ruta_word_salida, ruta_foto)
        print("[✔] Foto de la unidad procesada e insertada en el informe.")
    
    # 4. Aplicar parche al Checklist de VT multihoja
    print("[*] Procesando y parchando el Checklist VT...")
    ruta_checklist_salida = os.path.join(dir_salida, f"Checklist_VT_{grupo_busczak := grupo_buscado}.xlsx")
    
    if ruta_checklist and os.path.exists(str(ruta_checklist)):
        parchar_checklist_vt(str(ruta_checklist), contexto, ruta_checklist_salida)
        print(f"[✔] Checklist parchado correctamente.")
    else:
        ruta_checklist_orig = "VT-CHECK LIST.xlsx"
        if not os.path.exists(ruta_checklist_orig):
            ruta_checklist_orig = f"assets/VT-CHECK LIST.xlsx"
            
        if os.path.exists(ruta_checklist_orig):
            parchar_checklist_vt(ruta_checklist_orig, contexto, ruta_checklist_salida)
        else:
            import shutil
            if os.path.exists(ruta_maestro):
                shutil.copy(ruta_maestro, ruta_checklist_salida)

    print(f"[✔] ¡Proceso completo finalizado para el grupo {grupo_buscado}!")
