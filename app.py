"""Punto de entrada: define el menú lateral y qué página se abre.

- «Resumen general»: balance total de ambos planes (pages/0_Resumen_General.py).
- «Plan de líneas»: control interno de informes del plan de tuberías (plan_de_lineas.py).
- «Planes adicionales»: puntos de inyección, dead legs y sulfidación.
- «Pescantes y trolleys»: control de informes de pescantes y trolleys por unidad.
"""

import streamlit as st

navegacion = st.navigation([
    st.Page(
        "pages/0_Resumen_General.py",
        title="Resumen general",
        icon=":material/dashboard:",
        default=True,
    ),
    st.Page(
        "plan_de_lineas.py",
        title="Plan de líneas",
        icon=":material/assignment:",
    ),
    st.Page(
        "pages/1_Planes_Adicionales.py",
        title="Planes adicionales",
        icon=":material/add_task:",
    ),
    st.Page(
        "pages/2_Pescantes_Trolleys.py",
        title="Pescantes y trolleys",
        icon=":material/construction:",
    ),
])
navegacion.run()
