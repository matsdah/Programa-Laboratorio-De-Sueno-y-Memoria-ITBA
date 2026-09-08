"""Tests del filtrado.

**Se verifica por PSD y como razón de atenuación**, no como valores exactos:
un filtro tiene banda de transición y ringing en los bordes, así que exigir un
número puntual sería exigir una implementación y no un comportamiento. Lo que
sí se puede afirmar es que la componente que el filtro tiene que sacar queda
órdenes de magnitud por debajo, y que la que tiene que dejar pasar queda como
estaba.

**Las frecuencias del testigo están elegidas con margen, y eso salió de
medir.** Un pasa-bajos de 35 Hz atenúa la componente de 40 Hz apenas **7
veces**, porque 40 Hz cae dentro de su banda de transición —MNE la calcula como
un cuarto del corte, así que va de 35 a 43,75 Hz—. Un test escrito sobre esa
pareja parecería exigir "que el filtro filtre" y en realidad estaría midiendo
el ancho de la transición de MNE. Con la componente en 50 Hz, bien adentro de
la banda de rechazo, la razón medida es de seis órdenes de magnitud y el umbral
del test le queda holgado.

El otro grupo de tests es el de lo que se rechaza, y ahí está **el caso que
justifica el módulo**: MNE acepta un pasa-altos por encima del pasa-bajos, arma
una banda eliminada y no avisa nada. Se afirma que acá se rechaza.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
from scipy.signal import welch

from psglab.analysis.filters import (
    DEFAULT_FILTERS,
    DEFAULT_NOTCH_HZ,
    FilterSettings,
    apply_filters,
    default_for,
    validate,
)
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.utils.errors import (
    ChannelNotFoundError,
    InvalidFilterError,
    InvalidRecordingError,
    PsgLabError,
)
from psglab.utils.units import MICROVOLT

#: Frecuencia de muestreo del testigo. 256 Hz deja Nyquist en 128, así que el
#: notch de 50 Hz entra cómodo y sobra lugar para probar cortes imposibles.
FS = 256.0

#: Las tres componentes del testigo, todas de 50 µV. Están repartidas a
#: propósito: 1 Hz es delta, 10 Hz es alfa y 50 Hz es la red eléctrica, que es
#: justo lo que el notch tiene que sacar.
COMPONENTES = (1.0, 10.0, 50.0)

#: Cuántas veces tiene que bajar la potencia de una componente para darla por
#: filtrada. Medido: un pasa-bajos de 20 a 35 Hz baja la de 50 Hz entre 10⁵ y
#: 10⁷ veces, así que mil deja margen de sobra sin exigir una implementación.
ATENUACION_MINIMA = 1000.0


def armar_registro(
    canales: list[tuple[str, ChannelKind, str]] | None = None,
    fs: float = FS,
    segundos: float = 60.0,
) -> Recording:
    """Un registro donde cada canal lleva las tres componentes conocidas.

    Que todos los canales lleven **lo mismo** es a propósito: así se puede
    filtrar uno y afirmar que el otro quedó idéntico, que es lo que verifica
    que los filtros no se derramen de un canal al otro.
    """
    canales = canales or [("C3", ChannelKind.EEG, MICROVOLT), ("C4", ChannelKind.EEG, MICROVOLT)]
    tiempos = np.arange(int(fs * segundos)) / fs
    una = sum(50.0 * np.sin(2 * np.pi * f * tiempos) for f in COMPONENTES)
    return Recording(
        file_path=Path("filtros.edf"),
        channels=[
            Channel(nombre, clase, unidad, posicion)
            for posicion, (nombre, clase, unidad) in enumerate(canales)
        ],
        data=np.vstack([una for _ in canales]),
        sampling_rate=fs,
        start_time=datetime(2026, 9, 8, 23, 0, 0),
    )


def potencias(registro: Recording, canal: str) -> dict[float, float]:
    """Potencia de cada componente conocida, en el canal pedido."""
    indice = registro.channel_by_name(canal).index
    frecuencias, densidad = welch(
        np.asarray(registro.data)[indice],
        fs=registro.sampling_rate,
        nperseg=int(4 * registro.sampling_rate),
    )
    return {
        hz: float(densidad[int(np.argmin(np.abs(frecuencias - hz)))])
        for hz in COMPONENTES
    }


def razones(antes: Recording, despues: Recording, canal: str) -> dict[float, float]:
    """Cuántas veces bajó cada componente. 1 significa que quedó igual."""
    previas, actuales = potencias(antes, canal), potencias(despues, canal)
    return {hz: previas[hz] / actuales[hz] for hz in COMPONENTES}


# -- Que filtre, verificado por PSD ------------------------------------------


def test_el_pasabajos_saca_la_componente_alta_y_deja_las_otras():
    """La afirmación central del módulo, como razón de atenuación."""
    crudo = armar_registro()

    filtrado = apply_filters(crudo, {"C3": FilterSettings(lowpass_hz=20.0)})

    razon = razones(crudo, filtrado, "C3")
    assert razon[50.0] > ATENUACION_MINIMA
    assert razon[1.0] == pytest.approx(1.0, rel=0.1)
    assert razon[10.0] == pytest.approx(1.0, rel=0.1)


def test_el_pasaaltos_saca_la_componente_baja():
    crudo = armar_registro()

    filtrado = apply_filters(crudo, {"C3": FilterSettings(highpass_hz=5.0)})

    razon = razones(crudo, filtrado, "C3")
    assert razon[1.0] > ATENUACION_MINIMA
    assert razon[10.0] == pytest.approx(1.0, rel=0.1)


def test_el_notch_saca_la_red_y_no_toca_lo_de_al_lado():
    """Es lo que distingue al notch de un pasa-bajos: saca una frecuencia, no
    todo lo que está por encima."""
    crudo = armar_registro()

    filtrado = apply_filters(crudo, {"C3": FilterSettings(notch_hz=DEFAULT_NOTCH_HZ)})

    razon = razones(crudo, filtrado, "C3")
    assert razon[50.0] > ATENUACION_MINIMA
    assert razon[10.0] == pytest.approx(1.0, rel=0.1)
    assert razon[1.0] == pytest.approx(1.0, rel=0.1)


def test_los_tres_filtros_juntos():
    crudo = armar_registro()

    filtrado = apply_filters(
        crudo,
        {"C3": FilterSettings(highpass_hz=5.0, lowpass_hz=20.0, notch_hz=DEFAULT_NOTCH_HZ)},
    )

    razon = razones(crudo, filtrado, "C3")
    assert razon[1.0] > ATENUACION_MINIMA
    assert razon[50.0] > ATENUACION_MINIMA
    assert razon[10.0] == pytest.approx(1.0, rel=0.1)


def test_un_canal_que_no_se_pidio_queda_igual():
    """Los filtros no se derraman: es lo que permite filtrar el EEG con un
    rango y el EMG con otro, que es lo que pide V1_F."""
    crudo = armar_registro()

    filtrado = apply_filters(crudo, {"C3": FilterSettings(lowpass_hz=20.0)})

    # **Idéntico bit a bit, no parecido.** El primer intento de este test usó
    # `array_equal` y falló por 1e-16: el viaje µV → V → µV del puente con MNE
    # deja error de punto flotante hasta en las filas que nadie filtró. Es
    # invisible en una señal de microvoltios, pero convertía la promesa "el
    # canal que no pediste queda igual" en algo que no se podía afirmar. El
    # módulo restaura esas filas del original, y por eso acá se puede exigir la
    # igualdad exacta.
    assert np.array_equal(
        np.asarray(filtrado.data)[filtrado.channel_by_name("C4").index],
        np.asarray(crudo.data)[crudo.channel_by_name("C4").index],
    )


def test_cada_canal_con_su_rango():
    """Dos canales, dos filtros distintos, en una sola llamada."""
    crudo = armar_registro()

    filtrado = apply_filters(
        crudo,
        {
            "C3": FilterSettings(lowpass_hz=20.0),
            "C4": FilterSettings(highpass_hz=5.0),
        },
    )

    assert razones(crudo, filtrado, "C3")[50.0] > ATENUACION_MINIMA
    assert razones(crudo, filtrado, "C4")[1.0] > ATENUACION_MINIMA
    # Y cada uno conservó lo que el otro sacó.
    assert razones(crudo, filtrado, "C3")[1.0] == pytest.approx(1.0, rel=0.1)
    assert razones(crudo, filtrado, "C4")[50.0] == pytest.approx(1.0, rel=0.1)


def test_se_filtra_lo_que_no_es_electrico():
    """**Acá el módulo se aparta de `reference.py`.** Restarle microvoltios a un
    termómetro inventa una temperatura, pero filtrar es una operación sobre el
    tiempo y no sobre la unidad: la fila respiratoria de `DEFAULT_FILTERS`
    existe justamente para esto."""
    crudo = armar_registro([("Flujo", ChannelKind.RESPIRATORY, "L/min")])

    filtrado = apply_filters(crudo, {"Flujo": FilterSettings(lowpass_hz=20.0)})

    assert razones(crudo, filtrado, "Flujo")[50.0] > ATENUACION_MINIMA
    assert filtrado.channel_by_name("Flujo").unit == "L/min"


# -- Poder deshacer ----------------------------------------------------------


def test_el_original_queda_intacto():
    """Regla 1 de la carpeta, y lo que hace que un filtro mal elegido no
    obligue a reabrir el archivo."""
    crudo = armar_registro()
    copia = np.array(crudo.data, copy=True)

    apply_filters(crudo, {"C3": FilterSettings(lowpass_hz=20.0)})

    assert np.array_equal(np.asarray(crudo.data), copia)


def test_devuelve_un_registro_nuevo():
    crudo = armar_registro()

    filtrado = apply_filters(crudo, {"C3": FilterSettings(lowpass_hz=20.0)})

    assert filtrado is not crudo
    assert np.asarray(filtrado.data) is not np.asarray(crudo.data)


def test_conserva_lo_que_el_filtro_no_cambia():
    crudo = armar_registro()

    filtrado = apply_filters(crudo, {"C3": FilterSettings(lowpass_hz=20.0)})

    assert filtrado.channel_names() == crudo.channel_names()
    assert filtrado.sampling_rate == crudo.sampling_rate
    assert filtrado.start_time == crudo.start_time
    assert filtrado.file_path == crudo.file_path
    assert filtrado.channel_by_name("C3").unit == MICROVOLT


def test_sin_filtros_devuelve_una_copia_igual():
    """Un diccionario vacío es un pedido válido: no filtrar nada. Sale un
    registro nuevo igual, no el mismo objeto, porque la carpeta promete que
    siempre sale uno nuevo."""
    crudo = armar_registro()

    filtrado = apply_filters(crudo, {})

    assert filtrado is not crudo
    assert np.asarray(filtrado.data) == pytest.approx(np.asarray(crudo.data))


def test_filtros_vacios_no_cambian_la_senal():
    """`FilterSettings()` sin nada es lo mismo que no nombrar el canal."""
    crudo = armar_registro()

    filtrado = apply_filters(crudo, {"C3": FilterSettings()})

    assert np.asarray(filtrado.data) == pytest.approx(np.asarray(crudo.data))


# -- Lo que se rechaza -------------------------------------------------------


def test_el_pasaaltos_por_encima_del_pasabajos_se_rechaza():
    """**El rechazo que justifica el módulo**, porque es el único que MNE no
    hace. Se midió: con 40 y 10 Hz acepta el par, arma una banda eliminada, no
    emite ningún aviso y devuelve la señal sin atenuar nada. El investigador
    cree que filtró y está mirando la señal cruda."""
    with pytest.raises(InvalidFilterError):
        validate(FilterSettings(highpass_hz=40.0, lowpass_hz=10.0), FS)


def test_el_pasaaltos_igual_al_pasabajos_se_rechaza():
    """Una banda de 10 a 10 Hz no deja pasar nada."""
    with pytest.raises(InvalidFilterError):
        validate(FilterSettings(highpass_hz=10.0, lowpass_hz=10.0), FS)


@pytest.mark.parametrize(
    "filtros",
    [
        FilterSettings(lowpass_hz=200.0),
        FilterSettings(highpass_hz=200.0),
        FilterSettings(notch_hz=200.0),
    ],
)
def test_un_corte_por_encima_de_nyquist_se_rechaza(filtros: FilterSettings):
    """Por encima de Nyquist no hay señal que filtrar: no está en el archivo."""
    with pytest.raises(InvalidFilterError):
        validate(filtros, FS)


def test_justo_en_nyquist_tambien_se_rechaza():
    """La comparación es estricta, igual que en MNE."""
    with pytest.raises(InvalidFilterError):
        validate(FilterSettings(lowpass_hz=FS / 2), FS)


def test_el_mensaje_de_nyquist_nombra_las_dos_frecuencias():
    """Un investigador tiene que poder corregirlo sin preguntarle a nadie: el
    cartel dice el corte que puso y el máximo que el registro admite."""
    with pytest.raises(InvalidFilterError) as elevado:
        validate(FilterSettings(lowpass_hz=200.0), FS)

    assert "200" in elevado.value.message
    assert "128" in elevado.value.message


@pytest.mark.parametrize("valor", [0.0, -1.0, float("nan"), float("inf")])
def test_una_frecuencia_que_no_es_positiva_y_finita_se_rechaza(valor: float):
    """**El cero incluido, y a propósito**: MNE lo interpreta como "sin
    filtro", así que aceptarlo dejaría al usuario creyendo que puso un corte."""
    with pytest.raises(InvalidFilterError):
        validate(FilterSettings(highpass_hz=valor), FS)


def test_un_canal_que_no_existe_se_rechaza():
    """No se lo ignora en silencio: un nombre mal escrito dejaría al
    investigador convencido de que filtró un canal que quedó crudo."""
    with pytest.raises(ChannelNotFoundError):
        apply_filters(armar_registro(), {"Cz": FilterSettings(lowpass_hz=20.0)})


def test_no_se_filtra_nada_si_un_canal_del_pedido_es_invalido():
    """**Todo o nada.** Media señal filtrada y media cruda es un estado del que
    nadie puede sacar conclusiones, y a simple vista no se distingue de una
    señal entera."""
    crudo = armar_registro()
    copia = np.array(crudo.data, copy=True)

    with pytest.raises(PsgLabError):
        apply_filters(
            crudo,
            {
                "C3": FilterSettings(lowpass_hz=20.0),
                "C4": FilterSettings(lowpass_hz=200.0),
            },
        )

    assert np.array_equal(np.asarray(crudo.data), copia)


def test_el_error_de_mne_sale_como_error_del_programa():
    """La red para lo que la validación no puede explicar bien. Medido: a 101 Hz
    de muestreo un notch de 50 Hz está por debajo de Nyquist (50,5) y MNE lo
    rechaza igual, porque el borde superior de su banda cae en 50,625."""
    crudo = armar_registro(fs=101.0)

    with pytest.raises(PsgLabError):
        apply_filters(crudo, {"C3": FilterSettings(notch_hz=50.0)})


# -- Los valores por defecto -------------------------------------------------


@pytest.mark.parametrize("clase", list(ChannelKind))
def test_hay_sugerencia_para_toda_clase_de_canal(clase: ChannelKind):
    """Una clase sin fila haría fallar el diálogo justo con el registro que la
    tenga, que es lo que nadie prueba a mano."""
    assert isinstance(default_for(clase), FilterSettings)


def test_los_sugeridos_son_los_de_la_tabla():
    assert default_for(ChannelKind.EEG) == DEFAULT_FILTERS[ChannelKind.EEG]


def test_los_sugeridos_salen_como_copia():
    """**`FilterSettings` es mutable.** Devolver la fila compartida haría que
    quien ajuste lo que recibió le cambie los valores por defecto al programa
    entero, para todos los registros y hasta que se cierre. Y es exactamente lo
    que el diálogo hace: pedir los sugeridos y dejar que el usuario los edite."""
    sugeridos = default_for(ChannelKind.EEG)

    sugeridos.lowpass_hz = 1.0

    assert DEFAULT_FILTERS[ChannelKind.EEG].lowpass_hz == 35.0
    assert default_for(ChannelKind.EEG).lowpass_hz == 35.0


def test_el_notch_por_defecto_sale_de_la_constante():
    """Que sea 50 y no 60 es geografía, no física: se declara una vez para que
    cambiarlo sea un cambio y no cinco."""
    assert default_for(ChannelKind.EEG).notch_hz == DEFAULT_NOTCH_HZ


def test_los_sugeridos_son_validos_en_un_registro_comun():
    """Ofrecer un valor por defecto que el programa después rechaza sería una
    trampa. Se verifica con 256 Hz, que es la frecuencia habitual."""
    for clase in ChannelKind:
        validate(default_for(clase), 256.0)


def test_el_emg_no_es_valido_a_baja_frecuencia():
    """La otra cara: los sugeridos son **sugerencias**, y el pasa-bajos de 100 Hz
    del EMG no entra en un registro de 128 Hz. Por eso el diálogo tiene que
    validar y no dar por buenos los valores por defecto."""
    with pytest.raises(InvalidFilterError):
        validate(default_for(ChannelKind.EMG), 128.0)


# -- Entradas hostiles -------------------------------------------------------


def test_filtrar_algo_que_no_es_un_registro():
    with pytest.raises(InvalidRecordingError):
        apply_filters("un registro", {})


def test_filtrar_con_algo_que_no_son_filtros():
    with pytest.raises(PsgLabError):
        apply_filters(armar_registro(), {"C3": "pasa-bajos de 20"})


def test_validar_algo_que_no_son_filtros():
    with pytest.raises(InvalidFilterError):
        validate("pasa-bajos de 20", FS)


def test_sugerir_para_algo_que_no_es_una_clase_de_canal():
    with pytest.raises(InvalidFilterError):
        default_for("EEG")
