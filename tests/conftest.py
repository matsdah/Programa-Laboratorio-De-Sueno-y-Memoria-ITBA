"""Fixtures compartidas por todos los tests.

Los tests usan **registros sintéticos generados en el momento**, nunca
registros reales de participantes: no se suben datos de personas al
repositorio.

Un registro sintético además es mejor para testear, porque se conoce de
antemano el resultado correcto. Si se genera una onda de 10 Hz, la PSD tiene
que dar un pico en 10 Hz, y eso se puede afirmar en un test.
"""

# **Antes de importar nada de Qt.** El plugin de plataforma se elige al crear la
# `QApplication`, y "offscreen" es lo que permite que los tests de `ui/` corran
# sin pantalla: en el CI no hay ninguna, y en una máquina de trabajo evita que
# la suite abra ventanas por sorpresa.
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pathlib

import numpy as np
import pytest

from datetime import datetime
from pathlib import Path

from psglab.config import WINDOW_SECONDS
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.units import MICROVOLT

#: Ventanas que dura la señal sintética. Se multiplica por `WINDOW_SECONDS` en
#: vez de escribir los 600 segundos a mano: `config.py` promete que cambiar la
#: duración de la ventana se hace en un solo lugar, y con el 600 escrito acá esa
#: promesa era falsa.
VENTANAS_SINTETICAS = 20


@pytest.fixture
def sampling_rate() -> float:
    """Frecuencia de muestreo típica de un registro de polisomnografía."""
    return 256.0


@pytest.fixture
def synthetic_signal(sampling_rate: float) -> np.ndarray:
    """Diez minutos de señal sintética de cuatro canales, en microvoltios.

    Cada canal lleva una frecuencia coherente con el tipo de señal que
    representa, para que los tests de análisis espectral sean a la vez
    verificables y plausibles:

        C3          ->  1 Hz   (delta, sueño lento)
        C4          -> 10 Hz   (alfa)
        EOG-izq     ->  0,5 Hz (movimientos oculares lentos)
        EMG-menton  -> 30 Hz   (actividad muscular)

    El orden coincide con el de la fixture `channel_names`.

    Son exactamente `VENTANAS_SINTETICAS` ventanas completas, un número cómodo
    para verificar los cálculos a mano. La duración sale de
    `config.WINDOW_SECONDS`, así que cambiar la ventana del pliego no rompe
    ningún test.
    """
    duration_seconds = VENTANAS_SINTETICAS * WINDOW_SECONDS
    n_samples = int(duration_seconds * sampling_rate)
    t = np.arange(n_samples) / sampling_rate
    frequencies = [1.0, 10.0, 0.5, 30.0]
    return np.vstack([50.0 * np.sin(2 * np.pi * f * t) for f in frequencies])


@pytest.fixture
def channel_names() -> list[str]:
    """Nombres de canal del registro sintético, uno por clase de señal.

    Cubren las cuatro clases que el pliego nombra en V1_P: EEG (C3 y C4),
    EOG y EMG. Sirven además para testear la detección automática de clase
    (V4_F): "C3" tiene que detectarse como EEG por su nombre 10-20, y
    "EMG-menton" como EMG por su prefijo.
    """
    return ["C3", "C4", "EOG-izq", "EMG-menton"]


@pytest.fixture(scope="session")
def qt_app():
    """Una única `QApplication` para toda la suite.

    **`ui/` no lleva tests unitarios de sus widgets**, y eso no cambia: la regla
    mantiene la capa delgada y empuja la lógica a `core/`. Lo que sí se verifica
    son las piezas que no dibujan —los conversores entre píxeles y unidades, y
    la grilla— porque ahí vive el riesgo de confundir unidades que todo el
    proyecto viene señalando, y porque son las únicas de `ui/` que se pueden
    afirmar sin mirar una pantalla.

    Es de alcance de sesión porque Qt no admite más de una `QApplication` por
    proceso, y se reutiliza la que exista para no chocar con nada.
    """
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


#: Resolución del BrainVision sintético: cuántos µV vale una cuenta entera del
#: `int16` del archivo. Es el campo que el lector tiene que aplicar, y con 0,5
#: un error de escala se ve enseguida.
RESOLUCION_BV_UV = 0.5

#: Frecuencia del BrainVision sintético. **No usa la fixture `sampling_rate`, y
#: el motivo es del formato**: `SamplingInterval` se escribe en microsegundos
#: enteros, así que sólo son representables las frecuencias que dividen un
#: millón. Con los 256 Hz de `sampling_rate` el intervalo da 3906,25 µs, se
#: trunca a 3906 y el archivo termina declarando 256,016 Hz. 250 Hz da 4000 µs
#: exactos y deja que los tests afirmen la frecuencia sin tolerancia.
FRECUENCIA_BV = 250.0


#: Cuántos µV vale cada unidad que el BrainVision sintético sabe escribir. Como
#: `UV_POR_UNIDAD_EDF`, **es la tabla del test** y lleva grafías que MNE no
#: convierte —`uv`, `mv`, la mu griega— junto a las que sí. Una unidad que no
#: está —"C", la vacía— se escribe como antes: los números en µV.
UV_POR_UNIDAD_BV: dict[str, float] = {
    "µV": 1.0,
    "uV": 1.0,
    "uv": 1.0,
    "μV": 1.0,
    "mV": 1e3,
    "mv": 1e3,
    "V": 1e6,
    "nV": 1e-3,
}


def escribir_brainvision(
    carpeta: pathlib.Path,
    segundos: float,
    canales: list[tuple[str, str]] | None = None,
    impedancias: dict[str, float | None] | None = None,
    frecuencia: float = FRECUENCIA_BV,
    codepage: str | None = "UTF-8",
    coordenadas: bool = False,
    sin_valor: dict[str, range] | None = None,
) -> pathlib.Path:
    """Escribe un BrainVision completo y devuelve la ruta de su `.vhdr`.

    **Por qué existe.** Los tests que leen el registro de `data/` eran los
    únicos que ejercitaban el lector de punta a punta, y se saltean en el CI
    porque `data/` está en el `.gitignore`: son registros de participantes. El
    resultado era que el lector de BrainVision no se ejecutaba en ninguna de las
    seis combinaciones de sistema y versión de Python que corre el CI.

    El formato permite arreglarlo sin pedirle nada a nadie: son tres archivos y
    ninguno es opaco. El `.vhdr` y el `.vmrk` son texto tipo INI y el `.eeg` es
    un `int16` multiplexado crudo, así que se escriben con numpy y pathlib.

    **La cabecera declara `Codepage=UTF-8` y escribe la unidad en UTF-8 a
    propósito**, porque ahí estuvo un bug real: leerla como latin-1 parte el
    micro en dos caracteres, y con la unidad irreconocible veintitrés canales
    EEG quedaron sin convertir y mal clasificados. Es lo que
    `readers/brainvision.py::_decodificar_cabecera` arregla, y sin esto nada lo
    comprueba fuera de una máquina que tenga los registros.

    Es función y no sólo fixture porque la duración importa: los tests del
    lector alcanzan con tres segundos, y `test_entrega.py` necesita varias
    ventanas de 30 s para poder scorear y exportar.

    **`frecuencia` la agregó el hito 17**, y no es un parámetro de comodidad:
    los sugeridos de filtrado dependen de dónde cae Nyquist, y el hallazgo que
    abrió ese hito —el notch de 50 Hz rechazado en un registro de 100— no se
    puede reproducir sin poder escribir un archivo a 100 Hz. Vale cualquier
    frecuencia que divida un millón, por el `SamplingInterval` entero de más
    arriba; 100 Hz da 10000 µs exactos.

    **Lo que agregó el hito 33**, para probar la escala contra la regla de MNE:

    - La señal se escribe **en la unidad que declara cada canal**: la
      resolución de la cabecera es `RESOLUCION_BV_UV` pasada a esa unidad, así
      que leerla bien es recuperar los mismos µV con cualquier grafía de
      `UV_POR_UNIDAD_BV`. Hasta ahí se escribía siempre en µV, y un canal
      declarado en mV salía mil veces más grande que lo sintetizado.
    - `codepage=None` omite la línea `Codepage=`, que es como MNE decide
      decodificar en UTF-8.
    - `coordenadas=True` agrega una sección `[Coordinates]`, cuyas líneas
      también empiezan con `Ch<n>=` y no hablan de unidades.
    - `sin_valor={"C3": range(10, 20)}` deja esas muestras en NaN, y para eso
      escribe el archivo en `IEEE_FLOAT_32` en vez de `INT_16`. **Es el único
      formato de los dos que puede traerlas**: el EDF guarda enteros, así que
      un NaN no le entra ni por un archivo dañado. Las cuentas son las mismas y
      la cabecera no cambia más que en esa línea, así que un test que pida
      muestras sin valor sigue leyendo los mismos µV en el resto de la señal.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    # Los tres por omisión cubren una clase de señal cada uno, que es lo que
    # necesitan los tests del lector. **Se pueden pedir otros**: la ICA, por
    # ejemplo, necesita dos canales EEG y con uno solo se niega, con razón.
    canales = canales or [("C3", "µV"), ("EOG-izq", "µV"), ("EMG-menton", "µV")]
    muestras = int(frecuencia * segundos)
    tiempos = np.arange(muestras) / frecuencia
    # Frecuencias distintas y conocidas por canal: una escala aplicada de más se
    # ve en los tres a la vez, y una permutación de canales, en uno solo.
    # Una frecuencia y una amplitud distintas por canal, cíclicas si se piden
    # más de tres: lo que importa es que ninguno sea igual a otro, para que una
    # permutación de canales se vea.
    formas = [(10.0, 50.0), (1.0, 30.0), (30.0, 20.0), (5.0, 40.0), (0.5, 60.0)]
    microvoltios = np.vstack(
        [
            amplitud * np.sin(2 * np.pi * frecuencia * tiempos)
            for frecuencia, amplitud in (
                formas[posicion % len(formas)] for posicion in range(len(canales))
            )
        ]
    )
    cuentas = np.round(microvoltios / RESOLUCION_BV_UV)
    if sin_valor:
        posiciones = {nombre: numero for numero, (nombre, _) in enumerate(canales)}
        for nombre, muestras_rotas in sin_valor.items():
            cuentas[posiciones[nombre], list(muestras_rotas)] = np.nan
    binario = "IEEE_FLOAT_32" if sin_valor else "INT_16"
    cuentas = cuentas.astype("<f4" if sin_valor else "<i2")
    # MULTIPLEXED es canal por canal dentro de cada instante, así que se
    # transpone antes de volcar los bytes.
    (carpeta / "sintetico.eeg").write_bytes(cuentas.T.tobytes(order="C"))

    cabecera = [
        "Brain Vision Data Exchange Header File Version 1.0",
        "",
        "[Common Infos]",
        *([f"Codepage={codepage}"] if codepage else []),
        "DataFile=sintetico.eeg",
        "MarkerFile=sintetico.vmrk",
        "DataFormat=BINARY",
        "DataOrientation=MULTIPLEXED",
        f"NumberOfChannels={len(canales)}",
        f"SamplingInterval={int(1_000_000 / frecuencia)}",
        "",
        "[Binary Infos]",
        f"BinaryFormat={binario}",
        "",
        "[Channel Infos]",
    ]
    for numero, (nombre, unidad) in enumerate(canales, start=1):
        # Las mismas cuentas, con la resolución expresada en la unidad del canal.
        resolucion = RESOLUCION_BV_UV / UV_POR_UNIDAD_BV.get(unidad, 1.0)
        cabecera.append(f"Ch{numero}={nombre},,{resolucion:.10g},{unidad}")
    if coordenadas:
        cabecera += ["", "[Coordinates]"]
        cabecera += [f"Ch{numero}=1,{numero * 10},0" for numero in range(1, len(canales) + 1)]
    # **La tabla de impedancias vive en `[Comment]`**, que es donde el formato
    # la pone y donde MNE la busca. `None` se escribe `???`, que es como el
    # `.vhdr` marca un electrodo que nadie midió: es el caso que separa "sin
    # medir" de "0 kΩ", y sin poder escribirlo no se podría testear.
    if impedancias:
        cabecera += ["", "[Comment]", "", "Impedance [kOhm] at 23:00:00 :"]
        for nombre, valor in impedancias.items():
            escrito = "???" if valor is None else f"{valor:g}"
            cabecera.append(f"{nombre}:{escrito:>12s}")

    vhdr = carpeta / "sintetico.vhdr"
    vhdr.write_text("\n".join(cabecera) + "\n", encoding="utf-8")

    marcadores = [
        "Brain Vision Data Exchange Marker File, Version 1.0",
        "",
        "[Common Infos]",
        "Codepage=UTF-8",
        "DataFile=sintetico.eeg",
        "",
        "[Marker Infos]",
        "Mk1=New Segment,,1,1,0,20260907130000000000",
    ]
    (carpeta / "sintetico.vmrk").write_text(
        "\n".join(marcadores) + "\n", encoding="utf-8"
    )
    return vhdr


@pytest.fixture
def brainvision_sintetico(tmp_path) -> pathlib.Path:
    """Tres segundos de BrainVision sintético: alcanza para el lector."""
    return escribir_brainvision(tmp_path / "brainvision", segundos=3)


#: Frecuencia del EDF sintético por omisión: la de la Sleep-EDF, el registro
#: real con que se probó el lector. El formato guarda cuántas muestras entran
#: en cada registro de datos, que acá dura un segundo, así que cualquier
#: frecuencia entera se representa exacta, sin el problema del BrainVision.
FRECUENCIA_EDF = 100.0

#: El pico de cada canal del EDF sintético, en µV, por posición. Distintos entre
#: sí por lo mismo que en el BrainVision: una permutación de canales se ve.
PICOS_EDF_UV: tuple[float, ...] = (50.0, 30.0, 20.0, 40.0, 60.0)

#: Cuántos µV vale cada unidad eléctrica que el EDF sintético sabe escribir.
#: **Es la tabla del test, escrita a mano**: si el escritor usara la de
#: `utils/units.py`, que es la que usa el lector, un factor equivocado se
#: cancelaría solo y el test pasaría sin verificar nada.
#:
#: **Lleva grafías que MNE no convierte** —`uv`, `UV`, `mv`, `nV`— junto a las
#: que sí, y la mu de Shift-JIS de los equipos japoneses, que MNE sí reconoce.
#: Leer bien es recuperar los mismos µV en todas: es lo que el hito 33 encontró
#: roto, porque MNE compara la grafía exacta y el lector no.
UV_POR_UNIDAD_EDF: dict[str, float] = {
    "uV": 1.0,
    "µV": 1.0,
    "\x83\xcaV": 1.0,
    "uv": 1.0,
    "UV": 1.0,
    "mV": 1e3,
    "mv": 1e3,
    "V": 1e6,
    "nV": 1e-3,
}

#: Etiqueta del canal de anotaciones de EDF+. `escribir_edf()` escribe ahí
#: anotaciones de tiempo vacías en vez de una señal.
ANOTACIONES_EDF = "EDF Annotations"

#: Lo que vale un canal que no es eléctrico —una temperatura en "DegC"— en su
#: propia unidad. Oscila medio grado alrededor de este valor, así que un factor
#: de conversión aplicado por error lo saca de cualquier rango plausible.
TEMPERATURA_EDF = 36.5


def _campo_edf(texto: str, ancho: int) -> bytes:
    """Un campo de la cabecera EDF, en latin-1 y rellenado con espacios.

    Latin-1 y no ASCII por el micro de "µV": es como lo escriben los equipos que
    no usan "uV", y como lo decodifica MNE.
    """
    crudo = texto.encode("latin-1")
    if len(crudo) > ancho:
        raise ValueError(f"{texto!r} no entra en los {ancho} bytes del campo")
    return crudo.ljust(ancho, b" ")


def _numero_edf(valor: float) -> str:
    """El número más preciso que entra en los ocho caracteres de un campo EDF."""
    for decimales in range(7, 0, -1):
        texto = f"{valor:.{decimales}f}".rstrip("0").rstrip(".")
        if len(texto) <= 8:
            return texto
    texto = f"{valor:.0f}"
    if len(texto) > 8:
        raise ValueError(f"{valor} no entra en los ocho caracteres de un campo EDF")
    return texto


def escribir_edf(
    carpeta: pathlib.Path,
    segundos: int,
    canales: list[tuple[str, str, float]] | None = None,
    inicio: datetime = datetime(2026, 9, 7, 23, 0, 0),
) -> pathlib.Path:
    """Escribe un EDF sintético y devuelve su ruta.

    **Por qué existe.** Hasta el hito 33 el lector de EDF sólo se ejercitaba con
    el registro de `data/`, que el CI no tiene: la conversión a microvoltios,
    que es lo que justifica el lector, no corría en ninguna de las seis
    combinaciones de sistema y versión de Python. La auditoría del 19 de
    septiembre de 2026 encontró justo ahí dos errores de escala. Es el mismo
    hueco que `escribir_brainvision()` cerró para el otro formato.

    El formato permite escribirlo sin ninguna dependencia: una cabecera de
    campos de texto de ancho fijo y después la señal como `int16` en registros
    de datos. Acá cada registro dura un segundo.

    Args:
        carpeta: dónde escribirlo; se crea si no existe.
        segundos: cuántos registros de datos de un segundo lleva el archivo.
        canales: `(nombre, unidad, frecuencia)` de cada canal. **La frecuencia
            puede ser distinta por canal**, como en la Sleep-EDF, que trae canales
            a 100 Hz y a 1 Hz. Un canal cuya unidad está en
            `UV_POR_UNIDAD_EDF` lleva un coseno de pico `PICOS_EDF_UV[i]` µV,
            **escrito en su propia unidad**: leerlo bien es recuperar esos µV. Uno
            con otra unidad oscila alrededor de `TEMPERATURA_EDF`, sin convertir.
            Uno llamado `ANOTACIONES_EDF` no es una señal: lleva las
            anotaciones de tiempo de EDF+, vacías, y el archivo pasa a ser
            EDF+. MNE lo excluye, así que corre las posiciones de los demás.
        inicio: la fecha y hora de la cabecera.

    El coseno tiene una décima de la frecuencia del canal, así que su primera
    muestra es exactamente el pico: los tests afirman el pico sin la tolerancia
    de un seno muestreado.
    """
    carpeta.mkdir(parents=True, exist_ok=True)
    canales = canales or [
        ("EEG C3-A2", "uV", FRECUENCIA_EDF),
        ("EOG izquierdo", "uV", FRECUENCIA_EDF),
        ("EMG submental", "uV", FRECUENCIA_EDF),
    ]

    senales: list[np.ndarray | None] = []
    rangos: list[tuple[str, str]] = []
    for posicion, (nombre, unidad, frecuencia) in enumerate(canales):
        muestras = int(frecuencia * segundos)
        oscilacion = np.cos(2 * np.pi * (frecuencia / 10) * np.arange(muestras) / frecuencia)
        if nombre == ANOTACIONES_EDF:
            senales.append(None)
            rangos.append(("-1", "1"))
        elif unidad in UV_POR_UNIDAD_EDF:
            pico = PICOS_EDF_UV[posicion % len(PICOS_EDF_UV)] / UV_POR_UNIDAD_EDF[unidad]
            senales.append(pico * oscilacion)
            rangos.append((_numero_edf(-2 * pico), _numero_edf(2 * pico)))
        else:
            senales.append(TEMPERATURA_EDF + 0.5 * oscilacion)
            rangos.append((_numero_edf(TEMPERATURA_EDF - 1), _numero_edf(TEMPERATURA_EDF + 1)))

    cantidad = len(canales)
    cabecera = b"".join(
        [
            _campo_edf("0", 8),
            _campo_edf("X X X X", 80),
            _campo_edf("Startdate X X X X", 80),
            _campo_edf(inicio.strftime("%d.%m.%y"), 8),
            _campo_edf(inicio.strftime("%H.%M.%S"), 8),
            _campo_edf(str(256 * (cantidad + 1)), 8),
            _campo_edf("EDF+C" if any(n == ANOTACIONES_EDF for n, _, _ in canales) else "", 44),
            _campo_edf(str(segundos), 8),
            _campo_edf("1", 8),
            _campo_edf(str(cantidad), 4),
        ]
    )
    # Los campos de cada canal van agrupados por campo, no por canal: primero
    # todas las etiquetas, después todos los transductores, y así.
    por_campo = [
        [_campo_edf(nombre, 16) for nombre, _, _ in canales],
        [_campo_edf("", 80) for _ in canales],
        [_campo_edf(unidad, 8) for _, unidad, _ in canales],
        [_campo_edf(minimo, 8) for minimo, _ in rangos],
        [_campo_edf(maximo, 8) for _, maximo in rangos],
        [_campo_edf("-32768", 8) for _ in canales],
        [_campo_edf("32767", 8) for _ in canales],
        [_campo_edf("", 80) for _ in canales],
        [_campo_edf(str(int(frecuencia)), 8) for _, _, frecuencia in canales],
        [_campo_edf("", 32) for _ in canales],
    ]
    cabecera += b"".join(b"".join(campo) for campo in por_campo)

    # Físico → digital con el rango **tal como quedó escrito**: si se usara el
    # número antes de recortarlo a ocho caracteres, el lector, que sólo ve el
    # recortado, recuperaría otra amplitud.
    digitales: list[np.ndarray] = []
    for (_, _, frecuencia), senal, (minimo, maximo) in zip(canales, senales, rangos):
        if senal is None:
            # Una anotación de tiempo por registro, "+<segundo>" y dos
            # separadores, rellenada con ceros hasta el largo del canal.
            largo = 2 * int(frecuencia)
            tal = b"".join(
                f"+{registro}\x14\x14\x00".encode("ascii").ljust(largo, b"\x00")
                for registro in range(segundos)
            )
            digitales.append(np.frombuffer(tal, dtype="<i2").reshape(segundos, -1))
            continue
        bajo, alto = float(minimo), float(maximo)
        cuentas = np.round((senal - bajo) / (alto - bajo) * 65535 - 32768)
        digitales.append(cuentas.astype("<i2").reshape(segundos, -1))
    cuerpo = b"".join(
        b"".join(canal[registro].tobytes() for canal in digitales)
        for registro in range(segundos)
    )

    edf = carpeta / "sintetico.edf"
    edf.write_bytes(cabecera + cuerpo)
    return edf


@pytest.fixture
def edf_sintetico(tmp_path) -> pathlib.Path:
    """Tres segundos de EDF sintético, tres canales a 100 Hz en µV."""
    return escribir_edf(tmp_path / "edf", segundos=3)


#: Clase de cada canal de `channel_names`, en su mismo orden. Está acá y no en
#: cada test porque `registro_sintetico` la necesita y hasta el hito 10 cada
#: archivo se la escribía sola: diez de ellos arman un `Recording` a mano.
CLASES_SINTETICAS: tuple[ChannelKind, ...] = (
    ChannelKind.EEG,
    ChannelKind.EEG,
    ChannelKind.EOG,
    ChannelKind.EMG,
)


@pytest.fixture
def registro_sintetico(
    synthetic_signal: np.ndarray, channel_names: list[str], sampling_rate: float
) -> Recording:
    """Los diez minutos sintéticos, ya envueltos en un `Recording`.

    **Faltaba, y la Parte 2 la necesita entera.** `synthetic_signal` es un array
    pelado y **todas** las funciones de `psglab/analysis/` reciben un
    `Recording`, así que sin esto cada test de análisis se lo armaría solo —que
    es lo que vienen haciendo diez archivos de la Parte 1.

    Trae contenido espectral conocido de antemano, que es lo que hace
    verificable un test de análisis sin usar un registro real: C3 en 1 Hz, C4 en
    10 Hz, el EOG en 0,5 Hz y el EMG en 30 Hz, todos de 50 µV. Una PSD de C4
    tiene que dar su pico en 10 Hz, y eso se puede afirmar.

    Son `VENTANAS_SINTETICAS` ventanas **exactas**: no ejercita la última
    ventana incompleta, que es un caso aparte y hay que escribirlo a propósito.
    """
    canales = [
        Channel(name=nombre, kind=clase, unit=MICROVOLT, index=posicion)
        for posicion, (nombre, clase) in enumerate(zip(channel_names, CLASES_SINTETICAS))
    ]
    return Recording(
        file_path=Path("sintetico.edf"),
        channels=canales,
        data=synthetic_signal,
        sampling_rate=sampling_rate,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
    )
