"""Tests del registro polisomnográfico cargado en memoria.

`Recording` es la estructura sobre la que opera todo lo demás, y la producen los
lectores. Por eso la mitad de estos tests no son sobre lo que el registro
**hace** sino sobre lo que **no deja construir**: un lector con un bug que
arme un registro incoherente tiene que fallar ahí y no tres capas más arriba.

Se usa la señal sintética de `conftest.py` —cuatro canales, diez minutos, que
son exactamente veinte ventanas de 30 segundos— y nunca un registro real.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.errors import (
    ChannelNotFoundError,
    DuplicateChannelError,
    InvalidRecordingError,
)

#: Clase de cada canal de la fixture `channel_names`, en su mismo orden.
CLASES = (ChannelKind.EEG, ChannelKind.EEG, ChannelKind.EOG, ChannelKind.EMG)


@pytest.fixture
def recording(synthetic_signal, channel_names, sampling_rate) -> Recording:
    """Un registro armado con la señal sintética de `conftest.py`."""
    canales = [
        Channel(name=nombre, kind=clase, unit="µV", index=i)
        for i, (nombre, clase) in enumerate(zip(channel_names, CLASES))
    ]
    return Recording(
        file_path=Path("sintetico.edf"),
        channels=canales,
        data=synthetic_signal,
        sampling_rate=sampling_rate,
        start_time=datetime(2026, 9, 4, 23, 30, 0),
    )


def canal(nombre: str, indice: int) -> Channel:
    """Un canal mínimo, para los tests que sólo miran la validación."""
    return Channel(name=nombre, kind=ChannelKind.EEG, unit="µV", index=indice)


# -- Lo que el registro sabe de sí mismo ------------------------------------


def test_la_cantidad_de_canales_es_la_de_la_lista(recording):
    assert recording.n_channels == 4


def test_la_cantidad_de_muestras_sale_de_la_señal(recording, sampling_rate):
    """Diez minutos a 256 Hz."""
    assert recording.n_samples == int(600 * sampling_rate)


def test_la_duracion_son_las_muestras_sobre_la_frecuencia(recording):
    assert recording.duration_seconds == pytest.approx(600.0)


def test_los_nombres_salen_en_el_orden_de_la_señal(recording, channel_names):
    """El orden importa: es el de las filas de la matriz."""
    assert recording.channel_names() == channel_names


# -- Buscar canales ---------------------------------------------------------


def test_se_busca_un_canal_por_su_nombre(recording):
    encontrado = recording.channel_by_name("C4")
    assert encontrado.name == "C4"
    assert encontrado.index == 1


def test_pedir_un_canal_que_no_existe_da_un_error_propio(recording):
    """No un `StopIteration` ni un `IndexError`: el usuario tiene que entenderlo."""
    with pytest.raises(ChannelNotFoundError) as excepcion:
        recording.channel_by_name("Fz")

    assert "Fz" in excepcion.value.message
    assert "C3" in (excepcion.value.details or "")


def test_se_filtran_los_canales_por_clase(recording):
    """Es lo que permite "mostrar todos los EEG" del selector de canales."""
    assert [c.name for c in recording.channels_of_kind(ChannelKind.EEG)] == ["C3", "C4"]
    assert [c.name for c in recording.channels_of_kind(ChannelKind.EOG)] == ["EOG-izq"]


def test_una_clase_sin_canales_devuelve_una_lista_vacia(recording):
    """No es un error: es un registro que no tiene ese tipo de señal."""
    assert recording.channels_of_kind(ChannelKind.ECG) == []


# -- Recortar tramos --------------------------------------------------------


def test_un_tramo_trae_todos_los_canales_por_defecto(recording, sampling_rate):
    tramo = recording.get_segment(0, int(30 * sampling_rate))
    assert tramo.shape == (4, int(30 * sampling_rate))


def test_se_puede_pedir_un_subconjunto_de_canales(recording, sampling_rate):
    """El visualizador dibuja sólo los canales visibles, no el registro entero."""
    tramo = recording.get_segment(0, int(30 * sampling_rate), channel_names=["C4"])
    assert tramo.shape == (1, int(30 * sampling_rate))


def test_los_canales_pedidos_salen_en_el_orden_pedido(recording):
    """Y no en el del registro: el usuario elige cómo apilarlos."""
    tramo = recording.get_segment(0, 10, channel_names=["EMG-menton", "C3"])
    esperado = recording.get_segment(0, 10)[[3, 0], :]
    assert np.array_equal(tramo, esperado)


def test_pedir_un_canal_inexistente_en_un_tramo_tambien_falla(recording):
    with pytest.raises(ChannelNotFoundError):
        recording.get_segment(0, 10, channel_names=["Fz"])


def test_el_tramo_que_se_pasa_del_final_sale_mas_corto(recording):
    """Es el caso normal de la última ventana, no un error.

    Un registro que no termina en un múltiplo exacto de 30 segundos tiene una
    última ventana incompleta, y `windows.window_to_samples` devuelve para ella
    un `stop` posterior al final del registro.
    """
    ultimo = recording.n_samples
    tramo = recording.get_segment(ultimo - 100, ultimo + 5_000)
    assert tramo.shape == (4, 100)


def test_el_tramo_es_el_mismo_dato_y_no_una_copia_alterada(recording, synthetic_signal):
    """Recortar no puede modificar la señal por el camino."""
    assert np.array_equal(recording.get_segment(0, 50), synthetic_signal[:, 0:50])


def test_un_indice_negativo_no_devuelve_señal_del_final_del_registro(recording):
    """El bug que más caro salía, porque el resultado era plausible.

    `core/windows.py` documenta que sus conversiones devuelven números negativos
    en silencio ante un índice de ventana negativo, y numpy interpreta un
    negativo como "desde el final". Sin esta guarda, pedir la ventana −1 dibujaba
    el final de la noche como si fuera el principio.
    """
    with pytest.raises(InvalidRecordingError):
        recording.get_segment(-100, -50)


def test_un_tramo_que_empieza_despues_de_terminar_se_rechaza(recording):
    """Devolvía un arreglo vacío, que se lee como "acá no hay señal"."""
    with pytest.raises(InvalidRecordingError):
        recording.get_segment(500, 100)


def test_el_tramo_devuelto_no_se_puede_modificar(recording):
    """Escribir en el tramo corrompía el registro entero.

    Y ocurría o no según qué canales hubiera pedido el usuario: sin lista, numpy
    devuelve un recorte que comparte memoria; con lista, copia. Marcarlo de sólo
    lectura iguala las dos ramas sin pagar una copia.
    """
    tramo = recording.get_segment(0, 50)
    with pytest.raises(ValueError):
        tramo[0, 0] = -999.0

    con_canales = recording.get_segment(0, 50, channel_names=["C3"])
    with pytest.raises(ValueError):
        con_canales[0, 0] = -999.0


def test_pedir_una_lista_vacia_de_canales_no_devuelve_ninguno(recording):
    """`None` y `[]` no son lo mismo: uno pide todos y el otro ninguno."""
    assert recording.get_segment(0, 10, channel_names=[]).shape == (0, 10)
    assert recording.get_segment(0, 10, channel_names=None).shape == (4, 10)


# -- Lo que no se deja construir --------------------------------------------


def test_una_señal_que_no_es_de_dos_dimensiones_se_rechaza():
    """Un lector que devuelva un solo canal aplanado tiene un bug."""
    with pytest.raises(InvalidRecordingError):
        Recording(
            file_path=Path("roto.edf"),
            channels=[canal("C3", 0)],
            data=np.zeros(1000),
            sampling_rate=256.0,
        )


def test_declarar_mas_canales_que_filas_se_rechaza():
    """El error más probable de un lector, y el que peor falla si pasa."""
    with pytest.raises(InvalidRecordingError) as excepcion:
        Recording(
            file_path=Path("roto.edf"),
            channels=[canal("C3", 0), canal("C4", 1)],
            data=np.zeros((1, 1000)),
            sampling_rate=256.0,
        )

    assert "2" in excepcion.value.message and "1" in excepcion.value.message


@pytest.mark.parametrize("frecuencia", [0.0, -256.0, float("nan"), float("inf")])
def test_una_frecuencia_de_muestreo_que_no_es_finita_y_positiva_se_rechaza(frecuencia):
    """Sin frecuencia válida no se puede ubicar ninguna ventana en el tiempo.

    NaN e infinito están en la lista por un motivo concreto: `<= 0` a secas es
    **falso** para NaN, así que la primera versión de esta validación los dejaba
    pasar. El NaN reaparecía mucho más lejos, como un `ValueError` de numpy
    adentro de `core/windows.py` —justo lo que `__post_init__` dice existir para
    evitar— y el infinito daba una duración de 0 segundos para un registro con
    muestras.
    """
    with pytest.raises(InvalidRecordingError):
        Recording(
            file_path=Path("roto.edf"),
            channels=[canal("C3", 0)],
            data=np.zeros((1, 1000)),
            sampling_rate=frecuencia,
        )


def test_una_señal_con_valores_enteros_se_rechaza():
    """Los enteros son las cuentas crudas del conversor del equipo.

    Que lleguen hasta acá significa que el lector no convirtió a microvoltios,
    que es el fallo que `utils/units.py` existe para impedir: la señal queda
    escalada por un factor arbitrario y en pantalla sigue pareciendo una señal.
    """
    with pytest.raises(InvalidRecordingError):
        Recording(
            file_path=Path("roto.edf"),
            channels=[canal("C3", 0)],
            data=np.zeros((1, 1000), dtype=np.int16),
            sampling_rate=256.0,
        )


def test_un_registro_sin_ningun_canal_se_rechaza():
    """No hay nada que mostrar ni que scorear, y las cuentas cerraban igual.

    `len(channels) == data.shape[0]` se cumple con cero de cada uno, así que
    este registro pasaba la validación entera.
    """
    with pytest.raises(InvalidRecordingError):
        Recording(
            file_path=Path("roto.edf"),
            channels=[],
            data=np.zeros((0, 1000)),
            sampling_rate=256.0,
        )


def test_una_ruta_que_no_es_una_ruta_se_rechaza():
    """Se valida primero porque todos los demás mensajes usan `file_path.name`.

    Con un `str`, el camino feliz construía sin quejarse y **cualquier otro
    error de validación** se convertía en un `AttributeError`, que es peor que
    el error que iba a reportar.
    """
    with pytest.raises(InvalidRecordingError):
        Recording(
            file_path="roto.edf",
            channels=[canal("C3", 0)],
            data=np.zeros((1, 1000)),
            sampling_rate=256.0,
        )


def test_un_canal_con_la_posicion_equivocada_se_rechaza():
    """`Channel.index` y la posición en la lista son la misma cosa.

    Si pudieran discrepar habría dos fuentes de verdad, y `get_segment` usa
    `index` para elegir la fila.
    """
    with pytest.raises(InvalidRecordingError) as excepcion:
        Recording(
            file_path=Path("roto.edf"),
            channels=[canal("C3", 0), canal("C4", 7)],
            data=np.zeros((2, 1000)),
            sampling_rate=256.0,
        )

    assert "C4" in (excepcion.value.details or "")


def test_dos_canales_con_el_mismo_nombre_se_rechazan():
    """Los canales se piden por nombre en toda la interfaz."""
    with pytest.raises(DuplicateChannelError) as excepcion:
        Recording(
            file_path=Path("roto.edf"),
            channels=[canal("C3", 0), canal("C3", 1)],
            data=np.zeros((2, 1000)),
            sampling_rate=256.0,
        )

    assert "C3" in (excepcion.value.details or "")


def test_un_registro_valido_se_construye_sin_quejarse(recording):
    """La contracara de los cinco anteriores.

    Sin este test, una validación demasiado estricta pasaría inadvertida: los
    otros seguirían en verde mientras ningún registro real se pudiera abrir.
    """
    assert recording.n_channels == 4
    assert recording.metadata == {}
    assert recording.start_time is not None
