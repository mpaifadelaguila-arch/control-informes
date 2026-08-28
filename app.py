# --- NAVEGACIÓN DE PESTAÑAS Y TABLAS CON ÍNDICE DESDE 1 ---
(
    t_admin, t_gen, t_pasig, t_proc, t_pinsp, t_rfiab, 
    t_pesp, t_resp, t_psaim, t_res_m, t_p_m, t_res_o
) = st.tabs([
    "🔔 Administración", "📋 Tabla General", "📝 Pend. Asignar", "🔄 En Proceso", 
    "⏳ Pend. Inspección", "🔍 Rev. Fiabilidad", "🧑‍🔬 Pend. Rev. Especialista", 
    "🔬 Rev. por Especialista", "🛠️ Correc. PSAIM", "📅 Resumen Mes (T3)", 
    "📊 Pend. Mes/Obs (T4)", "📌 Resumen Obs (T5)"
])

with t_admin:
    st.subheader("⚙️ Gestión de Datos: Cargar / Restaurar Excel & Descargar Respaldo")
    with st.expander("⚙️ Gestión de Datos: Cargar / Restaurar Excel & Descargar Respaldo", expanded=True):
        c_up, c_down = st.columns([2, 1])
        with c_up:
            st.markdown("##### 📥 Cargar Base de Datos desde Excel")
            file_excel = st.file_uploader("Seleccionar archivo Excel:", type=["xlsx", "xlsm"], key="up_excel")
            if file_excel is not None:
                if st.button("🔄 Reemplazar Base de Datos"):
                    try:
                        df_new = pd.read_excel(file_excel)
                        cols_req = ["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN", "ESTADO - VALORIZACIÓN"]
                        for cr in cols_req:
                            if cr not in df_new.columns:
                                df_new[cr] = ""
                            else:
                                df_new[cr] = df_new[cr].fillna("").astype(str)
                        if "LINEAS" in df_new.columns:
                            df_new["LINEAS"] = pd.to_numeric(df_new["LINEAS"], errors="coerce").fillna(1)
                        else:
                            df_new["LINEAS"] = 1
                        if guardar_base_datos(df_new):
                            st.success("¡Base de datos actualizada con éxito!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al procesar el archivo: {e}")
        with c_down:
            st.markdown("##### 💾 Descargar Respaldo Actual")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df_export = df_data.copy()
                if "CLAVE_GLOBAL" in df_export.columns:
                    df_export = df_export.drop(columns=["CLAVE_GLOBAL"])
                df_export.to_excel(writer, index=False, sheet_name="BaseDatos")
            st.download_button(
                label="💾 Descargar Copia en Excel (.xlsx)",
                data=buffer.getvalue(),
                file_name="RESPALDO_BASE_DE_DATOS.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    st.markdown("---")
    st.subheader("🔔 Solicitudes Pendientes de Modificación")
    solicitudes = cargar_solicitudes()
    pendientes = [s for s in solicitudes if s["estado"] == "PENDIENTE"]
    
    if not pendientes:
        st.info("No hay solicitudes pendientes en este momento.")
    else:
        for sol in pendientes:
            with st.container():
                c_info, c_acc1, c_acc2 = st.columns([3, 1, 1])
                c_info.markdown(f"**[{sol['tipo']}]** Código: `{sol['codigo']}` | Grupo: `{sol['grupo']}` | Solicitado por: **{sol['usuario']}** ({sol['fecha']})")
                if c_acc1.button("🟢 Aceptar", key=f"ac_{sol['id']}"):
                    df_mod = cargar_base_datos()
                    mask = (df_mod["CODIGO DE INFORME"].str.strip() == sol["codigo"].strip()) & (df_mod["GRUPO DE TUBERÍAS"].str.strip() == sol["grupo"].strip())
                    
                    if sol["tipo"] == "INFORME COMPLETADO (GABINETE)":
                        df_mod.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "Finalizado"
                        df_mod.loc[mask, "OBSERVACIÓN"] = "Informe (Carta) entregado para su revisión - Fiabilidad"
                        df_mod.loc[mask, "RESPONSABLE"] = sol["usuario"]
                    elif sol["tipo"] == "REVISIÓN ESPECIALISTA":
                        df_mod.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "Finalizado"
                        df_mod.loc[mask, "OBSERVACIÓN"] = f"REV. POR EL ESPECIALISTA ({sol['usuario']})"
                    elif sol["tipo"] == "CORRECCIÓN PSAIM":
                        df_mod.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "Finalizado"
                        df_mod.loc[mask, "OBSERVACIÓN"] = "Informe (Carta) entregado para su revisión - Fiabilidad"
                    
                    guardar_base_datos(df_mod)
                    sol["estado"] = "APROBADO"
                    guardar_solicitudes(solicitudes)
                    st.success("Solicitud aprobada y datos actualizados.")
                    st.rerun()

                if c_acc2.button("🔴 Rechazar", key=f"rc_{sol['id']}"):
                    sol["estado"] = "RECHAZADO"
                    guardar_solicitudes(solicitudes)
                    st.warning("Solicitud rechazada.")
                    st.rerun()

with t_gen:
    st.subheader("📋 Tabla General de Informes")
    df_gen_disp = df_data.copy()
    if "CLAVE_GLOBAL" in df_gen_disp.columns:
        df_gen_disp = df_gen_disp.drop(columns=["CLAVE_GLOBAL"])
    df_gen_disp.index = pd.RangeIndex(start=1, stop=len(df_gen_disp) + 1, step=1)
    st.dataframe(df_gen_disp, use_container_width=True)

with t_pasig:
    if not df_pend_asignacion.empty:
        res_pasig = df_pend_asignacion.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False).agg({"LINEAS": "count"})
        res_pasig.index = pd.RangeIndex(start=1, stop=len(res_pasig) + 1, step=1)
        st.dataframe(res_pasig, use_container_width=True)

with t_proc:
    if not df_en_proceso.empty:
        tg = df_en_proceso.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False).agg({"LINEAS": "count"})
        tg_disp = tg.copy()
        tg_disp.index = pd.RangeIndex(start=1, stop=len(tg_disp) + 1, step=1)
        st.dataframe(tg_disp, use_container_width=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_s = c1.selectbox("Código:", tg["CODIGO DE INFORME"].unique(), key="spc")
        resp_s = c2.selectbox("Inspector:", PERSONAL_LISTA, key="spr")
        if c3.button("🟢 Enviar al 100%", key="b_proc"):
            ok, m = registrar_solicitud("INFORME COMPLETADO (GABINETE)", cod_s, tg[tg["CODIGO DE INFORME"] == cod_s]["GRUPO DE TUBERÍAS"].values[0], resp_s)
            st.success(m) if ok else st.warning(m)

with t_pinsp:
    if not df_pend_inspeccion.empty:
        res_pinsp = df_pend_inspeccion.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False).agg({"LINEAS": "count"})
        res_pinsp.index = pd.RangeIndex(start=1, stop=len(res_pinsp) + 1, step=1)
        st.dataframe(res_pinsp, use_container_width=True)

with t_rfiab:
    if not df_fiab_activos.empty:
        res_fiab = df_fiab_activos.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "count"})
        res_fiab.index = pd.RangeIndex(start=1, stop=len(res_fiab) + 1, step=1)
        st.dataframe(res_fiab, use_container_width=True)

with t_pesp:
    if not df_pesp_det.empty:
        tg_e = df_pesp_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "count"})
        tg_e_disp = tg_e.copy()
        tg_e_disp.index = pd.RangeIndex(start=1, stop=len(tg_e_disp) + 1, step=1)
        st.dataframe(tg_e_disp, use_container_width=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_pe = c1.selectbox("Código:", tg_e["CODIGO DE INFORME"].unique(), key="pesp_c")
        resp_pe = c2.selectbox("Especialista:", ESPECIALISTAS_LISTA, key="pesp_r")
        if c3.button("🟢 Enviar a Revisión", key="b_pesp"):
            grupo_sel = tg_e[tg_e["CODIGO DE INFORME"] == cod_pe]["GRUPO DE TUBERÍAS"].values[0]
            ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_pe, grupo_sel, resp_pe)
            st.success(m) if ok else st.warning(m)

with t_resp:
    if not df_resp_det.empty:
        tg_re = df_resp_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "count"})
        tg_re_disp = tg_re.copy()
        tg_re_disp.index = pd.RangeIndex(start=1, stop=len(tg_re_disp) + 1, step=1)
        st.dataframe(tg_re_disp, use_container_width=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_se = c1.selectbox("Código:", tg_re["CODIGO DE INFORME"].unique(), key="sec")
        resp_se = c2.selectbox("Especialista:", ESPECIALISTAS_LISTA, key="ser")
        if c3.button("🟢 Liberar Especialista", key="b_esp"):
            ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_se, tg_re[tg_re["CODIGO DE INFORME"] == cod_se]["GRUPO DE TUBERÍAS"].values[0], resp_se)
            st.success(m) if ok else st.warning(m)

with t_psaim:
    if not df_psaim_det.empty:
        tg_p = df_psaim_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "count"})
        tg_p_disp = tg_p.copy()
        tg_p_disp.index = pd.RangeIndex(start=1, stop=len(tg_p_disp) + 1, step=1)
        st.dataframe(tg_p_disp, use_container_width=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_sp = c1.selectbox("Código:", tg_p["CODIGO DE INFORME"].unique(), key="spc_p")
        resp_sp = c2.selectbox("Revisor PSAIM:", REVISORES_PSAIM_LISTA, key="spr_p")
        if c3.button("🟢 PSAIM Corregido", key="b_psaim"):
            ok, m = registrar_solicitud("CORRECCIÓN PSAIM", cod_sp, tg_p[tg_p["CODIGO DE INFORME"] == cod_sp]["GRUPO DE TUBERÍAS"].values[0], resp_sp)
            st.success(m) if ok else st.warning(m)

with t_res_m:
    st.subheader("📅 Resumen Mes (T3)")
    piv_m = pd.pivot_table(df_activos, index="MES", columns="ESTADO - ELABORACIÓN DE INFORME", values="LINEAS", aggfunc="count", fill_value=0)
    piv_m.index = pd.RangeIndex(start=1, stop=len(piv_m) + 1, step=1)
    st.dataframe(piv_m, use_container_width=True)

with t_p_m:
    st.subheader("📊 Pend. Mes/Obs (T4)")
    piv_po = pd.pivot_table(df_activos, index="MES", columns="OBSERVACIÓN", values="LINEAS", aggfunc="count", fill_value=0)
    piv_po.index = pd.RangeIndex(start=1, stop=len(piv_po) + 1, step=1)
    st.dataframe(piv_po, use_container_width=True)

with t_res_o:
    st.subheader("📌 Resumen Obs (T5)")
    piv_o = pd.pivot_table(df_activos, index="OBSERVACIÓN", columns="ESTADO - ELABORACIÓN DE INFORME", values="LINEAS", aggfunc="count", fill_value=0)
    piv_o.index = pd.RangeIndex(start=1, stop=len(piv_o) + 1, step=1)
    st.dataframe(piv_o, use_container_width=True)
    # --- NAVEGACIÓN DE PESTAÑAS Y TABLAS CON ÍNDICE DESDE 1 ---
(
    t_admin, t_gen, t_pasig, t_proc, t_pinsp, t_rfiab, 
    t_pesp, t_resp, t_psaim, t_res_m, t_p_m, t_res_o
) = st.tabs([
    "🔔 Administración", "📋 Tabla General", "📝 Pend. Asignar", "🔄 En Proceso", 
    "⏳ Pend. Inspección", "🔍 Rev. Fiabilidad", "🧑‍🔬 Pend. Rev. Especialista", 
    "🔬 Rev. por Especialista", "🛠️ Correc. PSAIM", "📅 Resumen Mes (T3)", 
    "📊 Pend. Mes/Obs (T4)", "📌 Resumen Obs (T5)"
])

with t_admin:
    st.subheader("⚙️ Gestión de Datos: Cargar / Restaurar Excel & Descargar Respaldo")
    with st.expander("⚙️ Gestión de Datos: Cargar / Restaurar Excel & Descargar Respaldo", expanded=True):
        c_up, c_down = st.columns([2, 1])
        with c_up:
            st.markdown("##### 📥 Cargar Base de Datos desde Excel")
            file_excel = st.file_uploader("Seleccionar archivo Excel:", type=["xlsx", "xlsm"], key="up_excel")
            if file_excel is not None:
                if st.button("🔄 Reemplazar Base de Datos"):
                    try:
                        df_new = pd.read_excel(file_excel)
                        cols_req = ["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN", "ESTADO - VALORIZACIÓN"]
                        for cr in cols_req:
                            if cr not in df_new.columns:
                                df_new[cr] = ""
                            else:
                                df_new[cr] = df_new[cr].fillna("").astype(str)
                        if "LINEAS" in df_new.columns:
                            df_new["LINEAS"] = pd.to_numeric(df_new["LINEAS"], errors="coerce").fillna(1)
                        else:
                            df_new["LINEAS"] = 1
                        if guardar_base_datos(df_new):
                            st.success("¡Base de datos actualizada con éxito!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al procesar el archivo: {e}")
        with c_down:
            st.markdown("##### 💾 Descargar Respaldo Actual")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df_export = df_data.copy()
                if "CLAVE_GLOBAL" in df_export.columns:
                    df_export = df_export.drop(columns=["CLAVE_GLOBAL"])
                df_export.to_excel(writer, index=False, sheet_name="BaseDatos")
            st.download_button(
                label="💾 Descargar Copia en Excel (.xlsx)",
                data=buffer.getvalue(),
                file_name="RESPALDO_BASE_DE_DATOS.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    st.markdown("---")
    st.subheader("🔔 Solicitudes Pendientes de Modificación")
    solicitudes = cargar_solicitudes()
    pendientes = [s for s in solicitudes if s["estado"] == "PENDIENTE"]
    
    if not pendientes:
        st.info("No hay solicitudes pendientes en este momento.")
    else:
        for sol in pendientes:
            with st.container():
                c_info, c_acc1, c_acc2 = st.columns([3, 1, 1])
                c_info.markdown(f"**[{sol['tipo']}]** Código: `{sol['codigo']}` | Grupo: `{sol['grupo']}` | Solicitado por: **{sol['usuario']}** ({sol['fecha']})")
                if c_acc1.button("🟢 Aceptar", key=f"ac_{sol['id']}"):
                    df_mod = cargar_base_datos()
                    mask = (df_mod["CODIGO DE INFORME"].str.strip() == sol["codigo"].strip()) & (df_mod["GRUPO DE TUBERÍAS"].str.strip() == sol["grupo"].strip())
                    
                    if sol["tipo"] == "INFORME COMPLETADO (GABINETE)":
                        df_mod.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "Finalizado"
                        df_mod.loc[mask, "OBSERVACIÓN"] = "Informe (Carta) entregado para su revisión - Fiabilidad"
                        df_mod.loc[mask, "RESPONSABLE"] = sol["usuario"]
                    elif sol["tipo"] == "REVISIÓN ESPECIALISTA":
                        df_mod.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "Finalizado"
                        df_mod.loc[mask, "OBSERVACIÓN"] = f"REV. POR EL ESPECIALISTA ({sol['usuario']})"
                    elif sol["tipo"] == "CORRECCIÓN PSAIM":
                        df_mod.loc[mask, "ESTADO - ELABORACIÓN DE INFORME"] = "Finalizado"
                        df_mod.loc[mask, "OBSERVACIÓN"] = "Informe (Carta) entregado para su revisión - Fiabilidad"
                    
                    guardar_base_datos(df_mod)
                    sol["estado"] = "APROBADO"
                    guardar_solicitudes(solicitudes)
                    st.success("Solicitud aprobada y datos actualizados.")
                    st.rerun()

                if c_acc2.button("🔴 Rechazar", key=f"rc_{sol['id']}"):
                    sol["estado"] = "RECHAZADO"
                    guardar_solicitudes(solicitudes)
                    st.warning("Solicitud rechazada.")
                    st.rerun()

with t_gen:
    st.subheader("📋 Tabla General de Informes")
    df_gen_disp = df_data.copy()
    if "CLAVE_GLOBAL" in df_gen_disp.columns:
        df_gen_disp = df_gen_disp.drop(columns=["CLAVE_GLOBAL"])
    df_gen_disp.index = pd.RangeIndex(start=1, stop=len(df_gen_disp) + 1, step=1)
    st.dataframe(df_gen_disp, use_container_width=True)

with t_pasig:
    if not df_pend_asignacion.empty:
        res_pasig = df_pend_asignacion.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False).agg({"LINEAS": "count"})
        res_pasig.index = pd.RangeIndex(start=1, stop=len(res_pasig) + 1, step=1)
        st.dataframe(res_pasig, use_container_width=True)

with t_proc:
    if not df_en_proceso.empty:
        tg = df_en_proceso.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False).agg({"LINEAS": "count"})
        tg_disp = tg.copy()
        tg_disp.index = pd.RangeIndex(start=1, stop=len(tg_disp) + 1, step=1)
        st.dataframe(tg_disp, use_container_width=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_s = c1.selectbox("Código:", tg["CODIGO DE INFORME"].unique(), key="spc")
        resp_s = c2.selectbox("Inspector:", PERSONAL_LISTA, key="spr")
        if c3.button("🟢 Enviar al 100%", key="b_proc"):
            ok, m = registrar_solicitud("INFORME COMPLETADO (GABINETE)", cod_s, tg[tg["CODIGO DE INFORME"] == cod_s]["GRUPO DE TUBERÍAS"].values[0], resp_s)
            st.success(m) if ok else st.warning(m)

with t_pinsp:
    if not df_pend_inspeccion.empty:
        res_pinsp = df_pend_inspeccion.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME"], as_index=False).agg({"LINEAS": "count"})
        res_pinsp.index = pd.RangeIndex(start=1, stop=len(res_pinsp) + 1, step=1)
        st.dataframe(res_pinsp, use_container_width=True)

with t_rfiab:
    if not df_fiab_activos.empty:
        res_fiab = df_fiab_activos.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "count"})
        res_fiab.index = pd.RangeIndex(start=1, stop=len(res_fiab) + 1, step=1)
        st.dataframe(res_fiab, use_container_width=True)

with t_pesp:
    if not df_pesp_det.empty:
        tg_e = df_pesp_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "count"})
        tg_e_disp = tg_e.copy()
        tg_e_disp.index = pd.RangeIndex(start=1, stop=len(tg_e_disp) + 1, step=1)
        st.dataframe(tg_e_disp, use_container_width=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_pe = c1.selectbox("Código:", tg_e["CODIGO DE INFORME"].unique(), key="pesp_c")
        resp_pe = c2.selectbox("Especialista:", ESPECIALISTAS_LISTA, key="pesp_r")
        if c3.button("🟢 Enviar a Revisión", key="b_pesp"):
            grupo_sel = tg_e[tg_e["CODIGO DE INFORME"] == cod_pe]["GRUPO DE TUBERÍAS"].values[0]
            ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_pe, grupo_sel, resp_pe)
            st.success(m) if ok else st.warning(m)

with t_resp:
    if not df_resp_det.empty:
        tg_re = df_resp_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "count"})
        tg_re_disp = tg_re.copy()
        tg_re_disp.index = pd.RangeIndex(start=1, stop=len(tg_re_disp) + 1, step=1)
        st.dataframe(tg_re_disp, use_container_width=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_se = c1.selectbox("Código:", tg_re["CODIGO DE INFORME"].unique(), key="sec")
        resp_se = c2.selectbox("Especialista:", ESPECIALISTAS_LISTA, key="ser")
        if c3.button("🟢 Liberar Especialista", key="b_esp"):
            ok, m = registrar_solicitud("REVISIÓN ESPECIALISTA", cod_se, tg_re[tg_re["CODIGO DE INFORME"] == cod_se]["GRUPO DE TUBERÍAS"].values[0], resp_se)
            st.success(m) if ok else st.warning(m)

with t_psaim:
    if not df_psaim_det.empty:
        tg_p = df_psaim_det.groupby(["MES", "ESTADO - ELABORACIÓN DE INFORME", "RESPONSABLE", "GRUPO DE TUBERÍAS", "CODIGO DE INFORME", "OBSERVACIÓN"], as_index=False).agg({"LINEAS": "count"})
        tg_p_disp = tg_p.copy()
        tg_p_disp.index = pd.RangeIndex(start=1, stop=len(tg_p_disp) + 1, step=1)
        st.dataframe(tg_p_disp, use_container_width=True)
        c1, c2, c3 = st.columns([2, 2, 1])
        cod_sp = c1.selectbox("Código:", tg_p["CODIGO DE INFORME"].unique(), key="spc_p")
        resp_sp = c2.selectbox("Revisor PSAIM:", REVISORES_PSAIM_LISTA, key="spr_p")
        if c3.button("🟢 PSAIM Corregido", key="b_psaim"):
            ok, m = registrar_solicitud("CORRECCIÓN PSAIM", cod_sp, tg_p[tg_p["CODIGO DE INFORME"] == cod_sp]["GRUPO DE TUBERÍAS"].values[0], resp_sp)
            st.success(m) if ok else st.warning(m)

with t_res_m:
    st.subheader("📅 Resumen Mes (T3)")
    piv_m = pd.pivot_table(df_activos, index="MES", columns="ESTADO - ELABORACIÓN DE INFORME", values="LINEAS", aggfunc="count", fill_value=0)
    piv_m.index = pd.RangeIndex(start=1, stop=len(piv_m) + 1, step=1)
    st.dataframe(piv_m, use_container_width=True)

with t_p_m:
    st.subheader("📊 Pend. Mes/Obs (T4)")
    piv_po = pd.pivot_table(df_activos, index="MES", columns="OBSERVACIÓN", values="LINEAS", aggfunc="count", fill_value=0)
    piv_po.index = pd.RangeIndex(start=1, stop=len(piv_po) + 1, step=1)
    st.dataframe(piv_po, use_container_width=True)

with t_res_o:
    st.subheader("📌 Resumen Obs (T5)")
    piv_o = pd.pivot_table(df_activos, index="OBSERVACIÓN", columns="ESTADO - ELABORACIÓN DE INFORME", values="LINEAS", aggfunc="count", fill_value=0)
    piv_o.index = pd.RangeIndex(start=1, stop=len(piv_o) + 1, step=1)
    st.dataframe(piv_o, use_container_width=True)
