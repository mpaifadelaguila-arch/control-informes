"""Configuración: parámetros del negocio, respaldo y auditoría."""

import streamlit as st

import calculos as calc
import datos
import drive_json
import estilos as ui
import operaciones as ops


def mostrar() -> None:
    db = datos.cargar()
    ui.encabezado("Configuración", "Parámetros, respaldo y registro de cambios")

    st.subheader("Parámetros", anchor=False)
    with st.form("form_config"):
        c1, c2 = st.columns(2)
        tasa = c1.number_input("Interés por defecto (%)", 0.0, 100.0, float(db["config"]["tasa_default"]), 1.0,
                               help="Se propone al crear un crédito; puedes cambiarlo en cada uno.")
        mora = c2.number_input("Mora diaria (%)", 0.0, 5.0, float(db["config"]["mora_diaria_pct"]), 0.1,
                               help="Sobre el saldo vencido, por cada día de atraso. 0 = no se cobra mora (valor actual del negocio).")
        if st.form_submit_button("Guardar parámetros", type="primary"):
            try:
                ops.guardar_config(db, tasa, mora)
            except ValueError as e:
                st.error(str(e))
            else:
                datos.guardar(db)
                ui.avisar("ok", "Parámetros guardados.")
                st.rerun()

    st.subheader("Respaldo", anchor=False)
    if drive_json.configurado():
        st.success("El respaldo en Google Drive está activo: cada cambio se sube automáticamente.")
    else:
        st.warning("Sin respaldo en Google Drive. Si la app se reinicia en la nube, los datos se pierden. "
                   "Configura `gcp_service_account` y `prestamos_drive_folder_id` en los secretos, o descarga un respaldo seguido.")
    st.download_button("Descargar respaldo (JSON)", datos.a_bytes(db), file_name=f"respaldo_m3k_{calc.hoy()}.json", mime="application/json",
                       icon=":material/download:")
    archivo = st.file_uploader("Restaurar desde un respaldo", type=["json"])
    if archivo is not None:
        try:
            nueva = datos.desde_bytes(archivo.getvalue())
        except ValueError as e:
            st.error(str(e))
        else:
            st.info(f"El respaldo tiene {len(nueva['clientes'])} cliente(s) y {len(nueva['prestamos'])} crédito(s). Reemplazará todo lo actual.")
            if st.checkbox("Entiendo que se reemplazan los datos actuales", key="ok_restaurar") and st.button("Restaurar respaldo"):
                datos.reemplazar(nueva)
                ui.avisar("ok", "Respaldo restaurado.")
                st.rerun()

    st.subheader("Auditoría", anchor=False)
    if not db["auditoria"]:
        ui.vacio("Sin cambios registrados", "Cada alta, cobro, anulación o cambio de capital base queda anotado aquí.", "📝")
    else:
        ui.tabla(["Fecha y hora", "Acción", "Detalle"],
                 [[a["ts"].replace("T", " ")[:16], a["accion"], a["detalle"]] for a in reversed(db["auditoria"][-100:])],
                 etiqueta="Registro de cambios", apilar=True)
