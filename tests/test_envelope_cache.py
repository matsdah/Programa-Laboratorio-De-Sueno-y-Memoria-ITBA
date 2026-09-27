"""Tests de la caché de la envolvente (`psglab/ui/envelope_cache.py`).

Sin Qt: la caché es numpy y un diccionario, y se testea sin armar ninguna
ventana. Lo que se verifica es lo que la hace servir: que dé lo mismo que
calcular la envolvente de una vez, que no recalcule lo que ya tiene, que olvide
lo de otro registro y que no crezca sin límite. Lo que se dibuja con ella está
en `test_signal_view.py`.
"""

import numpy as np
import pytest

from psglab.core.decimation import bucket_size_for, envelope_by_bucket_size
from psglab.ui import envelope_cache as modulo
from psglab.ui.envelope_cache import CUBETAS_POR_TROZO, EnvelopeCache


@pytest.fixture
def canal() -> np.ndarray:
    """Diez minutos a 100 Hz con picos que la envolvente no puede perder."""
    generador = np.random.default_rng(0)
    senal = generador.normal(size=60_000)
    senal[12_345] = 500.0
    senal[40_000] = -700.0
    return senal


def test_con_pocas_muestras_devuelve_todas(canal: np.ndarray):
    posiciones, valores = EnvelopeCache().samples_to_draw("C3", 100, 300, canal, 1000)

    assert np.array_equal(posiciones, np.arange(200))
    assert np.array_equal(valores, canal[100:300])


def test_con_muchas_muestras_devuelve_la_envolvente_sin_perder_picos(canal: np.ndarray):
    posiciones, valores = EnvelopeCache().samples_to_draw("C3", 0, len(canal), canal, 1000)

    assert len(valores) < len(canal) // 10
    assert valores.max() == pytest.approx(500.0)
    assert valores.min() == pytest.approx(-700.0)
    assert np.array_equal(valores, canal[posiciones])


def test_por_trozos_da_lo_mismo_que_de_una_vez(canal: np.ndarray):
    """Los trozos son una forma de guardar, no de calcular otra cosa."""
    por_cubeta = bucket_size_for(len(canal), 1000)
    esperados, _ = envelope_by_bucket_size(canal, por_cubeta)

    posiciones, _ = EnvelopeCache().samples_to_draw("C3", 0, len(canal), canal, 1000)

    assert np.array_equal(posiciones, esperados)


def test_lo_ya_calculado_no_se_vuelve_a_calcular(canal: np.ndarray, monkeypatch):
    """Es lo que hace servir la caché de un cuadro al otro: correr la página un
    poco sólo calcula los trozos que entran."""
    llamadas = []
    original = modulo.envelope_by_bucket_size

    def contando(senal, por_cubeta):
        llamadas.append(len(senal))
        return original(senal, por_cubeta)

    monkeypatch.setattr(modulo, "envelope_by_bucket_size", contando)
    cache = EnvelopeCache()
    cache.samples_to_draw("C3", 0, 30_000, canal, 1000)
    primeras = len(llamadas)

    cache.samples_to_draw("C3", 0, 30_000, canal, 1000)

    assert primeras > 0
    assert len(llamadas) == primeras


def test_los_trozos_se_cuentan_desde_el_registro_y_no_desde_la_pagina(
    canal: np.ndarray, monkeypatch
):
    """Corrida una cubeta, la página vuelve a usar casi todos sus trozos."""
    llamadas = []
    original = modulo.envelope_by_bucket_size
    monkeypatch.setattr(
        modulo,
        "envelope_by_bucket_size",
        lambda senal, por_cubeta: llamadas.append(1) or original(senal, por_cubeta),
    )
    cache = EnvelopeCache()
    cache.samples_to_draw("C3", 0, 30_000, canal, 1000)
    antes = len(llamadas)
    por_cubeta = bucket_size_for(30_000, 1000)

    cache.samples_to_draw("C3", por_cubeta, 30_000 + por_cubeta, canal, 1000)

    assert len(llamadas) - antes <= 1


def test_otro_registro_la_vacia():
    """Filtrar devuelve un registro nuevo con los mismos índices de muestra: sin
    esto se dibujaría la envolvente de la señal cruda sobre la filtrada."""
    cache = EnvelopeCache()
    cache.forget_if_changed("registro A")
    cache.samples_to_draw("C3", 0, 60_000, np.zeros(60_000), 1000)
    assert len(cache) > 0

    cache.forget_if_changed("registro A")
    assert len(cache) > 0
    cache.forget_if_changed("registro B")
    assert len(cache) == 0


def test_tiene_tope():
    cache = EnvelopeCache(capacity=3)

    cache.samples_to_draw("C3", 0, 60_000, np.zeros(60_000), 1000)

    assert 60_000 // (CUBETAS_POR_TROZO * bucket_size_for(60_000, 1000)) > 3
    assert len(cache) == 3
