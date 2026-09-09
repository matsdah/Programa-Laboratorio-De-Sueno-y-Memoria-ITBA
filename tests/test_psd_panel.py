"""Tests del panel del espectro.

**El dibujo no se testea.** Lo que sí, y por eso el panel separa `channels()`,
`band_ranges()` y `curve_data()` del `paintEvent` de pyqtgraph, es lo que es una
decisión: qué curvas quedan, dónde cae cada banda sombreada, y que redibujar
reemplace en vez de acumular.

Ese último es el que importa: si pedir el espectro de otra ventana dejara
encima la curva de la anterior, el investigador vería dos espectros
superpuestos y creería que el espectro cambió menos de lo que cambió.
"""

import numpy as np
import pytest

pytest.importorskip("pyqtgraph")

from psglab.analysis.psd import DEFAULT_BANDS  # noqa: E402
from psglab.ui.psd_panel import PsdPanel  # noqa: E402


@pytest.fixture
def panel(qt_app) -> PsdPanel:
    widget = PsdPanel()
    widget.resize(600, 400)
    return widget


def espectro(canales: int = 1, puntos: int = 201):
    """Frecuencias de 0 a 50 Hz y una potencia por canal."""
    frecuencias = np.linspace(0.0, 50.0, puntos)
    potencias = np.vstack(
        [np.exp(-((frecuencias - (10.0 * (i + 1))) ** 2)) + 1e-6 for i in range(canales)]
    )
    return frecuencias, potencias


# -- Qué queda dibujado ------------------------------------------------------


def test_arranca_vacio(panel: PsdPanel):
    assert panel.channels() == []
    assert panel.band_ranges() == {}


def test_dibuja_una_curva_por_canal(panel: PsdPanel):
    frecuencias, potencias = espectro(canales=3)
    panel.set_spectrum(frecuencias, potencias, ["C3", "C4", "O1"])

    assert panel.channels() == ["C3", "C4", "O1"]


def test_los_puntos_salen_en_microvoltios_cuadrados_y_no_en_su_logaritmo(
    panel: PsdPanel,
):
    """**El eje va en logarítmico y eso no puede escaparse del panel.**

    `PlotDataItem.getData()` devuelve lo que se dibuja, así que con el eje
    logarítmico una potencia de 1e-6 vuelve como -6. Quien pregunta por el
    espectro está pensando en potencia, no en su logaritmo. Es la misma
    confusión de unidades que el proyecto persigue con los píxeles.
    """
    frecuencias, potencias = espectro()
    panel.set_spectrum(frecuencias, potencias, ["C3"])

    x, y = panel.curve_data("C3")
    assert np.allclose(x, frecuencias)
    assert np.allclose(y, potencias[0])
    assert np.all(y > 0), "salieron logaritmos, no potencias"


def test_un_canal_que_no_esta_devuelve_none(panel: PsdPanel):
    panel.set_spectrum(*espectro(), ["C3"])

    assert panel.curve_data("O2") is None


def test_una_psd_de_un_solo_canal_en_una_dimension_tambien_entra(panel: PsdPanel):
    """`compute_psd` devuelve dos dimensiones, pero un llamador puede pasar la
    fila sola."""
    frecuencias, potencias = espectro()
    panel.set_spectrum(frecuencias, potencias[0], ["C3"])

    assert panel.channels() == ["C3"]


def test_sobran_nombres_de_canal_y_no_rompe(panel: PsdPanel):
    """Un nombre de más no puede voltear el panel: se dibuja lo que hay."""
    frecuencias, potencias = espectro(canales=1)
    panel.set_spectrum(frecuencias, potencias, ["C3", "C4"])

    assert panel.channels() == ["C3"]


# -- Redibujar reemplaza -----------------------------------------------------


def test_redibujar_no_acumula_curvas(panel: PsdPanel):
    """**El error que haría creer que el espectro cambió menos de lo que
    cambió.**"""
    panel.set_spectrum(*espectro(canales=2), ["C3", "C4"])
    panel.set_spectrum(*espectro(canales=1), ["O1"])

    assert panel.channels() == ["O1"]


def test_redibujar_no_acumula_bandas(panel: PsdPanel):
    panel.set_spectrum(*espectro(), ["C3"])
    cuantas = len(panel.band_ranges())
    panel.set_spectrum(*espectro(), ["C3"])

    assert len(panel.band_ranges()) == cuantas


def test_vaciar_lo_deja_como_al_principio(panel: PsdPanel):
    panel.set_spectrum(*espectro(), ["C3"])
    panel.clear_spectrum()

    assert panel.channels() == []


# -- Las bandas --------------------------------------------------------------


def test_sombrea_las_bandas_convencionales(panel: PsdPanel):
    panel.set_spectrum(*espectro(), ["C3"])

    assert set(panel.band_ranges()) == set(DEFAULT_BANDS)


def test_cada_banda_cae_donde_dice(panel: PsdPanel):
    panel.set_spectrum(*espectro(), ["C3"])
    rangos = panel.band_ranges()

    for nombre, (desde, hasta) in DEFAULT_BANDS.items():
        assert rangos[nombre] == pytest.approx((desde, hasta))


def test_se_pueden_pedir_bandas_propias(panel: PsdPanel):
    """Los límites varían entre laboratorios, igual que en el módulo."""
    panel.set_spectrum(*espectro(), ["C3"], bands={"mia": (9.0, 11.0)})

    assert panel.band_ranges() == {"mia": pytest.approx((9.0, 11.0))}


# -- El eje ------------------------------------------------------------------


def test_la_potencia_va_en_logaritmico(panel: PsdPanel):
    """**No es una preferencia.** La potencia delta de una ventana de sueño
    lento es de dos a tres órdenes de magnitud mayor que la gamma de la misma
    ventana: en lineal, todo lo que no es delta queda aplastado contra el eje.
    """
    assert panel.uses_log_power


def test_un_espectro_vacio_no_rompe(panel: PsdPanel):
    """Puede pasar si alguien pide el espectro de un tramo sin datos."""
    panel.set_spectrum(np.array([]), np.empty((0, 0)), [])

    assert panel.channels() == []


# -- La potencia por banda (hito 19) -----------------------------------------
#
# **El sombreado no es la potencia por banda.** El panel marcaba dónde cae cada
# banda sobre la curva y nunca decía cuánta potencia tenía, mientras
# `band_power()` la calculaba desde el hito 13 y no la leía nadie. Delta se ve
# alta a ojo; theta contra sigma, no.


def test_arranca_sin_potencias(panel: PsdPanel):
    assert panel.band_powers() == {}
    assert panel.tabla.rowCount() == 0


def test_las_potencias_que_le_dan_son_las_que_quedan(panel: PsdPanel):
    panel.set_spectrum(*espectro(), ["C3"])
    panel.set_band_powers({"Delta": (12.5, 0.62), "Theta": (3.25, 0.16)})

    assert panel.band_powers() == {"Delta": (12.5, 0.62), "Theta": (3.25, 0.16)}
    assert panel.tabla.rowCount() == 2


def test_la_tabla_muestra_la_banda_la_absoluta_y_la_relativa(panel: PsdPanel):
    """**Van las dos.** La absoluta depende del grosor del cráneo y de la
    impedancia; la relativa es la que permite comparar entre participantes, y
    es la que no se veía en ningún lado."""
    panel.set_spectrum(*espectro(), ["C3"])
    panel.set_band_powers({"Delta": (12.5, 0.625)})

    fila = [panel.tabla.item(0, columna).text() for columna in range(3)]
    assert fila[0] == "Delta"
    assert fila[2] == "62,5", "la relativa tiene que salir como porcentaje"


def test_el_separador_decimal_es_la_coma(panel: PsdPanel):
    """La misma convención que el informe de impedancia y la ocupación."""
    panel.set_band_powers({"Alpha": (1.5, 0.5)})

    for columna in (1, 2):
        assert "." not in panel.tabla.item(0, columna).text()


def test_pedir_otro_espectro_vacia_las_potencias_viejas(panel: PsdPanel):
    """**Es el mismo cuidado que con las curvas.** Unas potencias de la ventana
    anterior debajo del espectro de ésta se leerían como si fueran de ésta."""
    panel.set_spectrum(*espectro(), ["C3"])
    panel.set_band_powers({"Delta": (12.5, 0.62)})

    panel.set_spectrum(*espectro(), ["C4"])

    assert panel.band_powers() == {}
    assert panel.tabla.rowCount() == 0
