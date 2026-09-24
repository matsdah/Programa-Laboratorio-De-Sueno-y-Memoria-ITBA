"""Tests de los esquemas de color.

**No se testea ningún color en particular.** Que el fondo oscuro sea `#3c3c3c` y
no `#3a3a3a` es una elección estética y cambiarla no debería hacer fallar nada.
Lo que sí se testea son las tres promesas de las que cuelga el resto:

- un esquema es **inmutable**, así que repartirlo entre seis widgets es seguro;
- la asignación de color por canal **cicla** y nunca se queda sin color;
- lo que se guarda en un archivo **vuelve igual**, incluso si el archivo lo
  escribió una versión del programa que tenía otros campos.

No hace falta `qt_app`: el módulo se importa y se usa sin ninguna ventana.
"""

import dataclasses

import pytest

pytest.importorskip("pyqtgraph")

import psglab.ui.theme as theme  # noqa: E402
from psglab.utils.errors import PsgLabError, UnknownColorSchemeError  # noqa: E402


@pytest.fixture(autouse=True)
def esquema_restaurado():
    """Devuelve el esquema global a como estaba.

    `set_current()` escribe en la configuración global de pyqtgraph, que es
    estado de proceso: sin esto, un test que cambia de esquema le cambia el
    fondo a todos los que corran después.
    """
    anterior = theme.current()
    yield
    theme.set_current(anterior)


# -- Los esquemas de fábrica -------------------------------------------------


def test_son_dos_esquemas_y_nada_mas():
    """**Eran ocho y cada color se podía editar** hasta el hito 35, así que el
    programa tenía infinitos aspectos posibles y ninguno garantizado: el
    control de contraste sólo alcanzaba a los de fábrica. Dos verificados y
    ninguna perilla es menos programa y más garantía."""
    assert list(theme.SCHEMES) == ["Sereno", "Nocturno"]


def test_un_esquema_no_se_puede_guardar_ni_leer_de_un_archivo():
    """La contracara de lo anterior: sin esquemas propios no hay nada que
    serializar, y el archivo de preferencias guarda el **nombre**."""
    assert not hasattr(theme, "scheme_to_dict")
    assert not hasattr(theme, "scheme_from_dict")


def test_cada_esquema_se_llama_como_su_clave():
    """La clave del diccionario y el nombre que ve el usuario son lo mismo.

    El menú se arma recorriendo las claves y el archivo de preferencias guarda
    el nombre: si divergieran, elegir un esquema guardaría otro.
    """
    assert all(clave == esquema.name for clave, esquema in theme.SCHEMES.items())


def test_el_de_fabrica_existe():
    assert theme.DEFAULT_SCHEME_NAME in theme.SCHEMES


def test_el_de_fabrica_es_sereno():
    """Era «Claro» hasta el rediseño de la pantalla principal.

    Sigue siendo el claro y no el oscuro por el mismo motivo de entonces: quien
    abre el programa de noche elige Nocturno, y quien no, no tiene por qué
    encontrarse la pantalla apagada. A quien ya lo venía usando no le cambia
    nada, porque su archivo de preferencias trae el esquema que eligió.
    """
    assert theme.scheme_by_name(theme.DEFAULT_SCHEME_NAME) is theme.SERENO


#: Los campos en los que `None` quiere decir algo: sin línea de base, la ventana
#: del mismo color que el fondo, las lecturas con la tipografía de siempre.
CAMPOS_OPCIONALES = {"baseline", "chrome", "numeric_font", "danger", "stage_colors"}


def test_ningun_esquema_deja_campos_sin_definir():
    """Un campo en `None` que no sea uno de los opcionales dejaría algo sin dibujar."""
    sin_definir = [
        (esquema.name, campo.name)
        for esquema in theme.SCHEMES.values()
        for campo in dataclasses.fields(theme.ColorScheme)
        if getattr(esquema, campo.name) is None and campo.name not in CAMPOS_OPCIONALES
    ]

    assert sin_definir == []


def test_un_esquema_no_se_puede_modificar():
    """Se reparte entre seis widgets: si alguno pudiera escribirle encima, el
    resto quedaría dibujando con un esquema que ya no es el elegido."""
    with pytest.raises(dataclasses.FrozenInstanceError):
        theme.SERENO.background = "#000000"  # type: ignore[misc]


# -- El color de cada canal --------------------------------------------------


def test_los_canales_toman_colores_distintos():
    colores = [theme.NOCTURNO.color_for_channel(i) for i in range(4)]

    assert len(set(colores)) == 4


def test_la_paleta_cicla_en_vez_de_quedarse_sin_color():
    """Con más canales que colores dos van a repetir, y repetir es mejor que
    quedarse sin color: es lo mismo que hace `AnnotationSet.color_of()`."""
    largo = len(theme.NOCTURNO.signal_palette)

    assert theme.NOCTURNO.color_for_channel(largo) == theme.NOCTURNO.color_for_channel(0)


def test_sin_variar_colores_todos_los_canales_son_iguales():
    """Los dos esquemas varían el color por canal; el campo existe igual, para
    quien quiera todas las curvas del mismo color."""
    esquema = dataclasses.replace(theme.SERENO, vary_signal_colors=False)

    assert esquema.color_for_channel(0) == esquema.signals
    assert esquema.color_for_channel(3) == esquema.signals


def test_una_paleta_vacia_no_deja_al_canal_sin_color():
    esquema = dataclasses.replace(theme.NOCTURNO, signal_palette=())

    assert esquema.color_for_channel(0) == esquema.signals


# -- Elegir un esquema -------------------------------------------------------


def test_elegir_un_esquema_lo_deja_como_el_actual():
    theme.set_current(theme.NOCTURNO)

    assert theme.current() is theme.NOCTURNO


def test_elegir_algo_que_no_es_un_esquema_avisa():
    with pytest.raises(UnknownColorSchemeError):
        theme.set_current("Oscuro")  # type: ignore[arg-type]


def test_un_esquema_inexistente_avisa_y_dice_cuales_hay():
    """El nombre suele venir de un archivo de preferencias escrito por otra
    versión del programa, así que el mensaje tiene que ayudar a corregirlo."""
    with pytest.raises(UnknownColorSchemeError) as fallo:
        theme.scheme_by_name("Fluorescente")

    assert "Fluorescente" in str(fallo.value)
    assert "Sereno" in (fallo.value.details or "")


def test_pedir_un_esquema_con_algo_que_no_es_texto_avisa():
    with pytest.raises(UnknownColorSchemeError):
        theme.scheme_by_name(3)  # type: ignore[arg-type]


def test_los_errores_del_modulo_son_del_programa():
    """La ventana principal atrapa una sola clase; lo que no herede de ella le
    llega al investigador como traza de Python."""
    assert issubclass(UnknownColorSchemeError, PsgLabError)


# -- El color de cada fase (rediseño de la pantalla principal) ---------------
#
# Es lo que el programa no tenía: el hipnograma se dibujaba en una sola tinta,
# así que una fase no se reconocía sin leer el eje. La escala vive en el
# esquema porque tiene que ser la misma en el hipnograma, en la franja de
# posición y en el botón.


@pytest.mark.parametrize("esquema", [theme.SERENO, theme.NOCTURNO], ids=lambda e: e.name)
def test_los_esquemas_del_rediseno_traen_escala_de_fases(esquema: theme.ColorScheme):
    for fase in ("W", "REM", "R", "S1", "S2", "S3", "S4", "N1", "N2", "N3", "MT"):
        assert esquema.color_for_stage(fase) is not None


def test_un_esquema_sin_escala_no_distingue_las_fases():
    """El campo admite el vacío a propósito: un esquema puede querer no
    distinguirlas —imprimir en blanco y negro, por ejemplo— y entonces las tres
    cosas que la usan se dibujan con una sola tinta, como antes del hito 34."""
    esquema = dataclasses.replace(theme.SERENO, stage_colors=())

    assert esquema.color_for_stage("N2") is None


def test_una_fase_que_el_esquema_no_conoce_no_tiene_color():
    """`UNSCORED` es la que importa: no es una fila del histograma sino la
    ausencia de una, y tiene que quedar en blanco (V1_P)."""
    assert theme.SERENO.color_for_stage("-") is None


def test_las_dos_nomenclaturas_comparten_la_escala():
    """S2 y N2 son el mismo sueño con otro nombre: cambiar de nomenclatura no
    puede cambiar de colores."""
    for equivalentes in (("S1", "N1"), ("S2", "N2"), ("S4", "N3"), ("REM", "R")):
        rk, aasm = equivalentes
        assert theme.SERENO.color_for_stage(rk) == theme.SERENO.color_for_stage(aasm)


def test_la_profundidad_es_la_luminosidad():
    """La regla del diseño, afirmada: de S1 a S4 el azul se va oscureciendo
    sobre fondo claro, que es lo que hace que la fase se lea sin leyenda."""
    contrastes = [
        theme.contrast_ratio(theme.SERENO.color_for_stage(fase), theme.SERENO.background)
        for fase in ("S1", "S2", "S3", "S4")
    ]

    assert contrastes == sorted(contrastes)


def test_una_fase_que_no_se_distingue_del_fondo_se_informa():
    """Entra en el mismo control que los canales: es algo que se dibuja."""
    esquema = dataclasses.replace(theme.SERENO, stage_colors=(("N2", "#fbfaf6"),))

    problemas = dict(theme.low_contrast_elements(esquema))

    assert "el color de la fase N2" in problemas


# -- La hoja de estilo de los widgets de Qt ----------------------------------


@pytest.fixture(params=[theme.SERENO, theme.NOCTURNO], ids=lambda e: e.name)
def esquema_con_fases(request: pytest.FixtureRequest) -> theme.ColorScheme:
    """Los dos que traen escala de fases, para no escribir dos veces el test."""
    return request.param


@pytest.mark.parametrize("esquema", list(theme.SCHEMES.values()), ids=lambda e: e.name)
def test_los_dos_esquemas_pintan_los_widgets(esquema: theme.ColorScheme):
    """Sin esto, el árbol de canales y el panel de scoring quedan con el gris
    de fábrica de Qt sobre el fondo del esquema, y la ventana a dos colores.

    **Hasta el hito 35 había un esquema que no ponía hoja de estilo**, «Claro»,
    y dejaba el aspecto nativo del sistema. Se fue con los otros cinco: ahora
    los dos que hay se pintan enteros.
    """
    hoja = theme.stylesheet(esquema)

    assert esquema.background in hoja
    assert esquema.foreground in hoja
    for widget in ("QMenuBar", "QTreeWidget", "QPushButton", "QHeaderView"):
        assert widget in hoja


def test_la_ventana_se_pinta_con_su_propio_fondo():
    """El lienzo de la señal y la ventana alrededor son dos colores distintos:
    es lo que despega la señal del resto."""
    hoja = theme.stylesheet(theme.SERENO)

    assert f"QWidget {{ background-color: {theme.SERENO.chrome};" in hoja
    assert theme.SERENO.background in hoja


def test_sin_fondo_de_ventana_propio_la_hoja_es_la_misma():
    """`chrome` vacío es «el mismo que el fondo», y la hoja sale igual que si
    se lo hubiera escrito."""
    sin_chrome = dataclasses.replace(theme.NOCTURNO, chrome=None)
    con_chrome = dataclasses.replace(
        theme.NOCTURNO, chrome=theme.NOCTURNO.background
    )

    assert theme.stylesheet(sin_chrome) == theme.stylesheet(con_chrome)


def test_las_lecturas_toman_la_tipografia_del_esquema():
    hoja = theme.stylesheet(theme.SERENO)

    assert f'QLabel[{theme.READOUT_PROPERTY}="true"]' in hoja
    assert theme.SERENO.numeric_font in hoja


def test_la_hoja_lleva_una_regla_por_fase(esquema_con_fases: theme.ColorScheme):
    """El botón de fase lleva la propiedad `fase` y el color sale de acá: así
    no hay un color de fase escrito en el panel de scoring."""
    hoja = theme.stylesheet(esquema_con_fases)

    for fase, color in esquema_con_fases.stage_colors:
        assert f'QPushButton[fase="{fase}"]' in hoja
        assert color in hoja


def test_el_relleno_de_la_fase_es_solo_de_la_marcada():
    """Las cinco pintadas a la vez no dicen cuál es la de esta época."""
    hoja = theme.stylesheet(theme.SERENO)
    color = theme.SERENO.color_for_stage("N2")

    marcada = f'QPushButton[fase="N2"]:checked {{ background-color: {color};'
    assert marcada in hoja
    assert f'QPushButton[fase="N2"] {{ background-color:' not in hoja


@pytest.mark.parametrize(
    ("esquema", "tinta"),
    [(theme.SERENO, "#ffffff"), (theme.NOCTURNO, theme.NOCTURNO.background)],
    ids=["Sereno", "Nocturno"],
)
def test_la_tinta_de_la_fase_marcada_se_elige_midiendo(
    esquema: theme.ColorScheme, tinta: str
):
    """El blanco que se lee sobre el azul profundo desaparece sobre el ámbar
    del esquema oscuro, así que no se elige por esquema sino por contraste."""
    hoja = theme.stylesheet(esquema)
    color = esquema.color_for_stage("W")

    assert f"background-color: {color}; color: {tinta};" in hoja


def test_un_esquema_sin_fases_no_genera_ninguna_regla():
    sin_escala = dataclasses.replace(theme.NOCTURNO, stage_colors=())

    assert "fase=" not in theme.stylesheet(sin_escala)


def test_la_hoja_pinta_los_paneles_y_sus_solapas():
    """Los seis de análisis se apilan en solapas: sin regla propia, la pila y
    el título del panel quedaban con el gris de fábrica de Qt sobre el fondo
    del esquema."""
    hoja = theme.stylesheet(theme.NOCTURNO)

    assert "QDockWidget::title" in hoja
    assert "QTabBar::tab" in hoja
    assert f"border-radius: {theme.RADIO_DE_CONTROL}px" in hoja


def test_el_foco_del_teclado_se_ve():
    """Un cambio de fondo no alcanza: con el esquema aplicado, el control
    enfocado se distinguía sólo por un gris que casi no cambiaba."""
    hoja = theme.stylesheet(theme.SERENO)

    assert f"border: {theme.ANILLO_DE_FOCO}px solid {theme.SERENO.accent}" in hoja


def test_sin_tipografia_numerica_no_hay_regla_para_las_lecturas():
    sin_mono = dataclasses.replace(theme.NOCTURNO, numeric_font=None)

    assert theme.READOUT_PROPERTY not in theme.stylesheet(sin_mono)


def test_un_fondo_de_ventana_poco_legible_se_detecta():
    esquema = dataclasses.replace(theme.SERENO, chrome="#2a2a2a")

    assert "el texto de la ventana" in [que for que, _ in theme.low_contrast_elements(esquema)]


def test_armar_la_hoja_de_algo_que_no_es_un_esquema_avisa():
    with pytest.raises(UnknownColorSchemeError):
        theme.stylesheet("Oscuro")  # type: ignore[arg-type]


# -- Qué cuenta como color ----------------------------------------------------------


@pytest.mark.parametrize("color", ["#112233", "#abc", "#11223344", "red", "w"])
def test_un_color_que_pyqtgraph_sabe_dibujar_es_valido(color: str):
    assert theme.is_valid_color(color)


@pytest.mark.parametrize("color", ["gris oscuro", "", "   ", None, 3, "#12"])
def test_lo_que_no_se_puede_dibujar_no_es_un_color(color: object):
    assert not theme.is_valid_color(color)


# -- Contraste --------------------------------------------------------------------------


@pytest.mark.parametrize("nombre", list(theme.SCHEMES))
def test_ningun_esquema_de_fabrica_tiene_algo_que_no_se_distinga(nombre: str):
    """**WCAG 2.1**: 4,5 a 1 para el texto y 3 a 1 para lo que hay que
    distinguir. Dos esquemas no llegaban: el azul del oscuro daba 2,42 y el
    dorado de «Azul sobre gris» daba 2,41."""
    assert theme.low_contrast_elements(theme.SCHEMES[nombre]) == []


def test_el_contraste_va_de_uno_a_veintiuno():
    assert theme.contrast_ratio("#000000", "#ffffff") == pytest.approx(21.0)
    assert theme.contrast_ratio("#777777", "#777777") == pytest.approx(1.0)


def test_el_contraste_no_depende_del_orden():
    assert theme.contrast_ratio("#123456", "#fedcba") == pytest.approx(
        theme.contrast_ratio("#fedcba", "#123456")
    )


def test_medir_el_contraste_de_algo_que_no_es_un_color_avisa():
    with pytest.raises(UnknownColorSchemeError):
        theme.contrast_ratio("gris", "#ffffff")


def test_un_color_de_canal_que_no_se_distingue_se_detecta():
    esquema = dataclasses.replace(
        theme.NOCTURNO, signal_palette=("#ffff00", "#404040")
    )

    bajos = theme.low_contrast_elements(esquema)

    assert [que for que, _ in bajos] == ["el color 2 de los canales"]
    assert bajos[0][1] < theme.MIN_GRAPHIC_CONTRAST


def test_un_texto_poco_legible_se_detecta_con_el_umbral_del_texto():
    """3,5 a 1 alcanza para una curva y no para un texto."""
    esquema = dataclasses.replace(theme.SERENO, foreground="#8a8a8a")

    assert theme.contrast_ratio("#8a8a8a", theme.SERENO.background) > 3.0
    assert "el texto de los gráficos" in [que for que, _ in theme.low_contrast_elements(esquema)]


# -- El color de los iconos ------------------------------------------------------


@pytest.mark.parametrize("nombre", list(theme.SCHEMES))
def test_los_iconos_toman_el_texto_del_esquema(nombre: str):
    esquema = theme.SCHEMES[nombre]

    assert theme.icon_ink(esquema) == esquema.foreground


def test_el_color_de_los_iconos_pide_un_esquema():
    with pytest.raises(UnknownColorSchemeError):
        theme.icon_ink("Oscuro")  # type: ignore[arg-type]


# -- La tinta de lo que destruye (hito 39) -----------------------------------


@pytest.mark.parametrize("esquema", list(theme.SCHEMES.values()), ids=lambda e: e.name)
def test_los_dos_esquemas_traen_la_tinta_de_lo_que_destruye(esquema):
    """La usa «Descartar», que es el único control del programa que pierde
    trabajo del investigador."""
    assert esquema.danger is not None
    assert f'QPushButton[{theme.DESTRUCTIVO_PROPERTY}="true"]' in theme.stylesheet(esquema)


def test_un_esquema_sin_esa_tinta_no_pone_la_regla():
    """Un esquema puede no traerla, y entonces el botón se ve como cualquier
    otro: el cartel que lo rodea sigue diciendo qué se pierde."""
    sin_tinta = dataclasses.replace(theme.SERENO, danger=None)

    assert theme.DESTRUCTIVO_PROPERTY not in theme.stylesheet(sin_tinta)


def test_la_tinta_de_lo_que_destruye_entra_en_el_control_de_contraste():
    """Es el rótulo de un botón, así que le toca el mínimo de texto y no el de
    gráfico. Sin la medida, un rojo apagado pasaba sin que nada lo notara."""
    apagado = dataclasses.replace(theme.SERENO, danger="#e8d7d0")

    problemas = dict(theme.low_contrast_elements(apagado))

    assert "la tinta de lo que destruye" in problemas


# -- La fila seleccionada (hito 41) ------------------------------------------


@pytest.mark.parametrize("esquema", list(theme.SCHEMES.values()), ids=lambda e: e.name)
def test_el_texto_de_una_fila_seleccionada_se_lee(esquema):
    """**Lo mostró una captura del panel de ICA.** La hoja pintaba el fondo de
    la fila elegida y no su tinta, así que Qt usaba la suya —blanco— sobre el
    realce del esquema: en Sereno eso da 1,24 a 1 y el nombre desaparecía."""
    assert theme.contrast_ratio(esquema.foreground, esquema.overview_current) >= (
        theme.MIN_TEXT_CONTRAST
    )


def test_la_hoja_le_pone_tinta_a_la_fila_seleccionada():
    """Pintar sólo el fondo deja la tinta en manos de Qt."""
    hoja = theme.stylesheet(theme.SERENO)
    regla = hoja.split("QListWidget::item:selected")[1].split("}")[0]

    assert "color:" in regla


def test_ink_over_se_lee_sobre_un_relleno_palido():
    """**Hasta el hito 53 este test afirmaba lo contrario**: elegía entre el
    blanco y el fondo del esquema, y sobre el realce de Sereno devolvía blanco,
    a 1,24 a 1. Con la tinta del esquema como tercera candidata, se lee."""
    elegida = theme.ink_over(theme.SERENO, theme.SERENO.overview_current)

    assert theme.contrast_ratio(elegida, theme.SERENO.overview_current) >= (
        theme.MIN_TEXT_CONTRAST
    )


@pytest.mark.parametrize("esquema", list(theme.SCHEMES.values()), ids=list(theme.SCHEMES))
def test_ink_over_se_lee_sobre_los_colores_de_clase(esquema):
    """Es la tinta del rótulo de una banda de anotación y de los chips de evento
    de la Übersicht. Con dos candidatas, en Sereno el amarillo daba 1,75 a 1.

    **El piso es el de un gráfico y no el de un texto**: el peor color de la
    paleta da 4,23 en Sereno y 4,44 en Nocturno, apenas debajo de los 4,5 que
    pide un texto chico. Subirlo es cambiar la paleta de clases, que es otra
    decisión."""
    from psglab.core.annotations import PALETTE

    for color in PALETTE:
        tinta = theme.ink_over(esquema, color)
        assert theme.contrast_ratio(tinta, color) >= theme.MIN_GRAPHIC_CONTRAST


# -- La casilla sin marcar (hito 53) ---------------------------------------


@pytest.mark.parametrize("esquema", list(theme.SCHEMES.values()), ids=list(theme.SCHEMES))
def test_la_casilla_sin_marcar_tiene_borde(esquema):
    """**En Sereno no se veía**: con el estilo nativo de Windows, un elemento
    sin marcar de una lista no dibujaba ninguna casilla, así que un canal
    oculto del selector no tenía nada que tildar. Lo encontró la captura."""
    hoja = theme.stylesheet(esquema)
    regla = hoja.split("QCheckBox::indicator:unchecked")[1].split("}")[0]

    assert "QListWidget::indicator:unchecked" in hoja
    assert "QTreeWidget::indicator:unchecked" in hoja
    assert esquema.overview_text in regla


def test_la_casilla_marcada_se_deja_al_estilo_nativo():
    """Una regla para el estado marcado obligaría a traer una imagen propia de
    la tilde: sin ella, Qt dibuja la casilla vacía."""
    assert "indicator:checked" not in theme.stylesheet(theme.SERENO)


# -- El botón principal (hito 55) ------------------------------------------


@pytest.mark.parametrize("esquema", list(theme.SCHEMES.values()), ids=list(theme.SCHEMES))
def test_el_boton_principal_va_relleno_del_acento(esquema):
    """«Aplicar», «Exportar…»: lo que el panel existe para hacer. El prototipo
    los rellenaba del acento, y el hito 44 había sacado la regla."""
    hoja = theme.stylesheet(esquema)
    regla = hoja.split(f'QPushButton[{theme.PRIMARIO_PROPERTY}="true"] {{')[1].split("}")[0]

    assert esquema.accent in regla


@pytest.mark.parametrize("esquema", list(theme.SCHEMES.values()), ids=list(theme.SCHEMES))
def test_el_texto_del_boton_principal_se_lee(esquema):
    tinta = theme.ink_over(esquema, esquema.accent)

    assert theme.contrast_ratio(tinta, esquema.accent) >= theme.MIN_TEXT_CONTRAST


def test_el_boton_principal_apagado_no_parece_encendido():
    """Sin la regla de apagado, el botón de la ICA sin componentes seguía
    relleno del acento, invitando a apretar algo que no hace nada."""
    assert ':disabled' in theme.stylesheet(theme.SERENO).split(theme.PRIMARIO_PROPERTY, 2)[2]
