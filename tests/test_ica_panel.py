"""Tests del panel de inspección de la ICA.

**El dibujo no se testea.** Lo que sí son las decisiones que el panel toma
alrededor de una advertencia concreta: quitar el componente equivocado modifica
la señal de forma irreversible.

De ahí salen las tres afirmaciones que más importan acá:

- **Ninguno viene marcado de fábrica.** Sugerir cuál quitar sería adivinar por
  el usuario sobre una operación que no se puede deshacer.
- **Nada se aplica solo**: marcar no hace nada hasta que se aprieta el botón.
- **Lo que se lee en pantalla es base 1 y lo que sale es base 0**, porque es lo
  que `apply_ica()` espera. Equivocar la conversión quitaría un componente
  distinto del que el usuario marcó, que es exactamente el error irreversible
  que todo esto trata de evitar.
"""

import numpy as np
import pytest

pytest.importorskip("pyqtgraph")

from psglab.ui.ica_panel import IcaPanel  # noqa: E402


@pytest.fixture
def panel(qt_app) -> IcaPanel:
    widget = IcaPanel()
    widget.resize(800, 400)
    return widget


def topografias(cuantos: int = 3) -> list[dict[str, float]]:
    """Una topografía por componente, con una forma distinta cada una."""
    canales = ["Fp1", "Fp2", "O1", "O2"]
    return [
        {canal: 1.0 if posicion == numero % len(canales) else 0.2
         for posicion, canal in enumerate(canales)}
        for numero in range(cuantos)
    ]


# -- Qué queda cargado -------------------------------------------------------


def test_arranca_vacio(panel: IcaPanel):
    assert panel.component_count() == 0
    assert panel.excluded() == []
    assert panel.shown_component() is None


def test_carga_un_componente_por_topografia(panel: IcaPanel):
    panel.set_components(topografias(4))

    assert panel.component_count() == 4


def test_muestra_el_primero_al_cargar(panel: IcaPanel):
    """Que el panel arranque en blanco obligaría a un clic para ver nada."""
    panel.set_components(topografias())

    assert panel.shown_component() == 0


def test_las_barras_son_las_del_componente_mostrado(panel: IcaPanel):
    todas = topografias(3)
    panel.set_components(todas)

    assert panel.topography_bars() == todas[0]


def test_cambiar_de_componente_cambia_las_barras(panel: IcaPanel):
    todas = topografias(3)
    panel.set_components(todas)
    panel.lista.setCurrentRow(2)

    assert panel.topography_bars() == todas[2]


# -- Nada se marca ni se aplica solo -----------------------------------------


def test_ninguno_viene_marcado(panel: IcaPanel):
    """**Sugerir cuál quitar sería adivinar por el usuario** sobre una
    operación que no se puede deshacer."""
    panel.set_components(topografias(4))

    assert panel.excluded() == []


def test_marcar_no_aplica_nada(panel: IcaPanel):
    """Marcar es inspeccionar; aplicar es otro paso."""
    aplicados: list[list[int]] = []
    panel.on_apply = aplicados.append
    panel.set_components(topografias(3))

    panel.set_excluded([0, 2])

    assert aplicados == []


def test_el_boton_avisa_que_componentes_marco(panel: IcaPanel):
    aplicados: list[list[int]] = []
    panel.on_apply = aplicados.append
    panel.set_components(topografias(3))
    panel.set_excluded([0, 2])

    panel._aplicar()

    assert aplicados == [[0, 2]]


def test_aplicar_sin_marcar_nada_avisa_con_una_lista_vacia(panel: IcaPanel):
    """No es lo mismo que no apretar: reconstruir sin quitar nada sirve para
    comprobar que la descomposición no rompe la señal."""
    aplicados: list[list[int]] = []
    panel.on_apply = aplicados.append
    panel.set_components(topografias(2))

    panel._aplicar()

    assert aplicados == [[]]


def test_sin_componentes_el_boton_esta_apagado(panel: IcaPanel):
    assert not panel.boton.isEnabled()

    panel.set_components(topografias(2))
    assert panel.boton.isEnabled()


# -- Base 1 al mostrar, base 0 al devolver -----------------------------------


def test_lo_que_se_lee_en_pantalla_empieza_en_uno(panel: IcaPanel):
    panel.set_components(topografias(3))

    assert panel.lista.item(0).text() == "Componente 1"
    assert panel.lista.item(2).text() == "Componente 3"


def test_lo_que_se_devuelve_empieza_en_cero(panel: IcaPanel):
    """**Es lo que `apply_ica()` espera.** Equivocar la conversión quitaría un
    componente distinto del que el usuario marcó."""
    panel.set_components(topografias(3))
    panel.set_excluded([0])

    assert panel.excluded() == [0]
    assert panel.lista.item(0).text() == "Componente 1"


# -- Recargar ----------------------------------------------------------------


def test_recargar_no_acumula_componentes(panel: IcaPanel):
    panel.set_components(topografias(4))
    panel.set_components(topografias(2))

    assert panel.component_count() == 2


def test_recargar_desmarca_lo_de_antes(panel: IcaPanel):
    """Una marca de una descomposición vieja aplicada a otra quitaría un
    componente que el usuario nunca miró."""
    panel.set_components(topografias(3))
    panel.set_excluded([0, 1])

    panel.set_components(topografias(3))

    assert panel.excluded() == []


def test_vaciar_lo_deja_como_al_principio(panel: IcaPanel):
    panel.set_components(topografias(3))
    panel.clear_components()

    assert panel.component_count() == 0
    assert panel.shown_component() is None
    assert not panel.boton.isEnabled()


# -- La curva temporal (hito 19) ---------------------------------------------
#
# La topografía dice **dónde** pesa el componente y la curva dice **cuándo**
# ocurre. Con una sola de las dos, el investigador decide a ciegas sobre una
# operación que no se puede deshacer. El panel no la calcula: avisa cuál se está
# mirando y espera que le pasen la curva, que es el mismo reparto de `PsdPanel`.


def test_al_arrancar_no_hay_curva(panel: IcaPanel):
    assert panel.time_course_data() is None


def test_la_curva_que_le_dan_es_la_que_queda(panel: IcaPanel):
    panel.set_components(topografias(2))
    segundos = np.linspace(0.0, 30.0, 300)
    valores = np.sin(segundos)

    panel.set_time_course(segundos, valores)

    x, y = panel.time_course_data()
    assert np.allclose(x, segundos)
    assert np.allclose(y, valores)


def test_elegir_un_componente_pide_su_curva(panel: IcaPanel):
    """El panel avisa **cuál** se está mirando: reconstruir las fuentes cuesta,
    y de otro modo se pagarían todas para mirar una."""
    pedidos: list[int] = []
    panel.on_component_shown = pedidos.append

    panel.set_components(topografias(3))
    assert pedidos == [0], "no pidió la curva del que muestra al abrirse"

    panel.lista.setCurrentRow(2)
    assert pedidos == [0, 2]


def test_cambiar_de_componente_borra_la_curva_anterior(panel: IcaPanel):
    """**Es el mismo cuidado que `set_components()` tiene con las marcas.** Una
    curva vieja debajo de otra topografía se lee como si fuera de ésta."""
    panel.set_components(topografias(3))
    panel.set_time_course(np.linspace(0.0, 30.0, 10), np.zeros(10))

    panel.lista.setCurrentRow(1)

    assert panel.time_course_data() is None


def test_vaciar_el_panel_tambien_borra_la_curva(panel: IcaPanel):
    panel.set_components(topografias(2))
    panel.set_time_course(np.linspace(0.0, 30.0, 10), np.zeros(10))

    panel.clear_components()

    assert panel.time_course_data() is None
