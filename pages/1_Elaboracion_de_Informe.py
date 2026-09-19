import os
import pandas as pd
from informe import generar_word_informe
from checklist import parchar_checklist_vt

def ejecutar_proceso_grupo(grupo_buscado, ruta_maestro, ruta_base_lineas, ruta_plantilla_word, dir_salida="salida_informes"):
    print(f"[*] Iniciando procesamiento automático para el grupo: {grupo_buscado}")
    
    # 1. Leer el archivo maestro/detalle subido para extraer los Tags de Línea (LÍNEAS) del grupo
    df_maestro = pd.read_excel(ruta_maestro)
    
    # Detectar dinámicamente la columna que contiene los tags o líneas
    col_lineas = next((c for c in df_maestro.columns if "linea" in c.lower() or "tag" in c.lower()), df_maestro.columns[0])
    lista_tags_lineas = df_maestro[col_lineas].dropna().astype(str).str.strip().tolist()
    
    print(f"[*] Tags de línea detectados para el grupo {grupo_buscado}: {lista_tags_lineas}")
    
    # 2. Leer la Base de Datos de Líneas (FASE 1)
    df_base_lineas = pd.read_excel(ruta_base_lineas)
    
    # Detectar dinámicamente la columna de tag/línea en la Base FASE 1
    col_base_tag = next((c for c in df_base_lineas.columns if "linea" in c.lower() or "tag" in c.lower()), df_base_lineas.columns[0])
    
    # Filtrar los parámetros técnicos basándose estrictamente en los tags de las líneas del grupo
    df_filtrado_tecnico = df_base_lineas[df_base_lineas[col_base_tag].astype(str).str.strip().isin(lista_tags_lineas)]
    
    if df_filtrado_tecnico.empty:
        print(f"[!] Advertencia: No se encontraron coincidencias directas en la Base FASE 1 para los tags: {lista_tags_lineas}")
        datos_tecnicos = {}
    else:
        # Extraer los datos técnicos de las líneas encontradas
        datos_tecnicos = df_filtrado_tecnico.iloc[0].to_dict()
    
    # Consolidar los metadatos generales
    datos_maestro = {
        "GRUPO DE TUBERÍAS": grupo_buscado,
        "LINEAS": ", ".join(lista_tags_lineas)
    }
    
    # Contexto unificado que se enviará al informe y al checklist
    contexto = {**datos_maestro, **datos_tecnicos}
    
    # Crear la carpeta de salida si no existe
    os.makedirs(dir_salida, exist_ok=True)
    
    # 3. Generar el Informe en Word
    print("[*] Generando informe en Word...")
    ruta_word_salida = os.path.join(dir_salida, f"Informe_{grupo_buscado}.docx")
    generar_word_informe(ruta_plantilla_word, contexto, ruta_word_salida)
    
    # 4. Aplicar el parche en el Checklist de VT (multihoja y validando fotos)
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
