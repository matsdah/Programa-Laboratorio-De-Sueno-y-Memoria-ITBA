"""Tests de las excepciones propias del programa.

`psglab/utils/errors.py` no tiene stubs y por eso se venía quedando sin test.
Pero es la pieza sobre la que se apoya **todo** el manejo de errores que ve el
investigador, y hace dos promesas que ningún otro archivo verifica:

1. El mensaje para el usuario y la causa técnica viajan **por separado**, para
   que la interfaz pueda mostrar uno y registrar el otro.
2. Las subclases se atrapan **todas con un solo `except PsgLabError`**, que es
   lo que permite que la ventana principal tenga un único lugar donde convertir
   un error en un cartel legible.

Si alguna de las dos se rompiera, el programa seguiría funcionando y la falla
sólo aparecería el día que un investigador viera una traza de Python en pantalla.
"""

import inspect

import pytest

from psglab.utils import errors
from psglab.utils.errors import (
    ChannelNotFoundError,
    InvalidRecordingError,
    PsgLabError,
    RecordingTooLargeError,
    UnknownUnitError,
    memoria_suficiente,
)


def test_el_mensaje_para_el_usuario_queda_accesible():
    """Es el texto que la interfaz muestra en el cartel."""
    error = PsgLabError("No se pudo abrir el registro.")
    assert error.message == "No se pudo abrir el registro."


def test_la_causa_tecnica_viaja_aparte_del_mensaje():
    """Separarlas es la razón de ser de esta clase.

    Un `KeyError: 'C3'` no le sirve al investigador, pero sí a quien diagnostica,
    así que tiene que estar disponible sin ensuciar el cartel.
    """
    error = PsgLabError("No se encontró el canal.", details="KeyError: 'C3'")
    assert error.message == "No se encontró el canal."
    assert error.details == "KeyError: 'C3'"


def test_la_causa_tecnica_es_opcional():
    """La mayoría de los errores no tienen nada técnico que agregar."""
    assert PsgLabError("Algo salió mal.").details is None


def test_el_mensaje_llega_a_la_representacion_estandar_de_python():
    """`str(error)` tiene que decir algo útil.

    Es lo que termina en un log o en una traza si el error escapa sin que nadie
    lo atrape, y ahí el mensaje en español sigue siendo más útil que un vacío.

    Ojo con lo que este test **no** prueba: `BaseException.__new__` ya guarda los
    argumentos posicionales, así que `str()` funcionaría igual sin el
    `super().__init__(message)` del constructor. Lo que sí verifica es que el
    mensaje viaje entero, sin el `details` pegado ni recortado.
    """
    error = PsgLabError("El registro está incompleto.", details="EOFError")
    assert str(error) == "El registro está incompleto."
    assert "EOFError" not in str(error)


def test_todas_las_excepciones_del_modulo_heredan_de_la_base():
    """La promesa que sostiene el manejo de errores de toda la interfaz.

    Se recorre el módulo en vez de enumerar las clases a mano: una excepción
    nueva que se olvide de heredar de `PsgLabError` tiene que hacer fallar esto,
    y una lista escrita a mano no la vería.
    """
    sueltas = [
        nombre
        for nombre, clase in inspect.getmembers(errors, inspect.isclass)
        if issubclass(clase, Exception)
        and clase.__module__ == errors.__name__
        and not issubclass(clase, PsgLabError)
    ]
    assert not sueltas, f"excepciones que no heredan de PsgLabError: {sueltas}"


def test_un_solo_except_atrapa_cualquiera_de_las_subclases():
    """Es lo que permite que haya un único lugar que convierte error en cartel."""
    subclases = [
        clase
        for _, clase in inspect.getmembers(errors, inspect.isclass)
        if issubclass(clase, PsgLabError) and clase is not PsgLabError
    ]
    assert subclases, "el módulo tiene que definir subclases; si no, este test no prueba nada"

    for clase in subclases:
        try:
            raise clase("Mensaje de prueba.", details="causa técnica")
        except PsgLabError as error:
            assert error.message == "Mensaje de prueba."
            assert error.details == "causa técnica"


def test_las_subclases_conservan_los_dos_campos():
    """Ninguna sobrescribe `__init__`, y no debería empezar a hacerlo."""
    error = ChannelNotFoundError("No existe el canal C3.", details="canales: C4, EOG")
    assert error.message == "No existe el canal C3."
    assert error.details == "canales: C4, EOG"


def test_una_subclase_no_atrapa_a_otra():
    """Heredar de una base común no puede volverlas intercambiables.

    Si `UnknownUnitError` atrapara un `ChannelNotFoundError`, un `except` pensado
    para un caso silenciaría el otro.
    """
    with pytest.raises(ChannelNotFoundError):
        raise ChannelNotFoundError("No existe el canal.")

    with pytest.raises(PsgLabError):
        raise UnknownUnitError("Unidad desconocida.")

    assert not issubclass(UnknownUnitError, ChannelNotFoundError)


def test_el_registro_incoherente_tiene_su_propio_error():
    """`InvalidRecordingError` no es lo mismo que no poder leer el archivo.

    El archivo se leyó bien; lo que quedó mal es el `Recording` que armó el
    lector. Distinguirlos es lo que hace que el mensaje apunte al bug.
    """
    assert issubclass(InvalidRecordingError, PsgLabError)
    assert not issubclass(InvalidRecordingError, errors.UnreadableFileError)


# -- Quedarse sin memoria (hito 18) ------------------------------------------


def test_un_memory_error_sale_como_error_del_programa():
    """**`MemoryError` era el único error que rompía la promesa del módulo.**

    No hereda de `PsgLabError`, así que atravesaba el `except` de la ventana
    principal y le llegaba al investigador como traza de Python. Y no es un
    caso remoto: la señal vive entera en memoria y una noche de 32 canales a
    256 Hz son 1,9 GB por copia.
    """
    with pytest.raises(RecordingTooLargeError):
        with memoria_suficiente("filtrar la señal"):
            raise MemoryError()


def test_el_cartel_dice_que_se_estaba_haciendo():
    """No es lo mismo quedarse sin memoria abriendo el archivo que
    filtrándolo: en el segundo caso el registro ya está en pantalla."""
    with pytest.raises(RecordingTooLargeError) as elevado:
        with memoria_suficiente("calcular la ICA"):
            raise MemoryError()

    assert "calcular la ICA" in elevado.value.message


def test_el_cartel_dice_que_el_registro_sigue_abierto():
    """Es la mitad accionable del mensaje: el investigador puede seguir
    trabajando, porque ninguna función de `analysis/` modifica su entrada."""
    with pytest.raises(RecordingTooLargeError) as elevado:
        with memoria_suficiente("filtrar la señal"):
            raise MemoryError()

    assert "sin cambios" in elevado.value.message
    assert elevado.value.details


def test_lo_que_no_es_un_memory_error_pasa_de_largo():
    """No se traga otros errores: un `ValueError` de MNE tiene que seguir
    llegando a quien lo sepa traducir."""
    with pytest.raises(ValueError):
        with memoria_suficiente("filtrar la señal"):
            raise ValueError("otra cosa")


def test_sin_error_no_hace_nada():
    with memoria_suficiente("filtrar la señal"):
        resultado = 2 + 2

    assert resultado == 4
