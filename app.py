"""Punto de entrada: define el menú lateral y qué página se abre.

- «Plan de líneas»: control interno de informes del plan de tuberías (plan_de_lineas.py).
- «Planes adicionales»: puntos de inyección, dead legs y sulfidación.
"""

import streamlit as st

navegacion = st.navigation([
    st.Page(
        "plan_de_lineas.py",
        title="Plan de líneas",
        icon=":material/assignment:",
        default=True,
    ),
    st.Page(
        "pages/1_Planes_Adicionales.py",
        title="Planes adicionales",
        icon=":material/add_task:",
    ),
])
navegacion.run()
