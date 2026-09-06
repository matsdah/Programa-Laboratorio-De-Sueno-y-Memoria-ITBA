"""Tests de la conversión entre ventanas, muestras y tiempo.

Es matemática pura y sin interfaz, así que se puede testear a fondo. También
es el lugar donde más barato sale un error de una unidad: si la conversión se
corre en una ventana, todo el scoring queda desplazado 30 segundos y el
resultado es sutilmente incorrecto en vez de romperse de forma visible.
"""

from datetime import datetime, timedelta

import pytest

from psglab.config import WINDOW_SECONDS
from psglab.core.windows import (
    count_windows,
    sample_to_seconds,
    sample_to_window,
    seconds_to_sample,
    seconds_to_window_fraction,
    window_duration,
    window_fraction_to_seconds,
    window_to_clock_time,
    window_to_samples,
)


def test_registro_exacto_da_cantidad_exacta_de_ventanas(sampling_rate):
    """Veinte ventanas completas dan exactamente veinte ventanas."""
    n_samples = int(20 * WINDOW_SECONDS * sampling_rate)
    assert count_windows(n_samples, sampling_rate) == 20


def test_ultima_ventana_incompleta_se_cuenta_igual(sampling_rate):
    """Un registro que corta a la mitad de una ventana la cuenta igual.

    El usuario tiene que poder ver y scorear la última ventana aunque esté
    incompleta; descartarla perdería datos reales del final de la noche.
    """
    n_samples = int(20.5 * WINDOW_SECONDS * sampling_rate)  # 20 ventanas y media
    assert count_windows(n_samples, sampling_rate) == 21


def test_registro_vacio_no_tiene_ventanas(sampling_rate):
    assert count_windows(0, sampling_rate) == 0


def test_primera_ventana_arranca_en_la_muestra_cero(sampling_rate):
    start, stop = window_to_samples(0, sampling_rate)
    assert start == 0
    assert stop == int(WINDOW_SECONDS * sampling_rate)


def test_ventanas_consecutivas_no_se_solapan_ni_dejan_hueco(sampling_rate):
    """El final de una ventana es exactamente el inicio de la siguiente."""
    _, stop_primera = window_to_samples(0, sampling_rate)
    inicio_segunda, _ = window_to_samples(1, sampling_rate)
    assert stop_primera == inicio_segunda


def test_ida_y_vuelta_entre_ventana_y_muestra(sampling_rate):
    """Convertir a muestras y volver devuelve la misma ventana."""
    for ventana in (0, 1, 19, 100):
        start, _ = window_to_samples(ventana, sampling_rate)
        assert sample_to_window(start, sampling_rate) == ventana


def test_ultima_muestra_de_una_ventana_pertenece_a_esa_ventana(sampling_rate):
    """El borde es el error clásico: la muestra anterior al corte no pasa aún."""
    _, stop = window_to_samples(3, sampling_rate)
    assert sample_to_window(stop - 1, sampling_rate) == 3
    assert sample_to_window(stop, sampling_rate) == 4


# -- Frecuencias de muestreo no redondas ------------------------------------
#
# Los tests de arriba usan 256 Hz, donde 30 * fs = 7680 es entero. Con esa
# frecuencia, calcular los bordes desde el índice de la ventana y acumular un
# paso ya redondeado dan exactamente lo mismo, así que ninguno de esos tests
# distingue una implementación correcta de una que deriva.
#
# En EDF la frecuencia efectiva no siempre es redonda: 2049 muestras por
# registro de 8 segundos dan 256,125 Hz, y ahí 30 * fs = 7683,75. Acumular
# int(7683,75) desplaza la ventana 960 unas 720 muestras, casi tres segundos.
# El scoring de la segunda mitad de la noche queda corrido sin que nada falle
# de forma visible.

FRECUENCIA_NO_REDONDA = 256.125


def test_los_bordes_no_derivan_con_una_frecuencia_no_redonda():
    """La ventana 960 arranca donde le toca, no donde la deja el acumulado."""
    fs = FRECUENCIA_NO_REDONDA
    start, _ = window_to_samples(960, fs)
    assert start == int(960 * WINDOW_SECONDS * fs)


def test_las_ventanas_siguen_sin_solaparse_con_una_frecuencia_no_redonda():
    """Recorrer la noche entera no deja huecos ni pisadas."""
    fs = FRECUENCIA_NO_REDONDA
    for ventana in range(0, 1000):
        _, stop = window_to_samples(ventana, fs)
        inicio_siguiente, _ = window_to_samples(ventana + 1, fs)
        assert stop == inicio_siguiente


def test_ida_y_vuelta_exacta_con_una_frecuencia_no_redonda():
    """La primera muestra de una ventana tiene que caer en esa ventana.

    Es el caso que rompe si `sample_to_window` usa el borde real en vez del
    borde redondeado que devuelve `window_to_samples`.
    """
    fs = FRECUENCIA_NO_REDONDA
    for ventana in (0, 1, 100, 959, 960):
        start, stop = window_to_samples(ventana, fs)
        assert sample_to_window(start, fs) == ventana
        assert sample_to_window(stop - 1, fs) == ventana


# -- Hora de la noche (V2_F del histograma) ---------------------------------


def test_sin_horario_de_inicio_no_hay_hora_de_la_noche():
    """Es la rama que decide si el eje va en hora real o de 1 a VENMAX."""
    assert window_to_clock_time(42, None) is None


def test_la_hora_de_la_noche_avanza_una_ventana_por_ventana():
    """La hora del eje se calcula desde el índice, no acumulando."""
    inicio = datetime(2026, 9, 4, 23, 0, 0)
    una_hora = int(3600 / WINDOW_SECONDS)
    assert window_to_clock_time(0, inicio) == inicio
    assert window_to_clock_time(una_hora, inicio) == datetime(2026, 9, 5, 0, 0, 0)


# -- Duración real de la ventana --------------------------------------------


def test_una_ventana_del_medio_dura_treinta_segundos(sampling_rate):
    n_samples = int(20 * WINDOW_SECONDS * sampling_rate)
    assert window_duration(5, n_samples, sampling_rate) == timedelta(seconds=WINDOW_SECONDS)


def test_la_ultima_ventana_incompleta_dura_lo_que_le_queda(sampling_rate):
    """Un registro que corta la ventana 20 a la mitad: dura media ventana.

    Informar la ventana entera falsearía el total de la noche en
    "Informacion.txt".
    """
    n_samples = int(20.5 * WINDOW_SECONDS * sampling_rate)
    assert window_duration(20, n_samples, sampling_rate) == timedelta(
        seconds=WINDOW_SECONDS / 2
    )


def test_una_ventana_posterior_al_final_del_registro_dura_cero(sampling_rate):
    """Preguntar por una ventana que no existe no debería romper el programa."""
    n_samples = int(20 * WINDOW_SECONDS * sampling_rate)
    assert window_duration(50, n_samples, sampling_rate) == timedelta(0)


# -- Precondiciones ---------------------------------------------------------
#
# El módulo es aritmética pura y no valida sus argumentos: quien llama ya lo
# hizo (`Session.go_to_window()` eleva `WindowOutOfRangeError` antes de llegar
# acá). Estos tests no piden que valide: fijan lo que hace hoy, para que si
# alguien decide agregar validación sea una decisión y no un accidente.


def test_un_indice_negativo_devuelve_numeros_negativos_sin_avisar(sampling_rate):
    """Documentado en el docstring del módulo: no valida, y quien llama sí."""
    start, stop = window_to_samples(-1, sampling_rate)
    assert start < 0
    assert stop == 0


def test_una_frecuencia_de_cero_no_se_puede_convertir(sampling_rate):
    """Una división por cero es correcta acá: no hay ventana que calcular."""
    with pytest.raises(ZeroDivisionError):
        sample_to_window(100, 0.0)


@pytest.mark.parametrize("frecuencia", [0.0, -256.0, float("nan"), float("inf")])
def test_ninguna_conversion_acepta_una_frecuencia_no_positiva(frecuencia):
    """La promesa del módulo valía para dos de las cuatro funciones.

    `window_to_samples` devolvía `(0, 0)` y `window_duration` devolvía cero, en
    silencio: una frecuencia corrupta leída de un EDF producía una ventana vacía
    en vez de un error, y el problema aparecía mucho después y lejos.
    """
    with pytest.raises(ZeroDivisionError):
        window_to_samples(5, frecuencia)
    with pytest.raises(ZeroDivisionError):
        window_duration(5, 1000, frecuencia)
    with pytest.raises(ZeroDivisionError):
        sample_to_window(100, frecuencia)
    with pytest.raises(ZeroDivisionError):
        count_windows(1000, frecuencia)


def test_un_registro_vacio_con_frecuencia_corrupta_tambien_falla():
    """El atajo de `n_samples <= 0` no puede tapar el archivo corrupto."""
    with pytest.raises(ZeroDivisionError):
        count_windows(0, 0.0)


def test_la_cantidad_de_ventanas_nunca_es_negativa(sampling_rate):
    """Es lo único que garantiza la guarda de `n_samples <= 0`, y nadie lo pedía.

    Un registro vacío da 0 con guarda y sin ella, así que borrarla dejaba la
    suite en verde. Donde sí importa es más abajo: con menos muestras que
    -1 ventana, la fórmula devuelve un número negativo, y ese número va
    derecho a `Scoring(n_windows=...)`.
    """
    por_ventana = int(WINDOW_SECONDS * sampling_rate)
    assert count_windows(-40 * por_ventana, sampling_rate) == 0


@pytest.mark.parametrize(("n_samples", "ventanas"), [(0, 0), (1, 1)])
def test_los_extremos_de_count_windows(n_samples, ventanas, sampling_rate):
    """Cero muestras dan cero ventanas; una muestra ya da una.

    Nadie llamaba a `count_windows` con estos dos valores, y el atajo
    `if n_samples <= 0: return 0` quedaba sin exigir: cambiarlo por `< 0`, por
    `== 0` o por `<= 1` dejaba la suite en verde. La segunda variante es la que
    duele: un registro de una sola muestra pasaría a tener cero ventanas y el
    programa diría que no hay nada que scorear.
    """
    assert count_windows(n_samples, sampling_rate) == ventanas


def test_una_muestra_mas_que_un_multiplo_exacto_abre_una_ventana(sampling_rate):
    """El `- 1` de `count_windows` tiene que ser exactamente uno.

    `count_windows` se define como `sample_to_window(n_samples - 1) + 1`. Con
    `- 2` la cuenta sólo cambia cuando la penúltima muestra cae en la ventana
    anterior, que es justo este caso: un registro de veinte ventanas más una
    muestra. Los tests que había —veinte ventanas justas y veinte y media— dan
    el mismo número con las dos versiones.
    """
    por_ventana = int(WINDOW_SECONDS * sampling_rate)
    assert count_windows(20 * por_ventana + 1, sampling_rate) == 21


def test_un_hercio_es_una_frecuencia_valida():
    """1 Hz no es una frecuencia corrupta: está en el registro de prueba.

    El EDF de la Sleep-EDF trae `Resp oro-nasal`, `EMG submental`,
    `Temp rectal` y `Event marker` a 1 Hz. Nada exigía que la guarda fuera
    `<= 0` y no `<= 1`, y con `<= 1` esos cuatro canales harían fallar la
    apertura del archivo con un error que habla de una frecuencia inválida.
    """
    assert count_windows(90, 1.0) == 3
    assert window_to_samples(1, 1.0) == (30, 60)


# -- Las otras unidades: fracción de ventana y segundos ----------------------


def test_la_mitad_de_la_ventana_es_la_fraccion_un_medio():
    """Es la conversión que necesita el medidor de ocupación.

    Su `OccupancyLine` trabaja en fracción y `ViewerTool` le entrega segundos;
    saltearse esta conversión es lo que haría informar 3000 % de ocupación.
    """
    assert seconds_to_window_fraction(WINDOW_SECONDS / 2) == pytest.approx(0.5)
    assert seconds_to_window_fraction(0.0) == pytest.approx(0.0)
    assert seconds_to_window_fraction(WINDOW_SECONDS) == pytest.approx(1.0)


def test_la_fraccion_y_los_segundos_son_inversas():
    for segundos in (0.0, 7.5, 15.0, 29.9):
        fraccion = seconds_to_window_fraction(segundos)
        assert window_fraction_to_seconds(fraccion) == pytest.approx(segundos)


def test_un_evento_al_inicio_de_una_ventana_cae_en_su_primera_muestra(sampling_rate):
    """Es la conversión que necesita el anotador: recibe segundos y guarda muestras."""
    for ventana in (0, 1, 19, 500):
        start, _ = window_to_samples(ventana, sampling_rate)
        assert seconds_to_sample(ventana, 0.0, sampling_rate) == start


def test_segundos_y_muestras_son_inversas_con_una_frecuencia_no_redonda():
    """Con 256,125 Hz, que es el caso que rompe las cuentas ingenuas."""
    frecuencia = 256.125
    for ventana in (0, 1, 960):
        for segundos in (0.0, WINDOW_SECONDS * 0.4, WINDOW_SECONDS - 0.5):
            muestra = seconds_to_sample(ventana, segundos, frecuencia)
            vuelta = sample_to_seconds(ventana, muestra, frecuencia)
            assert vuelta == pytest.approx(segundos, abs=1 / frecuencia)


def test_un_evento_anotado_cae_en_la_ventana_de_la_que_salio():
    """La propiedad que importa de verdad: la anotación no se corre de ventana.

    Con una frecuencia no redonda, calcular la muestra como
    `ventana * 30 * fs + segundos * fs` la deja caer en la ventana de al lado.
    """
    frecuencia = 256.125
    for ventana in (0, 1, 500, 960, 2000):
        for segundos in (0.0, 15.0, 29.99):
            muestra = seconds_to_sample(ventana, segundos, frecuencia)
            assert sample_to_window(muestra, frecuencia) == ventana


def test_una_muestra_pedida_al_filo_de_la_ventana_sigue_en_esa_ventana():
    """La promesa textual del módulo, que no se cumplía.

    `floor(i·spw) + floor(off·fs)` puede alcanzar el borde de la ventana
    siguiente. Medido a 256,125 Hz —una frecuencia real de EDF— sobre ocho
    horas: 240 de 960 ventanas caían del otro lado. Una anotación marcada al
    final de la ventana desaparecía del lugar donde el usuario la puso.
    """
    frecuencia = 256.125
    fuera = [
        i
        for i in range(960)
        if sample_to_window(
            seconds_to_sample(i, WINDOW_SECONDS - 0.001, frecuencia), frecuencia
        )
        != i
    ]
    assert not fuera, f"{len(fuera)} ventanas devolvieron una muestra de otra ventana"


def test_el_recorte_cae_en_la_ultima_muestra_de_la_ventana():
    """El recorte tiene que dar `stop - 1`, no `stop - 2`.

    Los tests de al lado afirman que la muestra recortada **pertenece** a la
    ventana, y eso lo cumple cualquier muestra de adentro: con `stop - 2` la
    suite seguía verde y una anotación marcada en el último instante quedaba
    una muestra antes de donde el usuario la puso.
    """
    for frecuencia in (256.0, 256.125):
        _, stop = window_to_samples(3, frecuencia)
        assert seconds_to_sample(3, WINDOW_SECONDS, frecuencia) == stop - 1
        assert seconds_to_sample(3, 10 * WINDOW_SECONDS, frecuencia) == stop - 1


def test_el_redondeo_de_una_muestra_es_hacia_abajo():
    """Fija el sentido, que ningún test distinguía.

    Con `ceil` en vez de `floor` el resultado se corre una muestra, y la
    tolerancia de los otros tests —una muestra entera— no lo nota.
    """
    assert seconds_to_sample(0, 0.019, 100.0) == 1
