"""Tests de la conversión entre ventanas, muestras y tiempo.

Es matemática pura y sin interfaz, así que se puede testear a fondo. También
es el lugar donde más barato sale un error de una unidad: si la conversión se
corre en una ventana, todo el scoring queda desplazado 30 segundos y el
resultado es sutilmente incorrecto en vez de romperse de forma visible.
"""

from datetime import datetime, timedelta

import pytest

from psglab.core.windows import (
    count_windows,
    sample_to_window,
    window_duration,
    window_to_clock_time,
    window_to_samples,
)


def test_registro_exacto_da_cantidad_exacta_de_ventanas(sampling_rate):
    """Diez minutos a 256 Hz son exactamente 20 ventanas de 30 segundos."""
    n_samples = int(600 * sampling_rate)
    assert count_windows(n_samples, sampling_rate) == 20


def test_ultima_ventana_incompleta_se_cuenta_igual(sampling_rate):
    """Un registro que corta a la mitad de una ventana la cuenta igual.

    El usuario tiene que poder ver y scorear la última ventana aunque esté
    incompleta; descartarla perdería datos reales del final de la noche.
    """
    n_samples = int(615 * sampling_rate)  # 20 ventanas y media
    assert count_windows(n_samples, sampling_rate) == 21


def test_registro_vacio_no_tiene_ventanas(sampling_rate):
    assert count_windows(0, sampling_rate) == 0


def test_primera_ventana_arranca_en_la_muestra_cero(sampling_rate):
    start, stop = window_to_samples(0, sampling_rate)
    assert start == 0
    assert stop == int(30 * sampling_rate)


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
    assert start == int(960 * 30 * fs)


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


def test_la_hora_de_la_noche_avanza_treinta_segundos_por_ventana():
    """Ciento veinte ventanas de 30 s son exactamente una hora."""
    inicio = datetime(2026, 9, 4, 23, 0, 0)
    assert window_to_clock_time(0, inicio) == inicio
    assert window_to_clock_time(120, inicio) == datetime(2026, 9, 5, 0, 0, 0)


# -- Duración real de la ventana --------------------------------------------


def test_una_ventana_del_medio_dura_treinta_segundos(sampling_rate):
    n_samples = int(600 * sampling_rate)
    assert window_duration(5, n_samples, sampling_rate) == timedelta(seconds=30)


def test_la_ultima_ventana_incompleta_dura_lo_que_le_queda(sampling_rate):
    """Un registro de 615 s corta la ventana 20 a la mitad: dura 15 s, no 30.

    Informar 30 s falsearía el total de la noche en "Informacion.txt".
    """
    n_samples = int(615 * sampling_rate)
    assert window_duration(20, n_samples, sampling_rate) == timedelta(seconds=15)


def test_una_ventana_posterior_al_final_del_registro_dura_cero(sampling_rate):
    """Preguntar por una ventana que no existe no debería romper el programa."""
    n_samples = int(600 * sampling_rate)
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
