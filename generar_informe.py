import os
import pandas as pd
from informe import generar_word_informe
from checklist import parchar_checklist_vt

def ejecutar_proceso_grupo(grupo_buscado, ruta_maestro, ruta_base_lineas, ruta_plantilla_word, dir_salida="salida_informes"):
    print(f"[*] Iniciando procesamiento automático para el grupo: {grupo_buscado}")
    
    # 1. Leer Excel Maestro para extraer los datos de gestión (Código, SAP, Unidad, Responsable)
    df_maestro = pd.read_excel(ruta_maestro)
    fila_maestro = df_maestro[df_maestro["GRUPO DE TUBERÍAS"].astype(str).str.strip() == grupo_buscado]
    
    if fila_maestro.empty:
        raise ValueError(f"No se encontró el grupo {grupo_buscado} en el Excel Maestro.")
    
    datos_maestro = fila_maestro.iloc[0].to_dict()
    
    # 2. Leer la Base de Datos de Líneas (Fase 1) para extraer los parámetros técnicos
    df_lineas = pd.read_excel(ruta_base_lineas)
    fila_lineas = df_lineas[df_lineas["GRUPO DE TUBERÍAS"].astype(str).str.strip() == grupo_buscado]
    
    datos_tecnicos = fila_lineas.iloc[0].to_dict() if not fila_lineas.empty else {}
    
    # Fusionar toda la información en un solo diccionario de contexto
    contexto = {**datos_maestro, **datos_tecnicos}
    
    # Crear la carpeta de salida si no existe
    os.makedirs(dir_salida, exist_ok=True)
    
    # 3. Generar el Informe en Word
    print("[*] Generando informe en Word...")
    ruta_word_salida = os.path.join(dir_salida, f"Informe_{grupo_buscado}.docx")
    generar_word_informe(ruta_plantilla_word, contexto, ruta_word_salida)
    
    # 4. Aplicar el parche en el Checklist de VT (multihoja y validando fotos)
    print("[*] Procesando y parchando el Checklist VT...")
    ruta_checklist_orig = f"assets/checklist_{grupo_buscado}.xlsx" # O el nombre correspondiente
    ruta_checklist_salida = os.path.join(dir_salida, f"Checklist_VT_{grupo_buscado}.xlsx")
    
    if os.path.exists(ruta_checklist_orig):
        # Aquí se pasan las recomendaciones o el contexto según la lógica que definimos
        parchar_checklist_vt(ruta_checklist_orig, contexto, ruta_checklist_salida)
    else:
        print(f"[!] Advertencia: No se encontró el checklist original en {ruta_checklist_orig}")

    print(f"[✔] ¡Proceso completo finalizado para el grupo {grupo_buscado}!")

if __name__ == "__main__":
    # Prueba directa ejecutando un grupo de ejemplo
    GRUPO_OBJETIVO = "22-GLP-GT-023"
    ejecutar_proceso_grupo(
        grupo_buscado=GRUPO_OBJETIVO,
        ruta_maestro="assets/inventario_maestro.xlsx",
        ruta_base_lineas="assets/BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx",
        ruta_plantilla_word="assets/plantilla_base.docx"
    )
