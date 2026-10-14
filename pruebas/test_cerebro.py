import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from cerebro import ImagenIlegible, analizar_pagina, calificar, crear_cliente
from modelos import Apunte, Pregunta


class ClienteFalso:
    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.llamadas = []
        self.models = self

    def generate_content(self, **kwargs):
        self.llamadas.append(kwargs)
        return self.respuesta


@pytest.fixture
def datos_apunte():
    pregunta = {
        "enunciado": "¿Cuál es la respuesta correcta?",
        "opciones": ["Primera", "Segunda", "Tercera", "Cuarta"],
        "correcta": 1,
    }
    return {
        "titulo": "La célula",
        "materia": "Ciencias",
        "resumen": "La célula es la unidad básica de los seres vivos.",
        "conceptos": [
            {"termino": f"Concepto {indice}", "explicacion": "Explicación del concepto."}
            for indice in range(3)
        ],
        "tarjetas": [
            {"pregunta": f"Pregunta {indice}", "respuesta": f"Respuesta {indice}"}
            for indice in range(5)
        ],
        "examen": [pregunta, {**pregunta, "correcta": 2}, {**pregunta, "correcta": 3}],
        "dificultad": 3,
    }


@pytest.fixture
def apunte(datos_apunte):
    return Apunte.model_validate(datos_apunte)


def test_devuelve_un_apunte_cuando_la_ia_contesta_bien(apunte):
    cliente = ClienteFalso(SimpleNamespace(parsed=apunte, text=None))

    resultado = analizar_pagina(b"imagen", "image/jpeg", cliente)

    assert resultado is apunte


def test_envia_el_esquema_y_el_tipo_de_respuesta_json(apunte):
    cliente = ClienteFalso(SimpleNamespace(parsed=apunte, text=None))

    analizar_pagina(b"imagen", "image/jpeg", cliente)

    configuracion = cliente.llamadas[0]["config"]
    assert configuracion.response_schema is Apunte
    assert configuracion.response_mime_type == "application/json"


def test_recupera_el_apunte_desde_texto_json_cuando_parsed_viene_vacio(datos_apunte):
    cliente = ClienteFalso(SimpleNamespace(parsed=None, text=json.dumps(datos_apunte)))

    resultado = analizar_pagina(b"imagen", "image/jpeg", cliente)

    assert isinstance(resultado, Apunte)
    assert resultado.titulo == datos_apunte["titulo"]


def test_avisa_claro_cuando_la_ia_no_devuelve_nada():
    cliente = ClienteFalso(None)

    with pytest.raises(ImagenIlegible, match="No recibimos un análisis de la página"):
        analizar_pagina(b"imagen", "image/jpeg", cliente)

    assert len(cliente.llamadas) == 1


def test_avisa_claro_cuando_la_ia_devuelve_texto_que_no_es_json():
    cliente = ClienteFalso(SimpleNamespace(parsed=None, text="Esto no es JSON"))

    with pytest.raises(ImagenIlegible, match="Probá con una foto más clara"):
        analizar_pagina(b"imagen", "image/jpeg", cliente)


def test_no_llama_a_la_ia_si_no_hay_imagen():
    cliente = ClienteFalso(None)

    with pytest.raises(ValueError, match="No se recibió ninguna imagen"):
        analizar_pagina(b"", "image/jpeg", cliente)

    assert cliente.llamadas == []


def test_no_se_puede_crear_cliente_sin_llave():
    with pytest.raises(ValueError, match="La llave de la API no puede estar vacía"):
        crear_cliente("   ")


def test_rechaza_una_pregunta_con_indice_correcto_fuera_de_rango():
    with pytest.raises(ValidationError, match="índice de la opción correcta"):
        Pregunta(
            enunciado="¿Cuál?",
            opciones=["A", "B", "C", "D"],
            correcta=4,
        )


def test_rechaza_opciones_repetidas_sin_distinguir_mayusculas():
    with pytest.raises(ValidationError, match="deben ser distintas"):
        Pregunta(
            enunciado="¿Cuál?",
            opciones=["Respuesta", "respuesta", "Otra", "Una más"],
            correcta=0,
        )


def test_rechaza_un_apunte_con_menos_tarjetas_de_las_pedidas(datos_apunte):
    datos_apunte["tarjetas"] = datos_apunte["tarjetas"][:4]

    with pytest.raises(ValidationError, match="al menos 5 tarjetas"):
        Apunte.model_validate(datos_apunte)


def test_rechaza_dificultad_fuera_de_rango(datos_apunte):
    datos_apunte["dificultad"] = 6

    with pytest.raises(ValidationError, match="dificultad debe estar entre 1 y 5"):
        Apunte.model_validate(datos_apunte)


def test_calificar_cuenta_todas_las_respuestas_correctas(apunte):
    assert calificar(apunte, {0: 1, 1: 2, 2: 3}) == (3, 3)


def test_calificar_cuenta_respuestas_correctas_y_erroneas(apunte):
    assert calificar(apunte, {0: 1, 1: 0, 2: 3}) == (2, 3)


def test_calificar_cuenta_como_incorrectas_las_preguntas_sin_responder(apunte):
    assert calificar(apunte, {}) == (0, 3)
