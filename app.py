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
    footer {visibility: hidden;}
    .stAppDeployButton {display:none !important;}
    header {visibility: hidden !important;}
    
    :root {
        --primary-navy: #0E2A47;
        --secondary-navy: #1A3E68;
        --gold-accent: #D4AF37;
        --bg-card: #FFFFFF;
        --border-color: #E2E8F0;
        --text-main: #1E293B;
        --text-sub: #64748B;
    }

    .stApp { background-color: #F8FAFC; }

    .header-banner {
        background: linear-gradient(135deg, #0E2A47 0%, #1A3E68 100%);
        padding: 24px 32px;
        border-radius: 12px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(14, 42, 71, 0.15);
        border-left: 6px solid #D4AF37;
    }
    .header-title { font-size: 26px; font-weight: 700; letter-spacing: 0.5px; margin: 0; color: #FFFFFF; }
    .header-subtitle { font-size: 14px; color: #CBD5E1; margin-top: 4px; font-weight: 400; }

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
        align-items: center;
    }
    .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); }
    .kpi-title { font-size: 9.5px; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.2px; margin-bottom: 4px; line-height: 1.2; }
    .kpi-value { font-size: 22px; font-weight: 800; color: #0E2A47; }

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

    .stTabs [data-baseweb="tab-list"] { gap: 4px; background-color: #F1F5F9; padding: 6px; border-radius: 8px; }
    .stTabs [data-baseweb="tab"] { height: 38px; border-radius: 6px; font-size: 11.5px; font-weight: 600; color: #475569; padding: 0 10px; }
    .stTabs [aria-selected="true"] { background-color: #0E2A47 !important; color: #FFFFFF !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .stDataFrame, div[data-testid="stDataEditor"] { background-color: #FFFFFF !important; border-radius: 8px; border: 1px solid #E2E8F0; padding: 4px; }
    </style>
""",
    unsafe_allow_html=True,
)

DB_FILE = "database_informes.json"
SOLICITUDES_FILE = "database_solicitudes.json"

COLUMNAS_EXCEL = [
    "ITEM POR MES", "IT2", "UNIDAD", "MES", "LINEAS", "CODIGO DE INFORME",
    "GRUPO DE TUBERÍAS", "SAP", "ALCANCE DEL SERVICIO",
    "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "OBSERVACIÓN", "ESTADO - VALORIZACIÓN"
]

ORDEN_MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SETIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]

ESPECIALISTAS_LISTA = ["Jesús Rehkoff Díaz", "M. Paifa", "Julio Ponce", "Omar", "Christopher", "Timana", "Ingrid"]
REVISORES_PSAIM_LISTA = ["Franmary Gutierrez", "Alejandro Macury", "M. Paifa", "Julio Ponce", "Omar", "Christopher", "Timana", "Ingrid"]
PERSONAL_LISTA_BASE = ["M. Paifa", "Julio Ponce", "Omar", "Christopher", "Timana", "Ingrid", "Juan José", "Dante", "Jesús Rehkoff Díaz", "Franmary Gutierrez", "Alejandro Macury", "Otro Inspector"]

def formatear_entero_limpio(valor):
    if pd.isna(valor) or valor is None:
        return ""
    val_str = str(valor).strip()
    if val_str.endswith(".0"):
        return val_str[:-2]
    return val_str

def texto_normalizado(texto):
    if pd.isna(texto): return ""
    t = str(texto).strip().upper()
    replacements = {"Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ü": "U", "Ñ": "N"}
    for orig, repl in replacements.items(): t = t.replace(orig, repl)
    return t

def limpiar_estado_y_responsable(df_input):
    df_clean = df_input.copy()
    for col in ["ITEM POR MES", "IT2", "SAP"]:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(object)

    for idx, row in df_clean.iterrows():
        val_estado = str(row["ESTADO - ELABORACIÓN DE INFORME"]).strip()
        val_resp = str(row["RESPONSABLE"]).strip()
        if "-" in val_estado:
            partes = val_estado.split("-", 1)
            df_clean.at[idx, "ESTADO - ELABORACIÓN DE INFORME"] = partes[0].strip()
            if val_resp in ["", "nan", "None"]:
                df_clean.at[idx, "RESPONSABLE"] = partes[1].strip()
        
        df_clean.at[idx, "ITEM POR MES"] = formatear_entero_limpio(row["ITEM POR MES"])
        df_clean.at[idx, "IT2"] = formatear_entero_limpio(row["IT2"])
        df_clean.at[idx, "SAP"] = formatear_entero_limpio(row["SAP"])
        
    return df_clean

def es_codigo_provisional(codigo):
    t = texto_normalizado(codigo)
    return t in ["", "-"] or any(p in t for p in ["PENDIENTE ASIGNAR", "PENDIENTE DE ASIGNAR", "POR ASIGNAR"])

def es_correccion_psaim(observacion):
    t = texto_normalizado(observacion)
    return "PSAIM" in t and any(word in t for word in ["CORRECCION", "CORREGIR", "CORREGIDO", "CORREGIDA"])

def es_pendiente_inspeccion_fn(row):
    estado = texto_normalizado(row.get("ESTADO - ELABORACIÓN DE INFORME", ""))
    alcance = texto_normalizado(row.get("ALCANCE DEL SERVICIO", ""))
    obs = texto_normalizado(row.get("OBSERVACIÓN", ""))
    return ("PENDIENTE COMPLETAR INSPECCION" in estado or "PENDIENTE INSPECCION" in estado or
            "PENDIENTE INSPECCION" in alcance or "FALTA CARPETA" in alcance or
            "COMPLETAR INSPECCION" in obs or "COMPLETAR INSPECCIÓN" in obs)

def preparar_tabla_con_indice_1(df_input):
    if df_input.empty:
        return df_input
    df_res = df_input.reset_index(drop=True)
    df_res.index = range(1, len(df_res) + 1)
    return df_res

def cargar_datos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            df = pd.DataFrame(json.load(f))
            for col in COLUMNAS_EXCEL:
                if col not in df.columns: df[col] = ""
            return limpiar_estado_y_responsable(df)[COLUMNAS_EXCEL]
    else:
        df = pd.DataFrame(columns=COLUMNAS_EXCEL)
        guardar_datos(df)
        return df

def guardar_datos(df):
    df.to_json(DB_FILE, orient="records", force_ascii=False, indent=4)

def cargar_solicitudes():
    if os.path.exists(SOLICITUDES_FILE):
        with open(SOLICITUDES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_solicitudes(solicitudes):
    with open(SOLICITUDES_FILE, "w", encoding="utf-8") as f:
        json.dump(solicitudes, f, ensure_ascii=False, indent=4)

def registrar_solicitud(tipo, codigo, grupo, solicitante):
    solicitudes = cargar_solicitudes()
    for s in solicitudes:
        if s["codigo"] == codigo and s["grupo"] == grupo and s["tipo"] == tipo and s["estado"] == "PENDIENTE":
            return False, "Ya existe una solicitud pendiente de aprobación para este informe."
    solicitudes.append({"id": len(solicitudes) + 1, "tipo": tipo, "codigo": codigo, "grupo": grupo, "solicitante": solicitante, "estado": "PENDIENTE"})
    guardar_solicitudes(solicitudes)
    return True, "Solicitud enviada con éxito al Administrador."

if "df_data" not in st.session_state:
    st.session_state.df_data = cargar_datos()

df = st.session_state.df_data

resp_unicos = [str(r).strip() for r in df["RESPONSABLE"].unique() if pd.notna(r) and str(r).strip() not in ["", "nan", "None"]]
PERSONAL_LISTA = sorted(list(set(PERSONAL_LISTA_BASE + resp_unicos)))

st.markdown("""
    <div class="header-banner">
        <div class="header-title">CONTROL INTERNO DE INFORMES - ADEMINSAC</div>
        <div class="header-subtitle">Sistema de Monitoreo de Inspección Técnicas y Valorización | Refinería La Pampilla</div>
    </div>
""", unsafe_allow_html=True)

with st.expander("⚙️ **Gestión de Datos: Cargar / Restaurar Excel & Descargar Respaldo**", expanded=False):
    col_carg, col_desc = st.columns(2)
    with col_carg:
        st.markdown("##### 📤 Cargar Base de Datos desde Excel")
        archivo_excel = st.file_uploader("Seleccionar archivo Excel:", type=["xlsx", "xlsm"], key="uploader_main")
        if archivo_excel and st.button("🔄 Reemplazar Base de Datos"):
            try:
                excel_file = pd.ExcelFile(archivo_excel)
                hoja = "CONTROL" if "CONTROL" in excel_file.sheet_names else excel_file.sheet_names[0]
                df_cargado = pd.read_excel(excel_file, sheet_name=hoja)
                mapeo = {c: r for c in df_cargado.columns for r in COLUMNAS_EXCEL if str(c).strip().upper() == r.upper()}
                df_cargado = df_cargado.rename(columns=mapeo)
                for col in COLUMNAS_EXCEL:
                    if col not in df_cargado.columns: df_cargado[col] = ""
                st.session_state.df_data = limpiar_estado_y_responsable(df_cargado)[COLUMNAS_EXCEL]
                guardar_datos(st.session_state.df_data)
                st.success("¡Base de datos cargada correctamente!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    with col_desc:
        st.markdown("##### 📥 Descargar Respaldo Actual")
        if not df.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="CONTROL")
            buffer.seek(0)
            st.download_button("💾 Descargar Copia en Excel (.xlsx)", buffer, "Respaldo_Control_Informes.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if not df.empty:
    df_activos = df[df["OBSERVACIÓN"].apply(texto_normalizado) != "RETIRADO"].copy()
    df_activos["CLAVE_GLOBAL"] = df_activos.apply(lambda r: f"{str(r['MES']).strip()}|SIN-CODIGO-GRUPO|{texto_normalizado(r['GRUPO DE TUBERÍAS'])}" if es_codigo_provisional(r["CODIGO DE INFORME"]) else f"{str(r['MES']).strip()}|{str(r['CODIGO DE INFORME']).strip()}", axis=1)

    mask_psaim = df_activos["OBSERVACIÓN"].apply(es_correccion_psaim)
    mask_pend_insp = df_activos.apply(es_pendiente_inspeccion_fn, axis=1)
    mask_pend_elab = df_activos["ESTADO - ELABORACIÓN DE INFORME"].apply(texto_normalizado).str.contains("PENDIENTE ELABORACION")

    df_psaim_det = df_activos[mask_psaim]
    df_pend_inspeccion = df_activos[mask_pend_insp]
    df_pend_asignacion = df_activos[mask_pend_elab]
    df_en_proceso = df_activos[df_activos["ESTADO - ELABORACIÓN DE INFORME"].apply(texto_normalizado).str.contains("EN PROCESO") & ~mask_pend_insp]

    dict_unicos, dict_psaim_unicos = {}, set()
    dict_t3_val, dict_t3_pen, dict_t3_ademinsac, dict_t3_fiabilidad, dict_t3_psaim = {}, {}, {}, {}, {}
    dict_t4, dict_t5 = {}, {}
    cnt_revision_fiabilidad, cnt_pend_revision_especialista, cnt_revision_por_especialista = 0, 0, 0

    for _, row in df_activos.iterrows():
        mes, cod, grupo = str(row["MES"]).strip(), str(row["CODIGO DE INFORME"]).strip(), str(row["GRUPO DE TUBERÍAS"]).strip()
        obs = str(row["OBSERVACIÓN"]).strip() if pd.notna(row["OBSERVACIÓN"]) else ""
        estado_val, clave_global = texto_normalizado(row["ESTADO - VALORIZACIÓN"]), row["CLAVE_GLOBAL"]

        if mes and grupo:
            if not es_codigo_provisional(cod) and es_correccion_psaim(obs):
                if f"{mes}|{cod}" not in dict_psaim_unicos:
                    dict_psaim_unicos.add(f"{mes}|{cod}")
                    dict_t3_psaim[mes] = dict_t3_psaim.get(mes, 0) + 1

            if clave_global not in dict_unicos:
                dict_unicos[clave_global] = True
                dict_t3_val.setdefault(mes, 0); dict_t3_pen.setdefault(mes, 0)
                dict_t3_ademinsac.setdefault(mes, 0); dict_t3_fiabilidad.setdefault(mes, 0)
                obs_norm = texto_normalizado(obs)

                if estado_val == "SI":
                    dict_t3_val[mes] += 1
                else:
                    dict_t3_pen[mes] += 1
                    if "ENTREGADO PARA SU REVISION" in obs_norm and "FIABILIDAD" in obs_norm: cnt_revision_fiabilidad += 1
                    if "PENDIENTE REVISION POR EL ESPECIALISTA" in obs_norm: cnt_pend_revision_especialista += 1
                    if ("REV. POR EL ESPECIALISTA" in obs_norm or "REVISION POR EL ESPECIALISTA" in obs_norm) and "PENDIENTE" not in obs_norm: cnt_revision_por_especialista += 1
                    if "ADEMINSAC" in obs_norm: dict_t3_ademinsac[mes] += 1
                    else: dict_t3_fiabilidad[mes] += 1
                    
                    obs_key = "(En blanco)" if obs == "" else obs
                    dict_t4[f"{mes}|{obs_key}"] = dict_t4.get(f"{mes}|{obs_key}", 0) + 1
                    dict_t5[obs_key] = dict_t5.get(obs_key, 0) + 1

    k1, k2, k3, k4, k5, k6, k7, k8, k9, k10 = st.columns(10)
    kpis = [
        (k1, "INFORMES TOTALES", len(dict_unicos), "b-blue"),
        (k2, "PENDIENTES TOTAL", sum(dict_t3_pen.values()), "b-orange"),
        (k3, "VALORIZADOS (SI)", sum(dict_t3_val.values()), "b-green"),
        (k4, "PEND. ASIGNAR INFORME", df_pend_asignacion["CLAVE_GLOBAL"].nunique(), "b-pink"),
        (k5, "EN PROCESO", df_en_proceso["CLAVE_GLOBAL"].nunique(), "b-purple"),
        (k6, "PEND. INSPECCIÓN", df_pend_inspeccion["CLAVE_GLOBAL"].nunique(), "b-red"),
        (k7, "REV. FIABILIDAD", cnt_revision_fiabilidad, "b-teal"),
        (k8, "PEND. REV. ESPECIALISTA", cnt_pend_revision_especialista, "b-indigo"),
        (k9, "REV. POR ESPECIALISTA", cnt_revision_por_especialista, "b-cyan"),
        (k10, "CORRECCIÓN PSAIM", sum(dict_t3_psaim.values()), "b-gold")
    ]
    for col, titulo, valor, clase in kpis:
        col.markdown(f'<div class="kpi-card {clase}"><div class="kpi-title">{titulo}</div><div class="kpi-value">{valor}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    solic_activas = [s for s in cargar_solicitudes() if s["estado"] == "PENDIENTE"]
    # --- PESTAÑAS DE NAVEGACIÓN ---
    t_gen, t_reg, t_sol, t_res, t_adm = st.tabs([
        "📋 TABLA GENERAL",
        "📝 REGISTRAR NUEVO INFORME",
        "📩 SOLICITUDES DE APROBACIÓN",
        "📊 RESUMEN EJECUTIVO",
        "⚙️ ADMINISTRACIÓN"
    ])

    # ==========================================
    # PESTAÑA 1: TABLA GENERAL
    # ==========================================
    with t_gen:
        # --- FRANJA SUPERIOR: FILTROS Y BUSCADOR COMPLETO ---
        c_m, c_b, c_sw = st.columns([1, 3, 1])
        
        meses_disp = ["Todos"] + sorted(
            [m for m in df["MES"].dropna().astype(str).str.strip().str.upper().unique() if m],
            key=lambda x: ORDEN_MESES.index(x) if x in ORDEN_MESES else 99
        )
        m_sel = c_m.selectbox("Filtrar Mes:", meses_disp, key="sb_mes_gen")
        txt_b = c_b.text_input("🔍 Buscador (GRUPO, CÓDIGO, SAP, LÍNEAS o ALCANCE):", key="txt_busc_gen")
        modo_edicion = c_sw.toggle("✏️ Habilitar Edición", value=False, key="sw_edit_gen")

        # --- APLICACIÓN DE FILTROS A LA TABLA GENERAL ---
        df_dis = df[COLUMNAS_EXCEL].copy()
        
        # Limpieza y formateo de campos
        for column in df_dis.columns:
            df_dis[column] = df_dis[column].apply(formatear_entero_limpio)

        # Filtro 1: Mes
        if m_sel != "Todos": 
            df_dis = df_dis[df_dis["MES"].astype(str).str.strip().str.upper() == m_sel]

        # Filtro 2: Buscador Ampliado (Grupo, Código, SAP, Líneas y Alcance del Servicio)
        if txt_b.strip():
            q = texto_normalizado(txt_b)
            df_dis = df_dis[df_dis.apply(
                lambda r: q in texto_normalizado(r["GRUPO DE TUBERÍAS"]) or 
                          q in texto_normalizado(r["CODIGO DE INFORME"]) or 
                          q in texto_normalizado(r["SAP"]) or
                          q in texto_normalizado(r["LINEAS"]) or
                          q in texto_normalizado(r["ALCANCE DEL SERVICIO"]), 
                axis=1
            )]
        
        df_dis["ESTADO - VALORIZACIÓN"] = df_dis["ESTADO - VALORIZACIÓN"].apply(
            lambda x: "SI" if texto_normalizado(x) == "SI" else "Pendiente - valorización"
        )

        # Configuración visual de columnas
        config_columnas = {
            "ITEM POR MES": st.column_config.TextColumn("ITEM POR MES", width="small"),
            "IT2": st.column_config.TextColumn("IT2", width="small"),
            "UNIDAD": st.column_config.TextColumn("UNIDAD", width="small"),
            "MES": st.column_config.TextColumn("MES", width="small"),
            "LINEAS": st.column_config.TextColumn("LINEAS", width="large"),
            "CODIGO DE INFORME": st.column_config.TextColumn("CODIGO DE INFORME", width="medium"),
            "GRUPO DE TUBERÍAS": st.column_config.TextColumn("GRUPO DE TUBERÍAS", width="medium"),
            "SAP": st.column_config.TextColumn("SAP", width="small"),
            "ALCANCE DEL SERVICIO": st.column_config.TextColumn("ALCANCE DEL SERVICIO", width="large"),
            "ESTADO - ELABORACIÓN DE INFORME": st.column_config.TextColumn("ESTADO - ELABORACIÓN DE INFORME", width="medium"),
            "RESPONSABLE": st.column_config.TextColumn("RESPONSABLE", width="medium"),
            "OBSERVACIÓN": st.column_config.TextColumn("OBSERVACIÓN", width="large"),
            "ESTADO - VALORIZACIÓN": st.column_config.SelectboxColumn(
                "ESTADO - VALORIZACIÓN",
                help="Seleccione el estado de valorización",
                options=["Pendiente - valorización", "SI"],
                required=True,
                width="medium"
            )
        }

        # Función para resaltado condicional
        def resaltar_filas(row):
            val_estado = str(row.get("ESTADO - VALORIZACIÓN", "")).strip().upper()
            val_alcance = texto_normalizado(row.get("ALCANCE DEL SERVICIO", ""))

            if val_estado == "SI":
                return ["background-color: #D1FAE5; color: #065F46; font-weight: bold;"] * len(row)

            if val_alcance in [
                "VT-CIRCUITOS - PENDIENTE INSPECCION",
                "VT-CIRCUITOS - FALTA CARPETA",
                "LINEAS - PENDIENTE INSPECCION"
            ]:
                return ["background-color: #FEF08A; color: #713F12; font-weight: bold;"] * len(row)

            if val_alcance == "VT-CIRCUITOS - INSPECCION COMPLEMENTARIA":
                return ["background-color: #BAE6FD; color: #0C4A6E; font-weight: bold;"] * len(row)

            return [""] * len(row)

        if modo_edicion:
            ed_df = st.data_editor(
                df_dis,
                column_config=config_columnas,
                hide_index=True,
                use_container_width=True, 
                key="editor_tabla_general_select"
            )

            if st.button("💾 Guardar Cambios", key="btn_guardar_gen"):
                for real_idx, row in ed_df.iterrows():
                    for col in COLUMNAS_EXCEL:
                        st.session_state.df_data.at[real_idx, col] = row[col]

                    if str(row["ESTADO - VALORIZACIÓN"]).strip().upper() == "SI":
                        st.session_state.df_data.at[real_idx, "OBSERVACIÓN"] = ""

                st.session_state.df_data = limpiar_estado_y_responsable(st.session_state.df_data[COLUMNAS_EXCEL])
                guardar_datos(st.session_state.df_data)
                st.success("Cambios guardados con éxito en la base de datos.")
                st.rerun()
        else:
            df_styled = df_dis.style.apply(resaltar_filas, axis=1)
            st.dataframe(
                df_styled,
                column_config=config_columnas,
                hide_index=True,
                use_container_width=True
            )

    # ==========================================
    # PESTAÑA 2: REGISTRAR NUEVO INFORME
    # ==========================================
    with t_reg:
        st.markdown("### 📝 Registrar Nuevo Informe Técnico")
        with st.form("form_nuevo_informe", clear_on_submit=True):
            r1c1, r1c2, r1c3, r1c4 = st.columns(4)
            mes_n = r1c1.selectbox("MES:", ORDEN_MESES)
            unidad_n = r1c2.text_input("UNIDAD (Ej. RLP1):")
            grupo_n = r1c3.text_input("GRUPO DE TUBERÍAS:")
            codigo_n = r1c4.text_input("CÓDIGO DE INFORME (Opcional):")

            r2c1, r2c2, r2c3 = st.columns([2, 1, 1])
            lineas_n = r2c1.text_area("LÍNEAS DE INSPECCIÓN:")
            sap_n = r2c2.text_input("N° SOLICITUD SAP:")
            alcance_n = r2c3.selectbox("ALCANCE DEL SERVICIO:", [
                "VT-CIRCUITOS - COMPLETO",
                "VT-CIRCUITOS - PENDIENTE INSPECCION",
                "VT-CIRCUITOS - FALTA CARPETA",
                "VT-CIRCUITOS - INSPECCION COMPLEMENTARIA",
                "LINEAS - COMPLETO",
                "LINEAS - PENDIENTE INSPECCION"
            ])

            r3c1, r3c2, r3c3 = st.columns(3)
            estado_n = r3c1.selectbox("ESTADO - ELABORACIÓN:", [
                "EN PROCESO DE ELABORACION DE INFORME",
                "PENDIENTE ELABORACION DE INFORME",
                "PENDIENTE ASIGNAR INFORME"
            ])
            resp_n = r3c2.selectbox("RESPONSABLE:", PERSONAL_LISTA)
            obs_n = r3c3.text_input("OBSERVACIÓN INICIAL:")

            btn_reg = st.form_submit_button("➕ Registrar Informe")

            if btn_reg:
                if not grupo_n.strip():
                    st.error("El campo 'GRUPO DE TUBERÍAS' es obligatorio.")
                else:
                    items_mes = df[df["MES"] == mes_n]
                    nuevo_item = len(items_mes) + 1
                    nuevo_reg = {
                        "ITEM POR MES": str(nuevo_item),
                        "IT2": str(nuevo_item),
                        "UNIDAD": unidad_n,
                        "MES": mes_n,
                        "LINEAS": lineas_n,
                        "CODIGO DE INFORME": codigo_n if codigo_n.strip() else "-",
                        "GRUPO DE TUBERÍAS": grupo_n,
                        "SAP": sap_n,
                        "ALCANCE DEL SERVICIO": alcance_n,
                        "ESTADO - ELABORACIÓN DE INFORME": estado_n,
                        "RESPONSABLE": resp_n,
                        "OBSERVACIÓN": obs_n,
                        "ESTADO - VALORIZACIÓN": "Pendiente - valorización"
                    }
                    st.session_state.df_data = pd.concat([st.session_state.df_data, pd.DataFrame([nuevo_reg])], ignore_index=True)
                    guardar_datos(st.session_state.df_data)
                    st.success("¡Informe registrado exitosamente!")
                    st.rerun()

    # ==========================================
    # PESTAÑA 3: SOLICITUDES DE APROBACIÓN
    # ==========================================
    with t_sol:
        st.markdown("### 📩 Gestión de Solicitudes de Modificación")
        solic_pendientes = cargar_solicitudes()
        
        if not solic_pendientes:
            st.info("No hay solicitudes pendientes ni registradas en el sistema.")
        else:
            df_sol = pd.DataFrame(solic_pendientes)
            st.dataframe(df_sol, use_container_width=True)
            
            p_sol = [s for s in solic_pendientes if s["estado"] == "PENDIENTE"]
            if p_sol:
                st.markdown("---")
                st.markdown("#### ⚡ Aprobación Rápida (Administrador)")
                col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
                sol_id = col_s1.selectbox("Seleccionar Solicitud:", [f"ID {s['id']} - {s['tipo']}: {s['codigo']} ({s['grupo']})" for s in p_sol])
                
                selected_id = int(sol_id.split(" ")[1])
                
                if col_s2.button("✅ Aprobar Solicitud"):
                    for s in solic_pendientes:
                        if s["id"] == selected_id:
                            s["estado"] = "APROBADO"
                    guardar_solicitudes(solic_pendientes)
                    st.success("Solicitud Aprobada.")
                    st.rerun()
                    
                if col_s3.button("❌ Rechazar Solicitud"):
                    for s in solic_pendientes:
                        if s["id"] == selected_id:
                            s["estado"] = "RECHAZADO"
                    guardar_solicitudes(solic_pendientes)
                    st.warning("Solicitud Rechazada.")
                    st.rerun()

    # ==========================================
    # PESTAÑA 4: RESUMEN EJECUTIVO
    # ==========================================
    with t_res:
        st.markdown("### 📊 Resumen Ejecutivo y Estadísticas por Mes")
        if not df.empty:
            df_resumen = df.groupby(["MES", "ESTADO - VALORIZACIÓN"]).size().unstack(fill_value=0)
            st.bar_chart(df_resumen)

    # ==========================================
    # PESTAÑA 5: ADMINISTRACIÓN
    # ==========================================
    with t_adm:
        st.markdown("### ⚙️ Panel Administrativo")
        st.warning("⚠️ Acción Restringida: Limpieza completa de la Base de Datos")
        if st.button("🚨 Vaciar Base de Datos Completa"):
            st.session_state.df_data = pd.DataFrame(columns=COLUMNAS_EXCEL)
            guardar_datos(st.session_state.df_data)
            st.success("Base de datos reiniciada a cero.")
            st.rerun()
else:
    st.info("La base de datos se encuentra totalmente vacía. Cargue un archivo Excel o registre un nuevo informe para comenzar.")
