from pydantic import BaseModel, Field, field_validator, model_validator


class Concepto(BaseModel):
    termino: str = Field(description="Término o concepto importante identificado en la página del cuaderno.")
    explicacion: str = Field(description="Explicación clara del término según el contenido de la página.")


class Tarjeta(BaseModel):
    pregunta: str = Field(description="Pregunta breve para repasar una idea del contenido de la página.")
    respuesta: str = Field(description="Respuesta correcta y concisa a la pregunta de repaso.")


class Pregunta(BaseModel):
    enunciado: str = Field(description="Enunciado de una pregunta de opción múltiple sobre el contenido de la página.")
    opciones: list[str] = Field(description="Opciones de respuesta para la pregunta.")
    correcta: int = Field(description="Índice, empezando en 0, de la opción correcta dentro de la lista de opciones.")

    @field_validator("opciones")
    @classmethod
    def validar_opciones(cls, opciones: list[str]) -> list[str]:
        if len(opciones) != 4:
            raise ValueError("La pregunta debe tener exactamente cuatro opciones.")

        if len({opcion.casefold() for opcion in opciones}) != 4:
            raise ValueError("Las cuatro opciones deben ser distintas, sin importar mayúsculas y minúsculas.")

        return opciones

    @model_validator(mode="after")
    def validar_indice_correcto(self) -> "Pregunta":
        if not 0 <= self.correcta < len(self.opciones):
            raise ValueError(
                f"El índice de la opción correcta debe estar entre 0 y {len(self.opciones) - 1}; "
                f"se recibió {self.correcta}."
            )

        return self


class Apunte(BaseModel):
    titulo: str = Field(description="Título breve que representa el tema principal de la página.")
    materia: str = Field(description="Materia escolar a la que corresponde el contenido de la página.")
    resumen: str = Field(description="Resumen claro de las ideas principales de la página.")
    conceptos: list[Concepto] = Field(description="Conceptos importantes de la página, con una explicación para cada uno.")
    tarjetas: list[Tarjeta] = Field(description="Tarjetas de pregunta y respuesta para repasar el contenido.")
    examen: list[Pregunta] = Field(description="Preguntas de opción múltiple para evaluar la comprensión del contenido.")
    dificultad: int = Field(description="Nivel de dificultad del contenido, expresado como un número entero.")

    @field_validator("dificultad")
    @classmethod
    def validar_dificultad(cls, dificultad: int) -> int:
        if not 1 <= dificultad <= 5:
            raise ValueError(f"La dificultad debe estar entre 1 y 5; se recibió {dificultad}.")

        return dificultad

    @model_validator(mode="after")
    def validar_cantidad_de_material(self) -> "Apunte":
        if len(self.conceptos) < 3:
            raise ValueError(f"El apunte debe incluir al menos 3 conceptos; se recibieron {len(self.conceptos)}.")
        if len(self.tarjetas) < 5:
            raise ValueError(f"El apunte debe incluir al menos 5 tarjetas; se recibieron {len(self.tarjetas)}.")
        if len(self.examen) < 3:
            raise ValueError(f"El apunte debe incluir al menos 3 preguntas de examen; se recibieron {len(self.examen)}.")

        return self
