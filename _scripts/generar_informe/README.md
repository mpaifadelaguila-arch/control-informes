# generar_informe.py — pipeline de automatización de informes "Plan de Líneas de Proceso"

Reconstruido el 15/09/2026 (la versión original se perdió al cambiar de
computadora — ver `claude/analisis-estructura-informe-y-plan-automatizacion.md`,
sección 13, en el Proyecto de Claude "INFORMES PLAN DE LÍNEAS").

## Qué hace

Para un grupo de tuberías nuevo, genera automáticamente:

1. **El informe Word** (`.docx`), patcheando directamente `assets/plantilla_base.docx`
   (nunca reconstruye desde cero): tabla SUMARIO, RECOMENDACIONES, 7.0
   Características, 9.0 CIRCUITO/LÍNEA, Recomendación #1 (texto oficial API
   570 según Clase), nota "solo VT", fecha/personal, banner y título de
   portada, mecanismo de daño.
2. **El checklist VT patcheado**: reemplaza la celda "Comentario" de cada
   ítem observado/rechazado por la Recomendación ya redactada, editando el
   XML directo — **nunca pierde las fotos incrustadas** (a diferencia de
   abrir el archivo con Excel/openpyxl y regrabarlo).
3. **Los anexos** (separadores + fusión con el contenido real): Anexo A
   (P&ID, 1 por grupo), Anexo B (Inspección Visual, 1 por línea), Anexo C
   (Ultrasonido/PSAIM, 1 por línea con `Alcance=LINEAS`).

Cualquier insumo que falte (PSAIM, checklist lleno, P&ID, isométricos,
hallazgos/recomendaciones) se reemplaza por un texto "PENDIENTE" explícito
y se avisa al final — **el pipeline nunca se detiene por completo por un
insumo faltante**, genera lo que sí puede con lo que sí tiene.

## Cómo correrlo

```bash
python3 generar_informe.py config_GT-0XX.json
```

Copia `config_ejemplo.json` a un archivo nuevo por grupo y ajusta las
rutas. Cada campo tiene su `_nota_*` explicando qué es y si es opcional.

### Insumos que SIEMPRE debe traer el usuario para un grupo nuevo

- El **alcance** del grupo: Item, Unidad, Líneas (TAG), Código de informe,
  Grupo de tuberías, SAP, Alcance del servicio — idealmente el mismo
  archivo "Listado de líneas.xlsx" / hoja SAP que ya usa, porque de ahí
  también se derivan automáticamente el rango de fechas de inspección y la
  lista de examinadores (columnas "FECHA DE INSPECCIÓN" e "INSPECTORES").
- **Quién elaboró el informe** — nunca se asume solo, siempre hay que
  preguntarlo (va primero en la lista de examinadores, con el calificativo
  "Examinador Nivel II - Elaboración de Informe").
- El PSAIM (versión con detalle por TML, columna "TML Vida útil") de cada
  línea con `Alcance=LINEAS`.

La base de datos técnica maestra (`BASE_DE_DATOS_DE_LINEAS_FASE1.xlsx`) NO
hace falta pedirla cada vez: vive en la raíz de la carpeta del proyecto,
compartida entre todos los grupos.

## Sobre `assets/plantilla_base.docx`

Es una copia del último informe real completado (grupo GT-010) — no una
plantilla "limpia" separada. Ya trae corregidos: el ancho del banner de
portada y su rectángulo naranja de fondo (para que el código del informe
no se corte), los anchos de columna de la tabla 7.0, y el patrón de la
nota "solo VT". El código internamente ubica los párrafos de un solo
ejemplar (Recomendación #1, nota VT, fecha/personal) por su `w14:paraId` y,
si no los encuentra (por ejemplo si algún día se reemplaza esta plantilla
por otra), cae de respaldo a buscarlos por el texto con el que empiezan —
ver las constantes `PARA_ID_*` en `informe.py`.

**Recomendación:** guardar SIEMPRE una copia de esta carpeta completa
(`generar_informe.zip`) dentro de la propia carpeta del proyecto en el USB
(`_scripts/`), no solo entregada por el chat — así sobrevive a cualquier
cambio de computadora o sesión nueva de Claude.

## Limitaciones conocidas / pendientes (honestidad ante todo)

- **`checklist.py` (el parser, `parse_hoja`)** se construyó con una
  heurística razonable sobre el layout descrito en la documentación
  (busca la columna "Comentario", columnas A/O/R/NA, cabecera con
  TAG/Unidad/Fecha/Examinadores), pero **no se pudo probar contra un
  checklist VT real ya lleno** (no había ninguno disponible al
  reconstruir el pipeline el 15/09/2026). La parte que SÍ está probada a
  fondo (con un .xlsx sintético con foto incrustada) es el patch de celda
  (`patch_cells_inline_str`) — esa es la parte crítica que protege las
  fotos. Conviene revisar el resultado de `parse_hoja` la primera vez que
  se corra contra un checklist real y ajustar si el layout real difiere.
- **`anexos.py`** genera los separadores con la fuente **Cambria** si la
  encuentra como fuente del sistema (en Windows, donde corre normalmente
  este script, debería estar siempre disponible vía Office/Windows). Si no
  la encuentra, usa una serif de respaldo y no avisa con un error — revisar
  visualmente el primer separador de cada grupo nuevo.
- El **motor de Hallazgo → Recomendación** (COMPENDIO + ROL Y OBJETIVO) NO
  es parte de este código — es un prompt de IA que Claude corre cada
  sesión leyendo el checklist lleno, y el resultado se guarda como el
  JSON que consume `hallazgos_recomendaciones_json`. Este pipeline solo
  aplica ese JSON al informe y al checklist, no lo redacta.
- Si algún grupo usa un código de informe mucho más largo de lo habitual
  (el banner probado va de 3 a 4+3+4 dígitos), conviene revisar
  visualmente que el texto no se salga del rectángulo naranja de portada.

## Estructura de archivos

```
generar_informe.py   CLI orquestador
informe.py            patch del .docx (tablas, párrafos, portada)
docxlib.py             helpers XML de bajo nivel (clonar filas, IDs, etc.)
inventario.py          cruce técnico + lectura del alcance
psaim.py                cálculo de rate de corrosión / vida útil
checklist.py            parser + patch del checklist VT (preserva fotos)
anexos.py                separadores + fusión de anexos
config_ejemplo.json    plantilla de config, copiar por grupo
assets/plantilla_base.docx   plantilla real (ver arriba)
```
