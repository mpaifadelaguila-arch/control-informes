import io
import json
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="CONTROL INTERNO DE INFORMES - ADEMINSAC",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- ESTILOS CSS PROFESIONALES Y PALETA CORPORATIVA ---
st.markdown(
    """
    <style>
    /* Ocultar elementos sobrantes de Streamlit */
    footer {visibility: hidden;}
    .stAppDeployButton {display:none !important;}
    header {visibility: hidden !important;}
    
    /* Variables de Color Corporativas */
    :root {
        --primary-navy: #0E2A47;
        --secondary-navy: #1A3E68;
        --gold-accent: #D4AF37;
        --bg-card: #FFFFFF;
        --border-color: #E2E8F0;
        --text-main: #1E293B;
        --text-sub: #64748B;
    }

    /* Fondo principal */
    .stApp {
        background-color: #F8FAFC;
    }

    /* Banner Superior */
    .header-banner {
        background: linear-gradient(135deg, #0E2A47 0%, #1A3E68 100%);
        padding: 24px 32px;
        border-radius: 12px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(14, 42, 71, 0.15);
        border-left: 6px solid #D4AF37;
    }
    .header-title {
        font-size: 26px;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin: 0;
        color: #FFFFFF;
    }
    .header-subtitle {
        font-size: 14px;
        color: #CBD5E1;
        margin-top: 4px;
        font-weight: 400;
    }

    /* Tarjetas KPI Personalizadas */
    .kpi-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px 6px;
        text-align: center;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s, box-shadow 0.2s;
        min-height: 95px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    .kpi-title {
        font-size: 9.5px;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.2px;
        margin-bottom: 4px;
        line-height: 1.2;
    }
    .kpi-value {
        font-size: 22px;
        font-weight: 800;
        color: #0E2A47;
    }

    /* Bordes coloridos por cada KPI */
    .b-blue { border-top: 4px solid #0E2A47; }
    .b-orange { border-top: 4px solid #F59E0B; }
    .b-green { border-top: 4px solid #10B981; }
    .b-purple { border-top: 4px solid #8B5CF6; }
    .b-red { border-top: 4px solid #EF4444; }
    .b-teal { border-top: 4px solid #14B8A6; }
    .b-indigo { border-top: 4px solid #6366F1; }
    .b-cyan { border-top: 4px solid #06B6D4; }
    .b-gold { border-top: 4px solid #D4AF37; }
    .b-pink { border-top: 4px solid #EC4899; }

    /* Estilizado de pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #F1F5F9;
        padding: 6px;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 38px;
        border-radius: 6px;
        font-size: 11.5px;
        font-weight: 600;
        color: #475569;
        padding: 0 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0E2A47 !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Tabla y data editor */
    .stDataFrame, div[data-testid="stDataEditor"] {
        background-color: #FFFFFF !important;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        padding: 4px;
    }

    /* Botones primarios */
    .stButton>button {
        background-color: #0E2A47;
        color: white;
        border-radius: 6px;
        font-weight: 600;
        border: none;
        padding: 8px 16px;
        transition: background-color 0.2s;
    }
    .stButton>button:hover {
        background-color: #1A3E68;
        color: white;
    }
    </style>
""",
    unsafe_allow_html=True,
)

DB_FILE = "database_informes.json"

COLUMNAS_EXCEL = [
    "ITEM POR MES",
    "IT2",
    "UNIDAD",
    "MES",
    "LINEAS",
    "CODIGO DE INFORME",
    "GRUPO DE TUBERÍAS",
    "SAP",
    "ALCANCE DEL SERVICIO",
    "ESTADO - ELABORACIÓN DE INFORME",
    "RESPONSABLE",
    "OBSERVACIÓN",
    "ESTADO - VALORIZACIÓN",
]

ORDEN_MESES = [
    "ENERO",
    "FEBRERO",
    "MARZO",
    "ABRIL",
    "MAYO",
    "JUNIO",
    "JULIO",
    "AGOSTO",
    "SETIEMBRE",
    "OCTUBRE",
    "NOVIEMBRE",
    "DICIEMBRE",
]


def texto_normalizado(texto):
    if pd.isna(texto):
        return ""
    t = str(texto).strip().upper()
    replacements = {
        "Á": "A",
        "É": "E",
        "Í": "I",
        "Ó": "O",
        "Ú": "U",
        "Ü": "U",
        "Ñ": "N",
        "Ã\x81": "A",
        "Ã\x89": "E",
        "Ã\x8d": "I",
        "Ã\x93": "O",
        "Ã\x9a": "U",
        "Ã\x91": "N",
    }
    for orig, repl in replacements.items():
        t = t.replace(orig, repl)
    return t


def limpiar_estado_y_responsable(df_input):
    df_clean = df_input.copy()
    for idx, row in df_clean.iterrows():
        val_estado = str(row["ESTADO - ELABORACIÓN DE INFORME"]).strip()
        val_resp = str(row["RESPONSABLE"]).strip()

        if "-" in val_estado:
            partes = val_estado.split("-", 1)
            estado_puro = partes[0].strip()
            persona = partes[1].strip()

            df_clean.at[idx, "ESTADO - ELABORACIÓN DE INFORME"] = estado_puro
            if val_resp in ["", "nan", "None"]:
                df_clean.at[idx, "RESPONSABLE"] = persona
    return df_clean


def es_codigo_provisional(codigo):
    t = texto_normalizado(codigo)
    if t in ["", "-"]:
        return True
    if any(
        p in t
        for p in ["PENDIENTE ASIGNAR", "PENDIENTE DE ASIGNAR", "POR ASIGNAR"]
    ):
        return True
    return False


def es_correccion_psaim(observacion):
    t = texto_normalizado(observacion)
    return "PSAIM" in t and any(
        word in t for word in ["CORRECCION", "CORREGIR", "CORREGIDO", "CORREGIDA"]
    )


def es_pendiente_inspeccion_fn(row):
    estado = texto_normalizado(row.get("ESTADO - ELABORACIÓN DE INFORME", ""))
    alcance = texto_normalizado(row.get("ALCANCE DEL SERVICIO", ""))
    obs = texto_normalizado(row.get("OBSERVACIÓN", ""))

    if (
        "PENDIENTE COMPLETAR INSPECCION" in estado
        or "PENDIENTE INSPECCION" in estado
    ):
        return True
    if "PENDIENTE INSPECCION" in alcance or "FALTA CARPETA" in alcance:
        return True
    if "COMPLETAR INSPECCION" in obs or "COMPLETAR INSPECCIÓN" in obs:
        return True

    return False


def cargar_datos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            df = pd.DataFrame(data)
            for col in COLUMNAS_EXCEL:
                if col not in df.columns:
                    df[col] = ""
            df = limpiar_estado_y_responsable(df)
            return df[COLUMNAS_EXCEL]
    else:
        df = pd.DataFrame(columns=COLUMNAS_EXCEL)
        guardar_datos(df)
        return df


def guardar_datos(df):
    df.to_json(DB_FILE, orient="records", force_ascii=False, indent=4)


if "df_data" not in st.session_state:
    st.session_state.df_data = cargar_datos()

df = st.session_state.df_data

# --- BANNER CORPORATIVO ---
st.markdown(
    """
    <div class="header-banner">
        <div class="header-title">CONTROL INTERNO DE INFORMES - ADEMINSAC</div>
        <div class="header-subtitle">Sistema de Monitoreo de Inspección Técnicas y Valorización | Refinería La Pampilla</div>
    </div>
""",
    unsafe_allow_html=True,
)

# --- SECCIÓN EN PANTALLA PRINCIPAL: GESTIÓN DE DATOS Y RESPALDOS ---
with st.expander(
    "⚙️ **Gestión de Datos: Cargar / Restaurar Excel & Descargar Respaldo**",
    expanded=False,
):
    col_carg, col_desc = st.columns(2)

    with col_carg:
        st.markdown("##### 📤 Cargar / Restaurar Base de Datos desde Excel")
        archivo_excel = st.file_uploader(
            "Seleccionar archivo Excel (.xlsx / .xlsm):",
            type=["xlsx", "xlsm"],
            key="uploader_main",
        )
        if archivo_excel is not None:
            if st.button("🔄 Reemplazar Base de Datos con este Excel"):
                try:
                    excel_file = pd.ExcelFile(archivo_excel)
                    hojas = excel_file.sheet_names
                    hoja_objetivo = "CONTROL" if "CONTROL" in hojas else hojas[0]

                    df_cargado = pd.read_excel(
                        excel_file, sheet_name=hoja_objetivo
                    )

                    mapeo = {}
                    for col_cargada in df_cargado.columns:
                        for col_real in COLUMNAS_EXCEL:
                            if (
                                str(col_cargada).strip().upper()
                                == col_real.upper()
                            ):
                                mapeo[col_cargada] = col_real
                    df_cargado = df_cargado.rename(columns=mapeo)

                    for col in COLUMNAS_EXCEL:
                        if col not in df_cargado.columns:
                            df_cargado[col] = ""

                    df_cargado = limpiar_estado_y_responsable(df_cargado)
                    st.session_state.df_data = df_cargado[COLUMNAS_EXCEL]
                    guardar_datos(st.session_state.df_data)
                    st.success(
                        "¡Base de datos cargada y guardada correctamente!"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al procesar el archivo Excel: {e}")

    with col_desc:
        st.markdown("##### 📥 Descargar Respaldo de Datos Actuales")
        if not df.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="CONTROL")
            buffer.seek(0)

            st.download_button(
                label="💾 Descargar Copia en Excel (.xlsx)",
                data=buffer,
                file_name="Respaldo_Control_Informes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

st.markdown("<br>", unsafe_allow_html=True)

if not df.empty:
    df_activos = df[
        df["OBSERVACIÓN"].apply(texto_normalizado) != "RETIRADO"
    ].copy()

    def generar_clave(row):
        mes = str(row["MES"]).strip()
        cod = str(row["CODIGO DE INFORME"]).strip()
        grupo = str(row["GRUPO DE TUBERÍAS"]).strip()
        if es_codigo_provisional(cod):
            return f"{mes}|SIN-CODIGO-GRUPO|{texto_normalizado(grupo)}"
        return f"{mes}|{cod}"

    df_activos["CLAVE_GLOBAL"] = df_activos.apply(generar_clave, axis=1)

    mask_psaim = df_activos["OBSERVACIÓN"].apply(es_correccion_psaim)
    mask_pend_insp = df_activos.apply(es_pendiente_inspeccion_fn, axis=1)

    # Identificación de informes pendientes de asignación
    mask_pend_elab = df_activos[
        "ESTADO - ELABORACIÓN DE INFORME"
    ].apply(texto_normalizado).str.contains("PENDIENTE ELABORACION")

    df_psaim_det = df_activos[mask_psaim]
    df_pend_inspeccion = df_activos[mask_pend_insp]
    df_pend_asignacion = df_activos[mask_pend_elab]

    df_en_proceso = df_activos[
        df_activos["ESTADO - ELABORACIÓN DE INFORME"]
        .apply(texto_normalizado)
        .str.contains("EN PROCESO")
        & ~mask_pend_insp
    ]

    cnt_en_proceso = df_en_proceso["CLAVE_GLOBAL"].nunique()
    cnt_pend_inspeccion = df_pend_inspeccion["CLAVE_GLOBAL"].nunique()
    cnt_pend_asignacion = df_pend_asignacion["CLAVE_GLOBAL"].nunique()

    dict_unicos = {}
    dict_psaim_unicos = set()
    dict_t3_val, dict_t3_pen = {}, {}
    dict_t3_ademinsac, dict_t3_fiabilidad, dict_t3_psaim = {}, {}, {}
    dict_t4, dict_t5 = {}, {}

    cnt_revision_fiabilidad = 0
    cnt_pend_revision_especialista = 0
    cnt_revision_por_especialista = 0

    for _, row in df_activos.iterrows():
        mes = str(row["MES"]).strip()
        cod = str(row["CODIGO DE INFORME"]).strip()
        grupo = str(row["GRUPO DE TUBERÍAS"]).strip()
        obs = (
            str(row["OBSERVACIÓN"]).strip()
            if pd.notna(row["OBSERVACIÓN"])
            else ""
        )
        estado_val = texto_normalizado(row["ESTADO - VALORIZACIÓN"])
        clave_global = row["CLAVE_GLOBAL"]

        if mes != "" and grupo != "":
            if not es_codigo_provisional(cod) and es_correccion_psaim(obs):
                clave_psaim = f"{mes}|{cod}"
                if clave_psaim not in dict_psaim_unicos:
                    dict_psaim_unicos.add(clave_psaim)
                    dict_t3_psaim[mes] = dict_t3_psaim.get(mes, 0) + 1

            if clave_global not in dict_unicos:
                dict_unicos[clave_global] = True

                dict_t3_val.setdefault(mes, 0)
                dict_t3_pen.setdefault(mes, 0)
                dict_t3_ademinsac.setdefault(mes, 0)
                dict_t3_fiabilidad.setdefault(mes, 0)

                obs_norm = texto_normalizado(obs)

                if estado_val == "SI":
                    dict_t3_val[mes] += 1
                else:
                    dict_t3_pen[mes] += 1

                    if (
                        "INFORME (CARTA) ENTREGADO PARA SU REVISION - FIABILIDAD"
                        in obs_norm
                        or (
                            "ENTREGADO PARA SU REVISION" in obs_norm
                            and "FIABILIDAD" in obs_norm
                        )
                    ):
                        cnt_revision_fiabilidad += 1

                    if "PENDIENTE REVISION POR EL ESPECIALISTA" in obs_norm:
                        cnt_pend_revision_especialista += 1

                    if ("REV. POR EL ESPECIALISTA" in obs_norm or "REVISION POR EL ESPECIALISTA" in obs_norm) and "PENDIENTE" not in obs_norm:
                        cnt_revision_por_especialista += 1

                    if "ADEMINSAC" in obs_norm:
                        dict_t3_ademinsac[mes] += 1
                    else:
                        dict_t3_fiabilidad[mes] += 1

                    obs_key = "(En blanco)" if obs == "" else obs
                    dict_t4[f"{mes}|{obs_key}"] = (
                        dict_t4.get(f"{mes}|{obs_key}", 0) + 1
                    )
                    dict_t5[obs_key] = dict_t5.get(obs_key, 0) + 1

    tot_informes = len(dict_unicos)
    tot_val = sum(dict_t3_val.values())
    tot_pen = sum(dict_t3_pen.values())

    # --- TARJETAS KPI REDISEÑADAS EN 10 COLUMNAS ---
    k1, k2, k3, k4, k5, k6, k7, k8, k9, k10 = st.columns(10)

    kpis = [
        (k1, "INFORMES TOTALES", tot_informes, "b-blue"),
        (k2, "PENDIENTES TOTAL", tot_pen, "b-orange"),
        (k3, "VALORIZADOS (SI)", tot_val, "b-green"),
        (k4, "PEND. ASIGNAR INFORME", cnt_pend_asignacion, "b-pink"),
        (k5, "EN PROCESO", cnt_en_proceso, "b-purple"),
        (k6, "PEND. INSPECCIÓN", cnt_pend_inspeccion, "b-red"),
        (k7, "REV. FIABILIDAD", cnt_revision_fiabilidad, "b-teal"),
        (k8, "PEND. REV. DEL ESPECIALISTA", cnt_pend_revision_especialista, "b-indigo"),
        (k9, "REV. POR EL ESPECIALISTA", cnt_revision_por_especialista, "b-cyan"),
        (k10, "CORRECCIÓN PSAIM", sum(dict_t3_psaim.values()), "b-gold"),
    ]

    for col, titulo, valor, clase_borde in kpis:
        col.markdown(
            f"""
            <div class="kpi-card {clase_borde}">
                <div class="kpi-title">{titulo}</div>
                <div class="kpi-value">{valor}</div>
            </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    (
        tab_general,
        tab_pend_asignacion,
        tab_en_proceso,
        tab_pend_insp,
        tab_rev_fiabilidad,
        tab_pend_rev_especialista,
        tab_rev_por_especialista,
        tab_psaim,
        tab_t3,
        tab_t4,
        tab_t5,
    ) = st.tabs(
        [
            "📋 Tabla General",
            "📋 Pend. Asignar Informe",
            "🔄 En Proceso",
            "⏳ Pend. Inspección",
            "🔍 Rev. Fiabilidad",
            "👨‍🔬 Pend. Rev. Especialista",
            "🔬 Rev. por Especialista",
            "🛠️ Correc. PSAIM",
            "📅 Resumen Mes (T3)",
            "📊 Pend. Mes/Obs (T4)",
            "📌 Resumen Obs (T5)",
        ]
    )

    # 1. TABLA GENERAL CON BUSCADOR DINÁMICO
    with tab_general:
        st.markdown("#### **TABLA GENERAL DE CONTROL DE INFORMES**")

        busqueda_txt = st.text_input(
            "🔍 Buscador Dinámico (Filtra por Línea, SAP, Código de Informe o Grupo de Tuberías):",
            value="",
            help="Ingresa una línea o SAP para ver la fila exacta, o un Código de Informe / Grupo para listar todas las líneas asociadas.",
        )

        df_general_display = df[COLUMNAS_EXCEL].copy()

        if busqueda_txt.strip():
            query_norm = texto_normalizado(busqueda_txt)

            mask_lineas = df_general_display["LINEAS"].apply(texto_normalizado).str.contains(query_norm)
            mask_sap = df_general_display["SAP"].apply(texto_normalizado).str.contains(query_norm)
            mask_cod = df_general_display["CODIGO DE INFORME"].apply(texto_normalizado).str.contains(query_norm)
            mask_grupo = df_general_display["GRUPO DE TUBERÍAS"].apply(texto_normalizado).str.contains(query_norm)

            codigos_coincidentes = df_general_display[mask_cod]["CODIGO DE INFORME"].unique()
            grupos_coincidentes = df_general_display[mask_grupo]["GRUPO DE TUBERÍAS"].unique()

            mask_relacional = (
                mask_lineas
                | mask_sap
                | df_general_display["CODIGO DE INFORME"].isin(codigos_coincidentes)
                | df_general_display["GRUPO DE TUBERÍAS"].isin(grupos_coincidentes)
            )

            df_general_display = df_general_display[mask_relacional]

        edited_df = st.data_editor(
            df_general_display,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_general",
            column_config={
                "OBSERVACIÓN": st.column_config.TextColumn(
                    "OBSERVACIÓN",
                    help="Detalle amplio de las observaciones del informe",
                    width="large",
                )
            },
        )
        if st.button("💾 Guardar Cambios"):
            df_actualizado = df.copy()
            df_actualizado.update(edited_df)
            
            cleaned_df = limpiar_estado_y_responsable(df_actualizado[COLUMNAS_EXCEL])
            st.session_state.df_data = cleaned_df
            guardar_datos(cleaned_df)
            st.success("¡Datos guardados y actualizados correctamente!")
            st.rerun()

    # 2. INFORMES PENDIENTES DE ASIGNACIÓN DE ENCARGADO
    with tab_pend_asignacion:
        st.markdown("#### **DETALLE DE INFORMES PENDIENTES DE ASIGNAR INFORME**")
        if not df_pend_asignacion.empty:
            df_asig_grouped = df_pend_asignacion.copy()
            df_asig_grouped["CANT. LÍNEAS"] = 1
            tabla_asig = (
                df_asig_grouped.groupby(
                    [
                        "MES",
                        "ESTADO - ELABORACIÓN DE INFORME",
                        "RESPONSABLE",
                        "GRUPO DE TUBERÍAS",
                        "CODIGO DE INFORME",
                    ],
                    as_index=False,
                )
                .agg({"CANT. LÍNEAS": "count"})
                .rename(
                    columns={
                        "ESTADO - ELABORACIÓN DE INFORME": "ESTADO INFORME",
                        "GRUPO DE TUBERÍAS": "GRUPO DE TUBERIAS",
                        "CODIGO DE INFORME": "CODIGO(S) DE INFORME",
                    }
                )
            )
            tabla_asig["MES_CAT"] = pd.Categorical(
                tabla_asig["MES"].str.upper(),
                categories=ORDEN_MESES,
                ordered=True,
            )
            tabla_asig = tabla_asig.sort_values("MES_CAT").drop(
                columns=["MES_CAT"]
            )
            st.dataframe(tabla_asig, use_container_width=True)
        else:
            st.info("No hay informes pendientes a la espera de asignar encargado.")

    # 3. INFORMES EN PROCESO
    with tab_en_proceso:
        st.markdown("#### **DETALLE DE INFORMES EN PROCESO**")
        if not df_en_proceso.empty:
            df_proceso_grouped = df_en_proceso.copy()
            df_proceso_grouped["CANT. LÍNEAS"] = 1
            tabla_proceso = (
                df_proceso_grouped.groupby(
                    [
                        "MES",
                        "ESTADO - ELABORACIÓN DE INFORME",
                        "RESPONSABLE",
                        "GRUPO DE TUBERÍAS",
                        "CODIGO DE INFORME",
                    ],
                    as_index=False,
                )
                .agg({"CANT. LÍNEAS": "count"})
                .rename(
                    columns={
                        "ESTADO - ELABORACIÓN DE INFORME": "ESTADO INFORME",
                        "GRUPO DE TUBERÍAS": "GRUPO DE TUBERIAS",
                        "CODIGO DE INFORME": "CODIGO(S) DE INFORME",
                    }
                )
            )
            tabla_proceso["MES_CAT"] = pd.Categorical(
                tabla_proceso["MES"].str.upper(),
                categories=ORDEN_MESES,
                ordered=True,
            )
            tabla_proceso = tabla_proceso.sort_values("MES_CAT").drop(
                columns=["MES_CAT"]
            )
            st.dataframe(tabla_proceso, use_container_width=True)
        else:
            st.info("No hay informes registrados en proceso.")

    # 4. INFORMES PENDIENTES DE COMPLETAR INSPECCIÓN
    with tab_pend_insp:
        st.markdown(
            "#### **DETALLE DE INFORMES PENDIENTES COMPLETAR INSPECCIÓN**"
        )
        if not df_pend_inspeccion.empty:
            df_insp_grouped = df_pend_inspeccion.copy()
            df_insp_grouped["CANT. LÍNEAS"] = 1
            tabla_insp = (
                df_insp_grouped.groupby(
                    [
                        "MES",
                        "ESTADO - ELABORACIÓN DE INFORME",
                        "RESPONSABLE",
                        "GRUPO DE TUBERÍAS",
                        "CODIGO DE INFORME",
                    ],
                    as_index=False,
                )
                .agg({"CANT. LÍNEAS": "count"})
                .rename(
                    columns={
                        "ESTADO - ELABORACIÓN DE INFORME": "ESTADO INFORME",
                        "GRUPO DE TUBERÍAS": "GRUPO DE TUBERIAS",
                        "CODIGO DE INFORME": "CODIGO(S) DE INFORME",
                    }
                )
            )
            tabla_insp["MES_CAT"] = pd.Categorical(
                tabla_insp["MES"].str.upper(),
                categories=ORDEN_MESES,
                ordered=True,
            )
            tabla_insp = tabla_insp.sort_values("MES_CAT").drop(
                columns=["MES_CAT"]
            )
            st.dataframe(tabla_insp, use_container_width=True)
        else:
            st.info("No hay informes pendientes de completar inspección.")

    # 5. REVISIÓN FIABILIDAD
    with tab_rev_fiabilidad:
        st.markdown("#### **DETALLE DE INFORMES EN REVISIÓN FIABILIDAD**")
        df_fiab = df_activos[
            df_activos["OBSERVACIÓN"].apply(
                lambda x: "ENTREGADO PARA SU REVISION" in texto_normalizado(x)
                and "FIABILIDAD" in texto_normalizado(x)
            )
        ].copy()

        if not df_fiab.empty:
            df_fiab["CANT. LÍNEAS"] = 1
            tabla_fiab = df_fiab.groupby(
                [
                    "MES",
                    "ESTADO - ELABORACIÓN DE INFORME",
                    "RESPONSABLE",
                    "GRUPO DE TUBERÍAS",
                    "CODIGO DE INFORME",
                    "OBSERVACIÓN",
                ],
                as_index=False,
            ).agg({"CANT. LÍNEAS": "count"})
            st.dataframe(tabla_fiab, use_container_width=True)
        else:
            st.info("No hay informes registrados en revisión por fiabilidad.")

    # 6. PENDIENTE REVISIÓN ESPECIALISTA
    with tab_pend_rev_especialista:
        st.markdown(
            "#### **DETALLE DE INFORMES PENDIENTES REVISIÓN DEL ESPECIALISTA**"
        )
        df_esp = df_activos[
            df_activos["OBSERVACIÓN"].apply(
                lambda x: "PENDIENTE REVISION POR EL ESPECIALISTA"
                in texto_normalizado(x)
            )
        ].copy()

        if not df_esp.empty:
            df_esp["CANT. LÍNEAS"] = 1
            tabla_esp = df_esp.groupby(
                [
                    "MES",
                    "ESTADO - ELABORACIÓN DE INFORME",
                    "RESPONSABLE",
                    "GRUPO DE TUBERÍAS",
                    "CODIGO DE INFORME",
                    "OBSERVACIÓN",
                ],
                as_index=False,
            ).agg({"CANT. LÍNEAS": "count"})
            st.dataframe(tabla_esp, use_container_width=True)
        else:
            st.info(
                "No hay informes registrados pendientes de revisión por el"
                " especialista."
            )

    # 7. REVISIÓN POR EL ESPECIALISTA
    with tab_rev_por_especialista:
        st.markdown(
            "#### **DETALLE DE INFORMES EN REVISIÓN POR EL ESPECIALISTA**"
        )
        df_rev_esp = df_activos[
            df_activos["OBSERVACIÓN"].apply(
                lambda x: ("REV. POR EL ESPECIALISTA" in texto_normalizado(x) or "REVISION POR EL ESPECIALISTA" in texto_normalizado(x))
                and "PENDIENTE" not in texto_normalizado(x)
            )
        ].copy()

        if not df_rev_esp.empty:
            df_rev_esp["CANT. LÍNEAS"] = 1
            tabla_rev_esp = df_rev_esp.groupby(
                [
                    "MES",
                    "ESTADO - ELABORACIÓN DE INFORME",
                    "RESPONSABLE",
                    "GRUPO DE TUBERÍAS",
                    "CODIGO DE INFORME",
                    "OBSERVACIÓN",
                ],
                as_index=False,
            ).agg({"CANT. LÍNEAS": "count"})
            st.dataframe(tabla_rev_esp, use_container_width=True)
        else:
            st.info(
                "No hay informes registrados con la observación de revisión por el especialista."
            )

    # 8. CORRECCIÓN PSAIM
    with tab_psaim:
        st.markdown("#### **DETALLE DE INFORMES EN CORRECCIÓN PSAIM**")
        if not df_psaim_det.empty:
            df_psaim_grouped = df_psaim_det.copy()
            df_psaim_grouped["CANT. LÍNEAS"] = 1
            tabla_psaim = df_psaim_grouped.groupby(
                [
                    "MES",
                    "ESTADO - ELABORACIÓN DE INFORME",
                    "RESPONSABLE",
                    "GRUPO DE TUBERÍAS",
                    "CODIGO DE INFORME",
                    "OBSERVACIÓN",
                ],
                as_index=False,
            ).agg({"CANT. LÍNEAS": "count"})
            st.dataframe(tabla_psaim, use_container_width=True)
        else:
            st.info("No hay informes registrados en corrección PSAIM.")

    # 9. TABLA 3: RESUMEN POR MES
    with tab_t3:
        st.markdown("#### **RESUMEN DE VALORIZACIÓN POR MES**")
        meses_unicos = list(
            set(list(dict_t3_val.keys()) + list(dict_t3_pen.keys()))
        )
        filas_t3 = []
        for m in meses_unicos:
            v_val = dict_t3_val.get(m, 0)
            v_pen = dict_t3_pen.get(m, 0)
            grupos_mes = df_activos[
                df_activos["MES"].astype(str).str.strip() == m
            ]["GRUPO DE TUBERÍAS"].nunique()
            filas_t3.append(
                {
                    "MES": m,
                    "GRUPOS": grupos_mes,
                    "VALORIZADOS": v_val,
                    "PENDIENTE VALORIZAR": v_pen,
                    "SUMA TOTAL": v_val + v_pen,
                    "PENDIENTE POR ADEMINSAC": dict_t3_ademinsac.get(m, 0),
                    "PENDIENTE POR FIABILIDAD": dict_t3_fiabilidad.get(m, 0),
                    "INFORMES CON CORRECCION PSAIM": dict_t3_psaim.get(m, 0),
                }
            )

        df_t3 = pd.DataFrame(filas_t3)
        if not df_t3.empty:
            df_t3["MES_CAT"] = pd.Categorical(
                df_t3["MES"].str.upper(), categories=ORDEN_MESES, ordered=True
            )
            df_t3 = df_t3.sort_values("MES_CAT").drop(columns=["MES_CAT"])
            tot_row = pd.DataFrame(
                [
                    {
                        "MES": "TOTAL GENERAL",
                        "GRUPOS": df_t3["GRUPOS"].sum(),
                        "VALORIZADOS": df_t3["VALORIZADOS"].sum(),
                        "PENDIENTE VALORIZAR": df_t3[
                            "PENDIENTE VALORIZAR"
                        ].sum(),
                        "SUMA TOTAL": df_t3["SUMA TOTAL"].sum(),
                        "PENDIENTE POR ADEMINSAC": df_t3[
                            "PENDIENTE POR ADEMINSAC"
                        ].sum(),
                        "PENDIENTE POR FIABILIDAD": df_t3[
                            "PENDIENTE POR FIABILIDAD"
                        ].sum(),
                        "INFORMES CON CORRECCION PSAIM": df_t3[
                            "INFORMES CON CORRECCION PSAIM"
                        ].sum(),
                    }
                ]
            )
            st.dataframe(
                pd.concat([df_t3, tot_row], ignore_index=True),
                use_container_width=True,
            )

    # 10. TABLA 4: PENDIENTES POR MES Y OBSERVACIÓN
    with tab_t4:
        st.markdown("#### **DETALLE DE PENDIENTES POR MES Y OBSERVACIÓN**")
        filas_t4 = [
            {
                "MES": k.split("|", 1)[0],
                "OBSERVACIÓN PENDIENTE": k.split("|", 1)[1],
                "CANTIDAD": v,
            }
            for k, v in dict_t4.items()
        ]
        df_t4 = pd.DataFrame(filas_t4)
        if not df_t4.empty:
            df_t4["MES_CAT"] = pd.Categorical(
                df_t4["MES"].str.upper(), categories=ORDEN_MESES, ordered=True
            )
            df_t4 = df_t4.sort_values(
                ["MES_CAT", "CANTIDAD"], ascending=[True, False]
            ).drop(columns=["MES_CAT"])
            st.dataframe(df_t4, use_container_width=True)

    # 11. TABLA 5: RESUMEN GENERAL DE OBSERVACIONES
    with tab_t5:
        st.markdown("#### **RESUMEN GENERAL DE OBSERVACIONES PENDIENTES**")
        filas_t5 = [
            {
                "OBSERVACIÓN PENDIENTE": k,
                "CANTIDAD TOTAL": v,
                "RESPONSABLE": (
                    "ADEMINSAC"
                    if "ADEMINSAC" in texto_normalizado(k)
                    else "FIABILIDAD"
                ),
            }
            for k, v in dict_t5.items()
        ]
        df_t5 = pd.DataFrame(filas_t5)
        if not df_t5.empty:
            st.dataframe(
                df_t5.sort_values("CANTIDAD TOTAL", ascending=False),
                use_container_width=True,
            )

else:
    st.info(
        "Haga clic en la sección superior '⚙️ Gestión de Datos' para cargar un"
        " archivo Excel o iniciar la base de datos."
    )
