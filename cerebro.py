import json

from google.genai import Client, types
from pydantic import ValidationError

from modelos import Apunte


MODELO = "gemini-3.8-flash"
INSTRUCCION_SISTEMA = (
    "Actúa como un profesor paciente de bachillerato de El Salvador. "
    "Escribe siempre en español salvadoreño claro. Basa tu respuesta únicamente "
    "en lo que se ve en la imagen y no inventes temas. Si la foto está borrosa, "
    "indícalo en el resumen en vez de inventar contenido. Haz que las opciones "
    "incorrectas del examen sean creíbles, no absurdas, y varía la posición de "
    "la respuesta correcta entre las preguntas."
)


class ImagenIlegible(Exception):
    """Indica que no se pudo obtener un apunte válido de la imagen."""


def crear_cliente(api_key: str) -> Client:
    if not api_key or not api_key.strip():
        raise ValueError("La llave de la API no puede estar vacía.")

    return Client(api_key=api_key)


def analizar_pagina(datos_imagen: bytes, tipo_mime: str, cliente: Client) -> Apunte:
    if not datos_imagen:
        raise ValueError("No se recibió ninguna imagen para analizar.")

    respuesta = cliente.models.generate_content(
        model=MODELO,
        contents=[
            types.Part.from_bytes(data=datos_imagen, mime_type=tipo_mime),
            "Analiza esta página del cuaderno y crea el apunte solicitado.",
        ],
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCCION_SISTEMA,
            response_mime_type="application/json",
            response_schema=Apunte,
            temperature=0.4,
        ),
    )

    if respuesta is None:
        raise ImagenIlegible(
            "No recibimos un análisis de la página. Probá de nuevo con una foto clara y bien enfocada."
        )

    if isinstance(respuesta.parsed, Apunte):
        return respuesta.parsed

    try:
        datos = json.loads(respuesta.text)
        return Apunte.model_validate(datos)
    except (json.JSONDecodeError, TypeError, ValidationError) as error:
        raise ImagenIlegible(
            "No pudimos leer bien la página. Probá con una foto más clara, enfocada y con buena iluminación."
        ) from error


def calificar(apunte: Apunte, respuestas: dict) -> tuple[int, int]:
    """Cuenta aciertos; respuestas usa el índice de cada pregunta como clave y el de opción como valor."""
    total = len(apunte.examen)
    aciertos = sum(
        respuestas.get(indice) == pregunta.correcta
        for indice, pregunta in enumerate(apunte.examen)
    )
    return aciertos, total
