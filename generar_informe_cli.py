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
        --psaim "PSAIM_GT-023.xlsx" \
        --pid "PID_GT-023.pdf" \
        --isometricos iso_1.pdf iso_2.pdf \
        --salida salida/

Solo --detalle y --fotos son obligatorios; todo lo demás es opcional, igual
que en la interfaz web (página "Elaboración de Informe").
"""
import argparse
import os
import sys
import zipfile
from pathlib import Path

DIR_RAIZ = Path(__file__).resolve().parent
if str(DIR_RAIZ) not in sys.path:
    sys.path.insert(0, str(DIR_RAIZ))

import anexos
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


def _asignar_isometricos(rutas_iso, tags_detectados):
    """Misma lógica de sugerencia automática que la interfaz web: empareja
    cada isométrico con la línea cuyo TAG (sin espacios ni símbolos)
    aparece dentro del nombre del archivo. El que no calza con ninguna
    línea se descarta (igual que dejarlo en '-- Sin asignar --' en la
    interfaz) -- nunca se asigna "a ciegas"."""
    tags_norm = {_normaliza(t): t for t in tags_detectados}
    asignados = {}
    sin_asignar = []
    for ruta in rutas_iso:
        nombre_norm = _normaliza(Path(ruta).name)
        sugerido = next((t for tn, t in tags_norm.items() if tn and tn in nombre_norm), None)
        if sugerido:
            asignados[sugerido] = str(ruta)
        else:
            sin_asignar.append(str(ruta))
    return asignados, sin_asignar


def generar(
    ruta_detalle,
    rutas_fotos,
    dir_salida,
    ruta_checklist=None,
    ruta_psaim=None,
    ruta_pid=None,
    rutas_isometricos=None,
    ruta_base_maestra=RUTA_MAESTRA_DEFAULT,
    ruta_plantilla=RUTA_PLANTILLA_DEFAULT,
    ruta_catalogo=RUTA_CATALOGO_DEFAULT,
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
        rutas_iso_por_tag, sin_asignar = _asignar_isometricos(rutas_isometricos, tags_detectados)
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
        ruta_psaim=ruta_psaim,
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
        inv = inventario.cargar_inventario(str(ruta_base_maestra))
        inv_norm = {k.strip().upper(): v for k, v in inv.items()}
        filas_tecnicas = []
        for ln in resultado["lineas_alcance"]:
            tag = ln["tag"]
            datos, _ = inventario.cruzar_linea(tag, inv_norm.get(tag.strip().upper()))
            filas_tecnicas.append({"tag": tag, **datos})
        psaim_pdf_por_tag = reportes_pdf.generar_pdf_psaim_por_tag(
            resultado["psaim_por_tag"], filas_tecnicas, str(dir_anexos)
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

    return {
        "word": str(out_word_path),
        "excel": str(out_excel_path) if out_excel_path else None,
        "anexos_zip": str(out_zip_path),
        "compilado": str(ruta_compilado) if ruta_compilado else None,
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
    ap.add_argument("--psaim", help="Excel PSAIM (opcional)")
    ap.add_argument("--pid", help="PDF de P&ID del grupo (opcional)")
    ap.add_argument("--isometricos", nargs="*", default=[],
                     help="PDF(s) de isométricos por línea (opcional)")
    ap.add_argument("--salida", default="salida_informes", help="Carpeta de salida")
    ap.add_argument("--base-maestra", default=str(RUTA_MAESTRA_DEFAULT))
    ap.add_argument("--plantilla", default=str(RUTA_PLANTILLA_DEFAULT))
    ap.add_argument("--catalogo", default=str(RUTA_CATALOGO_DEFAULT))
    args = ap.parse_args()

    generar(
        ruta_detalle=args.detalle,
        rutas_fotos=args.fotos,
        dir_salida=args.salida,
        ruta_checklist=args.checklist,
        ruta_psaim=args.psaim,
        ruta_pid=args.pid,
        rutas_isometricos=args.isometricos,
        ruta_base_maestra=args.base_maestra,
        ruta_plantilla=args.plantilla,
        ruta_catalogo=args.catalogo,
    )


if __name__ == "__main__":
    main()
