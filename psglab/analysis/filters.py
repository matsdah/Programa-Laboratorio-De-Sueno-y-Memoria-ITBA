"""Filtrado de la señal cruda.

Permite importar un registro sin filtros y aplicarle pasa-altos, pasa-bajos y
notch, con rangos distintos según el tipo de canal. Los rangos por defecto son
los habituales en polisomnografía, pero el usuario los puede cambiar: son
valores de referencia, no una imposición.

El notch es 50 Hz en Argentina (frecuencia de la red eléctrica). En países con
red de 60 Hz hay que cambiarlo, así que queda configurable.

**Por qué `validate()` rechaza más de lo que MNE rechaza.** Se midió qué hace
MNE con un pasa-altos por encima del pasa-bajos —40 y 10 Hz, digamos— y la
respuesta es el peor caso posible: **lo acepta, arma en silencio un filtro de
banda eliminada y no avisa nada**. Es una función legítima de MNE, pero acá los
dos números salen de dos campos rotulados "pasa-altos" y "pasa-bajos", así que
un 40 y un 10 son un error de tipeo, no un pedido de banda eliminada. Con la
señal de prueba —1, 10 y 50 Hz— el resultado volvía **sin atenuar nada**: el
investigador cree que filtró y está mirando la señal cruda.

Por lo mismo se rechaza el cero, que MNE interpreta como "sin filtro", y lo que
no es finito, que llega hasta adentro y sale como `cannot convert float NaN to
integer`.

**Y por qué igual hay un `except` alrededor de MNE.** La comprobación de
Nyquist es necesaria pero **no suficiente para el notch**: el notch se arma
como una banda alrededor de la frecuencia, y esa banda puede pasarse de Nyquist
aunque la frecuencia no. Medido: a 101 Hz de muestreo un notch de 50 Hz está
por debajo de Nyquist (50,5) y MNE lo rechaza igual, porque el borde superior
de su banda cae en 50,625. Lo que la validación no puede explicar bien se
atrapa y se traduce, en vez de dejar salir un `ValueError` crudo que la ventana
principal no atrapa.

**Qué pasa con lo que no es eléctrico**, que es donde este módulo se aparta de
`reference.py`: acá **sí se filtra**. Restarle microvoltios a un termómetro
inventa una temperatura, pero filtrar es una operación sobre el tiempo y no
sobre la unidad, y el canal respiratorio de `DEFAULT_FILTERS` existe justamente
para eso: un pasa-bajos de 5 Hz sobre el flujo es lo habitual.

**Un canal grabado más lento que el registro** (hito 67). Un EDF puede traer
canales de 1 Hz junto a otros de 100 Hz, y MNE los lleva a todos a la más
alta: el canal lento llega a 100 Hz, pero no tiene nada por encima de 0,5 Hz.
Un pasa-altos por encima de eso lo deja plano —el EMG submental del EDF del
laboratorio quedaba con el 0,0 % de su desvío con el de 10 Hz que se sugiere
para EMG— y el programa decía «Se filtró la señal». `apply_filters()` lo
rechaza, y `settings_for_kinds()`, que reparte los filtros de una clase, no se
lo da a ese canal. La frecuencia de origen es `Channel.original_sampling_rate`.

Cubre del pliego: V1_F de "Filtración de la señal".
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Final

import numpy as np

from psglab.analysis.mne_bridge import _registro_parcial, from_raw, to_raw
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.errors import (
    InvalidFilterError,
    InvalidRecordingError,
    memoria_suficiente,
)


@dataclass
class FilterSettings:
    """Filtros a aplicar a un canal.

    Attributes:
        highpass_hz: frecuencia de corte del pasa-altos. None lo desactiva.
        lowpass_hz: frecuencia de corte del pasa-bajos. None lo desactiva.
        notch_hz: frecuencia del notch. None lo desactiva.
    """

    highpass_hz: float | None = None
    lowpass_hz: float | None = None
    notch_hz: float | None = None

    @property
    def is_empty(self) -> bool:
        """Si no activa ningún filtro: aplicarla deja el canal como estaba."""
        return self.highpass_hz is None and self.lowpass_hz is None and self.notch_hz is None


#: Frecuencia de la red eléctrica, que es la que hay que filtrar con el notch.
#: 50 Hz en Argentina y en la mayor parte del mundo; 60 Hz en América del Norte
#: y parte de América del Sur. Se declara una sola vez para que cambiarla sea
#: un cambio y no cinco.
DEFAULT_NOTCH_HZ: Final[float] = 50.0

#: Cuántos canales se le pasan a MNE por llamada al filtrar (hito 59). Medido
#: sobre 32 canales a 256 Hz y una hora: de a uno el pico es 1,13 copias de la
#: señal y tarda 4,0 s; de a cuatro, 1,32 y 2,9 s; todos juntos, 3,07 y 2,5 s.
#: Cuatro recupera casi todo el tiempo y deja casi toda la memoria.
_CANALES_POR_TANDA: Final[int] = 4

#: Rangos habituales por tipo de canal, ofrecidos como punto de partida.
DEFAULT_FILTERS: Final[dict[ChannelKind, FilterSettings]] = {
    ChannelKind.EEG: FilterSettings(highpass_hz=0.3, lowpass_hz=35.0, notch_hz=DEFAULT_NOTCH_HZ),
    ChannelKind.EOG: FilterSettings(highpass_hz=0.3, lowpass_hz=15.0, notch_hz=DEFAULT_NOTCH_HZ),
    ChannelKind.EMG: FilterSettings(highpass_hz=10.0, lowpass_hz=100.0, notch_hz=DEFAULT_NOTCH_HZ),
    ChannelKind.ECG: FilterSettings(highpass_hz=0.5, lowpass_hz=70.0, notch_hz=DEFAULT_NOTCH_HZ),
    ChannelKind.RESPIRATORY: FilterSettings(highpass_hz=0.05, lowpass_hz=5.0),
    ChannelKind.OTHER: FilterSettings(),
}


def _exigir_registro(recording: Recording) -> None:
    """Rechaza como `PsgLabError` lo que no sea un `Recording`."""
    if not isinstance(recording, Recording):
        raise InvalidRecordingError(
            "No se puede filtrar eso: no es un registro abierto.",
            details=f"recording es {type(recording).__name__}, se esperaba Recording.",
        )


def _frecuencia(valor: object, rotulo: str) -> float | None:
    """Devuelve la frecuencia como número, o eleva un error explicando cuál.

    `None` pasa: es como se desactiva cada filtro. Lo demás tiene que ser un
    número finito y positivo. **El cero se rechaza a propósito**: MNE lo
    interpreta como "sin filtro", así que aceptarlo dejaría al usuario creyendo
    que puso un corte donde no puso ninguno.
    """
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise InvalidFilterError(
            f"El {rotulo} tiene que ser un número en Hz.",
            details=f"{rotulo} = {valor!r} ({type(valor).__name__}).",
        )
    numero = float(valor)
    if not math.isfinite(numero):
        raise InvalidFilterError(
            f"El {rotulo} tiene que ser un número en Hz.",
            details=f"{rotulo} = {numero!r}.",
        )
    if numero <= 0:
        raise InvalidFilterError(
            f"El {rotulo} tiene que ser mayor que cero. Para desactivarlo, se "
            "deja vacío.",
            details=f"{rotulo} = {numero} Hz.",
        )
    return numero


def _frecuencia_de_muestreo(valor: object) -> float:
    """La frecuencia de muestreo como número, o un error que se pueda leer.

    La usan `validate()` y `default_for()`, que desde el hito 17 son las dos
    que necesitan saber dónde cae Nyquist.
    """
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise InvalidFilterError(
            "No se puede trabajar con el filtro sin la frecuencia de muestreo "
            "del registro.",
            details=f"sampling_rate es {type(valor).__name__}.",
        )
    numero = float(valor)
    if not math.isfinite(numero) or numero <= 0:
        raise InvalidFilterError(
            "No se puede trabajar con el filtro sin la frecuencia de muestreo "
            "del registro.",
            details=f"sampling_rate = {numero!r}.",
        )
    return numero


def _original_mas_lenta(channel: Channel, sampling_rate: float) -> float | None:
    """La frecuencia a la que se grabó el canal, si es menor que la del registro.

    Es la que dice hasta dónde tiene contenido de verdad: por encima de su
    mitad, lo que trae es interpolación. `None` si el archivo no la informa o
    si el canal se grabó a la frecuencia del registro, que es lo común.
    """
    original = channel.original_sampling_rate
    if original is None or not original < sampling_rate:
        return None
    return float(original)


def _hz(valor: float) -> str:
    """Una frecuencia como la lee el investigador: 0,5 y no 0.5."""
    return f"{valor:g}".replace(".", ",")


def _borra_el_canal(filtros: FilterSettings, original: float | None) -> bool:
    """Si el pasa-altos queda por encima de lo que el canal contiene."""
    paso_alto = filtros.highpass_hz
    return (
        original is not None
        and isinstance(paso_alto, (int, float))
        and not isinstance(paso_alto, bool)
        and paso_alto >= original / 2
    )


def _mismo_registro_con(recording: Recording, datos: np.ndarray) -> Recording:
    """Un `Recording` nuevo con los mismos canales y otros datos.

    Existe para no armar un `Recording` a mano en dos lugares del módulo y que
    uno de los dos se olvide de copiar los metadatos.
    """
    return Recording(
        file_path=recording.file_path,
        channels=list(recording.channels),
        data=datos,
        sampling_rate=recording.sampling_rate,
        start_time=recording.start_time,
        metadata=dict(recording.metadata),
    )


def apply_filters(
    recording: Recording,
    settings: dict[str, FilterSettings],
) -> Recording:
    """Aplica los filtros indicados y devuelve un registro nuevo.

    Args:
        settings: filtros por nombre de canal. Los canales que no aparezcan
            quedan sin filtrar.

    Returns:
        Un `Recording` nuevo. El original queda intacto para poder comparar.

    Raises:
        InvalidFilterError: si una frecuencia de corte supera la frecuencia de
            Nyquist del registro, si el pasa-altos queda por encima del
            pasa-bajos, o si queda por encima de la mitad de la frecuencia a
            la que **se grabó** el canal, que lo dejaría plano (hito 67).
        ChannelNotFoundError: si `settings` nombra un canal que el registro no
            tiene. **No se lo ignora en silencio**: un nombre mal escrito
            dejaría al investigador convencido de que filtró un canal que quedó
            crudo, y la pantalla no se lo va a decir.
        InvalidRecordingError: si lo que se pasa no es un registro, o si
            `settings` no es un diccionario de `FilterSettings`.

    **Se valida todo antes de tocar un solo dato.** Si el pedido tiene un canal
    con frecuencias imposibles, no se filtra ninguno: media señal filtrada y
    media cruda es un estado del que nadie puede sacar conclusiones, y a simple
    vista no se distingue de una señal entera.
    """
    _exigir_registro(recording)
    if not isinstance(settings, dict):
        raise InvalidRecordingError(
            "No se puede filtrar con eso: hacen falta los filtros de cada canal.",
            details=f"settings es {type(settings).__name__}, se esperaba dict.",
        )

    # Primera pasada: que exista cada canal y que sus filtros sean aplicables.
    # `channel_by_name()` es el que eleva `ChannelNotFoundError`.
    indices: dict[str, int] = {}
    for nombre, filtros in settings.items():
        if not isinstance(filtros, FilterSettings):
            raise InvalidRecordingError(
                f"Los filtros de «{nombre}» no son filtros.",
                details=(
                    f"settings[{nombre!r}] es {type(filtros).__name__}, se "
                    "esperaba FilterSettings."
                ),
            )
        validate(filtros, recording.sampling_rate)
        canal = recording.channel_by_name(nombre)
        original = _original_mas_lenta(canal, recording.sampling_rate)
        if original is not None and _borra_el_canal(filtros, original):
            raise InvalidFilterError(
                f"El pasa-altos de {_hz(filtros.highpass_hz)} Hz no se puede aplicar a "
                f"«{nombre}»: se grabó a {_hz(original)} Hz, así que no tiene nada por "
                f"encima de {_hz(original / 2)} Hz, y el filtro lo dejaría plano.",
                details=(
                    f"highpass_hz = {filtros.highpass_hz}, frecuencia original = "
                    f"{original} Hz, frecuencia del registro = "
                    f"{recording.sampling_rate} Hz."
                ),
            )
        indices[nombre] = canal.index

    activos = {
        nombre: filtros
        for nombre, filtros in settings.items()
        if filtros != FilterSettings()
    }

    # **Nada que filtrar: se copia y listo, sin pasar por MNE.** Igual sale un
    # registro nuevo, porque la promesa de la carpeta es ésa, pero el viaje de
    # ida y vuelta costaba tres copias completas de la señal para no cambiarle
    # nada —1337 MB sobre el registro real de 22 h—. Es el caso de abrir el
    # panel, vaciar las celdas y aplicar, que es una forma legítima de decir
    # "quiero la señal como está".
    if not activos:
        with memoria_suficiente("copiar la señal"):
            copia = np.array(recording.data, dtype=float, copy=True)
        return _mismo_registro_con(recording, copia)

    # **De a tandas de canales, sobre una salida que se reserva una vez** (hito
    # 59). Cada filtro mira un solo canal, así que el resultado es el mismo que
    # pasándolos todos juntos; lo que cambia es el pico. Con la señal entera en
    # un `Raw`, MNE la copiaba a la ida y a la vuelta: tres copias, cuatro si ya
    # había una filtrada. Así son el original, la salida y una tanda.
    #
    # **Los canales que nadie pidió filtrar ya están en la salida**, copiados
    # del original sin pasar por MNE. Antes se los restauraba después, porque
    # el viaje µV → V → µV del puente les dejaba error de punto flotante —del
    # orden de 1e-16— y volvía indemostrable que un canal sin filtros vuelve
    # igual.
    with memoria_suficiente("filtrar la señal"):
        salida = np.array(recording.data, dtype=float, copy=True)

    # Una tanda son canales con los mismos filtros: MNE arma el núcleo del
    # filtro una vez por llamada.
    grupos: dict[tuple[float | None, float | None, float | None], list[str]] = {}
    for nombre, filtros in activos.items():
        clave = (filtros.highpass_hz, filtros.lowpass_hz, filtros.notch_hz)
        grupos.setdefault(clave, []).append(nombre)

    for (paso_alto, paso_bajo, notch), nombres in grupos.items():
        for desde in range(0, len(nombres), _CANALES_POR_TANDA):
            tanda = nombres[desde : desde + _CANALES_POR_TANDA]
            filas = [indices[nombre] for nombre in tanda]
            parte = _registro_parcial(recording, tanda, recording.data[filas])
            raw = to_raw(parte)
            _filtrar_grupo(raw, list(range(len(tanda))), paso_alto, paso_bajo, notch)
            salida[filas] = from_raw(raw, parte).data
    return _mismo_registro_con(recording, salida)


def _filtrar_grupo(
    raw: Any,
    picks: list[int],
    highpass_hz: float | None,
    lowpass_hz: float | None,
    notch_hz: float | None,
) -> None:
    """Le pasa a MNE un grupo de canales que llevan los mismos filtros.

    Traduce a `InvalidFilterError` lo que MNE rechace. La validación de arriba
    atrapa lo que puede explicar bien; **esto es la red para lo que no**, y no
    es una guarda de más: el notch se arma como una banda alrededor de la
    frecuencia y esa banda puede pasarse de Nyquist aunque la frecuencia no
    —medido a 101 Hz de muestreo con un notch de 50—. Sin esto sale un
    `ValueError` crudo, que la ventana principal no atrapa porque sólo atrapa
    `PsgLabError`, y le llega al investigador como traza de Python.
    """
    try:
        with memoria_suficiente("filtrar la señal"):
            if highpass_hz is not None or lowpass_hz is not None:
                raw.filter(highpass_hz, lowpass_hz, picks=picks, verbose="ERROR")
            if notch_hz is not None:
                raw.notch_filter([notch_hz], picks=picks, verbose="ERROR")
    except ValueError as error:
        raise InvalidFilterError(
            "No se pudo aplicar el filtro con esas frecuencias. Suele pasar "
            "cuando el corte queda demasiado cerca de la mitad de la frecuencia "
            "de muestreo del registro.",
            details=str(error),
        ) from error


def settings_for_kinds(
    recording: Recording,
    by_kind: dict[ChannelKind, FilterSettings],
) -> dict[str, FilterSettings]:
    """Reparte filtros por clase de canal a los canales que tienen esa clase.

    **Existe porque la regla es del pliego y no de la pantalla.** V1_F pide
    filtrar *por tipo de canal*, mientras que `apply_filters()` recibe filtros
    *por nombre de canal*, que es la firma general —permite darle a C3 algo
    distinto que a C4—. Traducir de una a la otra es la regla, así que vive acá
    y no en el diálogo: en `ui/` no se podría correr desde un script del
    laboratorio ni testear sin abrir una ventana.

    **A un canal grabado más lento que el registro no le da el pasa-altos**
    que lo dejaría plano (hito 67): el resto de los filtros de su clase sí.
    Es la misma regla con que `default_for()` deja vacío un corte que el
    registro no admite, aplicada a cada canal; `apply_filters()` rechazaría
    el pedido entero, y la clase no puede saber qué canales la comparten.

    Args:
        by_kind: filtros por clase. Las clases que no aparezcan quedan sin
            filtrar, igual que los canales que no aparecen en `apply_filters()`.

    Returns:
        Un diccionario listo para `apply_filters()`.

    Raises:
        InvalidRecordingError: si no se le pasa un registro, o si `by_kind` no
            es un diccionario.
        InvalidFilterError: si alguna clave no es un `ChannelKind` o algún valor
            no es un `FilterSettings`.
    """
    _exigir_registro(recording)
    if not isinstance(by_kind, dict):
        raise InvalidRecordingError(
            "No se puede filtrar con eso: hacen falta los filtros de cada clase "
            "de canal.",
            details=f"by_kind es {type(by_kind).__name__}, se esperaba dict.",
        )
    for clase, filtros in by_kind.items():
        if not isinstance(clase, ChannelKind):
            raise InvalidFilterError(
                "Los filtros se reparten por clase de canal, y eso no es una "
                "clase de canal.",
                details=f"clave {clase!r} ({type(clase).__name__}).",
            )
        if not isinstance(filtros, FilterSettings):
            raise InvalidFilterError(
                f"Los filtros de {clase.name} no son filtros.",
                details=f"by_kind[{clase!r}] es {type(filtros).__name__}.",
            )

    por_canal: dict[str, FilterSettings] = {}
    for canal in recording.channels:
        if canal.kind not in by_kind:
            continue
        filtros = by_kind[canal.kind]
        if _borra_el_canal(filtros, _original_mas_lenta(canal, recording.sampling_rate)):
            filtros = replace(filtros, highpass_hz=None)
        por_canal[canal.name] = filtros
    return por_canal


def default_for(
    kind: ChannelKind, sampling_rate: float | None = None
) -> FilterSettings:
    """Filtros sugeridos para un tipo de canal.

    Args:
        sampling_rate: la del registro al que se le van a aplicar. Con ella,
            **los cortes que caen en Nyquist o por encima se descartan**; sin
            ella se devuelve la fila de la tabla tal cual.

    Returns:
        Una **copia**, no la fila de `DEFAULT_FILTERS`. `FilterSettings` es un
        dataclass mutable, así que devolver la compartida haría que cualquiera
        que ajuste el valor que recibió le cambie los valores por defecto al
        programa entero, para todos los registros y hasta que se cierre. Eso es
        exactamente lo que el diálogo de filtros hace: pedir los sugeridos y
        dejar que el usuario los edite.

    Raises:
        InvalidFilterError: si no se le pasa un `ChannelKind`. Sin la guarda
            salía un `KeyError` crudo, que la ventana principal no atrapa.
            También si la frecuencia de muestreo no es un número positivo.

    **Por qué existe el segundo argumento.** La tabla es la de polisomnografía
    y no depende del registro, pero **su resultado sí**: en un registro de
    100 Hz, Nyquist cae en 50 y el notch sugerido es exactamente 50, así que
    `validate()` lo rechaza y el investigador que abre el panel y aprieta
    Aplicar recibe un cartel de error sin haber tocado nada. El pasa-bajos de
    100 Hz del EMG tiene el mismo problema en cualquier registro por debajo de
    200 Hz. Y 100 Hz no es un caso raro: es lo que usa buena parte del
    equipamiento clínico. Lo destapó el hito 17 corriendo la Parte 2 sobre un
    registro real, que es la única forma de encontrarlo.

    **Se descarta, no se recorta, y el motivo es físico.** Por encima de
    Nyquist el registro **no contiene nada**: un pasa-bajos de 100 Hz sobre una
    señal muestreada a 100 Hz no filtraría nada aunque MNE pudiera
    construirlo, porque el muestreo ya limitó la banda. Ofrecerlo es ofrecer
    una operación vacía. Recortarlo a un valor arbitrario —el 80 % de Nyquist,
    digamos— sería inventarle al investigador un criterio clínico que nadie
    eligió, y encima disfrazado de valor por defecto.
    """
    if not isinstance(kind, ChannelKind):
        raise InvalidFilterError(
            "No se pueden sugerir filtros para eso: no es un tipo de canal.",
            details=f"kind es {type(kind).__name__}, se esperaba ChannelKind.",
        )
    sugeridos = replace(DEFAULT_FILTERS[kind])
    if sampling_rate is None:
        return sugeridos

    nyquist = _frecuencia_de_muestreo(sampling_rate) / 2
    for atributo in ("highpass_hz", "lowpass_hz", "notch_hz"):
        valor = getattr(sugeridos, atributo)
        if valor is not None and valor >= nyquist:
            setattr(sugeridos, atributo, None)
    return sugeridos


def validate(settings: FilterSettings, sampling_rate: float) -> None:
    """Verifica que los filtros sean aplicables al registro.

    Raises:
        InvalidFilterError: con un mensaje explicando el problema en términos
            que el usuario pueda entender.

    Lo que rechaza, y por qué cada uno:

    - **Un corte por encima de Nyquist**, que es la mitad de la frecuencia de
      muestreo. Por encima de ahí no hay señal que filtrar: no está en el
      archivo. La comparación es estricta —justo en Nyquist tampoco vale—,
      igual que en MNE.
    - **El pasa-altos por encima del pasa-bajos.** Es el rechazo que más
      importa, porque es el único que MNE **no** hace: acepta el par y arma una
      banda eliminada sin avisar. Ver el docstring del módulo.
    - **Frecuencias que no son números finitos y positivos.** El cero incluido:
      para desactivar un filtro se deja vacío.
    """
    if not isinstance(settings, FilterSettings):
        raise InvalidFilterError(
            "No se puede validar eso: no son filtros.",
            details=f"settings es {type(settings).__name__}, se esperaba FilterSettings.",
        )
    frecuencia = _frecuencia_de_muestreo(sampling_rate)

    paso_alto = _frecuencia(settings.highpass_hz, "pasa-altos")
    paso_bajo = _frecuencia(settings.lowpass_hz, "pasa-bajos")
    notch = _frecuencia(settings.notch_hz, "notch")

    nyquist = frecuencia / 2
    for valor, rotulo in ((paso_alto, "pasa-altos"), (paso_bajo, "pasa-bajos"), (notch, "notch")):
        if valor is not None and valor >= nyquist:
            raise InvalidFilterError(
                f"El {rotulo} de {valor:g} Hz no se puede aplicar a este "
                f"registro: con {frecuencia:g} Hz de muestreo, la frecuencia "
                f"más alta que contiene la señal es {nyquist:g} Hz.",
                details=f"{rotulo} = {valor} Hz, Nyquist = {nyquist} Hz.",
            )

    if paso_alto is not None and paso_bajo is not None and paso_alto >= paso_bajo:
        raise InvalidFilterError(
            f"El pasa-altos ({paso_alto:g} Hz) tiene que quedar por debajo del "
            f"pasa-bajos ({paso_bajo:g} Hz): al revés no queda ninguna banda "
            "para dejar pasar.",
            details=f"highpass_hz = {paso_alto}, lowpass_hz = {paso_bajo}.",
        )
