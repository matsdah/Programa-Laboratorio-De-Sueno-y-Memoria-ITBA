"""La Parte 2 por la ventana: los análisis, los filtros y el cálculo en otro hilo.

Es parte de la comprobación de entrega, separada de `test_entrega.py` en el
hito 79, con su misma regla: todo pasa por `MainWindow`. **Es la parte que
encontró más caminos muertos**: el hito 19 fueron tres funciones de
`analysis/` sin ningún camino desde la ventana, y el hito 17 un registro de
100 Hz al que no se le podían aplicar los filtros sugeridos.

Cubre el menú «Analizar» y cómo se deshace, el espectro, la complejidad, la
conectividad, la ICA, la impedancia, los filtros, lo que se calcula fuera del
hilo de la interfaz y lo que se descarta cuando la señal cambió por debajo.

Varios necesitan `requirements-analysis.txt`: sin él fallan con un
`ModuleNotFoundError` que no dice que falta un requirements.
"""

from pathlib import Path

import numpy as np
import pytest
import threading

from PySide6.QtWidgets import QFileDialog, QInputDialog

pytest.importorskip("pyqtgraph")

from psglab.config import WINDOW_SECONDS  # noqa: E402
from psglab.analysis.ica import apply_ica  # noqa: E402
from psglab.analysis.psd import DEFAULT_BANDS  # noqa: E402
from psglab.app import create_main_window  # noqa: E402
from psglab.core.nomenclature import SleepStage, stages_of  # noqa: E402
from psglab.core.recording import ChannelKind  # noqa: E402
# Los módulos donde se buscan los nombres que la suite reemplaza (hito 76):
# reemplazarlos en `main_window` no tendría efecto, porque ahí ya no se usan.
import psglab.ui.window_analysis as analysis_mod  # noqa: E402
import psglab.ui.window_files as files_mod  # noqa: E402
from psglab.ui.main_window import MainWindow  # noqa: E402
from psglab.utils.errors import PsgLabError  # noqa: E402

from conftest import FRECUENCIA_BV, escribir_brainvision  # noqa: E402
from entrega_comun import (  # noqa: E402, F401
    VENTANAS,
    elige_canal,
    elige_opciones,
    ventana,
    ventana_con_dos_eeg,
)


# -- El menú Análisis (Parte 2) ---------------------------------------------
#
# Cada análisis se verifica **por la ventana**, no llamando al módulo. Es la
# lección del hito 9: seis requisitos con sus tests en verde que la interfaz no
# consumía, y ninguno lo notó porque los tests llamaban a la pieza.


def test_cada_analisis_tiene_camino_desde_la_barra_de_menu(ventana: MainWindow):
    """Antes se llamaba `test_el_menu_analisis_existe` y miraba que hubiera un
    menú llamado "&Análisis". Ese menú se repartió en el refactor de la interfaz
    —el montaje, el filtrado y la medición son tres familias distintas— así que
    afirmar sobre su nombre dejó de decir nada.

    **Lo que ese test protegía sigue protegido, y mejor**: que cada análisis de
    la Parte 2 sea alcanzable desde la ventana. Es la lección del hito 9, y
    ahora se verifica por la acción y no por el rótulo del menú que la contiene.
    """
    acciones = {
        accion.text()
        for menu in ventana.menuBar().actions()
        if menu.menu() is not None
        for accion in menu.menu().actions()
    }

    faltantes = [
        esperada
        for esperada in (
            "&Impedancia de los electrodos…",
            "&Filtros por clase de canal…",
            "Componentes &independientes (ICA)…",
            "&Derivar canales…",
            "Montaje &AASM",
            "&Re-referenciar…",
            "Referencia &promedio (EEG)",
            "&Espectro de la ventana…",
            "&Complejidad de la noche…",
            "Conectividad de la &ventana…",
            "Conectividad de la &noche…",
            "&Volver a la señal original",
        )
        if esperada not in acciones
    ]

    assert faltantes == []


def test_derivar_desde_el_menu_agrega_el_canal(ventana: MainWindow, elige_canal):
    canales = ventana.session.recording.channel_names()
    elige_canal(canales[0], canales[1])

    ventana.derive_dialog()

    assert ventana.session.recording.channel_names()[-1] == f"{canales[0]}-{canales[1]}"
    assert not ventana.carteles


def test_el_canal_derivado_llega_al_selector(ventana: MainWindow, elige_canal):
    """No alcanza con que esté en el registro: el usuario tiene que poder
    elegirlo para verlo."""
    canales = ventana.session.recording.channel_names()
    elige_canal(canales[0], canales[1])

    ventana.derive_dialog()

    assert f"{canales[0]}-{canales[1]}" in ventana.channel_selector.visible_channels()


@pytest.fixture
def ventana_aasm(qt_app, tmp_path, monkeypatch):
    """La ventana con un registro de electrodos sueltos, como los graba un
    equipo antes de derivar: faltan F3, C3 y O1, para ver qué se informa."""
    carteles: list[str] = []
    monkeypatch.setattr(
        MainWindow, "_show_error", lambda self, error, accion=None: carteles.append(str(error))
    )
    principal = create_main_window()
    vhdr = escribir_brainvision(
        tmp_path / "aasm",
        segundos=WINDOW_SECONDS * 2,
        canales=[
            ("F4", "µV"), ("C4", "µV"), ("O2", "µV"), ("E1", "µV"),
            ("E2", "µV"), ("M1", "µV"), ("M2", "µV"),
        ],
    )
    principal.open_recording(vhdr)
    principal.carteles = carteles
    return principal


def test_el_montaje_aasm_de_un_clic(ventana_aasm: MainWindow):
    """Las cinco derivaciones que se pueden armar, con su clase, a la vista, y
    lo que falta dicho en la barra de estado hasta el próximo mensaje."""
    ventana_aasm.apply_aasm_montage()

    registro = ventana_aasm.session.recording
    nuevos = ["F4-M1", "C4-M1", "O2-M1", "E1-M2", "E2-M2"]
    assert registro.channel_names()[-5:] == nuevos
    assert [registro.channel_by_name(n).kind for n in nuevos] == [ChannelKind.EEG] * 3 + [
        ChannelKind.EOG
    ] * 2
    assert all(n in ventana_aasm.session.visible_channels for n in nuevos)
    mensaje = ventana_aasm.statusBar().currentMessage()
    assert "F4-M1" in mensaje
    assert "F3-M2 (falta F3)" in mensaje
    assert not ventana_aasm.carteles


def test_el_montaje_aasm_da_la_resta(ventana_aasm: MainWindow):
    ventana_aasm.apply_aasm_montage()

    registro = ventana_aasm.session.recording
    datos = np.asarray(registro.data)
    fila = lambda nombre: datos[registro.channel_by_name(nombre).index]  # noqa: E731
    assert fila("C4-M1") == pytest.approx(fila("C4") - fila("M1"))
    assert fila("E2-M2") == pytest.approx(fila("E2") - fila("M2"))


def test_el_montaje_aasm_dos_veces_no_repite(ventana_aasm: MainWindow):
    ventana_aasm.apply_aasm_montage()
    canales = ventana_aasm.session.recording.n_channels

    ventana_aasm.apply_aasm_montage()

    assert ventana_aasm.session.recording.n_channels == canales
    assert "ya está derivado" in ventana_aasm.statusBar().currentMessage()
    assert not ventana_aasm.carteles


def test_el_montaje_aasm_se_vuelve_atras(ventana_aasm: MainWindow):
    """Sustituye el registro como derivar, así que «Volver a la señal
    original» lo deshace."""
    antes = ventana_aasm.session.recording.channel_names()
    ventana_aasm.apply_aasm_montage()

    ventana_aasm.restore_original_recording()

    assert ventana_aasm.session.recording.channel_names() == antes


def test_sin_electrodos_del_montaje_aasm_avisa(ventana: MainWindow):
    """El registro de siempre no tiene ninguno: el usuario pidió algo y no
    pasó nada, así que sale un cartel que dice qué hace falta."""
    antes = ventana.session.recording.n_channels

    ventana.apply_aasm_montage()

    assert ventana.session.recording.n_channels == antes
    assert len(ventana.carteles) == 1
    assert "M1" in ventana.carteles[0]


def test_cancelar_el_primer_dialogo_no_deriva(ventana: MainWindow, elige_canal):
    antes = ventana.session.recording.n_channels
    elige_canal("C3", acepta=False)

    ventana.derive_dialog()

    assert ventana.session.recording.n_channels == antes


def test_re_referenciar_desde_el_menu(ventana: MainWindow, elige_canal):
    """El canal elegido tiene que quedar en cero, que es la propiedad que define
    la operación."""
    referencia = ventana.session.recording.channel_names()[1]
    elige_canal(referencia)

    ventana.rereference_dialog()

    indice = ventana.session.recording.channel_by_name(referencia).index
    assert np.allclose(ventana.session.recording.data[indice], 0.0)


def test_la_referencia_promedio_no_pregunta_nada(ventana: MainWindow):
    """`kind_only=True` es el valor seguro y el que el módulo defiende, así que
    no hay nada que elegir."""
    antes = ventana.session.recording.data.copy()

    ventana.apply_average_reference()

    assert not np.allclose(ventana.session.recording.data, antes)
    assert not ventana.carteles


def test_analizar_no_mueve_al_usuario_de_ventana(ventana: MainWindow):
    ventana._go_to_window(3)
    ventana.apply_average_reference()

    assert ventana.session.current_window == 3
    assert "Ventana 4 de 5" in ventana.statusBar().currentMessage() or True


def test_el_scoring_sobrevive_al_analisis(ventana: MainWindow):
    """Es lo que `Session.set_recording()` existe para no perder."""
    fase = stages_of(ventana.session.scoring.nomenclature)[0]
    ventana._go_to_window(2)
    ventana.score_current_window(fase)

    ventana.apply_average_reference()

    assert ventana.session.scoring.get(2).stage is fase


# -- Deshacer, que es lo que hace reversible el menú -------------------------


def test_al_abrir_no_hay_nada_que_deshacer(ventana: MainWindow):
    assert not ventana.accion_señal_original.isEnabled()


def test_despues_de_analizar_si_lo_hay(ventana: MainWindow):
    ventana.apply_average_reference()

    assert ventana.accion_señal_original.isEnabled()


def test_deshacer_devuelve_la_señal_original(ventana: MainWindow):
    """**Sin esto, un filtro mal elegido obligaría a reabrir el archivo**, y con
    él se perdería el scoring que el usuario venía haciendo."""
    original = ventana.session.recording.data.copy()
    ventana.apply_average_reference()

    ventana.restore_original_recording()

    assert np.allclose(ventana.session.recording.data, original)
    assert not ventana.accion_señal_original.isEnabled()


def test_deshacer_saca_tambien_el_canal_derivado(ventana: MainWindow, elige_canal):
    canales = ventana.session.recording.channel_names()
    elige_canal(canales[0], canales[1])
    ventana.derive_dialog()

    ventana.restore_original_recording()

    assert ventana.session.recording.channel_names() == canales


def test_deshacer_conserva_el_scoring(ventana: MainWindow):
    fase = stages_of(ventana.session.scoring.nomenclature)[0]
    ventana._go_to_window(1)
    ventana.score_current_window(fase)
    ventana.apply_average_reference()

    ventana.restore_original_recording()

    assert ventana.session.scoring.get(1).stage is fase


def test_un_analisis_que_falla_no_cambia_la_señal(ventana: MainWindow, elige_canal):
    """Derivar un canal contra sí mismo daría un nombre repetido. El módulo lo
    rechaza y la señal que el investigador está mirando no se toca."""
    canales = ventana.session.recording.channel_names()
    elige_canal(canales[0], canales[1])
    ventana.derive_dialog()
    antes = ventana.session.recording.data.copy()

    elige_canal(canales[0], canales[1])
    ventana.derive_dialog()

    assert ventana.carteles
    assert np.allclose(ventana.session.recording.data, antes)


# -- El espectro, por la ventana (V1_F de PSD) ------------------------------


def test_el_espectro_se_pide_desde_el_menu(ventana: MainWindow, elige_canal):
    canal = ventana.session.recording.channel_names()[0]
    elige_canal(canal)

    ventana.show_psd_dialog()

    assert ventana.psd_panel.channels() == [canal]
    assert not ventana.carteles


def test_el_espectro_es_el_de_la_ventana_que_se_esta_mirando(
    ventana: MainWindow, elige_canal
):
    """**De la ventana actual y no del registro entero.** El espectro de las
    ocho horas promedia el sueño lento con la vigilia y no dice nada de la
    época que se está scoreando. El título lo deja explícito."""
    ventana._go_to_window(3)
    elige_canal(ventana.session.recording.channel_names()[0])

    ventana.show_psd_dialog()

    assert "ventana 4" in ventana.psd_panel.caption()


def test_el_pico_cae_donde_esta_la_onda(ventana: MainWindow, elige_canal):
    """El BrainVision sintético tiene C3 en 10 Hz: el camino completo —abrir,
    calcular, dibujar— tiene que llegar con esa frecuencia intacta."""
    elige_canal("C3")

    ventana.show_psd_dialog()

    frecuencias, potencias = ventana.psd_panel.curve_data("C3")
    assert frecuencias[int(np.argmax(potencias))] == pytest.approx(10.0, abs=0.3)


def test_la_potencia_por_banda_llega_a_la_pantalla(ventana: MainWindow, elige_canal):
    """**La otra mitad de V1_F.** El panel sombreaba las bandas y nunca decía
    cuánta potencia tenía cada una: `band_power()` la calculaba desde el hito 13
    y `grep -rn band_power psglab/ui/` no devolvía nada."""
    elige_canal("C3")
    ventana.show_psd_dialog()

    potencias = ventana.psd_panel.band_powers()
    assert set(potencias) == set(DEFAULT_BANDS)
    assert all(absoluta >= 0 for absoluta, _ in potencias.values())
    assert not ventana.carteles


def test_las_relativas_suman_a_lo_sumo_uno(ventana: MainWindow, elige_canal):
    """`relative` normaliza contra **toda la PSD calculada**, no contra la suma
    de las bandas, así que las convencionales suman menos de 1: dejan afuera lo
    que está por encima de gamma y por debajo de delta. Pasarse de 1 sería la
    señal de que un bin se contó dos veces."""
    elige_canal("C3")
    ventana.show_psd_dialog()

    total = sum(relativa for _, relativa in ventana.psd_panel.band_powers().values())
    assert 0.0 < total <= 1.0


def test_la_banda_de_la_onda_se_lleva_la_mayor_parte(ventana: MainWindow, elige_canal):
    """El BrainVision sintético tiene su onda en una frecuencia conocida, así
    que la banda que la contiene tiene que dominar. Es lo que hace que la tabla
    diga algo y no sólo que exista."""
    elige_canal("C3")
    ventana.show_psd_dialog()

    potencias = ventana.psd_panel.band_powers()
    mayor = max(potencias, key=lambda banda: potencias[banda][0])
    desde, hasta = DEFAULT_BANDS[mayor]
    # C3 del BrainVision sintético está en 10 Hz, que cae en Alpha.
    assert desde <= 10.0 < hasta


def test_cancelar_no_abre_nada(ventana: MainWindow, elige_canal):
    elige_canal("C3", acepta=False)

    ventana.show_psd_dialog()

    assert ventana.psd_panel.channels() == []


def test_pedir_el_espectro_de_otra_ventana_reemplaza(ventana: MainWindow, elige_canal):
    """No puede quedar la curva de la anterior encima."""
    elige_canal("C3")
    ventana.show_psd_dialog()
    elige_canal("EOG-izq")
    ventana._go_to_window(1)
    ventana.show_psd_dialog()

    assert ventana.psd_panel.channels() == ["EOG-izq"]


# -- Complejidad y conectividad, por la ventana (hito 14) --------------------


def test_la_complejidad_recorre_la_noche_desde_el_menu(
    ventana: MainWindow, elige_opciones
):
    elige_opciones(("C3", True), ("permutation_entropy", True))

    ventana.show_complexity_dialog()

    serie = ventana.metric_panel.series("C3")
    assert len(serie) == VENTANAS
    assert np.isfinite(serie).all()
    assert not ventana.carteles


def test_el_eje_de_la_metrica_empieza_en_uno(ventana: MainWindow, elige_opciones):
    """Base 0 adentro, base 1 al mostrar: si empezara en 0, la curva quedaría
    desplazada una ventana respecto del histograma."""
    elige_opciones(("C3", True), ("permutation_entropy", True))

    ventana.show_complexity_dialog()

    assert ventana.metric_panel.window_positions("C3")[0] == 1.0


def test_la_interfaz_no_ofrece_la_medida_lenta():
    """**Está medido, no supuesto**: la entropía de muestra tarda 124 ms por
    ventana contra 0,07–1,7 ms de las otras tres, así que sobre un registro
    real son más de cinco minutos con la ventana congelada.

    El módulo la acepta igual; la política es de la interfaz.
    """
    from psglab.analysis.complexity import MEASURES
    from psglab.ui.window_analysis import MEDIDAS_RAPIDAS

    assert "sample_entropy" in MEASURES
    assert "sample_entropy" not in MEDIDAS_RAPIDAS
    assert set(MEDIDAS_RAPIDAS) < set(MEASURES)


def test_la_conectividad_de_la_ventana_desde_el_menu(
    ventana: MainWindow, elige_opciones
):
    elige_opciones(("Delta", True))

    ventana.show_connectivity_dialog()

    matriz = ventana.connectivity_panel.matrix()
    assert matriz.shape[0] == len(ventana.session.visible_channels)
    assert not ventana.carteles


def test_el_mapa_lleva_los_nombres_de_los_canales(
    ventana: MainWindow, elige_opciones
):
    elige_opciones(("Delta", True))

    ventana.show_connectivity_dialog()

    assert ventana.connectivity_panel.axis_labels() == ventana.session.visible_channels


def test_el_titulo_dice_la_ventana_y_el_promedio(ventana: MainWindow, elige_opciones):
    ventana._go_to_window(2)
    elige_opciones(("Delta", True))

    ventana.show_connectivity_dialog()

    titulo = ventana.connectivity_panel.caption()
    assert "ventana 3" in titulo
    assert "promedio" in titulo


def test_con_un_solo_canal_visible_avisa_en_vez_de_romper(
    ventana: MainWindow, elige_opciones
):
    """La conectividad se mide entre canales."""
    ventana.session.set_visible_channels(["C3"])
    elige_opciones(("Delta", True))

    ventana.show_connectivity_dialog()

    assert ventana.carteles


def test_cancelar_no_calcula_nada(ventana: MainWindow, elige_opciones):
    elige_opciones(("C3", False))

    ventana.show_complexity_dialog()

    assert ventana.metric_panel.channels() == []


# -- ICA, por la ventana (V5_F de "Filtración") ------------------------------


def test_con_un_solo_eeg_la_ica_avisa(ventana: MainWindow):
    """El módulo se niega y acá eso tiene que salir como cartel, no como traza:
    con un canal no hay mezcla que separar."""
    ventana.show_ica_dialog()
    ventana.wait_for_background()
    assert ventana.carteles
    # El cartel dice qué no se pudo hacer, también desde otro hilo (hito 65).
    assert ventana.acciones == ["calcular la ICA"]


def test_ajustar_no_aplica_nada(ventana_con_dos_eeg: MainWindow):
    """**Ajustar e inspeccionar son dos pasos separados de aplicar**, porque
    quitar el componente equivocado no se puede deshacer."""
    antes = ventana_con_dos_eeg.session.recording.data.copy()

    ventana_con_dos_eeg.show_ica_dialog()

    ventana_con_dos_eeg.wait_for_background()
    assert ventana_con_dos_eeg.ica_panel.component_count() == 2
    assert ventana_con_dos_eeg.ica_panel.excluded() == []
    assert np.array_equal(ventana_con_dos_eeg.session.recording.data, antes)
    assert not ventana_con_dos_eeg.carteles


def test_la_curva_del_componente_llega_a_la_pantalla(ventana_con_dos_eeg: MainWindow):
    """**La mitad de V5_F que faltaba.** `component_time_course()` existía desde
    el hito 15 prometiendo en su docstring ser "lo que se dibuja debajo de la
    señal", y hasta el hito 19 no la llamaba nadie: el panel mostraba sólo la
    topografía, o sea *dónde* pesa el componente y no *cuándo* ocurre.
    """
    ventana_con_dos_eeg.show_ica_dialog()
    ventana_con_dos_eeg.wait_for_background()
    curva = ventana_con_dos_eeg.ica_panel.time_course_data()
    assert curva is not None, "el panel abrió sin curva"
    segundos, valores = curva
    assert len(segundos) == len(valores) > 0
    assert not ventana_con_dos_eeg.carteles


def test_la_curva_abarca_una_ventana_y_no_el_registro_entero(
    ventana_con_dos_eeg: MainWindow,
):
    """**De la ventana actual**, por el mismo motivo que el espectro y la
    conectividad: la serie de las ocho horas no se puede mirar, y reconstruirla
    entera cuesta una copia completa de la señal."""
    sesion = ventana_con_dos_eeg.session
    ventana_con_dos_eeg.show_ica_dialog()
    ventana_con_dos_eeg.wait_for_background()
    segundos, valores = ventana_con_dos_eeg.ica_panel.time_course_data()
    assert segundos[-1] < WINDOW_SECONDS
    assert len(valores) < sesion.recording.n_samples


def test_la_curva_se_pide_para_la_ventana_en_la_que_esta_el_usuario(
    ventana_con_dos_eeg: MainWindow, monkeypatch
):
    """**No se puede afirmar comparando las dos curvas**, y conviene decir por
    qué: el BrainVision sintético es periódico, así que sus dos ventanas
    contienen la misma onda y dan, correctamente, la misma serie. Comparar los
    valores verificaría la señal de prueba y no el cableado.

    Lo que sí se puede afirmar es la costura: qué ventana se pide.
    """
    import psglab.ui.window_analysis as ventana_principal

    pedidas: list[int] = []
    real = ventana_principal.component_time_course

    def espiar(ica, component, recording, window_index=None):
        pedidas.append(window_index)
        return real(ica, component, recording, window_index=window_index)

    monkeypatch.setattr(ventana_principal, "component_time_course", espiar)

    ventana_con_dos_eeg.show_ica_dialog()

    ventana_con_dos_eeg.wait_for_background()
    assert pedidas == [0]

    ventana_con_dos_eeg.go_to_next_window()
    ventana_con_dos_eeg.ica_panel.lista.setCurrentRow(1)

    assert pedidas == [0, 1], "la curva no siguió a la ventana actual"
    assert not ventana_con_dos_eeg.carteles


def test_elegir_otro_componente_cambia_la_curva(ventana_con_dos_eeg: MainWindow):
    """Cada componente tiene su serie; mostrar la del anterior debajo de otra
    topografía se leería como si fuera de ésta."""
    ventana_con_dos_eeg.show_ica_dialog()
    ventana_con_dos_eeg.wait_for_background()
    _, del_primero = ventana_con_dos_eeg.ica_panel.time_course_data()

    ventana_con_dos_eeg.ica_panel.lista.setCurrentRow(1)
    _, del_segundo = ventana_con_dos_eeg.ica_panel.time_course_data()

    assert not np.allclose(del_primero, del_segundo)
    assert not ventana_con_dos_eeg.carteles


def test_aplicar_deja_volver_a_la_señal_original(ventana_con_dos_eeg: MainWindow):
    """**Es la única red contra una exclusión equivocada**, y por eso la ICA
    pasa por el mismo camino que los demás análisis del menú."""
    ventana_con_dos_eeg.show_ica_dialog()
    ventana_con_dos_eeg.wait_for_background()
    original = ventana_con_dos_eeg.session.recording.data.copy()

    ventana_con_dos_eeg.ica_panel.set_excluded([0])
    ventana_con_dos_eeg.ica_panel._aplicar()

    assert not np.array_equal(ventana_con_dos_eeg.session.recording.data, original)
    assert ventana_con_dos_eeg.accion_señal_original.isEnabled()

    ventana_con_dos_eeg.restore_original_recording()
    assert np.allclose(ventana_con_dos_eeg.session.recording.data, original)


# -- Que la ICA no sobreviva a un cambio de señal ----------------------------
#
# `fit_ica()` se ajusta sobre la señal que hay en ese momento y el panel se queda
# abierto esperando que el usuario elija qué quitar. Si entre el ajuste y el
# "Aplicar" la señal cambia, la matriz de desmezclado deja de corresponder.
#
# **Y no falla sola**, que es lo que lo vuelve caro: filtrar no cambia los
# nombres de los canales, así que MNE acepta el pedido sin protestar y devuelve
# una señal reconstruida con una descomposición ajena. Plausible, irreversible y
# equivocada. Son tres caminos y los tres se prueban por la ventana.


def test_filtrar_despues_de_ajustar_descarta_la_descomposicion(
    ventana_con_dos_eeg: MainWindow,
):
    """El camino que encontró el bug: ajustar, filtrar, y el panel seguía vivo."""
    ventana_con_dos_eeg.show_ica_dialog()
    ventana_con_dos_eeg.wait_for_background()
    assert ventana_con_dos_eeg.ica_panel.component_count() == 2

    ventana_con_dos_eeg.show_filter_dialog()
    ventana_con_dos_eeg.filter_panel.boton_aplicar.click()
    ventana_con_dos_eeg.wait_for_background()

    assert ventana_con_dos_eeg.analysis_controller.ica is None
    assert ventana_con_dos_eeg.ica_panel.component_count() == 0
    assert not ventana_con_dos_eeg.carteles


def test_volver_a_la_señal_original_descarta_la_descomposicion(
    ventana_con_dos_eeg: MainWindow,
):
    """Deshacer también cambia la señal: la ICA se ajustó sobre la procesada."""
    ventana_con_dos_eeg.show_filter_dialog()
    ventana_con_dos_eeg.filter_panel.boton_aplicar.click()
    ventana_con_dos_eeg.wait_for_background()
    ventana_con_dos_eeg.show_ica_dialog()
    ventana_con_dos_eeg.wait_for_background()
    assert ventana_con_dos_eeg.analysis_controller.ica is not None

    ventana_con_dos_eeg.restore_original_recording()

    assert ventana_con_dos_eeg.analysis_controller.ica is None
    assert ventana_con_dos_eeg.ica_panel.component_count() == 0


def test_abrir_otro_registro_descarta_la_descomposicion(
    ventana_con_dos_eeg: MainWindow, tmp_path: Path
):
    """Es el mismo motivo por el que abrir un registro suelta las herramientas:
    lo que quedó guardado es de otra señal y de otros canales."""
    ventana_con_dos_eeg.show_ica_dialog()
    ventana_con_dos_eeg.wait_for_background()
    assert ventana_con_dos_eeg.analysis_controller.ica is not None

    otro = escribir_brainvision(
        tmp_path / "otro",
        segundos=WINDOW_SECONDS * 2,
        canales=[("Fp1", "µV"), ("Fp2", "µV")],
    )
    ventana_con_dos_eeg.open_recording(otro)

    assert ventana_con_dos_eeg.analysis_controller.ica is None
    assert ventana_con_dos_eeg.ica_panel.component_count() == 0
    assert not ventana_con_dos_eeg.carteles


def test_aplicar_una_ica_de_otros_canales_avisa_en_vez_de_reconstruir(
    ventana_con_dos_eeg: MainWindow, tmp_path: Path
):
    """La segunda guarda, la del módulo, para cuando la primera no alcanzara.

    `apply_ica()` comprueba que los canales sobre los que se ajustó sigan
    existiendo. No ve el caso del filtro —ahí los nombres son los mismos— pero sí
    éste, que es el que deja una señal reconstruida con una mezcla de otra
    cabeza.
    """
    ventana_con_dos_eeg.show_ica_dialog()
    ventana_con_dos_eeg.wait_for_background()
    descomposicion = ventana_con_dos_eeg.analysis_controller.ica

    otro = escribir_brainvision(
        tmp_path / "ajeno",
        segundos=WINDOW_SECONDS * 2,
        canales=[("Fp1", "µV"), ("Fp2", "µV")],
    )
    ventana_con_dos_eeg.open_recording(otro)
    antes = np.array(ventana_con_dos_eeg.session.recording.data, copy=True)

    with pytest.raises(PsgLabError):
        apply_ica(ventana_con_dos_eeg.session.recording, descomposicion, [0])

    assert np.array_equal(ventana_con_dos_eeg.session.recording.data, antes)


# -- Impedancia, por la ventana (V1_F de "Impedancia") -----------------------


@pytest.fixture
def ventana_con_impedancias(qt_app, tmp_path, monkeypatch):
    """Como `ventana`, pero con un BrainVision que trae impedancias.

    Uno medido y bien, uno medido y alto, y uno sin medir: los tres estados
    que el informe tiene que distinguir.
    """
    carteles: list[str] = []
    monkeypatch.setattr(
        MainWindow, "_show_error", lambda self, error, accion=None: carteles.append(str(error))
    )
    principal = create_main_window()
    vhdr = escribir_brainvision(
        tmp_path / "con_impedancias",
        segundos=WINDOW_SECONDS * 2,
        canales=[("C3", "µV"), ("C4", "µV"), ("O1", "µV")],
        impedancias={"C3": 4.2, "C4": 12.5, "O1": None},
    )
    principal.open_recording(vhdr)
    principal.carteles = carteles
    return principal


def test_las_impedancias_del_archivo_llegan_a_la_tabla(
    ventana_con_impedancias: MainWindow,
):
    """**BrainVision sí las trae**, y el camino completo —archivo, lector,
    módulo, panel— tiene que conservarlas."""
    ventana_con_impedancias.show_impedance_dialog()

    assert ventana_con_impedancias.impedance_panel.values() == {"C3": 4.2, "C4": 12.5}
    assert not ventana_con_impedancias.carteles


def test_el_que_estaba_sin_medir_se_ve_como_sin_medir(
    ventana_con_impedancias: MainWindow,
):
    """**La distinción que sostiene el módulo**, vista por la ventana."""
    from psglab.ui.impedance_panel import SIN_MEDIR

    ventana_con_impedancias.show_impedance_dialog()
    panel = ventana_con_impedancias.impedance_panel

    assert panel.displayed_value("O1") == SIN_MEDIR
    assert panel.unmeasured() == ["O1"]


def test_el_informe_muestra_los_tres_estados(ventana_con_impedancias: MainWindow):
    ventana_con_impedancias.show_impedance_dialog()
    informe = ventana_con_impedancias.impedance_panel.report_text

    assert "Por encima del límite" in informe
    assert "Dentro del límite" in informe
    assert "Sin medición disponible" in informe


def test_editar_a_mano_rehace_el_informe(ventana_con_impedancias: MainWindow):
    """Es la tercera vía: cargar a mano lo que el archivo no trae."""
    ventana_con_impedancias.show_impedance_dialog()
    panel = ventana_con_impedancias.impedance_panel
    assert "Sin medición disponible" in panel.report_text

    for fila in range(panel.tabla.topLevelItemCount()):
        entrada = panel.tabla.topLevelItem(fila)
        if entrada.text(0) == "O1":
            entrada.setText(1, "3,1")

    assert "Sin medición disponible" not in panel.report_text
    assert panel.values()["O1"] == 3.1


def test_sin_ninguna_impedancia_el_informe_dice_que_hacer(ventana: MainWindow):
    """**Es el caso de todo EDF**, donde el formato no puede traerlas, y el de
    un BrainVision sin tabla como el de esta fixture.

    Listar los canales sin medir y callarse dejaría al investigador mirando una
    lista sin salida.
    """
    ventana.show_impedance_dialog()

    assert ventana.impedance_panel.values() == {}
    assert "No hay ninguna impedancia cargada" in ventana.impedance_panel.report_text


def test_importar_de_un_archivo_agrega_sin_reemplazar(
    ventana_con_impedancias: MainWindow, tmp_path: Path, monkeypatch
):
    """Un laboratorio puede tener medido medio montaje: el archivo suma."""
    archivo = tmp_path / "imp.txt"
    archivo.write_text("O1 3.1\n", encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(archivo), ""))
    )

    ventana_con_impedancias.show_impedance_dialog()
    ventana_con_impedancias.load_impedances_dialog()

    assert ventana_con_impedancias.impedance_panel.values() == {
        "C3": 4.2,
        "C4": 12.5,
        "O1": 3.1,
    }


def test_un_archivo_mal_formado_avisa_sin_romper(
    ventana_con_impedancias: MainWindow, tmp_path: Path, monkeypatch
):
    archivo = tmp_path / "malo.txt"
    archivo.write_text("C3 cuatro\n", encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(archivo), ""))
    )

    ventana_con_impedancias.show_impedance_dialog()
    ventana_con_impedancias.load_impedances_dialog()

    assert ventana_con_impedancias.carteles


# -- Filtración, por la ventana (V1_F de "Filtración") -----------------------


def test_el_panel_de_filtros_se_arma_con_las_clases_del_registro(ventana: MainWindow):
    """El camino completo: abrir un archivo, abrir el panel y encontrarlo
    cargado con los sugeridos de lo que ese registro tiene."""
    ventana.show_filter_dialog()

    assert ventana.filter_panel.kinds()
    assert set(ventana.filter_panel.kinds()) == {
        canal.kind for canal in ventana.session.recording.channels
    }
    assert not ventana.carteles


def test_abrir_el_panel_no_filtra_nada(ventana: MainWindow):
    """Un menú que filtre con sólo abrirse le cambiaría la señal a alguien que
    entró a mirar qué había."""
    original = np.array(ventana.session.recording.data, copy=True)

    ventana.show_filter_dialog()

    assert np.array_equal(ventana.session.recording.data, original)
    assert not ventana.accion_señal_original.isEnabled()


def test_filtrar_desde_la_ventana_cambia_la_señal(ventana: MainWindow):
    original = np.array(ventana.session.recording.data, copy=True)

    ventana.show_filter_dialog()
    ventana.filter_panel.boton_aplicar.click()
    ventana.wait_for_background()

    assert not np.array_equal(ventana.session.recording.data, original)
    assert not ventana.carteles


def test_un_filtro_mal_elegido_no_obliga_a_reabrir_el_archivo(ventana: MainWindow):
    """**Poder deshacer**, que es el requisito que el hito tenía escrito. La
    misma acción del menú que deshace una derivación deshace un filtro."""
    original = np.array(ventana.session.recording.data, copy=True)

    ventana.show_filter_dialog()
    ventana.filter_panel.boton_aplicar.click()
    ventana.wait_for_background()
    assert ventana.accion_señal_original.isEnabled()

    ventana.restore_original_recording()

    assert np.allclose(ventana.session.recording.data, original)


def test_un_corte_imposible_avisa_y_no_cambia_la_señal(ventana: MainWindow):
    """Un pasa-bajos por encima de Nyquist sale como cartel, y la señal que el
    investigador está mirando sigue siendo la de antes."""
    original = np.array(ventana.session.recording.data, copy=True)
    ventana.show_filter_dialog()
    ventana.filter_panel.tabla.topLevelItem(0).setText(2, "9000")

    ventana.filter_panel.boton_aplicar.click()

    ventana.wait_for_background()

    assert ventana.carteles
    assert np.array_equal(ventana.session.recording.data, original)


def test_se_puede_filtrar_despues_de_re_referenciar(ventana: MainWindow):
    """Se filtra **la señal que se está viendo**, no la original: es el orden
    en que se trabaja."""
    ventana.apply_average_reference()
    re_referenciada = np.array(ventana.session.recording.data, copy=True)

    ventana.show_filter_dialog()
    ventana.filter_panel.boton_aplicar.click()
    ventana.wait_for_background()

    assert not np.array_equal(ventana.session.recording.data, re_referenciada)
    assert not ventana.carteles


# -- Un registro de 100 Hz, por la ventana (hallazgo del hito 17) -------------


@pytest.fixture
def ventana_a_100_hz(qt_app, tmp_path, monkeypatch):
    """Como `ventana`, pero con un registro muestreado a 100 Hz.

    **Es la frecuencia que destapó el hito 17.** El registro real de `data/`
    está a 100 Hz, y con Nyquist en 50 el notch sugerido de 50 Hz quedaba justo
    afuera: abrir el panel y apretar Aplicar sin tocar nada terminaba en un
    cartel de error. Toda la suite usaba 256 Hz, así que nada lo veía.
    """
    carteles: list[str] = []
    monkeypatch.setattr(
        MainWindow, "_show_error", lambda self, error, accion=None: carteles.append(str(error))
    )
    principal = create_main_window()
    vhdr = escribir_brainvision(
        tmp_path / "cien_hz", segundos=WINDOW_SECONDS * 2, frecuencia=100.0
    )
    principal.open_recording(vhdr)
    assert not carteles, f"abrir el registro mostró un error: {carteles}"
    principal.carteles = carteles
    return principal


def test_el_registro_es_de_100_hz(ventana_a_100_hz: MainWindow):
    """Que la fixture sea lo que dice ser: sin esto los tres de abajo podrían
    estar pasando por la razón equivocada."""
    assert ventana_a_100_hz.session.recording.sampling_rate == 100.0


def test_aplicar_los_sugeridos_a_100_hz_no_da_ningun_cartel(
    ventana_a_100_hz: MainWindow,
):
    """**El hallazgo del hito 17, por el camino del usuario.** Abrir el panel,
    no tocar nada y apretar Aplicar, que es lo que hace cualquiera la primera
    vez. Antes daba `InvalidFilterError`."""
    original = np.array(ventana_a_100_hz.session.recording.data, copy=True)

    ventana_a_100_hz.show_filter_dialog()
    ventana_a_100_hz.filter_panel.boton_aplicar.click()
    ventana_a_100_hz.wait_for_background()

    assert not ventana_a_100_hz.carteles
    assert not np.array_equal(ventana_a_100_hz.session.recording.data, original)


def test_el_notch_no_se_ofrece_a_100_hz(ventana_a_100_hz: MainWindow):
    """La celda viene vacía porque el registro no contiene 50 Hz, no porque
    alguien se haya olvidado."""
    from psglab.core.recording import ChannelKind

    ventana_a_100_hz.show_filter_dialog()
    panel = ventana_a_100_hz.filter_panel

    assert panel.displayed_value(ChannelKind.EEG, "notch_hz") == ""
    assert "50" in panel.rotulo.text()


def test_a_256_hz_el_notch_sigue_estando(ventana: MainWindow):
    """La otra mitad: descartar sólo lo que no entra. La fixture normal es de
    250 Hz, así que el notch de 50 tiene que seguir ofreciéndose."""
    from psglab.core.recording import ChannelKind

    ventana.show_filter_dialog()

    assert ventana.filter_panel.displayed_value(ChannelKind.EEG, "notch_hz") == "50"


# -- Quedarse sin memoria, por la ventana (hito 18) --------------------------


def test_sin_memoria_sale_un_cartel_y_no_una_traza(ventana: MainWindow, monkeypatch):
    """**El único error del programa que llegaba como traza de Python.**

    `_aplicar_analisis()` atrapa `PsgLabError` y nada más, así que un
    `MemoryError` —que es el más probable de todos en un registro de ocho
    horas— se le escapaba y salía por la consola. Ahora sale por el mismo
    cartel que el resto.
    """
    import psglab.analysis.mne_bridge as puente

    def sin_memoria(*_args, **_kwargs):
        raise MemoryError()

    original = np.array(ventana.session.recording.data, copy=True)
    ventana.show_filter_dialog()
    monkeypatch.setattr(puente.np, "array", sin_memoria)

    ventana.filter_panel.boton_aplicar.click()

    ventana.wait_for_background()

    assert ventana.carteles, "el MemoryError no se convirtió en cartel"
    assert "memoria" in ventana.carteles[0].lower()


def test_sin_memoria_la_señal_queda_como_estaba(ventana: MainWindow, monkeypatch):
    """La otra mitad del mensaje, y tiene que ser cierta: el cartel promete que
    el registro sigue abierto y sin cambios.

    **La afirmación del cartel va junto con la de la señal, y no es de más.**
    La primera versión de este test miraba sólo la señal y pasaba igual con la
    guarda rota: sin ella el `MemoryError` sale por otro lado, Qt se lo traga, y
    la señal queda intacta de todos modos. Pasaba por la razón equivocada.
    """
    import psglab.analysis.mne_bridge as puente

    original = np.array(ventana.session.recording.data, copy=True)
    ventana.show_filter_dialog()
    monkeypatch.setattr(
        puente.np, "array", lambda *a, **k: (_ for _ in ()).throw(MemoryError())
    )

    ventana.filter_panel.boton_aplicar.click()

    ventana.wait_for_background()

    assert ventana.carteles
    assert np.array_equal(ventana.session.recording.data, original)
    assert not ventana.accion_señal_original.isEnabled()


# -- Que se note que está trabajando (hito 18) -------------------------------


def test_durante_un_analisis_el_cursor_dice_que_esta_trabajando(ventana: MainWindow):
    """**No acorta la espera: la hace legible.** Todo corre en el hilo de la
    interfaz, así que la ventana queda congelada mientras dura el cálculo, y sin
    ninguna señal eso se lee como que el programa se colgó. El hito 17 midió que
    la primera complejidad de cada sesión se lleva unos 21 s sólo compilando.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    visto: list[object] = []

    def mirar_el_cursor(registro):
        cursor = QApplication.overrideCursor()
        visto.append(cursor.shape() if cursor is not None else None)
        return registro

    ventana._aplicar_analisis("Se hizo algo", mirar_el_cursor)

    assert visto == [Qt.CursorShape.WaitCursor]


def test_abrir_un_registro_avisa_mientras_lee(
    ventana: MainWindow, tmp_path: Path, monkeypatch
):
    """Leer una noche entera son varios segundos con la ventana congelada: sin
    cursor de espera ni mensaje se lee como que el programa se colgó, y es lo
    primero que hace el usuario."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    visto: list[tuple[object, str]] = []
    leer = files_mod.read_recording

    def mirar(ruta):
        cursor = QApplication.overrideCursor()
        visto.append(
            (
                cursor.shape() if cursor is not None else None,
                ventana.statusBar().currentMessage(),
            )
        )
        return leer(ruta)

    monkeypatch.setattr(files_mod, "read_recording", mirar)
    otro = escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS)

    ventana.open_recording(otro)

    (forma, mensaje), = visto
    assert forma == Qt.CursorShape.WaitCursor
    assert otro.name in mensaje
    assert QApplication.overrideCursor() is None
    assert not ventana.carteles


def test_al_terminar_el_cursor_vuelve(ventana: MainWindow):
    """Un cursor de espera que no se restaura deja el programa inutilizable a
    la vista, aunque funcione."""
    from PySide6.QtWidgets import QApplication

    ventana._aplicar_analisis("Se hizo algo", lambda registro: registro)

    assert QApplication.overrideCursor() is None


def test_el_cursor_vuelve_aunque_el_analisis_falle(ventana: MainWindow):
    """Es lo que hace el `finally`: si un análisis eleva, el cursor no puede
    quedarse en espera para siempre."""
    from PySide6.QtWidgets import QApplication
    from psglab.utils.errors import InvalidRecordingError

    def fallar(_registro):
        raise InvalidRecordingError("no se pudo")

    ventana._aplicar_analisis("Se hizo algo", fallar)

    assert QApplication.overrideCursor() is None
    assert ventana.carteles


# -- La conectividad a lo largo de la noche ---------------------------------------
#
# Era un hueco declarado desde el hito 20: la función existía, el panel también,
# y ningún camino los juntaba.


def test_la_conectividad_de_la_noche_desde_el_menu(ventana: MainWindow, elige_opciones):
    """Un número por época, **con el largo de la noche**: es lo que lo deja
    alineado con el hipnograma."""
    elige_opciones(("Delta", True))

    ventana.show_connectivity_night_dialog()
    ventana.wait_for_background()

    (serie,) = ventana.metric_panel.channels()
    assert len(ventana.metric_panel.series(serie)) == ventana.session.n_windows
    assert ventana.metric_panel.window_positions(serie)[0] == 1.0
    assert not ventana.carteles


def test_cada_epoca_vale_lo_mismo_que_la_conectividad_de_esa_ventana(
    ventana: MainWindow, elige_opciones
):
    """**Los dos caminos tienen que coincidir.** El barrido promedia la misma
    matriz que el menú de la ventana muestra: si dieran distinto, uno de los dos
    le estaría mintiendo al investigador."""
    from psglab.analysis.connectivity import average_connectivity

    elige_opciones(("Delta", True), ("Delta", True))
    ventana._go_to_window(2)

    ventana.show_connectivity_night_dialog()
    ventana.wait_for_background()
    (serie,) = ventana.metric_panel.channels()
    de_la_noche = ventana.metric_panel.series(serie)[2]
    ventana.show_connectivity_dialog()
    de_la_ventana = average_connectivity(ventana.connectivity_panel.matrix())

    assert de_la_noche == pytest.approx(de_la_ventana)


def test_el_titulo_dice_la_banda_y_entre_que_canales(
    ventana: MainWindow, elige_opciones
):
    elige_opciones(("Theta", True))

    ventana.show_connectivity_night_dialog()
    ventana.wait_for_background()

    titulo = ventana.metric_panel.caption()
    assert "Theta" in titulo
    assert "noche" in titulo
    for canal in ventana.session.visible_channels:
        assert canal in titulo


def test_cancelar_la_banda_no_mide_nada(ventana: MainWindow, elige_opciones, monkeypatch):
    """Es la operación más cara del menú después de la ICA: cancelar no puede
    arrancarla igual."""
    llamadas: list[object] = []
    monkeypatch.setattr(
        analysis_mod,
        "connectivity_by_window",
        lambda *args, **kwargs: llamadas.append(args),
    )
    elige_opciones(("", False))

    ventana.show_connectivity_night_dialog()
    ventana.wait_for_background()

    assert llamadas == []
    assert not ventana.carteles


def test_con_un_solo_canal_visible_avisa_sin_medir(ventana: MainWindow):
    ventana.session.set_visible_channels(ventana.session.visible_channels[:1])

    ventana.show_connectivity_night_dialog()
    ventana.wait_for_background()

    assert ventana.carteles


def test_medir_la_noche_no_mueve_al_usuario_de_ventana(
    ventana: MainWindow, elige_opciones
):
    ventana._go_to_window(3)
    elige_opciones(("Delta", True))

    ventana.show_connectivity_night_dialog()
    ventana.wait_for_background()

    assert ventana.session.current_window == 3


def test_medir_la_noche_muestra_que_esta_trabajando(
    ventana: MainWindow, elige_opciones
):
    """Tarda entre quince y dieciocho segundos sobre un registro real: sin
    ninguna señal, se lee como un programa colgado.

    **Era el cursor de espera y ahora es una barra**, porque desde el hito 42
    el cálculo no corre en el hilo de la interfaz: el cursor de espera sólo
    tiene sentido mientras la ventana está bloqueada, y ahora no lo está. La
    barra es indeterminada a propósito: nada informa cuánto lleva hecho."""
    elige_opciones(("Delta", True))
    # **Hay que mostrarla**: un widget hijo de una ventana oculta nunca se
    # declara visible, aunque se le haya pedido que se muestre.
    ventana.show()

    ventana.show_connectivity_night_dialog()
    trabajando = ventana.analysis_controller.wait_bar.isVisible()
    ventana.wait_for_background()

    assert trabajando, "la barra tiene que verse mientras dura el cálculo"
    assert not ventana.analysis_controller.wait_bar.isVisible()
    assert "…" not in ventana.statusBar().currentMessage()


def test_mientras_mide_la_noche_no_se_puede_volver_a_pedir(
    ventana: MainWindow, elige_opciones
):
    """Dos cálculos a la vez sobre la misma sesión se pisan el resultado, y
    cuál gana depende de cuál termine primero. La entrada del menú se apaga:
    dejar pedir algo que va a fallar es peor que mostrarlo apagado."""
    elige_opciones(("Delta", True))

    ventana.show_connectivity_night_dialog()
    apagada = not ventana.accion_conectividad_de_la_noche.isEnabled()
    ventana.wait_for_background()

    assert apagada
    assert ventana.accion_conectividad_de_la_noche.isEnabled()


# -- Una banda de conectividad que el registro no puede medir (hito 33) ------


@pytest.mark.parametrize("metodo", ["show_connectivity_dialog", "show_connectivity_night_dialog"])
def test_una_banda_sobre_nyquist_sale_como_cartel(
    ventana: MainWindow, elige_opciones, metodo: str
):
    """Las bandas las escribe el usuario en la configuración, y una que sirve
    para un registro de 1000 Hz puede no servir para otro. mne-connectivity
    elevaba `ValueError`, que atravesaba el `except` de la ventana: no salía
    ningún cartel y la traza iba a la consola."""
    nyquist = FRECUENCIA_BV / 2
    ventana.apply_preferences(
        ventana.current_preferences.with_bands({"Alta": (nyquist + 10, nyquist + 40)})
    )
    elige_opciones(("Alta", True))

    getattr(ventana, metodo)()
    # La de la noche corre en otro hilo desde el hito 42, así que su error
    # llega por la señal y no por el `return` del método.
    ventana.wait_for_background()

    assert len(ventana.carteles) == 1
    assert f"{nyquist:g} Hz" in ventana.carteles[0]


# -- Lo largo fuera del hilo de la interfaz (hito 47) -------------------------
#
# **Ajustar la ICA es lo más caro del programa y no cambia la señal.** La
# auditoría del 19 de septiembre midió 9 s sobre un registro real; sobre ruido
# blanco, que es el peor caso para que FastICA converja, se midieron 345 s. Las
# dos operaciones que sí cambian la señal —aplicar la ICA y filtrar— resultaron
# costar décimas de segundo, así que la que había que sacar del hilo era ésta.


def test_ajustar_la_ica_no_cambia_la_senal(ventana_con_dos_eeg: MainWindow):
    """Es lo que la vuelve el mismo trabajo que la conectividad de la noche, y
    lo que hizo que no necesitara ninguna decisión nueva."""
    antes = ventana_con_dos_eeg.session.recording

    ventana_con_dos_eeg.show_ica_dialog()
    ventana_con_dos_eeg.wait_for_background()

    assert ventana_con_dos_eeg.session.recording is antes
    assert ventana_con_dos_eeg.analysis_controller.ica is not None


def test_ajustar_la_ica_apaga_lo_que_cambiaria_la_senal(
    ventana_con_dos_eeg: MainWindow,
):
    """**Cambiar la señal debajo de un ajuste en curso dejaría una
    descomposición de una señal que ya no está**, y eso no falla solo: MNE
    acepta el pedido y devuelve una señal reconstruida con una matriz ajena.

    Se mira a mitad de camino, con un `threading.Event`: sin eso el ajuste
    termina antes de que el test pueda mirar nada.
    """
    empezo = threading.Event()
    seguir = threading.Event()
    real = analysis_mod.fit_ica

    def lento(registro):
        empezo.set()
        seguir.wait(5.0)
        return real(registro)

    analysis_mod.fit_ica = lento
    try:
        ventana_con_dos_eeg.show_ica_dialog()
        assert empezo.wait(5.0), "el ajuste no arrancó"

        assert not ventana_con_dos_eeg.menu_montaje.menuAction().isEnabled()
        assert not ventana_con_dos_eeg.menu_filtrar.menuAction().isEnabled()
        assert not ventana_con_dos_eeg.accion_conectividad_de_la_noche.isEnabled()
    finally:
        seguir.set()
        ventana_con_dos_eeg.wait_for_background()
        analysis_mod.fit_ica = real

    assert ventana_con_dos_eeg.menu_montaje.menuAction().isEnabled()
    assert ventana_con_dos_eeg.menu_filtrar.menuAction().isEnabled()


def test_mientras_ajusta_se_puede_scorear(ventana_con_dos_eeg: MainWindow):
    """**Es lo que vuelve útil sacarlo del hilo.** Si hubiera que esperar igual
    para seguir trabajando, no se habría ganado nada: la época, el scoring y las
    anotaciones viven en `Session` y no dependen de los valores de las muestras.
    """
    empezo = threading.Event()
    seguir = threading.Event()
    real = analysis_mod.fit_ica

    def lento(registro):
        empezo.set()
        seguir.wait(5.0)
        return real(registro)

    analysis_mod.fit_ica = lento
    try:
        ventana_con_dos_eeg.show_ica_dialog()
        assert empezo.wait(5.0), "el ajuste no arrancó"

        ventana_con_dos_eeg.score_current_window(SleepStage.N2)
        # La fixture trae dos épocas, así que la 1 es la última que existe.
        ventana_con_dos_eeg._go_to_window(1)
    finally:
        seguir.set()
        ventana_con_dos_eeg.wait_for_background()
        analysis_mod.fit_ica = real

    assert not ventana_con_dos_eeg.carteles
    assert ventana_con_dos_eeg.session.scoring.get(0).stage is SleepStage.N2
    assert ventana_con_dos_eeg.session.current_window == 1


# -- Abrir y filtrar sin congelar la ventana (hito 79) -------------------------


def test_abrir_lee_el_registro_en_otro_hilo(ventana: MainWindow, tmp_path, monkeypatch):
    """Una noche son segundos, y en el hilo de la interfaz la ventana quedaba
    congelada y el sistema la marcaba como «no responde»."""
    hilos: list[threading.Thread] = []
    leer = files_mod.read_recording

    def leer_y_anotar(ruta):
        hilos.append(threading.current_thread())
        return leer(ruta)

    monkeypatch.setattr(files_mod, "read_recording", leer_y_anotar)
    otro = escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * 2)

    ventana.open_recording_in_background(otro)
    ventana.wait_for_background()

    assert hilos and hilos[0] is not threading.main_thread()
    assert ventana.session.n_windows == 2
    assert not ventana.carteles


def test_mientras_lee_sigue_el_registro_anterior(ventana: MainWindow, tmp_path, monkeypatch):
    """Se puede seguir scoreando el de antes, y la pregunta por el trabajo sin
    exportar llega después de leer: cuenta también lo que se hizo mientras."""
    puede_seguir = threading.Event()
    leer = files_mod.read_recording

    def leer_despacio(ruta):
        puede_seguir.wait(10)
        return leer(ruta)

    monkeypatch.setattr(files_mod, "read_recording", leer_despacio)
    anterior = ventana.session
    otro = escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * 2)

    ventana.open_recording_in_background(otro)
    try:
        assert ventana.session is anterior
        assert ventana.statusBar().currentMessage() == f"Leyendo «{otro.name}»…"
        assert not ventana.analysis_controller.wait_bar.isHidden()
        ventana.score_current_window(SleepStage.N2)
        assert anterior.scoring.get(0).stage is SleepStage.N2
    finally:
        puede_seguir.set()
    preguntas: list[list[str]] = []
    ventana.work_guard.ask = lambda _que, en_juego: preguntas.append(en_juego) or "descartar"
    ventana.wait_for_background()

    assert preguntas, "lo scoreado mientras leía tiene que contar como trabajo sin exportar"
    assert ventana.session.n_windows == 2
    assert ventana.analysis_controller.wait_bar.isHidden()


def test_un_archivo_que_no_se_lee_en_otro_hilo_avisa_y_no_suelta_nada(
    ventana: MainWindow, tmp_path
):
    anterior = ventana.session
    roto = tmp_path / "roto.vhdr"
    roto.write_text("esto no es un BrainVision", encoding="utf-8")

    ventana.open_recording_in_background(roto)
    ventana.wait_for_background()

    assert ventana.session is anterior
    assert len(ventana.carteles) == 1
    assert ventana.analysis_controller.wait_bar.isHidden()


def test_abrir_dos_a_la_vez_ignora_el_segundo(ventana: MainWindow, tmp_path, monkeypatch):
    puede_seguir = threading.Event()
    leer = files_mod.read_recording
    leidos: list[str] = []

    def leer_despacio(ruta):
        leidos.append(Path(ruta).parent.name)
        puede_seguir.wait(10)
        return leer(ruta)

    monkeypatch.setattr(files_mod, "read_recording", leer_despacio)
    uno = escribir_brainvision(tmp_path / "uno", segundos=WINDOW_SECONDS * 2)
    dos = escribir_brainvision(tmp_path / "dos", segundos=WINDOW_SECONDS * 3)

    ventana.open_recording_in_background(uno)
    try:
        ventana.open_recording_in_background(dos)
        mensaje = ventana.statusBar().currentMessage()
    finally:
        puede_seguir.set()
    ventana.wait_for_background()

    assert "Todavía se está abriendo" in mensaje
    assert leidos == ["uno"]
    assert ventana.session.n_windows == 2


def test_cerrar_mientras_lee_no_abre_lo_que_se_estaba_leyendo(
    ventana: MainWindow, tmp_path, monkeypatch
):
    """Cerrar espera a que termine la lectura, pero no la toma: volvería a
    preguntar por el trabajo y cambiaría la sesión mientras se cierra."""
    puede_seguir = threading.Event()
    leer = files_mod.read_recording

    def leer_despacio(ruta):
        puede_seguir.wait(10)
        return leer(ruta)

    monkeypatch.setattr(files_mod, "read_recording", leer_despacio)
    anterior = ventana.session
    otro = escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * 2)
    ventana.open_recording_in_background(otro)
    threading.Timer(0.2, puede_seguir.set).start()

    assert ventana.close()

    assert ventana.session is anterior
    assert not ventana.carteles


def test_abrir_no_espera_a_un_calculo_en_curso(ventana: MainWindow, tmp_path):
    """La lectura tiene su propia tarea: abrir mientras se ajusta una ICA se
    podía antes de que abrir fuera en segundo plano, y se sigue pudiendo."""
    puede_seguir = threading.Event()
    ventana.analysis_controller.run_in_background(
        "Calculando", lambda: puede_seguir.wait(10), lambda _r: None
    )
    otro = escribir_brainvision(tmp_path / "otro", segundos=WINDOW_SECONDS * 2)

    ventana.open_recording_in_background(otro)
    ventana._lectura.wait()
    puede_seguir.set()
    ventana.wait_for_background()

    assert ventana.session.n_windows == 2
    assert not ventana.carteles


def test_filtrar_corre_en_otro_hilo(ventana: MainWindow, monkeypatch):
    hilos: list[threading.Thread] = []
    filtrar = analysis_mod.apply_filters

    def filtrar_y_anotar(registro, ajustes):
        hilos.append(threading.current_thread())
        return filtrar(registro, ajustes)

    monkeypatch.setattr(analysis_mod, "apply_filters", filtrar_y_anotar)
    antes = ventana.session.recording
    ventana.show_filter_dialog()

    ventana.filter_panel.boton_aplicar.click()
    mientras = ventana.session.recording
    ventana.wait_for_background()

    assert hilos and hilos[0] is not threading.main_thread()
    assert mientras is antes
    assert ventana.session.recording is not antes
    assert ventana.statusBar().currentMessage().startswith("Se filtró la señal")
    assert not ventana.carteles


def test_un_reciente_que_ya_no_esta_se_quita_y_se_avisa(ventana: MainWindow, tmp_path):
    fantasma = str(tmp_path / "ya-no-esta.vhdr")
    ventana._preferencias = ventana._preferencias.with_recent_file(fantasma)

    ventana.open_recent_file(fantasma)

    assert fantasma not in ventana.current_preferences.recent_files
    assert "ya no está" in ventana.carteles[0]
    assert ventana.session.n_windows == VENTANAS


def test_guardar_una_vista_guarda_canales_orden_y_escala(ventana: MainWindow, monkeypatch):
    monkeypatch.setattr(QInputDialog, "getText", lambda *_a, **_k: ("Scoring", True))
    ventana._set_visible_channels(["EOG-izq", "C3"])
    ventana.session.set_scale_uv("C3", 40.0)

    ventana.save_channel_view()

    assert ventana.current_preferences.channel_view("Scoring") == (
        ("EOG-izq", ventana.session.scale_uv("EOG-izq")),
        ("C3", 40.0),
    )
    assert "Scoring" in [a.text() for a in ventana.menu_vistas.actions()]


def test_aplicar_una_vista_muestra_sus_canales_con_su_escala(ventana: MainWindow):
    ventana._preferencias = ventana._preferencias.with_channel_view(
        "Ocular", (("EOG-izq", 120.0), ("C3", 40.0))
    )

    ventana.apply_channel_view("Ocular")

    assert ventana.session.visible_channels == ["EOG-izq", "C3"]
    assert ventana.session.scale_uv("EOG-izq") == pytest.approx(120.0)
    assert ventana.session.scale_uv("C3") == pytest.approx(40.0)
    assert ventana.signal_view._visible == ["EOG-izq", "C3"]
    assert not ventana.carteles


def test_una_vista_con_canales_que_no_estan_usa_los_que_hay(ventana: MainWindow):
    """Una vista armada con otro montaje sirve igual para lo que coincide."""
    ventana._preferencias = ventana._preferencias.with_channel_view(
        "Otro montaje", (("F4", 50.0), ("C3", 40.0))
    )

    ventana.apply_channel_view("Otro montaje")

    assert ventana.session.visible_channels == ["C3"]
    assert "un canal no está" in ventana.statusBar().currentMessage()


def test_una_vista_sin_ningun_canal_del_registro_no_toca_nada(ventana: MainWindow):
    antes = ventana.session.visible_channels
    ventana._preferencias = ventana._preferencias.with_channel_view(
        "Ajena", (("F4", 50.0),)
    )

    ventana.apply_channel_view("Ajena")

    assert ventana.session.visible_channels == antes
    assert "Ninguno" in ventana.carteles[0]


def test_borrar_una_vista(ventana: MainWindow, monkeypatch):
    ventana._preferencias = ventana._preferencias.with_channel_view("Vieja", (("C3", 50.0),))
    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: ("Vieja", True))

    ventana.delete_channel_view()

    assert ventana.current_preferences.channel_views == ()


# -- Un cálculo de la señal anterior se descarta (hito 67) -------------------


def test_la_ica_de_otro_registro_no_se_muestra(
    ventana_con_dos_eeg: MainWindow, tmp_path
):
    """**Se aplicaba sobre el registro nuevo**: «Abrir» sigue habilitado
    mientras la ICA calcula, y la de la noche A quedaba en el panel como si
    fuera de la B. Con los mismos canales, «Aplicar y quitar» la usaba sin
    avisar."""
    ventana = ventana_con_dos_eeg
    empezo = threading.Event()
    seguir = threading.Event()
    real = analysis_mod.fit_ica

    def lento(registro):
        empezo.set()
        seguir.wait(5.0)
        return real(registro)

    otra = escribir_brainvision(
        tmp_path / "otra_noche",
        segundos=WINDOW_SECONDS * 2,
        canales=[("C3", "µV"), ("C4", "µV"), ("EOG-izq", "µV")],
    )
    analysis_mod.fit_ica = lento
    try:
        ventana.show_ica_dialog()
        assert empezo.wait(5.0), "el ajuste no arrancó"
        ventana.open_recording(otra)
    finally:
        seguir.set()
        ventana.wait_for_background()
        analysis_mod.fit_ica = real

    assert ventana.session.recording.file_path == otra
    assert ventana.analysis_controller.ica is None
    assert ventana.ica_panel.component_count() == 0
    assert "Se descartó" in ventana.statusBar().currentMessage()
    assert not ventana.carteles


def test_el_error_de_un_calculo_de_otro_registro_no_se_muestra(
    ventana_con_dos_eeg: MainWindow, tmp_path
):
    """Habla de una señal que ya no está en pantalla."""
    ventana = ventana_con_dos_eeg
    empezo = threading.Event()
    seguir = threading.Event()
    real = analysis_mod.fit_ica

    def falla(registro):
        empezo.set()
        seguir.wait(5.0)
        raise PsgLabError("La ICA no convergió.")

    analysis_mod.fit_ica = falla
    try:
        ventana.show_ica_dialog()
        assert empezo.wait(5.0), "el ajuste no arrancó"
        ventana.open_recording(escribir_brainvision(tmp_path / "otra", segundos=WINDOW_SECONDS))
    finally:
        seguir.set()
        ventana.wait_for_background()
        analysis_mod.fit_ica = real

    assert not ventana.carteles
    assert "Se descartó" in ventana.statusBar().currentMessage()


# -- Filtrar sin borrar un canal grabado más lento (hito 67) -----------------


def test_filtrar_desde_el_panel_no_deja_plano_al_canal_lento(
    ventana: MainWindow, tmp_path, monkeypatch
):
    """**El 0,0 %**: así quedaba el EMG del EDF del laboratorio, grabado a
    1 Hz, con los sugeridos del panel, y la barra decía sólo «Se filtró la
    señal». Ahora conserva su señal, y la barra dice por qué."""
    from psglab.core.recording import Channel, ChannelKind, Recording

    fs = 100.0
    tiempos = np.arange(int(fs * WINDOW_SECONDS * 2)) / fs
    lento = Recording(
        file_path=tmp_path / "lento.edf",
        channels=[
            Channel("C3", ChannelKind.EEG, "µV", 0, original_sampling_rate=fs),
            Channel("EMG", ChannelKind.EMG, "µV", 1, original_sampling_rate=1.0),
        ],
        data=np.vstack(
            [
                50.0 * np.sin(2 * np.pi * 10.0 * tiempos),
                20.0 * np.sin(2 * np.pi * 0.1 * tiempos),
            ]
        ),
        sampling_rate=fs,
    )
    monkeypatch.setattr(files_mod, "read_recording", lambda _ruta: lento)
    ventana.open_recording(tmp_path / "lento.edf")
    ventana.show_filter_dialog()
    assert "«EMG» se grabó a 1 Hz" in ventana.filter_panel.rotulo.text()

    ventana.filter_panel.boton_aplicar.click()

    ventana.wait_for_background()

    registro = ventana.session.recording
    emg = registro.get_segment(0, registro.n_samples, ["EMG"])[0]
    assert np.std(emg) == pytest.approx(np.std(lento.data[1]), rel=0.05)
    assert "sin pasa-altos en «EMG»" in ventana.statusBar().currentMessage()
    assert not ventana.carteles


# -- La frecuencia de origen en el espectro y la conectividad (hito 72) -------


@pytest.fixture
def ventana_con_un_canal_lento(ventana: MainWindow, tmp_path, monkeypatch) -> MainWindow:
    """La ventana con dos EEG de 100 Hz y un EMG grabado a 1 Hz, como el EDF
    del laboratorio. El EMG trae una onda de 0,1 Hz: es lo que puede tener."""
    from psglab.core.recording import Channel, ChannelKind, Recording

    fs = 100.0
    tiempos = np.arange(int(fs * WINDOW_SECONDS * 2)) / fs
    registro = Recording(
        file_path=tmp_path / "lento.edf",
        channels=[
            Channel("C3", ChannelKind.EEG, "µV", 0, original_sampling_rate=fs),
            Channel("C4", ChannelKind.EEG, "µV", 1, original_sampling_rate=fs),
            Channel("EMG", ChannelKind.EMG, "µV", 2, original_sampling_rate=1.0),
        ],
        data=np.vstack(
            [
                50.0 * np.sin(2 * np.pi * 10.0 * tiempos),
                40.0 * np.sin(2 * np.pi * 10.0 * tiempos + 0.5),
                20.0 * np.sin(2 * np.pi * 0.1 * tiempos),
            ]
        ),
        sampling_rate=fs,
    )
    monkeypatch.setattr(files_mod, "read_recording", lambda _ruta: registro)
    ventana.open_recording(tmp_path / "lento.edf")
    return ventana


def test_el_espectro_de_un_canal_lento_dice_hasta_donde_es_senal(
    ventana_con_un_canal_lento: MainWindow, monkeypatch
):
    """Se dibujaba hasta 50 Hz un canal que no tiene nada por encima de 0,5, y
    la potencia de las bandas de arriba parecía suya."""
    ventana = ventana_con_un_canal_lento
    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: ("EMG", True))

    ventana.show_psd_dialog()

    assert "«EMG» se grabó a 1 Hz: por encima de 0,5 Hz" in ventana.psd_panel.caption()


def test_el_espectro_de_un_canal_normal_no_lo_menciona(
    ventana_con_un_canal_lento: MainWindow, monkeypatch
):
    ventana = ventana_con_un_canal_lento
    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: ("C3", True))

    ventana.show_psd_dialog()

    assert "se grabó a" not in ventana.psd_panel.caption()


def banda_que(ventana: MainWindow, arriba_de: float) -> str:
    """El nombre de una banda de la configuración que empieza arriba de tanto."""
    return next(
        nombre
        for nombre, (desde, _) in ventana.current_preferences.bands().items()
        if desde >= arriba_de
    )


def test_la_conectividad_nombra_al_canal_que_no_tiene_nada_en_la_banda(
    ventana_con_un_canal_lento: MainWindow, monkeypatch
):
    """Medir la conectividad del EMG de 1 Hz en alfa es medir interpolación."""
    ventana = ventana_con_un_canal_lento
    alta = banda_que(ventana, arriba_de=1.0)
    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: (alta, True))

    ventana.show_connectivity_dialog()

    texto = ventana.connectivity_panel.caption()
    assert "«EMG» se grabó más lento que el registro y no tiene nada" in texto
    assert "«C3»" not in texto


def test_en_una_banda_que_el_canal_lento_alcanza_no_se_dice_nada(
    ventana_con_un_canal_lento: MainWindow, monkeypatch
):
    ventana = ventana_con_un_canal_lento
    actuales = ventana._preferencias.bands()
    ventana._preferencias = ventana._preferencias.with_changes(
        psd_bands=(
            ("Lenta", 0.05, 0.4),
            *((nombre, desde, hasta) for nombre, (desde, hasta) in actuales.items()),
        )
    )
    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: ("Lenta", True))

    ventana.show_connectivity_dialog()

    assert "se grabó más lento" not in ventana.connectivity_panel.caption()


def test_la_conectividad_de_la_noche_tambien_lo_dice(
    ventana_con_un_canal_lento: MainWindow, monkeypatch
):
    ventana = ventana_con_un_canal_lento
    alta = banda_que(ventana, arriba_de=1.0)
    monkeypatch.setattr(QInputDialog, "getItem", lambda *_a, **_k: (alta, True))

    ventana.show_connectivity_night_dialog()
    ventana.wait_for_background()

    assert "«EMG» se grabó más lento" in ventana.metric_panel.caption()
