"""
recomendaciones.py — motor de reglas (SIN IA) para redactar "Hallazgo" y
"Recomendación Técnica Aplicable" a partir de datos estructurados que el
inspector de campo llena en el VT-CHECK LIST, siguiendo el catálogo de casos
típicos de COMPLEMENTO/COMPENDIO TÉCNICO UNIFICADO DE HALLAZGOS Y
RECOMENDACIONES TÉCNICAS.REV.1.docx y las reglas críticas de
COMPLEMENTO/ROL_Y_OBJETIVO.REV2.txt.

No hay llamadas a ningún modelo de lenguaje: cada fila del checklist trae un
código de "CASO" (elegido de una lista cerrada) más un puñado de variables de
campo (NPS, longitud, cantidad, ubicación, color, etc.); este módulo busca el
caso en el catálogo, valida/aplica las reglas críticas (severidad leve
puntual -> sin recomendación, tramo no accesible -> andamios, etc.) y rellena
la plantilla oficial con los valores recibidos.

Uso típico (desde checklist.py):

    from recomendaciones import generar_hallazgo_y_recomendacion
    resultado = generar_hallazgo_y_recomendacion(fila_dict)
    if resultado is not None:
        hallazgo, recomendacion = resultado.hallazgo, resultado.recomendacion
"""
from dataclasses import dataclass, field
from typing import Optional


SIN_DATO = "SIN DATO"

# Casos en los que, aunque el tramo esté en altura / no accesible, el
# hallazgo SÍ se describe y recomienda de forma directa (excepción de la
# sección 3 de ROL_Y_OBJETIVO.REV2.txt: fuga en bridas, fuga en válvulas,
# pandeo/deformación de tubería).
CASOS_VISIBLES_PESE_A_ALTURA = {
    "BRIDA_FUGA_EMPAQUE",
    "VALVULA_CONTROL_FUGA_CUERPO_BONETE",
    "TUBERIA_PANDEO_DEFORMACION",
}

# Severidades que, según la matriz de decisión (regla 1 de ROL_Y_OBJETIVO),
# NUNCA generan recomendación técnica: falla de pintura o corrosión leve y
# puntual, el componente conserva su integridad.
SEVERIDADES_SIN_RECOMENDACION = {"LEVE PUNTUAL", "LEVE LOCALIZADA"}

CASO_ANDAMIO = "TUBERIA_TRAMO_NO_ACCESIBLE"


def _fmt(valor, default=None):
    """Devuelve el valor limpio como string, o SIN_DATO/placeholder si falta."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return default if default is not None else SIN_DATO
    return str(valor).strip()


@dataclass
class Caso:
    id: str
    categoria: str
    etiqueta: str
    hallazgo_tpl: str
    recomendacion_tpl: str
    variables: tuple = field(default_factory=tuple)
    defaults: dict = field(default_factory=dict)


@dataclass
class Resultado:
    caso_id: str
    hallazgo: str
    recomendacion: str


def _v(datos, clave, defecto=SIN_DATO):
    return _fmt(datos.get(clave), defecto)


# ==============================================================================
# CATÁLOGO — extraído 1:1 del COMPENDIO REV.1 (secciones A-H), con los
# marcadores entre corchetes convertidos a placeholders Python ({nps}, {x},
# {n}, {ubicacion}, {tag}, {color_actual}, {color_norma}, {tipo}, {material},
# {schedule}, {elemento}).
# ==============================================================================
CATALOGO = {
    # --- A. TUBERÍAS Y CIRCUITOS ------------------------------------------
    "TUBERIA_REEMPLAZO_TRAMO": Caso(
        id="TUBERIA_REEMPLAZO_TRAMO",
        categoria="TUBERIA",
        etiqueta="Corrosión / pérdida de espesor con reemplazo de tramo",
        hallazgo_tpl=(
            "Corrosión {severidad} y pérdida de espesor (verificado con medición de "
            "espesores) en tuberías y accesorios ({elemento}) (longitud aprox. {longitud} metros)."
        ),
        recomendacion_tpl=(
            "Efectuar el reemplazo de un (niple/tubería/accesorio) de NPS {nps}, "
            "Sch {schedule}, material {material}, utilizando su respectivo WPS y "
            "PQR previamente calificado."
        ),
        variables=("severidad", "elemento", "longitud", "nps", "schedule", "material"),
        defaults={"severidad": "moderada", "elemento": "tubería/accesorio"},
    ),
    "TUBERIA_DETERIORO_RECUBRIMIENTO_GENERALIZADO": Caso(
        id="TUBERIA_DETERIORO_RECUBRIMIENTO_GENERALIZADO",
        categoria="TUBERIA",
        etiqueta="Deterioro de recubrimiento y corrosión generalizada en circuito",
        hallazgo_tpl=(
            "Deterioro del recubrimiento y corrosión {severidad} generalizada en el "
            "tramo/circuito NPS {nps} (longitud aprox. {longitud} metros)."
        ),
        recomendacion_tpl=(
            "Efectuar el mantenimiento en la totalidad del recubrimiento de los "
            "accesorios y componentes pertenecientes al tramo/circuito NPS {nps} "
            "(longitud aprox. {longitud} metros), siguiendo los estándares Repsol "
            "ED-B-06.00-04d y el documento PE-B-0600.01H00R05."
        ),
        variables=("severidad", "nps", "longitud"),
        defaults={"severidad": "leve a moderada"},
    ),
    "TUBERIA_JUNTAS_SOLDADAS_SIN_PINTURA": Caso(
        id="TUBERIA_JUNTAS_SOLDADAS_SIN_PINTURA",
        categoria="TUBERIA",
        etiqueta="Juntas soldadas nuevas sin pintura",
        hallazgo_tpl=(
            "Corrosión leve en la zona de {cantidad} juntas soldadas sin "
            "recubrimiento protector (pintura) perteneciente al tramo nuevo del "
            "circuito NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar la aplicación del recubrimiento protector (pintura) en las "
            "{cantidad} juntas soldadas del tramo nuevo del circuito NPS {nps}, "
            "siguiendo los estándares Repsol ED-B-06.00-04d y el documento "
            "PE-B-0600.01H00R05."
        ),
        variables=("cantidad", "nps"),
    ),
    "TUBERIA_PANDEO_DEFORMACION": Caso(
        id="TUBERIA_PANDEO_DEFORMACION",
        categoria="TUBERIA",
        etiqueta="Deformación o pandeo en tuberías",
        hallazgo_tpl=(
            "Pandeo / Deformación en la tubería cerca de {ubicacion} (NPS {nps}, "
            "longitud aprox. {longitud} metros)."
        ),
        recomendacion_tpl=(
            "Recomendación:\n"
            "• Realizar la evaluación de integridad mecánica en el tramo de tubería "
            "de NPS {nps} y una longitud de {longitud} metros, cerca de {ubicacion}, "
            "afectado por deformación y pandeo, conforme a los lineamientos del "
            "código API 570 y los estándares Repsol aplicables."
        ),
        variables=("ubicacion", "nps", "longitud"),
    ),
    "TUBERIA_TRAMO_NO_ACCESIBLE": Caso(
        id="TUBERIA_TRAMO_NO_ACCESIBLE",
        categoria="TUBERIA",
        etiqueta="Tramo del circuito en altura / no accesible",
        hallazgo_tpl=(
            "Presencia de corrosión (otros) en tramo no accesible: circuito NPS "
            "{nps} evidencia corrosión en zonas sin acceso para inspección visual "
            "adecuada, por encontrarse en altura."
        ),
        recomendacion_tpl=(
            "Se requiere instalar facilidades (andamios de {longitud} metros) para "
            "acceder a la zona cerca de {ubicacion} y complementar la inspección de "
            "la zona observada en la tubería de NPS {nps}."
        ),
        variables=("nps", "longitud", "ubicacion"),
    ),
    "TUBERIA_COLOR_NO_REGLAMENTARIO": Caso(
        id="TUBERIA_COLOR_NO_REGLAMENTARIO",
        categoria="TUBERIA",
        etiqueta="Adecuación por código de color no reglamentario",
        hallazgo_tpl=(
            "Recubrimiento existente en color no reglamentario ({color_actual}) en "
            "el circuito NPS {nps}, requiriendo el código de color de "
            "identificación ({color_norma})."
        ),
        recomendacion_tpl=(
            "Realizar la aplicación de la capa de acabado/repintado del circuito "
            "NPS {nps}, para adecuarlo al color de identificación correspondiente "
            "al fluido transportado ({color_norma}), en conformidad con el "
            "estándar Repsol ED-B-06.00-04d y el documento PE-B-0600.01H00R05."
        ),
        variables=("color_actual", "nps", "color_norma"),
    ),

    # --- B. VÁLVULAS -------------------------------------------------------
    "VALVULA_MANUAL_CORROSION_MODERADA": Caso(
        id="VALVULA_MANUAL_CORROSION_MODERADA",
        categoria="VALVULA",
        etiqueta="Válvula manual con corrosión moderada",
        hallazgo_tpl=(
            "Deterioro del recubrimiento y corrosión moderada en válvula de {tipo} "
            "NPS {nps}."
        ),
        recomendacion_tpl=(
            "Efectuar el mantenimiento del recubrimiento en la válvula de {tipo} "
            "NPS {nps}, incluyendo el mantenimiento de los mecanismos del volante, "
            "bonete y prensaestopas, así como su lubricación, según los estándares "
            "Repsol ED-B-06.00-04d y PE-B-0600.01H00R05."
        ),
        variables=("tipo", "nps"),
    ),
    "VALVULA_CORROSION_SEVERA_PERNOS": Caso(
        id="VALVULA_CORROSION_SEVERA_PERNOS",
        categoria="VALVULA",
        etiqueta="Válvula con corrosión moderada a severa en pernos y mecanismos",
        hallazgo_tpl=(
            "Deterioro del recubrimiento y corrosión moderada a severa en "
            "{cantidad} válvulas de {tipo} de NPS {nps}, afectando principalmente "
            "a los pernos de ajuste del volante y de la prensaestopas."
        ),
        recomendacion_tpl=(
            "Realizar el reemplazo de los pernos de ajuste (del volante y de la "
            "prensaestopas) y el mantenimiento correctivo de los mecanismos "
            "(volante, bonete y prensaestopas) con su respectiva lubricación en "
            "las {cantidad} válvulas de {tipo} de NPS {nps}, conforme a los "
            "lineamientos de la norma API 598 y el código ASME B31.3. (Nota: al "
            "ser corrosión severa, se excluye el mantenimiento rutinario de "
            "recubrimiento)."
        ),
        variables=("cantidad", "tipo", "nps"),
    ),
    "VALVULA_VOLANTE_SUELTO": Caso(
        id="VALVULA_VOLANTE_SUELTO",
        categoria="VALVULA",
        etiqueta="Volante desprendido o suelto",
        hallazgo_tpl=(
            "Volante fuera de posición (desprendido del vástago) y sujetado "
            "provisoriamente con alambre de amarre en válvula de {tipo} de NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar el mantenimiento correctivo o reemplazo de la válvula de "
            "{tipo} de NPS {nps}, reinstalando y fijando de manera definitiva el "
            "volante al vástago, conforme a la norma API 598 y estándares Repsol "
            "aplicables."
        ),
        variables=("tipo", "nps"),
    ),
    "VALVULA_AGUJA_PERDIDA_MANIVELA": Caso(
        id="VALVULA_AGUJA_PERDIDA_MANIVELA",
        categoria="VALVULA",
        etiqueta="Pérdida de manivela/palanca en válvula de aguja",
        hallazgo_tpl=(
            "Pérdida de la manivela / palanca de accionamiento en la válvula de "
            "aguja de regulación para manómetro."
        ),
        recomendacion_tpl=(
            "Realizar el reemplazo de la manivela de la válvula de aguja para "
            "restablecer la maniobrabilidad del elemento de regulación y "
            "aislamiento, conforme a los lineamientos de la norma API 598 y el "
            "código ASME B31.3."
        ),
        variables=(),
    ),
    "VALVULA_FUGA_PRENSAESTOPAS": Caso(
        id="VALVULA_FUGA_PRENSAESTOPAS",
        categoria="VALVULA",
        etiqueta="Residuos de producto / fuga en prensaestopas",
        hallazgo_tpl=(
            "Presencia de restos de producto (humedecido) en la zona de la "
            "prensaestopas en {cantidad} válvulas de {tipo} de NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar el mantenimiento correctivo de las {cantidad} válvulas de "
            "{tipo} de NPS {nps}, incluyendo la limpieza integral del producto "
            "adherido, inspección de sus componentes, de acuerdo con la práctica "
            "recomendada API 598 y los estándares Repsol aplicables."
        ),
        variables=("cantidad", "tipo", "nps"),
    ),
    "VALVULA_LINEA_AISLADA_SIN_AISLAMIENTO_PROPIO": Caso(
        id="VALVULA_LINEA_AISLADA_SIN_AISLAMIENTO_PROPIO",
        categoria="VALVULA",
        etiqueta="Válvula en línea aislada sin aislamiento propio",
        hallazgo_tpl=(
            "Presencia de corrosión generalizada en {cantidad} válvulas sin "
            "aislamiento térmico ({tipo}) en línea aislada."
        ),
        recomendacion_tpl=(
            "Realizar limpieza en {cantidad} válvulas ({tipo}) y mantenimiento de "
            "elementos de ajuste (espárragos y tuercas), conforme al procedimiento "
            "Repsol RLP-FM-MANT-PRO-06-01.006. NOTA: si la línea con aislamiento "
            "térmico excede los 200 °C, ya no corresponde aplicar recubrimiento "
            "(pintura)."
        ),
        variables=("cantidad", "tipo"),
    ),
    "VALVULA_CONTROL_FUGA_CUERPO_BONETE": Caso(
        id="VALVULA_CONTROL_FUGA_CUERPO_BONETE",
        categoria="VALVULA",
        etiqueta="Válvula de control con fuga cuerpo-bonete",
        hallazgo_tpl=(
            "Fuga de producto / restos de producto en la unión entre cuerpo y "
            "bonete en válvula de control de tipo {tipo} de NPS {nps} ({tag})."
        ),
        recomendacion_tpl=(
            "Realizar el mantenimiento correctivo de la unión cuerpo-bonete y "
            "reemplazo del empaque/junta en la válvula de control {tag} / NPS "
            "{nps}, así como la limpieza integral del producto acumulado, "
            "siguiendo los lineamientos del código API 570 y los estándares "
            "Repsol aplicables."
        ),
        variables=("tipo", "nps", "tag"),
    ),
    "VALVULA_CONTROL_SUCIEDAD_EXTERNA": Caso(
        id="VALVULA_CONTROL_SUCIEDAD_EXTERNA",
        categoria="VALVULA",
        etiqueta="Válvula de control con suciedad externa en instrumentación",
        hallazgo_tpl=(
            "Presencia de suciedad en componentes externos (bonete, eje, "
            "indicador y métrica de posición) de la válvula de control {tag} / "
            "NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar limpieza de los componentes afectados de la válvula de "
            "control {tag} / NPS {nps}, conforme a los estándares de "
            "mantenimiento de instrumentación y lineamientos Repsol aplicables."
        ),
        variables=("tag", "nps"),
    ),

    # --- C. SOPORTES Y ELEMENTOS DE SUJECIÓN --------------------------------
    "SOPORTE_UBOLT_CONTACTO_DIRECTO": Caso(
        id="SOPORTE_UBOLT_CONTACTO_DIRECTO",
        categoria="SOPORTE",
        etiqueta="Soporte U-bolt con corrosión moderada y contacto directo",
        hallazgo_tpl=(
            "Soporte con abrazadera tipo U-bolt presenta corrosión moderada y "
            "contacto directo con tubería NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar el mantenimiento del recubrimiento en soporte y abrazadera "
            "tipo U-bolt e instalar un aislamiento de protección (teflón, "
            "elastómero o neopreno) para evitar el contacto directo metal-metal "
            "en la tubería NPS {nps}, de acuerdo con la norma MSS SP-58 y los "
            "estándares Repsol ED-B-06.00-04d, PE-B-0600.01H00R05 y "
            "ED-L-06.00-05a (sección 5.5)."
        ),
        variables=("nps",),
    ),
    "SOPORTE_LEVE_ABRAZADERA_SEVERA": Caso(
        id="SOPORTE_LEVE_ABRAZADERA_SEVERA",
        categoria="SOPORTE",
        etiqueta="Soporte con corrosión leve y abrazadera/pernos con corrosión severa",
        hallazgo_tpl=(
            "Deterioro del recubrimiento y corrosión leve por sectores en "
            "soporte, y corrosión severa en la abrazadera y sus pernos de ajuste "
            "(línea NPS {nps})."
        ),
        recomendacion_tpl=(
            "Recomendación:\n"
            "• Realizar el reemplazo de la abrazadera y sus pernos de ajuste en "
            "la línea NPS {nps}, de acuerdo con la norma MSS SP-58 y el estándar "
            "Repsol ED-L-06.00-05a (sección 5.5).\n"
            "• Nota: si el soporte solo cuenta con corrosión leve y no afecta su "
            "integridad, no se recomienda acción correctiva o preventiva sobre "
            "el soporte."
        ),
        variables=("nps",),
    ),
    "SOPORTE_REEMPLAZO_TOTAL": Caso(
        id="SOPORTE_REEMPLAZO_TOTAL",
        categoria="SOPORTE",
        etiqueta="Reemplazo total de soporte y abrazadera (corrosión severa)",
        hallazgo_tpl=(
            "Deterioro del recubrimiento, corrosión moderada y severa en soporte "
            "y abrazaderas ({cantidad}) en el tramo de la línea NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar el reemplazo del soporte y de las {cantidad} abrazaderas "
            "en el tramo de la línea NPS {nps}, siguiendo los estándares Repsol "
            "ED-B-06.00-04d, PE-B-0600.01H00R05 y ED-L-06.00-05a (sección 5.5) y "
            "la norma MSS SP-58. (Sin mantenimiento de recubrimiento/pintura)."
        ),
        variables=("cantidad", "nps"),
    ),
    "SOPORTE_METALICO_TIPICO": Caso(
        id="SOPORTE_METALICO_TIPICO",
        categoria="SOPORTE",
        etiqueta="Deterioro de recubrimiento y corrosión leve a moderada en soporte metálico típico",
        hallazgo_tpl=(
            "Deterioro del recubrimiento y corrosión {severidad} en el soporte "
            "tipo {tipo} de la línea NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar el mantenimiento del recubrimiento en el soporte tipo "
            "{tipo} de la línea NPS {nps}. La intervención deberá realizarse "
            "conforme al esquema de pinturas PE-B-0600.01-I, aplicando como "
            "color de acabado el verde RAL 6001."
        ),
        variables=("severidad", "tipo", "nps"),
        defaults={"severidad": "leve a moderada"},
    ),
    "SOPORTE_SPRING_HANGER": Caso(
        id="SOPORTE_SPRING_HANGER",
        categoria="SOPORTE",
        etiqueta="Soporte tipo resorte (spring hanger) con corrosión moderada",
        hallazgo_tpl=(
            "Deterioro del recubrimiento y corrosión moderada en soporte de "
            "resorte (spring hanger) de la línea NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar el mantenimiento del recubrimiento en el soporte tipo "
            "spring hanger de la línea NPS {nps}, conforme a los estándares "
            "Repsol ED-B-06.00-04d y al documento técnico PE-B-0600.01H00R05. "
            "(No se especifica código de color de acabado por sus "
            "consideraciones especiales frente a otros soportes)."
        ),
        variables=("nps",),
    ),

    # --- D. AISLAMIENTO TÉRMICO Y PROTECCIÓN IGNÍFUGA -----------------------
    "AISLAMIENTO_VENTANA_INSPECCION": Caso(
        id="AISLAMIENTO_VENTANA_INSPECCION",
        categoria="AISLAMIENTO",
        etiqueta="Contaminación/corrosión moderada en ventana de inspección",
        hallazgo_tpl=(
            "Contaminación del aislamiento térmico (humedad), así como también "
            "se visualiza corrosión moderada en zonas con ventanas de inspección "
            "(línea NPS {nps})."
        ),
        recomendacion_tpl=(
            "Retirar el aislamiento térmico y efectuar la limpieza de la zona "
            "corroída para evaluar el grado de daño. En caso de verificarse "
            "corrosión superficial, aplicar recubrimiento de pintura, siguiendo "
            "los estándares Repsol ED-B-06.00-04d y el documento "
            "PE-B-0600.01H00R05. Nota: solo se aplica recubrimiento a tuberías "
            "con temperatura de operación menor o igual a 200 °C."
        ),
        variables=("nps",),
    ),
    "AISLAMIENTO_ABERTURAS_ABOLLADURAS": Caso(
        id="AISLAMIENTO_ABERTURAS_ABOLLADURAS",
        categoria="AISLAMIENTO",
        etiqueta="Aberturas, abolladuras o exposición del aislante",
        hallazgo_tpl=(
            "Abertura(s) en la cubierta metálica, abolladuras, deterioro y/o "
            "exposición del material aislante en {ubicacion} del circuito NPS "
            "{nps}."
        ),
        recomendacion_tpl=(
            "Reparar el aislamiento térmico en {ubicacion} del circuito, "
            "siguiendo los lineamientos del API 583 sección 9.6.a, del "
            "estándar Repsol ED-N-01.00-03 y del documento PE-N-0100.01."
        ),
        variables=("ubicacion", "nps"),
    ),
    "AISLAMIENTO_AUSENCIA": Caso(
        id="AISLAMIENTO_AUSENCIA",
        categoria="AISLAMIENTO",
        etiqueta="Ausencia / falta de aislamiento térmico",
        hallazgo_tpl=(
            "Ausencia de aislamiento térmico en {ubicacion} de NPS {nps} "
            "(longitud aprox. {longitud} metros)."
        ),
        recomendacion_tpl=(
            "Instalar aislamiento térmico en {ubicacion} de NPS {nps} (longitud "
            "aprox. {longitud} metros), siguiendo los lineamientos del API 583 "
            "sección 9.6.a, del estándar Repsol ED-N-01.00-03 y del documento "
            "PE-N-0100.01."
        ),
        variables=("ubicacion", "nps", "longitud"),
    ),
    "AISLAMIENTO_MANCHAS_SUCIEDAD": Caso(
        id="AISLAMIENTO_MANCHAS_SUCIEDAD",
        categoria="AISLAMIENTO",
        etiqueta="Manchas de producto, suciedad o deterioro superficial del aislamiento",
        hallazgo_tpl=(
            "Presencia de manchas de producto, suciedad o deterioro en el "
            "aislamiento térmico en {cantidad} zonas del circuito (longitud "
            "aprox. {longitud} metros)."
        ),
        recomendacion_tpl=(
            "Realizar limpieza y/o reemplazo del aislamiento térmico en "
            "{ubicacion} del circuito, siguiendo los lineamientos del API 583 "
            "sección 9.6.a, del estándar Repsol ED-N-01.00-03 y del documento "
            "PE-N-0100.01."
        ),
        variables=("cantidad", "longitud", "ubicacion"),
    ),
    "AISLAMIENTO_PROTECCION_IGNIFUGA_AGRIETADA": Caso(
        id="AISLAMIENTO_PROTECCION_IGNIFUGA_AGRIETADA",
        categoria="AISLAMIENTO",
        etiqueta="Protección ignífuga agrietada (fireproofing)",
        hallazgo_tpl=(
            "Agrietamiento en la protección ignífuga de {elemento} en la zona "
            "cercana a {ubicacion}."
        ),
        recomendacion_tpl=(
            "Realizar la reparación de la protección ignífuga en {elemento}, "
            "asegurando el resane de las grietas, conforme a los lineamientos "
            "de los estándares Repsol aplicables."
        ),
        variables=("elemento", "ubicacion"),
    ),

    # --- E. INDICADORES DE PRESIÓN ------------------------------------------
    "INDICADOR_MANOMETRO_DETERIORADO": Caso(
        id="INDICADOR_MANOMETRO_DETERIORADO",
        categoria="INDICADOR",
        etiqueta="Manómetro con deterioro, aguja desprendida y opacidad en visor",
        hallazgo_tpl=(
            "Manómetro con deterioro, aguja desprendida, contaminación de "
            "glicerina e imposibilidad de toma de lectura por opacidad del "
            "visor en línea NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar el reemplazo del manómetro en la línea NPS {nps} para "
            "garantizar la confiabilidad en la lectura del instrumento y "
            "mantener la integridad operacional, conforme a los estándares de "
            "instrumentación y lineamientos Repsol aplicables."
        ),
        variables=("nps",),
    ),

    # --- F. BRIDAS -----------------------------------------------------------
    "BRIDA_ESPARRAGOS_CORTOS": Caso(
        id="BRIDA_ESPARRAGOS_CORTOS",
        categoria="BRIDA",
        etiqueta="Espárragos cortos (longitud insuficiente)",
        hallazgo_tpl=(
            "Hallazgo: Longitud insuficiente de espárragos en unión bridada de "
            "NPS {nps} (no sobresalen de la cara exterior de la tuerca)."
        ),
        recomendacion_tpl=(
            "Reemplazar los espárragos por unos de longitud adecuada que "
            "garanticen sobresalir al menos dos (2) hilos de rosca por encima "
            "de la cara exterior de la tuerca, conforme a la norma ASME B31.3 "
            "y al procedimiento Repsol RLP-FM-MANT-PRO-06-01.006."
        ),
        variables=("nps",),
    ),
    "BRIDA_PAR_GALVANICO": Caso(
        id="BRIDA_PAR_GALVANICO",
        categoria="BRIDA",
        etiqueta="Par galvánico (bridas inox + espárragos acero al carbono)",
        hallazgo_tpl=(
            "Hallazgo: Par galvánico por incompatibilidad de materiales (bridas "
            "de acero inoxidable con espárragos y tuercas de acero al carbono) "
            "en {cantidad} uniones bridadas del circuito NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar el reemplazo de la totalidad de los elementos de ajuste "
            "de acero al carbono por espárragos y tuercas de acero inoxidable "
            "de grado compatible, conforme a la norma ASME B31.3 y estándares "
            "Repsol aplicables."
        ),
        variables=("cantidad", "nps"),
    ),
    "BRIDA_CORROSION_LEVE_MODERADA": Caso(
        id="BRIDA_CORROSION_LEVE_MODERADA",
        categoria="BRIDA",
        etiqueta="Corrosión en espárragos/bridas (leve a moderada)",
        hallazgo_tpl=(
            "Hallazgo: Deterioro del recubrimiento y presencia de corrosión "
            "{severidad} en {cantidad} uniones bridadas, incluyendo sus "
            "elementos de ajuste (espárragos y tuercas) en la línea NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar limpieza mecánica, mantenimiento del recubrimiento y "
            "aplicar lubricante tipo Molykote 1000 en {cantidad} uniones "
            "bridadas, incluyendo sus elementos de ajuste (tuercas y "
            "espárragos), conforme al procedimiento Repsol "
            "RLP-FM-MANT-PRO-06-01.006 (Secc. 3.4.2) y los estándares Repsol "
            "ED-B-06.00-04d y PE-B-0600.01H00R05."
        ),
        variables=("severidad", "cantidad", "nps"),
        defaults={"severidad": "leve a moderada"},
    ),
    "BRIDA_SEVERA_ESPARRAGOS_MODERADA_BRIDA": Caso(
        id="BRIDA_SEVERA_ESPARRAGOS_MODERADA_BRIDA",
        categoria="BRIDA",
        etiqueta="Corrosión severa en espárragos y moderada en bridas",
        hallazgo_tpl=(
            "Hallazgo: Deterioro del recubrimiento y corrosión moderada en "
            "bridas, con corrosión severa en espárragos y tuercas en "
            "{cantidad} uniones bridadas de NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar el reemplazo de los elementos de ajuste (espárragos y "
            "tuercas) en las {cantidad} uniones bridadas de NPS {nps}, "
            "conforme al procedimiento Repsol RLP-FM-MANT-PRO-06-01.006 y ASME "
            "B31.3; asimismo, efectuar el mantenimiento del recubrimiento en "
            "las bridas según los estándares Repsol ED-B-06.00-04d y "
            "PE-B-0600.01H00R05."
        ),
        variables=("cantidad", "nps"),
    ),
    "BRIDA_PERNOS_EN_LUGAR_DE_ESPARRAGOS": Caso(
        id="BRIDA_PERNOS_EN_LUGAR_DE_ESPARRAGOS",
        categoria="BRIDA",
        etiqueta="Uso de pernos en lugar de espárragos",
        hallazgo_tpl=(
            "Hallazgo: Unión bridada de NPS {nps} con uso de pernos en lugar de "
            "espárragos de ajuste ({cantidad} unidades)."
        ),
        recomendacion_tpl=(
            "Reemplazar los pernos por espárragos con tuercas en la unión "
            "bridada NPS {nps}, garantizando que sobresalgan al menos dos (2) "
            "hilos de rosca, conforme a ASME B31.3 y el procedimiento Repsol "
            "RLP-FM-MANT-PRO-06-01.006."
        ),
        variables=("nps", "cantidad"),
    ),
    "BRIDA_TUERCA_FALTANTE": Caso(
        id="BRIDA_TUERCA_FALTANTE",
        categoria="BRIDA",
        etiqueta="Falta de elemento de ajuste (tuerca faltante)",
        hallazgo_tpl=(
            "Hallazgo: Ausencia de tuerca hexagonal en {cantidad} espárrago(s) "
            "de la junta bridada de NPS {nps}."
        ),
        recomendacion_tpl=(
            "Instalar la tuerca hexagonal faltante en el espárrago de la junta "
            "bridada de NPS {nps} y aplicar apriete/torque verificado para "
            "garantizar un sellado uniforme, conforme a ASME B31.3 y el "
            "procedimiento Repsol RLP-FM-MANT-PRO-06-01.006."
        ),
        variables=("cantidad", "nps"),
    ),
    "BRIDA_FUGA_EMPAQUE": Caso(
        id="BRIDA_FUGA_EMPAQUE",
        categoria="BRIDA",
        etiqueta="Fuga de producto / falla de empaque",
        hallazgo_tpl=(
            "Hallazgo: Presencia de fuga de producto / restos humedecidos en "
            "la junta bridada de NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar el mantenimiento de la unión bridada NPS {nps} mediante "
            "limpieza de caras, cambio de empaque y torqueado controlado "
            "conforme al código API 570, ASME B31.3 y el procedimiento Repsol "
            "RLP-FM-MANT-PRO-06-01.006."
        ),
        variables=("nps",),
    ),

    # --- G/H. BRIDAS DE ORIFICIO ---------------------------------------------
    "BRIDA_ORIFICIO_FALTA_SOLDADURA_SELLO": Caso(
        id="BRIDA_ORIFICIO_FALTA_SOLDADURA_SELLO",
        categoria="BRIDA_ORIFICIO",
        etiqueta="Falta de soldadura de sello en niples de toma de brida de orificio",
        hallazgo_tpl=(
            "Se identificó ausencia de soldadura de sello entre los 2 niples "
            "NPS ½” (tomas alta y baja presión) y las bridas de la placa "
            "orificio ({tag})."
        ),
        recomendacion_tpl=(
            "Aplicar soldadura de sello en las conexiones de las líneas de "
            "toma raíz con la brida de orificio {tag}, empleando el WPS y PQR "
            "correspondientes, debidamente calificados."
        ),
        variables=("tag",),
    ),

    # --- Casos adicionales frecuentes en campo (mismo estilo del COMPENDIO,
    # cubren defectos mecánicos directos que el REV.1 no tabuló como "caso
    # típico" explícito pero que sí caen bajo sus reglas de redacción) -------
    "VALVULA_VOLANTE_AUSENTE": Caso(
        id="VALVULA_VOLANTE_AUSENTE",
        categoria="VALVULA",
        etiqueta="Ausencia total de volante en válvula",
        hallazgo_tpl=(
            "Ausencia de volante en {cantidad} válvula(s) de {tipo} de NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar la instalación de un volante nuevo en {cantidad} "
            "válvula(s) de {tipo} de NPS {nps}, conforme a la norma API 598 y "
            "estándares Repsol aplicables."
        ),
        variables=("cantidad", "tipo", "nps"),
        defaults={"cantidad": "1", "tipo": "compuerta"},
    ),
    "SOPORTE_ABRAZADERA_FALTANTE": Caso(
        id="SOPORTE_ABRAZADERA_FALTANTE",
        categoria="SOPORTE",
        etiqueta="Ausencia total de abrazadera",
        hallazgo_tpl=(
            "Ausencia de abrazadera tipo {tipo} en la línea NPS {nps}."
        ),
        recomendacion_tpl=(
            "Realizar la instalación de una abrazadera tipo {tipo} en la "
            "línea NPS {nps}, conforme a la norma MSS SP-58 y el estándar "
            "Repsol ED-L-06.00-05a."
        ),
        variables=("tipo", "nps"),
        defaults={"tipo": "U-bolt"},
    ),
}

CATEGORIAS = sorted({c.categoria for c in CATALOGO.values()})


def casos_por_categoria(categoria):
    return [c for c in CATALOGO.values() if c.categoria == categoria.strip().upper()]


def _severidad_norm(v):
    return _fmt(v, "").strip().upper()


def generar_hallazgo_y_recomendacion(datos: dict) -> Optional[Resultado]:
    """Recibe un dict con, al menos, la clave "caso" (id del catálogo o su
    etiqueta) y las variables necesarias (nps, longitud, cantidad, ubicacion,
    tipo, tag, color_actual, color_norma, elemento, material, schedule,
    severidad) y devuelve un Resultado(hallazgo, recomendacion) ya redactado,
    o None si la regla crítica de severidad determina que NO corresponde
    recomendación (leve puntual / localizada -> aceptable, se omite).

    `datos` también puede traer "accesible" ("SI"/"NO") y el motor
    sustituye automáticamente el caso por TUBERIA_TRAMO_NO_ACCESIBLE cuando
    accesible="NO", salvo que el caso elegido esté en
    CASOS_VISIBLES_PESE_A_ALTURA (fuga de brida/válvula, pandeo)."""
    caso_id = _fmt(datos.get("caso"), "").strip()
    if not caso_id:
        return None

    caso = CATALOGO.get(caso_id.upper())
    if caso is None:
        # Tolerar que venga la etiqueta en español en vez del id.
        caso_id_norm = caso_id.strip().lower()
        for c in CATALOGO.values():
            if c.etiqueta.strip().lower() == caso_id_norm:
                caso = c
                break
    if caso is None:
        raise ValueError(
            f"Caso de hallazgo no reconocido en el catálogo: {caso_id!r}. "
            "Revisa la columna CASO del VT-CHECK LIST."
        )

    severidad = _severidad_norm(datos.get("severidad"))
    if severidad in SEVERIDADES_SIN_RECOMENDACION:
        return None

    accesible = _fmt(datos.get("accesible"), "SI").strip().upper()
    if accesible in ("NO", "N") and caso.id not in CASOS_VISIBLES_PESE_A_ALTURA:
        caso = CATALOGO[CASO_ANDAMIO]

    valores = dict(caso.defaults)
    for var in caso.variables:
        valores[var] = _v(datos, var)
    # Variables genéricas siempre disponibles aunque el caso no las declare
    # explícitamente en `variables` (por si el usuario las incluye en el
    # texto manualmente vía formato libre no usado aquí).
    if "severidad" in caso.hallazgo_tpl and "severidad" not in valores:
        valores["severidad"] = _v(datos, "severidad", caso.defaults.get("severidad", SIN_DATO))

    try:
        hallazgo = caso.hallazgo_tpl.format(**valores)
        recomendacion = caso.recomendacion_tpl.format(**valores)
    except KeyError as e:
        raise ValueError(
            f"Falta la variable {e} en el checklist para el caso {caso.id!r} "
            f"({caso.etiqueta})."
        )

    return Resultado(caso_id=caso.id, hallazgo=hallazgo, recomendacion=recomendacion)


# ==============================================================================
# SUGERENCIA DE CASO A PARTIR DE TEXTO LIBRE (formato real del VT-CHECK LIST)
# ==============================================================================
# El VT-CHECK LIST estándar de campo (formato fijo AD-UN05-TL-TUB-VT) NO trae
# una columna "CASO": el inspector escribe el hallazgo como texto libre en la
# columna "Comentario", por categoría (Recubrimientos, Bridas, Válvulas,
# Soportes, etc.) y marca A/O/R/NA. Esta sección NO usa ningún modelo de
# lenguaje: aplica un conjunto pequeño y explícito de reglas de palabras
# clave (categoría + condición) para sugerir, con alta confianza, cuál caso
# del CATALOGO corresponde, y solo cuando hay evidencia clara. Si ninguna
# regla calza con confianza, se devuelve None y el hallazgo queda marcado
# para redacción manual del especialista (nunca se inventa una
# recomendación técnica sobre una base ambigua).
import re

RE_NPS = re.compile(r'(\d+(?:\s+\d/\d)?"|\d/\d")')
RE_CANTIDAD = re.compile(r"\((\d{1,3})\)")
RE_LONGITUD = re.compile(r"([\d]+(?:\.[\d]+)?)\s*metros", re.IGNORECASE)


def _contiene_alguna(texto, alternativas):
    return any(alt in texto for alt in alternativas)


def _extraer_variables_de_texto(texto):
    variables = {}
    m = RE_NPS.search(texto)
    if m:
        variables["nps"] = m.group(1).strip()
    m = RE_CANTIDAD.search(texto)
    if m:
        variables["cantidad"] = str(int(m.group(1)))
    m = RE_LONGITUD.search(texto)
    if m:
        variables["longitud"] = m.group(1)
    return variables


# Cada regla: (caso_id, categorías del checklist a las que aplica (substring,
# minúsculas, o None = cualquiera), grupos de palabras clave -- se exige AL
# MENOS una coincidencia de CADA grupo para considerar la regla confiable).
# Reglas derivadas 1:1 de COMPLEMENTO/ROL_Y_OBJETIVO.REV2.txt (ese documento
# está hecho exactamente para esta transformación hallazgo->recomendación;
# aquí se aplica como reglas de texto explícitas, sin ningún modelo de
# lenguaje detrás).
REGLAS_SUGERENCIA = [
    (
        "TUBERIA_DETERIORO_RECUBRIMIENTO_GENERALIZADO",
        ("recubrimientos", "componentes", "placas orificio", "puntos de inyecc"),
        [
            ("deterioro del recubrimiento", "deterioro recubrimiento", "deterioro del recubirmiento"),
            ("generaliz", "leve a moderada", "leve  a moderada"),
        ],
    ),
    (
        "BRIDA_CORROSION_LEVE_MODERADA",
        ("bridas",),
        [
            ("corrosion", "corrosión"),
            ("leve", "moderada"),
            ("union bridada", "uniones bridadas", "unión bridada", "uniones bridada"),
        ],
    ),
    (
        "BRIDA_FUGA_EMPAQUE",
        ("bridas",),
        [
            ("fuga",),
            ("brida", "empaque", "junta"),
        ],
    ),
    (
        "BRIDA_TUERCA_FALTANTE",
        ("bridas",),
        [
            ("tuerca",),
            ("falta", "ausencia", "faltante"),
        ],
    ),
    (
        "BRIDA_PERNOS_EN_LUGAR_DE_ESPARRAGOS",
        ("bridas",),
        [
            ("perno",),
            ("lugar de esparrago", "lugar de espárrago", "en vez de esparrago"),
        ],
    ),
    (
        "VALVULA_MANUAL_CORROSION_MODERADA",
        ("valvulas", "válvulas"),
        [
            ("corrosion", "corrosión"),
            ("leve", "moderada"),
        ],
    ),
    (
        "VALVULA_VOLANTE_SUELTO",
        ("valvulas", "válvulas"),
        [
            ("volante",),
            ("suelto", "desprendid", "fuera de posicion", "fuera de posición", "rotura"),
        ],
    ),
    (
        "VALVULA_VOLANTE_AUSENTE",
        ("valvulas", "válvulas"),
        [
            ("volante",),
            ("ausencia", "ausente", "sin volante"),
        ],
    ),
    (
        "SOPORTE_ABRAZADERA_FALTANTE",
        ("soportes", "abrazaderas"),
        [
            ("abrazadera",),
            ("ausencia", "ausente"),
        ],
    ),
    (
        "SOPORTE_UBOLT_CONTACTO_DIRECTO",
        ("soportes", "abrazaderas"),
        [
            ("u-bolt", "u bolt", "ubolt"),
            ("contacto", "corrosion", "corrosión"),
        ],
    ),
    (
        # Caso genérico (COMPENDIO C.4): corrosión leve/moderada en soporte
        # metálico sin una condición más específica (u-bolt, spring hanger,
        # ausencia, rotura) -- mantenimiento de recubrimiento, seguro por
        # ser la acción menos invasiva.
        "SOPORTE_METALICO_TIPICO",
        ("soportes", "abrazaderas"),
        [
            ("corrosion", "corrosión"),
            ("leve", "moderada"),
        ],
    ),
    (
        "AISLAMIENTO_PROTECCION_IGNIFUGA_AGRIETADA",
        (None,),
        [
            ("ignifuga", "ignífuga", "ingnifuca", "ignifuca", "fireproofing"),
            ("grieta", "agrieta"),
        ],
    ),
    (
        "AISLAMIENTO_AUSENCIA",
        ("aislamiento",),
        [
            ("ausencia", "falta de aislamiento", "sin aislamiento"),
            ("aislamiento",),
        ],
    ),
    (
        "AISLAMIENTO_ABERTURAS_ABOLLADURAS",
        ("aislamiento",),
        [
            ("abertura", "abolladura", "expuesto", "exposicion", "exposición"),
            ("aislamiento", "cubierta metalica", "cubierta metálica"),
        ],
    ),
    (
        "INDICADOR_MANOMETRO_DETERIORADO",
        ("instrumentacion", "instrumentación"),
        [
            ("manometro", "manómetro"),
            ("deteriorad", "aguja", "opac", "glicerina"),
        ],
    ),
    (
        "TUBERIA_COLOR_NO_REGLAMENTARIO",
        ("recubrimientos", "componentes"),
        [
            ("color",),
            ("no reglamentario", "reglamentario", "identificacion", "identificación"),
        ],
    ),
    (
        "TUBERIA_PANDEO_DEFORMACION",
        (None,),
        [
            ("pandeo", "deformacion", "deformación"),
        ],
    ),
]

# Comentarios que NO representan un hallazgo real (informativos / sin
# incidencia): nunca se sugiere recomendación para ellos.
TEXTOS_SIN_HALLAZGO = (
    "no aplica",
    "sin indicaciones relevantes",
    "sin incidencias",
    "se limita la inspecc",
)

# Regla 1 de ROL_Y_OBJETIVO.REV2.txt: corrosión LEVE y PUNTUAL/LOCALIZADA,
# el componente conserva su integridad -> NUNCA se emite recomendación
# técnica (se clasifica como aceptable). Se detecta por texto, no por caso.
_RE_LEVE_PUNTUAL = re.compile(
    r"\bleve\b.{0,25}\b(puntual|localizad)|(\bno compromete\b|\bconserva su integridad\b|\bsin afectar\b)",
    re.IGNORECASE,
)
TEXTO_ACEPTABLE_SIN_ACCION = (
    "Aceptable — corrosión leve puntual/localizada que no compromete la "
    "integridad del componente; conforme a la matriz de decisión no "
    "corresponde emitir recomendación técnica ni mantenimiento de pintura."
)


def sugerir_caso_desde_texto(categoria_checklist, comentario):
    """Intenta sugerir, con alta confianza y SIN IA, el o los casos del
    CATALOGO que corresponden a un comentario en texto libre del VT-CHECK
    LIST real (por categoría de componente), aplicando las mismas reglas de
    COMPLEMENTO/ROL_Y_OBJETIVO.REV2.txt. Si el comentario describe más de un
    problema y calzan varias reglas, se devuelven combinadas (separadas por
    acciones, como indica la sección de "componentes mixtos" del ROL).
    Devuelve un Resultado(hallazgo, recomendacion) ya redactado y con las
    variables detectables (NPS, cantidad, longitud) extraídas por expresión
    regular, o None si ninguna regla calza con confianza (el hallazgo queda
    entonces para redacción manual) -- salvo que el texto corresponda a
    corrosión leve puntual/localizada, en cuyo caso se marca "Aceptable, sin
    recomendación" tal como exige la matriz de decisión.
    """
    texto_norm = (comentario or "").strip().lower()
    if not texto_norm or any(t in texto_norm for t in TEXTOS_SIN_HALLAZGO):
        return None

    categoria_norm = (categoria_checklist or "").strip().lower()

    resultados = []
    ids_usados = set()
    for caso_id, categorias_aplicables, grupos_palabras in REGLAS_SUGERENCIA:
        if categorias_aplicables != (None,) and not any(
            c in categoria_norm for c in categorias_aplicables
        ):
            continue
        if not all(_contiene_alguna(texto_norm, grupo) for grupo in grupos_palabras):
            continue

        datos = {"caso": caso_id, **_extraer_variables_de_texto(comentario)}
        try:
            resultado = generar_hallazgo_y_recomendacion(datos)
        except ValueError:
            continue
        if resultado is not None and resultado.caso_id not in ids_usados:
            resultados.append(resultado)
            ids_usados.add(resultado.caso_id)

    if resultados:
        if len(resultados) == 1:
            return resultados[0]
        return Resultado(
            caso_id="+".join(r.caso_id for r in resultados),
            hallazgo=" ".join(r.hallazgo for r in resultados),
            recomendacion=" ".join(r.recomendacion for r in resultados),
        )

    if _RE_LEVE_PUNTUAL.search(texto_norm):
        return Resultado(
            caso_id="ACEPTABLE_SIN_RECOMENDACION",
            hallazgo=comentario.strip(),
            recomendacion=TEXTO_ACEPTABLE_SIN_ACCION,
        )

    return None
