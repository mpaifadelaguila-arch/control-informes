import os
import pandas as pd
from docx import Document
from informe import generar_word_informe
from checklist import parchar_checklist_vt

def insertar_foto_unidad_segura(ruta_word, ruta_foto):
    """Inserta o reemplaza la foto de la unidad en el documento Word de forma segura."""
    try:
        doc = Document(ruta_word)
        # Buscamos si hay alguna tabla o marcador, o insertamos la imagen al final o en un párrafo clave
        # Como alternativa robusta, buscamos marcadores de texto o añadimos la imagen en una sección visual
        for para in doc.paragraphs:
            if "FOTO" in para.text.upper() or "IMAGEN" in para.text.upper():
                para.text = "" # Limpiar marcador
                run = para.add_run()
                run.add_picture(str(ruta_foto), width=Inches(4.5))
                doc.save(ruta_word)
                return
        
        # Si no hay marcador explícito, la agregamos al final del documento de manera elegante
        doc.add_paragraph("Fotografía de la Unidad / Grupo:")
        doc.add_picture(str(ruta_foto), width=Inches(5.0))
        doc.save(ruta_word)
    except Exception as e:
        print(f"[!] Aviso al insertar la foto: {e}")

def ejecutar_proceso_grupo(grupo_buscado, ruta_maestro, ruta_base_lineas, ruta_plantilla_word, dir_salida="salida_informes", ruta_foto=None):
    print(f"[*] Iniciando procesamiento automático para el grupo: {grupo_buscado}")
    
    # 1. Leer el archivo de detalle del grupo cargado para extraer los Tags de Línea (LÍNEAS)
    df_maestro = pd.read_excel(ruta_maestro)
    col_lineas = next((c for c in df_maestro.columns if "linea" in c.lower() or "tag" in c.lower()), df_maestro.columns[0])
    lista_tags_lineas = df_maestro[col_lineas].dropna().astype(str).str.strip().tolist()
    
    print(f"[*] Tags de línea detectados: {lista_tags_lineas}")
    
    # 2. Leer la Base de Datos FASE 1 para extraer los parámetros técnicos por Tag
    df_base_lineas = pd.read_excel(ruta_base_lineas)
    col_base_tag = next((c for c in df_base_lineas.columns if "linea" in c.lower() or "tag" in c.lower()), df_base_lineas.columns[0])
    
    df_filtrado_tecnico = df_base_lineas[df_base_lineas[col_base_tag].astype(str).str.strip().isin(lista_tags_lineas)]
    
    datos_tecnicos = df_filtrado_tecnico.iloc[0].to_dict() if not df_filtrado_tecnico.empty else {}
    
    datos_maestro = {
        "GRUPO DE TUBERÍAS": grupo_buscado,
        "LINEAS": ", ".join(lista_tags_lineas)
    }
    
    contexto = {**datos_maestro, **datos_tecnicos}
    os.makedirs(dir_salida, exist_ok=True)
    
    # 3. Generar Informe Word base
    print("[*] Generando informe en Word...")
    ruta_word_salida = os.path.join(dir_salida, f"Informe_{grupo_buscado}.docx")
    generar_word_informe(ruta_plantilla_word, contexto, ruta_word_salida)
    
    # Remplazar/Insertar la foto de la unidad en el Word si se proporcionó
    if ruta_foto and os.path.exists(ruta_foto):
        from docx.shared import Inches
        insertar_foto_unidad_segura(ruta_word_salida, ruta_foto)
        print("[✔] Foto de la unidad procesada e insertada en el informe.")
    
    # 4. Aplicar parche al Checklist de VT multihoja
    print("[*] Procesando y parchando el Checklist VT...")
    ruta_checklist_orig = f"(VT)-{grupo_buscado}.xlsx"
    if not os.path.exists(ruta_checklist_orig):
        ruta_checklist_orig = f"assets/checklist_{grupo_buscado}.xlsx"
        
    ruta_checklist_salida = os.path.join(dir_salida, f"Checklist_VT_{grupo_buscado}.xlsx")
    
    if os.path.exists(ruta_checklist_orig):
        parchar_checklist_vt(ruta_checklist_orig, contexto, ruta_checklist_salida)
    else:
        import shutil
        if os.path.exists(ruta_maestro):
            shutil.copy(ruta_maestro, ruta_checklist_salida)

    print(f"[✔] ¡Proceso completo finalizado para el grupo {grupo_buscado}!")
