#!/usr/bin/env python3
"""
generar_informe.py — CLI orquestador del pipeline de un grupo de tuberías
(informe Word, checklist VT patcheado, anexos). Uso:

    python3 generar_informe.py config_GT-0XX.json

Ver config_ejemplo.json para el formato esperado. Corre los 3 pasos
(informe, checklist, anexos) de forma independiente entre sí — si uno
falla o falta un insumo, los otros igual se intentan (regla de la sección
11.7: nunca detener todo el pipeline por un insumo faltante).

Insumos mínimos para poder correr algo: el archivo de alcance ("Listado de
líneas") y la base de datos técnica maestra. Todo lo demás (PSAIM,
checklist lleno, anexos, hallazgos/recomendaciones) es opcional y se
reemplaza por "PENDIENTE" donde falte — ver
`claude/checklist-insumos-por-grupo.md` en el Proyecto de Claude para la
lista completa de insumos por grupo.
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inventario
import psaim as psaim_mod
import informe as informe_mod
import checklist as checklist_mod
import anexos as anexos_mod


def cargar_lineas_resueltas(config):
    """A partir del config crudo, arma la lista `lineas` completamente
    resuelta (cruce técnico + PSAIM + hallazgos/recomendaciones, si están
    disponibles) que consume informe.patch_informe()."""
    avisos = []

    alcance_path = config.get("alcance_xlsx")
    if alcance_path:
        alcance = inventario.cargar_alcance(alcance_path)
    else:
        alcance = config["lineas_manual"]  # lista ya armada a mano

    inv = inventario.cargar_inventario(config["inventario_xlsx"])

    hallazgos_path = config.get("hallazgos_recomendaciones_json")
    hallazgos = {}
    if hallazgos_path and os.path.exists(hallazgos_path):
        with open(hallazgos_path, encoding="utf-8") as f:
            hallazgos = json.load(f)

    psaim_paths = config.get("psaim_por_tag", {})

    lineas = []
    for ln in alcance:
        tag = ln["tag"]
        row = inv.get(tag)
        cruce, avisos_cruce = inventario.cruzar_linea(tag, row)
        avisos.extend(f"[{tag}] {a}" for a in avisos_cruce)
        cruce_ok = row is not None

        psaim_data = None
        if str(ln.get("alcance", "")).upper() == "LINEAS":
            psaim_path = psaim_paths.get(tag)
            if psaim_path and os.path.exists(psaim_path):
                try:
                    pd_ = psaim_mod.leer_psaim(psaim_path)
                    rate = psaim_mod.rate_corrosion_mm_anio(pd_["rcr_mpy"])
                    vida = psaim_mod.vida_util_display(
                        pd_["vida_util_anios"], cruce.get("clase") if cruce_ok else None)
                    psaim_data = {"rate": rate, "vida_display": vida}
                except psaim_mod.PSAIMFaltaDetalle as e:
                    avisos.append(f"[{tag}] {e}")
            else:
                avisos.append(f"[{tag}] Línea con Alcance=LINEAS pero sin PSAIM "
                               "todavía — queda como PENDIENTE.")

        hallazgo_info = hallazgos.get(tag, {})

        lineas.append({
            "item": ln.get("item"), "tag": tag, "sap": str(ln.get("sap", "")),
            "alcance": ln.get("alcance"), "fecha_inspeccion": ln.get("fecha_inspeccion"),
            "clase": cruce.get("clase") if cruce_ok else None,
            "cruce": cruce if cruce_ok else None,
            "psaim": psaim_data,
            "hallazgo": hallazgo_info.get("hallazgo"),
            "recomendacion": hallazgo_info.get("recomendacion"),
        })

    elaborador = config.get("elaborador")
    if config.get("fecha_ini") and config.get("fecha_fin"):
        fecha_ini, fecha_fin = config["fecha_ini"], config["fecha_fin"]
        examinadores = config.get("examinadores", [])
    else:
        fecha_ini, fecha_fin, examinadores = inventario.derivar_fecha_y_examinadores(
            alcance, elaborador=elaborador)

    return lineas, fecha_ini, fecha_fin, examinadores, avisos


def run(config_path):
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    salida_dir = config.get("salida_dir", os.path.dirname(os.path.abspath(config_path)))
    os.makedirs(salida_dir, exist_ok=True)
    resumen_avisos = []

    lineas, fecha_ini, fecha_fin, examinadores, avisos_cruce = cargar_lineas_resueltas(config)
    resumen_avisos.extend(avisos_cruce)

    informe_config = {
        "grupo": config["grupo"],
        "unidad": config["unidad"],
        "codigo_informe": config["codigo_informe"],
        "fecha_ini": fecha_ini,
        "fecha_fin": fecha_fin,
        "examinadores": examinadores,
        "lineas": lineas,
        "mecanismos_dano": config.get("mecanismos_dano", []),
        "foto_portada": config.get("foto_portada"),
    }

    # --- Paso 1: informe .docx -------------------------------------------
    try:
        out_docx = os.path.join(salida_dir, config.get(
            "nombre_salida_docx", f"Informe_{config['grupo']}.docx"))
        avisos = informe_mod.patch_informe(
            informe_config, config["plantilla_docx"], out_docx)
        resumen_avisos.extend(avisos)
        print(f"[OK] Informe generado: {out_docx}")
    except Exception:
        print("[ERROR] Falló la generación del informe .docx:")
        traceback.print_exc()
        resumen_avisos.append("El paso de informe .docx falló por completo — ver traceback arriba.")

    # --- Paso 2: checklist VT patcheado (Comentario <- Recomendación) ----
    checklist_path = config.get("checklist_xlsx")
    if checklist_path and os.path.exists(checklist_path):
        try:
            out_checklist = os.path.join(
                salida_dir, config.get("nombre_salida_checklist",
                                        os.path.basename(checklist_path)))
            parsed = checklist_mod.parse_checklist(checklist_path)
            updates_por_hoja = {}
            hallazgos_path = config.get("hallazgos_recomendaciones_json")
            hallazgos = {}
            if hallazgos_path and os.path.exists(hallazgos_path):
                with open(hallazgos_path, encoding="utf-8") as f:
                    hallazgos = json.load(f)
            for hoja, datos in parsed.items():
                if "error" in datos:
                    resumen_avisos.append(f"[checklist:{hoja}] {datos['error']}")
                    continue
                info = hallazgos.get(hoja, {})
                reco = info.get("recomendacion")
                if reco and datos["items"]:
                    # Se reemplaza el comentario del/los ítems observados u
                    # rechazados por la recomendación redactada (sección 9.1).
                    col_updates = {}
                    for it in checklist_mod.items_observados_o_rechazados(datos):
                        cell_ref = f"{_col_idx_to_letter(it['col_comentario'])}{it['fila']}"
                        col_updates[cell_ref] = reco
                    if col_updates:
                        updates_por_hoja[hoja] = col_updates

            src = checklist_path
            for hoja, updates in updates_por_hoja.items():
                checklist_mod.patch_cells_inline_str(src, out_checklist, hoja, updates)
                src = out_checklist  # encadenar patches sucesivos sobre el mismo archivo

            if not updates_por_hoja:
                resumen_avisos.append(
                    "Checklist: no había recomendaciones redactadas todavía para "
                    "aplicar (falta el JSON de hallazgos/recomendaciones) — no se "
                    "generó copia patcheada.")
            else:
                diffs = checklist_mod.verify_media_untouched(checklist_path, out_checklist)
                if diffs:
                    resumen_avisos.append(f"¡ATENCIÓN! posibles fotos afectadas en el "
                                           f"checklist patcheado: {diffs}")
                print(f"[OK] Checklist patcheado: {out_checklist}")
        except Exception:
            print("[ERROR] Falló el patch del checklist:")
            traceback.print_exc()
            resumen_avisos.append("El paso de checklist falló por completo — ver traceback arriba.")
    else:
        resumen_avisos.append("Paso de checklist omitido: no se indicó 'checklist_xlsx' "
                               "o el archivo no existe todavía.")

    # --- Paso 3: anexos ----------------------------------------------------
    try:
        generados, avisos = anexos_mod.construir_anexos(
            {**config, "lineas": lineas}, os.path.join(salida_dir, "PDF"))
        resumen_avisos.extend(avisos)
        if generados:
            print(f"[OK] Anexos generados ({len(generados)}): {os.path.join(salida_dir, 'PDF')}")
    except Exception:
        print("[ERROR] Falló la generación de anexos:")
        traceback.print_exc()
        resumen_avisos.append("El paso de anexos falló por completo — ver traceback arriba.")

    print("\n=== RESUMEN — revisar manualmente ===")
    if resumen_avisos:
        for a in resumen_avisos:
            print(" -", a)
    else:
        print(" (sin avisos)")

    return resumen_avisos


def _col_idx_to_letter(idx):
    letters = ""
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    run(sys.argv[1])
