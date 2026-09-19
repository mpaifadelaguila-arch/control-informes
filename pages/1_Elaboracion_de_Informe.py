except Exception as err_backend:
                        # ESTO TE MOSTRARÁ EL ERROR REAL EN ROJO EN LA PANTALLA DE STREAMLIT
                        st.exception(err_backend)
                        raise err_backend
