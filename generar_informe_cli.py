#!/usr/bin/env python3
"""
generar_informe_cli.py — genera el informe técnico completo (Word, VT-CHECK
LIST parchado, Anexos y el Informe Compilado al 100% en PDF) desde la línea
de comandos, sin necesitar la interfaz Streamlit -- pensado para que un
colaborador sin acceso a la app (o Claude, en su nombre) pueda generar un
informe real usando exactamente el mismo motor que usa la app web.

Uso típico:
    python3 generar_informe_cli.py \
        --detalle "Detalle_GT-023.xlsx" \
        --fotos fotos/ \
        --checklist "VT-CHECK_LIST_GT-023.xlsx" \
        --psaim "PSAIM_linea1.xlsx" "PSAIM_linea2.xlsx" \
        --pid "PID_GT-023.pdf" \
        --isometricos iso_1.pdf iso_2.pdf \
        --salida salida/

Solo --detalle y --fotos son obligatorios; todo lo demás es opcional, igual
que en la interfaz web (página "Elaboración de Informe").
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
from generar_informe import ejecutar_proceso_grupo

RUTA_PLANTILLA_DEFAULT = DIR_RAIZ / "plantilla_base.docx"
RUTA_MAESTRA_DEFAULT = DIR_RAIZ / "BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx"
RUTA_CATALOGO_DEFAULT = DIR_RAIZ / "Catalogo_Hallazgos_Recomendaciones.xlsx"

_EXT_FOTOS = {".jpg", ".jpeg", ".png"}


def _normaliza(s):
    return "".join(c for c in str(s).upper() if c.isalnum())


def _recolectar_fotos(rutas):
    """Acepta una lista de archivos y/o carpetas; devuelve la lista final de
    fotos (jpg/jpeg/png), en el mismo orden de descubrimiento. La primera
    de la lista es la que se usa como foto de portada de la unidad."""
    fotos = []
    for r in rutas:
        p = Path(r)
        if p.is_dir():
            for hijo in sorted(p.iterdir()):
                if hijo.suffix.lower() in _EXT_FOTOS:
                    fotos.append(hijo)
        elif p.is_file() and p.suffix.lower() in _EXT_FOTOS:
            fotos.append(p)
    return fotos


_RE_ISO_UT_VT = re.compile(r"\b(UT|VT)[\s_-]*0*(\d+)\b", re.IGNORECASE)


def _asignar_isometricos(rutas_iso, lineas_preview):
    """Empareja cada isométrico con su línea, en dos pasos:

    1. Igual que la interfaz web: el TAG (sin espacios ni símbolos) aparece
       dentro del nombre del archivo -- la vía más confiable.
    2. Respaldo por convención de nombre "ISO-UT-N" / "ISO-VT-N" (confirmada
       con el usuario): "UT-N" es el N-ésimo isométrico, EN EL ORDEN del
       Detalle de grupo, entre las líneas con ALCANCE "LINEAS" (medición de
       espesores); "VT-N" es el N-ésimo entre las demás líneas (VT-CIRCUITOS
       / solo visual). Si el número no calza con ninguna posición (p.ej.
       "VT-11" pero solo hay 10 líneas VT), se descarta -- nunca se asigna
       "a ciegas"."""
    tags_detectados = [ln["tag"] for ln in lineas_preview]
    tags_norm = {_normaliza(t): t for t in tags_detectados}

    tags_ut = [
        ln["tag"] for ln in lineas_preview
        if str(ln.get("alcance") or "").strip().upper() == "LINEAS"
    ]
    tags_vt = [
        ln["tag"] for ln in lineas_preview
        if str(ln.get("alcance") or "").strip().upper() != "LINEAS"
    ]

    asignados = {}
    sin_asignar = []
    for ruta in rutas_iso:
        nombre = Path(ruta).name
        nombre_norm = _normaliza(nombre)
        sugerido = next((t for tn, t in tags_norm.items() if tn and tn in nombre_norm), None)

        if not sugerido:
            m = _RE_ISO_UT_VT.search(nombre)
            if m:
                grupo, num = m.group(1).upper(), int(m.group(2))
                lista = tags_ut if grupo == "UT" else tags_vt
                if 1 <= num <= len(lista):
                    sugerido = lista[num - 1]

        if sugerido:
            asignados[sugerido] = str(ruta)
        else:
            sin_asignar.append(str(ruta))
    return asignados, sin_asignar


def _cargar_casos_manual(ruta):
    """Lee el JSON --casos-manual: una lista [{"tag","fila","caso_id"}, ...]
    -- pensada para que un agente de IA (o una persona) elija, para cada
    hallazgo PENDIENTE listado en pendientes.json, cuál caso YA APROBADO
    del catálogo corresponde. El texto final sigue saliendo exacto del
    catálogo -- nunca se redacta nada nuevo, solo se elige el caso."""
    if not ruta:
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _escribir_pendientes_json(hallazgos_por_tag, dir_salida):
    """Si quedó algún hallazgo PENDIENTE (ninguna regla automática calzó ni
    se resolvió con --casos-manual), escribe pendientes.json con los datos
    que hacen falta para construir el --casos-manual de la siguiente
    corrida: tag, fila (identifica la observación exacta dentro de esa
    hoja) y el texto real del hallazgo. Devuelve la ruta, o None si no
    quedó ningún pendiente."""
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
    rutas_fotos,
    dir_salida,
    ruta_checklist=None,
    rutas_psaim=None,
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

    fotos = _recolectar_fotos(rutas_fotos)
    if not fotos:
        raise SystemExit("No se encontró ninguna foto (.jpg/.jpeg/.png) en las rutas indicadas en --fotos.")

    # Se recarga el catálogo desde su Excel en cada corrida, para que una
    # edición reciente del archivo (agregar o corregir un caso) surta
    # efecto sin tener que hacer nada más -- igual que en la app web.
    recomendaciones.recargar_catalogo(str(ruta_catalogo))

    lineas_preview = inventario.cargar_alcance(str(ruta_detalle))
    tags_detectados = [ln["tag"] for ln in lineas_preview]

    rutas_iso_por_tag = {}
    if rutas_isometricos:
        rutas_iso_por_tag, sin_asignar = _asignar_isometricos(rutas_isometricos, lineas_preview)
        for r in sin_asignar:
            print(f"Aviso: no se pudo asignar el isométrico «{r}» a ninguna línea por nombre de "
                  "archivo; se omite del Anexo A/B (nunca se asigna a ciegas).")

    grupo_input = ruta_detalle.stem.replace("(", "").replace(")", "").strip()

    resultado = ejecutar_proceso_grupo(
        grupo_buscado=grupo_input,
        ruta_maestro=ruta_detalle,
        ruta_base_lineas=ruta_base_maestra,
        ruta_plantilla_word=ruta_plantilla,
        dir_salida=str(dir_salida),
        ruta_foto=fotos[0],
        ruta_checklist=ruta_checklist,
        ruta_psaim=rutas_psaim,
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

    psaim_pdf_por_tag = {}
    if resultado.get("psaim_por_tag"):
        psaim_pdf_por_tag = reportes_pdf.generar_pdf_psaim_por_tag(
            resultado["psaim_por_tag"], str(dir_anexos)
        )

    config_anexos = {
        "lineas": resultado["lineas_alcance"],
        "anexos": {
            "pid_pdf": str(ruta_pid) if ruta_pid else None,
            "isometricos": rutas_iso_por_tag,
            "checklists_vt_pdf": checklists_vt_pdf,
            "psaim_pdf": psaim_pdf_por_tag,
        },
    }
    dir_anexos_finales = dir_salida / "anexos_finales"
    anexos_generados, avisos_anexos = anexos.construir_anexos(
        config_anexos, str(dir_anexos_finales)
    )

    codigo_informe = resultado.get("codigo_informe") or grupo_input
    dir_compilado = dir_salida / "informe_compilado"
    ruta_compilado, aviso_compilado = anexos.construir_informe_compilado(
        str(out_word_path), anexos_generados, str(dir_compilado), codigo_informe
    )

    nombre_grupo_real = next(
        (str(ln["grupo"]).strip() for ln in resultado["lineas_alcance"] if ln.get("grupo")),
        grupo_input,
    )
    nombre_grupo_archivo = anexos.nombre_archivo_seguro(nombre_grupo_real)

    out_zip_path = dir_salida / f"Anexos_Comprimidos_{nombre_grupo_archivo}.zip"
    with zipfile.ZipFile(out_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for ruta_anexo in anexos_generados:
            zipf.write(ruta_anexo, arcname=os.path.basename(ruta_anexo))
        for foto in fotos:
            zipf.write(foto, arcname=f"fotos/{foto.name}")

    avisos = list(resultado.get("avisos", [])) + list(avisos_anexos)
    if aviso_compilado:
        avisos.append(aviso_compilado)

    print("\n=== Informe generado con éxito ===")
    print(f"Informe Word:        {out_word_path}")
    if out_excel_path:
        print(f"VT-CHECK LIST:       {out_excel_path}")
    print(f"Anexos (ZIP):        {out_zip_path}")
    if ruta_compilado:
        print(f"Informe Compilado:   {ruta_compilado}")
    else:
        print("Informe Compilado:   NO generado (LibreOffice no está disponible en este equipo; "
              "los demás entregables sí se generaron con normalidad).")

    pendientes = [a for a in avisos if a.startswith("Hoja") and "PENDIENTE" in a]
    otros = [a for a in avisos if a not in pendientes]
    if pendientes:
        print(f"\n⚠️  {len(pendientes)} hallazgo(s) requieren redacción manual del especialista "
              "(ninguna regla automática calzó con confianza; el hallazgo de campo se conservó "
              "intacto en el checklist):")
        for a in pendientes:
            print(f"  - {a}")
    if otros:
        print(f"\n{len(otros)} aviso(s) técnico(s):")
        for a in otros:
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
    ap.add_argument("--detalle", required=True, help="Excel de Detalle de grupo/líneas (obligatorio)")
    ap.add_argument("--fotos", required=True, nargs="+",
                     help="Fotos de la unidad: uno o más archivos y/o carpetas (obligatorio)")
    ap.add_argument("--checklist", help="Excel VT-CHECK LIST (opcional)")
    ap.add_argument("--psaim", nargs="*", default=[],
                     help="Excel(es) PSAIM (opcional) -- en la práctica real suele ser uno por "
                          "línea con medición de espesores, no todo el grupo; se puede pasar más "
                          "de uno")
    ap.add_argument("--pid", help="PDF de P&ID del grupo (opcional)")
    ap.add_argument("--isometricos", nargs="*", default=[],
                     help="PDF(s) de isométricos por línea (opcional)")
    ap.add_argument("--salida", default="salida_informes", help="Carpeta de salida")
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
        rutas_fotos=args.fotos,
        dir_salida=args.salida,
        ruta_checklist=args.checklist,
        rutas_psaim=args.psaim,
        ruta_pid=args.pid,
        rutas_isometricos=args.isometricos,
        ruta_base_maestra=args.base_maestra,
        ruta_plantilla=args.plantilla,
        ruta_catalogo=args.catalogo,
        ruta_casos_manual=args.casos_manual,
    )


if __name__ == "__main__":
    main()
