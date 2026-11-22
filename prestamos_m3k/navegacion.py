"""Pestañas hechas con botones: la opción activa va rellena (verde) y las demás con borde.
Guardan la opción elegida en st.session_state[key], igual que un selector normal."""
import streamlit as st


def pestanas(opciones, key, etiquetas=None, iconos=None):
    """Muestra una fila de botones y devuelve la opción elegida. `etiquetas` y `iconos` son dicts opcionales por opción."""
    opciones = list(opciones)
    if st.session_state.get(key) not in opciones:
        st.session_state[key] = opciones[0]
    actual = st.session_state[key]
    n = len(opciones)
    columnas = st.columns([1] * n + [max(1, 7 - n)])
    for i, op in enumerate(opciones):
        texto = (etiquetas or {}).get(op, op)
        with columnas[i]:
            if st.button(texto, key=f"{key}__{i}", type="primary" if op == actual else "secondary",
                         icon=(iconos or {}).get(op), use_container_width=True):
                st.session_state[key] = op
                st.rerun()
    return st.session_state[key]
