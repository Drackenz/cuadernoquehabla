import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from cerebro import ImagenIlegible, analizar_pagina, calificar, crear_cliente


st.set_page_config(page_title="Mi cuaderno habla", page_icon="📓", layout="centered")

try:
    llave_api = st.secrets["GEMINI_API_KEY"]
except (KeyError, StreamlitSecretNotFoundError):
    st.error(
        "No encuentro GEMINI_API_KEY. Agregala en "
        "`.streamlit/secrets.toml` como `GEMINI_API_KEY = \"tu_llave\"` "
        "o configurala en los secretos de Streamlit Cloud."
    )
    st.stop()

# Streamlit vuelve a ejecutar este archivo con cada interacción; session_state conserva el apunte y el avance del examen.
st.session_state.setdefault("apunte", None)
st.session_state.setdefault("respuestas_examen", {})
st.session_state.setdefault("examen_entregado", False)
st.session_state.setdefault("version_examen", 0)
st.session_state.setdefault("celebracion_mostrada", False)


def analizar_imagen(imagen):
    if imagen is None:
        st.info("Tomá una foto o subí una imagen antes de analizar la página.")
        return

    try:
        with st.spinner("Analizando la página..."):
            cliente = crear_cliente(llave_api)
            apunte = analizar_pagina(imagen.getvalue(), imagen.type, cliente)
    except ImagenIlegible as error:
        st.warning(str(error))
    except Exception as error:
        st.error(f"No se pudo analizar la página. Revisá tu conexión e intentá de nuevo. Detalle: {error}")
    else:
        st.session_state["apunte"] = apunte
        st.session_state["respuestas_examen"] = {}
        st.session_state["examen_entregado"] = False
        st.session_state["celebracion_mostrada"] = False
        st.session_state["version_examen"] += 1


st.title("📓 Mi cuaderno habla")
st.write("Tomá una foto de tu cuaderno o subí una imagen para crear tu guía de estudio.")

tab_foto, tab_subir = st.tabs(["Tomar foto", "Subir imagen"])

with tab_foto:
    foto = st.camera_input("Enfocá la página del cuaderno")
    st.button(
        "Analizar la página",
        key="analizar_foto",
        on_click=analizar_imagen,
        args=(foto,),
        disabled=foto is None,
    )

with tab_subir:
    archivo = st.file_uploader(
        "Elegí una imagen de la página",
        type=["png", "jpg", "jpeg", "webp"],
    )
    st.button(
        "Analizar la página",
        key="analizar_archivo",
        on_click=analizar_imagen,
        args=(archivo,),
        disabled=archivo is None,
    )

apunte = st.session_state["apunte"]
if apunte is not None:
    st.header(apunte.titulo)
    st.subheader(f"Materia: {apunte.materia}")
    st.write(f"**Dificultad:** {'⭐' * apunte.dificultad} ({apunte.dificultad}/5)")

    st.subheader("Resumen")
    st.write(apunte.resumen)

    st.subheader("Conceptos")
    for concepto in apunte.conceptos:
        st.markdown(f"- **{concepto.termino}:** {concepto.explicacion}")

    st.subheader("Tarjetas de repaso")
    for indice, tarjeta in enumerate(apunte.tarjetas):
        with st.expander(tarjeta.pregunta):
            st.write(tarjeta.respuesta)

    st.subheader("Examen")
    for indice, pregunta in enumerate(apunte.examen):
        clave_widget = f"respuesta_{st.session_state['version_examen']}_{indice}"
        seleccion = st.radio(
            pregunta.enunciado,
            pregunta.opciones,
            index=None,
            key=clave_widget,
            disabled=st.session_state["examen_entregado"],
        )
        if seleccion is None:
            st.session_state["respuestas_examen"].pop(indice, None)
        else:
            st.session_state["respuestas_examen"][indice] = pregunta.opciones.index(seleccion)

        if st.session_state["examen_entregado"]:
            if seleccion is None:
                st.warning("Sin responder.")
            elif pregunta.opciones.index(seleccion) == pregunta.correcta:
                st.success("¡Correcta!")
            else:
                st.error(f"Incorrecta. La respuesta correcta era: {pregunta.opciones[pregunta.correcta]}")

    if not st.session_state["examen_entregado"]:
        if st.button("Entregar examen"):
            st.session_state["examen_entregado"] = True
            st.rerun()
    else:
        aciertos, total = calificar(apunte, st.session_state["respuestas_examen"])
        st.metric("Puntaje", f"{aciertos} de {total}")
        if aciertos == total and not st.session_state["celebracion_mostrada"]:
            st.balloons()
            st.session_state["celebracion_mostrada"] = True

    st.download_button(
        "Descargar guía de estudio",
        data=apunte.a_markdown(),
        file_name="guia_de_estudio.md",
        mime="text/markdown",
    )
