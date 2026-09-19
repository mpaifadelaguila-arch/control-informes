import os
import pandas as pd
from informe import generar_word_informe
from checklist import parchar_checklist_vt

def ejecutar_proceso_grupo(grupo_buscado, ruta_detalle_grupo, ruta_base_lineas, ruta_plantilla_word, dir_salida="salida_informes"):
    print(f"[*] Iniciando procesamiento para el grupo: {grupo_buscado}")
    
    # 1. Leer el archivo de detalle del grupo subido por el usuario para extraer los Tag de Línea (LÍNEAS)
    df_detalle = pd.read_excel(ruta_detalle_grupo)
    
    # Detectar la columna de líneas o tags dinámicamente
    col_lineas = next((c for c in df_detalle.columns if "linea" in c.lower() or "tag" in c.lower()), df_detalle.columns[0])
    lista_tags_lineas = df_detalle[col_lineas].dropna().astype(str).str.strip().tolist()
    
    print(f"[*] Tags de línea encontrados para el grupo {grupo_buscado}: {lista_tags_lineas}")
    
    # 2. Leer la Base de Datos de Líneas (FASE 1)
    df_base_lineas = pd.read_excel(ruta_base_lineas)
    
    # Detectar la columna de tag/línea en la base FASE 1
    col_base_tag = next((c for c in df_base_lineas.columns if "linea" in c.lower() or "tag" in c.lower()), df_base_lineas.columns[0])
    
    # Filtrar los registros de la base FASE 1 que coincidan con los tags de las líneas del grupo
    df_filtrado_tecnico = df_base_lineas[df_base_lineas[col_base_tag].astype(str).str.strip().isin(lista_tags_lineas)]
    
    if df_filtrado_tecnico.empty:
        print(f"[!] Advertencia: No se encontraron coincidencias directas en la Base FASE 1 para los tags: {lista_tags_lineas}")
        datos_tecnicos = {}
    else:
        # Extraemos los datos técnicos consolidados de las líneas del grupo
        datos_tecnicos = df_filtrado_tecnico.iloc[0].to_dict()
    
    # Metadatos generales del grupo
    datos_maestro = {
        "GRUPO DE TUBERÍAS": grupo_buscado,
        "LINEAS": ", ".join(lista_tags_lineas)
    }
    
    # Contexto unificado para el informe
    contexto = {**datos_maestro, **datos_tecnicos}
    
    os.makedirs(dir_salida, exist_ok=True)
    
    # 3. Generar el Informe en Word
    print("[*] Generando informe en Word con los datos por Tag de Línea...")
    ruta_word_salida = os.path.join(dir_salida, f"Informe_{grupo_buscado}.docx")
    generar_word_informe(ruta_plantilla_word, contexto, ruta_word_salida)
    
    # 4. Aplicar parche al Checklist de VT multihoja (validando fotos)
    print("[*] Procesando y parchando el Checklist VT...")
    ruta_checklist_orig = f"(VT)-{grupo_buscado}.xlsx"
    if not os.path.exists(ruta_checklist_orig):
        ruta_checklist_orig = f"assets/checklist_{grupo_buscado}.xlsx"
        
    ruta_checklist_salida = os.path.join(dir_salida, f"Checklist_VT_{grupo_buscado}.xlsx")
    
    if os.path.exists(ruta_checklist_orig):
        parchar_checklist_vt(ruta_checklist_orig, contexto, ruta_checklist_salida)
    else:
        print(f"[!] Advertencia: No se encontró el checklist original para {grupo_buscado}")

    print(f"[✔] ¡Proceso completo finalizado para el grupo {grupo_buscado}!")
