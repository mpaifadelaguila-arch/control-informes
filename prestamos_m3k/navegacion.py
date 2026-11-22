"""Pestañas hechas con botones: la opción activa va rellena (verde) y las demás con borde.
Guardan la opción elegida en st.session_state[key], igual que un selector normal."""
import streamlit as st


def _elegir(key, opcion):
    st.session_state[key] = opcion


def pestanas(opciones, key, etiquetas=None, iconos=None, ancho_completo=False):
    """Muestra una fila de botones y devuelve la opción elegida. `etiquetas` y `iconos` son dicts opcionales por opción."""
    opciones = list(opciones)
    if st.session_state.get(key) not in opciones:
        st.session_state[key] = opciones[0]
    actual = st.session_state[key]
    n = len(opciones)
    # ancho_completo: los botones se reparten todo el ancho (para columnas angostas, donde el texto se cortaría)
    if ancho_completo:  # el ancho de cada botón sigue a su texto, así las palabras largas no se salen
        columnas = st.columns([len((etiquetas or {}).get(op, op)) + 6 for op in opciones])
    else:
        columnas = st.columns([1] * n + [max(1, 7 - n)])
    for i, op in enumerate(opciones):
        texto = (etiquetas or {}).get(op, op)
        with columnas[i]:
            # on_click cambia la opción ANTES de redibujar la pantalla; así no hace falta st.rerun() ni se queda un clic "pegado"
            st.button(texto, key=f"{key}__{i}", type="primary" if op == actual else "secondary",
                      icon=(iconos or {}).get(op), use_container_width=True, on_click=_elegir, args=(key, op))
    return st.session_state[key]
