"""Tests de la conversión entre ventanas, muestras y tiempo.

Es matemática pura y sin interfaz, así que se puede testear a fondo. También
es el lugar donde más barato sale un error de una unidad: si la conversión se
corre en una ventana, todo el scoring queda desplazado 30 segundos y el
resultado es sutilmente incorrecto en vez de romperse de forma visible.
"""

import pytest

from psglab.core.windows import count_windows, sample_to_window, window_to_samples

pytestmark = pytest.mark.skip(reason="Esqueleto: la lógica todavía no está implementada.")


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
