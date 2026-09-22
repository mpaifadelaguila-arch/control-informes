#!/usr/bin/env python3
"""
generar_informe_complementario_cli.py — genera el Informe Complementario /
Anexo Adicional (para líneas de un grupo ya cerrado que se inspeccionan
tiempo después: solo inspección visual VT, sin PSAIM) desde la línea de
comandos, sin necesitar la interfaz Streamlit -- mismo motor que usa la
página "Informe Complementario" de la app web.

Uso típico:
    python3 generar_informe_complementario_cli.py \
        --detalle "Detalle_GT-023_complementario.xlsx" \
        --sumario "Como resultado de la aplicación de las técnicas de inspección..." \
        --codigo-principal "ADEMINSAC-FIAB-RLP-1820-2025" \
        --checklist "VT-CHECK_LIST.xlsx" \
        --fotos fotos/ \
        --pid "PID.pdf" \
        --isometricos iso_1.pdf iso_2.pdf \
        --salida salida/

Solo --detalle y --sumario son obligatorios (igual que en la página web:
Detalle de líneas + Sumario de Inspección). El detalle debe traer la
columna "N° ORIGINAL" para conservar la numeración del informe principal.
"""
import argparse
import json
import os
import re
import sys
import zipfile
from pathlib import Path

DIR_RAIZ = Path(__file__).resolve().parent
if str(DIR_RAIZ) not in sys.path:
    sys.path.insert(0, str(DIR_RAIZ))

import anexos
import checklist as checklist_mod
import inventario
import recomendaciones
import reportes_pdf
from generar_informe import ejecutar_proceso_grupo_complementario

RUTA_PLANTILLA_DEFAULT = DIR_RAIZ / "plantilla_complementario.docx"
RUTA_MAESTRA_DEFAULT = DIR_RAIZ / "BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx"
RUTA_CATALOGO_DEFAULT = DIR_RAIZ / "Catalogo_Hallazgos_Recomendaciones.xlsx"

_EXT_FOTOS = {".jpg", ".jpeg", ".png"}


def _normaliza(s):
    return "".join(c for c in str(s).upper() if c.isalnum())


def _recolectar_fotos(rutas):
    fotos = []
    for r in rutas or []:
        p = Path(r)
        if p.is_dir():
            for hijo in sorted(p.iterdir()):
                if hijo.suffix.lower() in _EXT_FOTOS:
                    fotos.append(hijo)
        elif p.is_file() and p.suffix.lower() in _EXT_FOTOS:
            fotos.append(p)
    return fotos


_RE_ISO_VT = re.compile(r"\bVT[\s_-]*0*(\d+)\b", re.IGNORECASE)


def _asignar_isometricos(rutas_iso, tags_detectados):
    """Igual que en generar_informe_cli.py: primero por TAG dentro del
    nombre del archivo; si no calza, respaldo por convención "ISO-VT-N" =
    la N-ésima línea del Detalle, en su mismo orden (un informe
    complementario es siempre solo inspección visual, así que aquí no
    aplica la distinción UT/VT del informe principal)."""
    tags_norm = {_normaliza(t): t for t in tags_detectados}
    asignados = {}
    sin_asignar = []
    for ruta in rutas_iso:
        nombre = Path(ruta).name
        nombre_norm = _normaliza(nombre)
        sugerido = next((t for tn, t in tags_norm.items() if tn and tn in nombre_norm), None)
        if not sugerido:
            m = _RE_ISO_VT.search(nombre)
            if m:
                num = int(m.group(1))
                if 1 <= num <= len(tags_detectados):
                    sugerido = tags_detectados[num - 1]
        if sugerido:
            asignados[sugerido] = str(ruta)
        else:
            sin_asignar.append(str(ruta))
    return asignados, sin_asignar


def _cargar_casos_manual(ruta):
    if not ruta:
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _escribir_pendientes_json(hallazgos_por_tag, dir_salida):
    pendientes = [
        {
            "tag": tag,
            "fila": info["fila_ultimo_hallazgo"],
            "item": info["item"],
            "categoria": info["categoria"],
            "hallazgo": info["hallazgo"],
        }
        for tag, items in (hallazgos_por_tag or {}).items()
        for info in items
        if info.get("recomendacion") == checklist_mod.TEXTO_PENDIENTE_MANUAL
    ]
    if not pendientes:
        return None
    ruta_pendientes = Path(dir_salida) / "pendientes.json"
    with open(ruta_pendientes, "w", encoding="utf-8") as f:
        json.dump(pendientes, f, ensure_ascii=False, indent=2)
    return ruta_pendientes


def generar(
    ruta_detalle,
    sumario_texto,
    dir_salida,
    codigo_informe_principal=None,
    ruta_checklist=None,
    rutas_fotos=None,
    ruta_pid=None,
    rutas_isometricos=None,
    ruta_base_maestra=RUTA_MAESTRA_DEFAULT,
    ruta_plantilla=RUTA_PLANTILLA_DEFAULT,
    ruta_catalogo=RUTA_CATALOGO_DEFAULT,
    ruta_casos_manual=None,
):
    ruta_detalle = Path(ruta_detalle)
    dir_salida = Path(dir_salida)
    dir_salida.mkdir(parents=True, exist_ok=True)

    if not sumario_texto or not sumario_texto.strip():
        raise SystemExit("Falta el texto del Sumario de Inspección (--sumario).")

    recomendaciones.recargar_catalogo(str(ruta_catalogo))

    lineas_preview = inventario.cargar_alcance(str(ruta_detalle))
    tags_detectados = [ln["tag"] for ln in lineas_preview]
    if not any(ln.get("numero_original") for ln in lineas_preview):
        print(
            "Aviso: el detalle de líneas no trae la columna \"N° ORIGINAL\" (o está vacía): "
            "la tabla N°/SAP/Línea del informe quedará numerada 1, 2, 3... en vez de "
            "conservar el N° del informe principal."
        )

    fotos = _recolectar_fotos(rutas_fotos)

    rutas_iso_por_tag = {}
    if rutas_isometricos:
        rutas_iso_por_tag, sin_asignar = _asignar_isometricos(rutas_isometricos, tags_detectados)
        for r in sin_asignar:
            print(f"Aviso: no se pudo asignar el isométrico «{r}» a ninguna línea por nombre de "
                  "archivo; se omite del Anexo A/B.")

    grupo_input = ruta_detalle.stem.replace("(", "").replace(")", "").strip()

    resultado = ejecutar_proceso_grupo_complementario(
        grupo_buscado=grupo_input,
        ruta_maestro=ruta_detalle,
        ruta_base_lineas=ruta_base_maestra,
        ruta_plantilla_word=ruta_plantilla,
        dir_salida=str(dir_salida),
        ruta_foto=fotos[0] if fotos else None,
        ruta_checklist=ruta_checklist,
        codigo_informe_principal=codigo_informe_principal,
        sumario_texto=sumario_texto,
        casos_manual=_cargar_casos_manual(ruta_casos_manual),
    )

    out_word_path = Path(resultado["ruta_word"])
    out_excel_path = Path(resultado["ruta_checklist"]) if resultado["ruta_checklist"] else None
    if not out_word_path.exists():
        raise SystemExit("El motor backend no generó el archivo Word en el directorio de salida.")

    dir_anexos = dir_salida / "anexos_pdf"
    dir_anexos.mkdir(exist_ok=True)

    checklists_vt_pdf = {}
    if out_excel_path and out_excel_path.exists():
        checklists_vt_pdf = reportes_pdf.generar_pdf_checklist_vt_por_tag(
            str(out_excel_path), str(dir_anexos)
        )

    config_anexos = {
        "lineas": resultado["lineas_alcance"],
        "anexos": {
            "pid_pdf": str(ruta_pid) if ruta_pid else None,
            "isometricos": rutas_iso_por_tag,
            "checklists_vt_pdf": checklists_vt_pdf,
        },
    }
    dir_anexos_finales = dir_salida / "anexos_finales"
    # incluir_anexo_c=False: un informe complementario nunca lleva Anexo C
    # (Ultrasonido/PSAIM) -- es siempre solo inspección visual.
    anexos_generados, avisos_anexos = anexos.construir_anexos(
        config_anexos, str(dir_anexos_finales), incluir_anexo_c=False
    )

    codigo_informe = resultado.get("codigo_informe") or grupo_input
    dir_compilado = dir_salida / "informe_compilado"
    ruta_compilado, aviso_compilado = anexos.construir_informe_compilado(
        str(out_word_path), anexos_generados, str(dir_compilado), codigo_informe
    )

    nombre_archivo = anexos.nombre_archivo_seguro(codigo_informe)
    out_zip_path = dir_salida / f"Anexos_Complementario_{nombre_archivo}.zip"
    with zipfile.ZipFile(out_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for ruta_anexo in anexos_generados:
            zipf.write(ruta_anexo, arcname=os.path.basename(ruta_anexo))
        for foto in fotos:
            zipf.write(foto, arcname=f"fotos/{foto.name}")

    avisos = list(resultado.get("avisos", [])) + list(avisos_anexos)
    if aviso_compilado:
        avisos.append(aviso_compilado)

    print("\n=== Informe Complementario generado con éxito ===")
    print(f"Código de informe:   {codigo_informe}")
    print(f"Informe Word:        {out_word_path}")
    if out_excel_path:
        print(f"VT-CHECK LIST:       {out_excel_path}")
    print(f"Anexos (ZIP):        {out_zip_path}")
    if ruta_compilado:
        print(f"Informe Compilado:   {ruta_compilado}")
    else:
        print("Informe Compilado:   NO generado (LibreOffice no está disponible en este equipo; "
              "los demás entregables sí se generaron con normalidad).")

    if avisos:
        print(f"\n{len(avisos)} aviso(s):")
        for a in avisos:
            print(f"  - {a}")

    ruta_pendientes = _escribir_pendientes_json(resultado.get("hallazgos_por_tag"), dir_salida)
    if ruta_pendientes:
        print(
            f"\n📋 Se escribió {ruta_pendientes} con el detalle de cada hallazgo PENDIENTE "
            "(tag, fila, ítem, categoría y el texto real del inspector). Para resolverlos: "
            "lee cada uno junto con Catalogo_Hallazgos_Recomendaciones.xlsx, elige el caso_id "
            "del catálogo que corresponda a cada hallazgo (NUNCA redactes un hallazgo o "
            "recomendación nuevos -- el texto final sale siempre del catálogo), arma un JSON "
            '[{"tag": "...", "fila": N, "caso_id": "..."}, ...] y vuelve a generar el informe '
            "agregando --casos-manual ese_archivo.json."
        )

    return {
        "codigo_informe": codigo_informe,
        "word": str(out_word_path),
        "excel": str(out_excel_path) if out_excel_path else None,
        "anexos_zip": str(out_zip_path),
        "compilado": str(ruta_compilado) if ruta_compilado else None,
        "pendientes_json": str(ruta_pendientes) if ruta_pendientes else None,
        "avisos": avisos,
    }


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--detalle", required=True,
                     help="Excel de Detalle de líneas, con columna N° ORIGINAL (obligatorio)")
    ap.add_argument("--sumario", required=True,
                     help="Texto del Sumario de Inspección, sección 1.0 (obligatorio)")
    ap.add_argument("--codigo-principal", default=None,
                     help='Código del informe principal ya cerrado, ej: "ADEMINSAC-FIAB-RLP-1820-2025"')
    ap.add_argument("--checklist", help="Excel VT-CHECK LIST (opcional)")
    ap.add_argument("--fotos", nargs="*", default=[],
                     help="Fotos de la unidad: archivos y/o carpetas (opcional)")
    ap.add_argument("--pid", help="PDF de P&ID del grupo (opcional)")
    ap.add_argument("--isometricos", nargs="*", default=[],
                     help="PDF(s) de isométricos por línea (opcional)")
    ap.add_argument("--salida", default="salida_informe_complementario", help="Carpeta de salida")
    ap.add_argument("--base-maestra", default=str(RUTA_MAESTRA_DEFAULT))
    ap.add_argument("--plantilla", default=str(RUTA_PLANTILLA_DEFAULT))
    ap.add_argument("--catalogo", default=str(RUTA_CATALOGO_DEFAULT))
    ap.add_argument(
        "--casos-manual",
        help="JSON [{\"tag\",\"fila\",\"caso_id\"}, ...] con el caso del catálogo elegido "
             "explícitamente (por una persona o por un agente de IA) para los hallazgos que "
             "quedaron PENDIENTE en una corrida anterior -- ver pendientes.json en --salida.",
    )
    args = ap.parse_args()

    generar(
        ruta_detalle=args.detalle,
        sumario_texto=args.sumario,
        dir_salida=args.salida,
        codigo_informe_principal=args.codigo_principal,
        ruta_checklist=args.checklist,
        rutas_fotos=args.fotos,
        ruta_pid=args.pid,
        rutas_isometricos=args.isometricos,
        ruta_base_maestra=args.base_maestra,
        ruta_plantilla=args.plantilla,
        ruta_casos_manual=args.casos_manual,
        ruta_catalogo=args.catalogo,
    )


if __name__ == "__main__":
    main()
