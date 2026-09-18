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


def test_estan_los_seis_esquemas():
    """Papel, el del lienzo de diseño del hito 26, va último: el orden del menú
    arranca por el que reproduce el aspecto histórico del programa."""
    assert list(theme.SCHEMES) == ["Claro", "Oscuro", "NK", "Azul sobre gris", "ECG", "Papel"]


def test_cada_esquema_se_llama_como_su_clave():
    """La clave del diccionario y el nombre que ve el usuario son lo mismo.

    El menú se arma recorriendo las claves y el archivo de preferencias guarda
    el nombre: si divergieran, elegir un esquema guardaría otro.
    """
    assert all(clave == esquema.name for clave, esquema in theme.SCHEMES.items())


def test_el_de_fabrica_existe():
    assert theme.DEFAULT_SCHEME_NAME in theme.SCHEMES


def test_el_de_fabrica_es_el_claro():
    """Quien ya venía usando el programa no tiene por qué encontrárselo
    cambiado sin haberlo pedido, aunque la referencia sea oscura."""
    assert theme.scheme_by_name(theme.DEFAULT_SCHEME_NAME) is theme.CLARO


#: Los campos en los que `None` quiere decir algo: sin línea de base, la ventana
#: del mismo color que el fondo, las lecturas con la tipografía de siempre.
CAMPOS_OPCIONALES = {"baseline", "chrome", "numeric_font"}


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
        theme.CLARO.background = "#000000"  # type: ignore[misc]


# -- El color de cada canal --------------------------------------------------


def test_los_canales_toman_colores_distintos():
    colores = [theme.OSCURO.color_for_channel(i) for i in range(4)]

    assert len(set(colores)) == 4


def test_la_paleta_cicla_en_vez_de_quedarse_sin_color():
    """Con más canales que colores dos van a repetir, y repetir es mejor que
    quedarse sin color: es lo mismo que hace `AnnotationSet.color_of()`."""
    largo = len(theme.OSCURO.signal_palette)

    assert theme.OSCURO.color_for_channel(largo) == theme.OSCURO.color_for_channel(0)


def test_sin_variar_colores_todos_los_canales_son_iguales():
    assert theme.NK.vary_signal_colors is False
    assert theme.NK.color_for_channel(0) == theme.NK.signals
    assert theme.NK.color_for_channel(3) == theme.NK.signals


def test_una_paleta_vacia_no_deja_al_canal_sin_color():
    esquema = dataclasses.replace(theme.OSCURO, signal_palette=())

    assert esquema.color_for_channel(0) == esquema.signals


# -- Elegir un esquema -------------------------------------------------------


def test_elegir_un_esquema_lo_deja_como_el_actual():
    theme.set_current(theme.ECG)

    assert theme.current() is theme.ECG


def test_elegir_algo_que_no_es_un_esquema_avisa():
    with pytest.raises(UnknownColorSchemeError):
        theme.set_current("Oscuro")  # type: ignore[arg-type]


def test_un_esquema_inexistente_avisa_y_dice_cuales_hay():
    """El nombre suele venir de un archivo de preferencias escrito por otra
    versión del programa, así que el mensaje tiene que ayudar a corregirlo."""
    with pytest.raises(UnknownColorSchemeError) as fallo:
        theme.scheme_by_name("Fluorescente")

    assert "Fluorescente" in str(fallo.value)
    assert "Claro" in (fallo.value.details or "")


def test_pedir_un_esquema_con_algo_que_no_es_texto_avisa():
    with pytest.raises(UnknownColorSchemeError):
        theme.scheme_by_name(3)  # type: ignore[arg-type]


def test_los_errores_del_modulo_son_del_programa():
    """La ventana principal atrapa una sola clase; lo que no herede de ella le
    llega al investigador como traza de Python."""
    assert issubclass(UnknownColorSchemeError, PsgLabError)


# -- La hoja de estilo de los widgets de Qt ----------------------------------


def test_el_esquema_claro_no_pone_hoja_de_estilo():
    """Devolver la cadena vacía le devuelve a Qt su apariencia nativa, que es
    exactamente como se veía el programa antes de que existiera este módulo."""
    assert theme.stylesheet(theme.CLARO) == ""


@pytest.mark.parametrize(
    "esquema",
    [theme.OSCURO, theme.NK, theme.AZUL_SOBRE_GRIS, theme.ECG, theme.PAPEL],
    ids=lambda e: e.name,
)
def test_los_demas_esquemas_pintan_los_widgets(esquema: theme.ColorScheme):
    """Sin esto, un esquema oscuro deja el árbol de canales y el panel de
    scoring en claro y la ventana queda a dos colores."""
    hoja = theme.stylesheet(esquema)

    assert esquema.background in hoja
    assert esquema.foreground in hoja
    for widget in ("QMenuBar", "QTreeWidget", "QPushButton", "QHeaderView"):
        assert widget in hoja


def test_papel_pinta_la_ventana_con_su_propio_fondo():
    """La señal en blanco y la ventana alrededor en gris cálido."""
    hoja = theme.stylesheet(theme.PAPEL)

    assert f"QWidget {{ background-color: {theme.PAPEL.chrome};" in hoja
    assert theme.PAPEL.background in hoja


@pytest.mark.parametrize(
    "esquema",
    [theme.OSCURO, theme.NK, theme.AZUL_SOBRE_GRIS, theme.ECG],
    ids=lambda e: e.name,
)
def test_sin_fondo_de_ventana_la_hoja_es_la_de_antes(esquema: theme.ColorScheme):
    """Un `chrome` vacío es «el mismo que el fondo»: los esquemas de antes del
    hito 26 no pueden haber cambiado."""
    igual_al_fondo = dataclasses.replace(esquema, chrome=esquema.background)

    assert theme.stylesheet(igual_al_fondo) == theme.stylesheet(esquema)


def test_papel_da_su_tipografia_a_las_lecturas():
    hoja = theme.stylesheet(theme.PAPEL)

    assert f'QLabel[{theme.READOUT_PROPERTY}="true"]' in hoja
    assert theme.PAPEL.numeric_font in hoja


def test_sin_tipografia_numerica_no_hay_regla_para_las_lecturas():
    assert theme.READOUT_PROPERTY not in theme.stylesheet(theme.OSCURO)


def test_un_fondo_de_ventana_poco_legible_se_detecta():
    esquema = dataclasses.replace(theme.PAPEL, chrome="#2a2a2a")

    assert "el texto de la ventana" in [que for que, _ in theme.low_contrast_elements(esquema)]


def test_un_fondo_de_ventana_mal_escrito_se_rechaza_al_leerlo():
    datos = theme.scheme_to_dict(theme.PAPEL) | {"chrome": "gris"}

    with pytest.raises(UnknownColorSchemeError):
        theme.scheme_from_dict(datos)


def test_una_tipografia_numerica_vacia_se_rechaza_al_leerla():
    datos = theme.scheme_to_dict(theme.PAPEL) | {"numeric_font": "  "}

    with pytest.raises(UnknownColorSchemeError):
        theme.scheme_from_dict(datos)


def test_armar_la_hoja_de_algo_que_no_es_un_esquema_avisa():
    with pytest.raises(UnknownColorSchemeError):
        theme.stylesheet("Oscuro")  # type: ignore[arg-type]


# -- Guardar y volver a leer -------------------------------------------------


@pytest.mark.parametrize("esquema", list(theme.SCHEMES.values()), ids=lambda e: e.name)
def test_ida_y_vuelta_devuelve_el_mismo_esquema(esquema: theme.ColorScheme):
    assert theme.scheme_from_dict(theme.scheme_to_dict(esquema)) == esquema


def test_la_paleta_vuelve_como_tupla():
    """En el archivo es una lista, y en el esquema tiene que ser inmutable como
    todo lo demás."""
    vuelto = theme.scheme_from_dict(theme.scheme_to_dict(theme.OSCURO))

    assert isinstance(vuelto.signal_palette, tuple)


def test_un_campo_que_falta_se_toma_del_esquema_claro():
    """Un archivo guardado por una versión anterior sigue cargando: perder la
    preferencia porque el programa creció es peor que dibujar un color de
    fábrica."""
    datos = theme.scheme_to_dict(theme.OSCURO)
    del datos["accent"]

    assert theme.scheme_from_dict(datos).accent == theme.CLARO.accent


def test_un_campo_que_sobra_se_ignora():
    datos = theme.scheme_to_dict(theme.OSCURO)
    datos["color_de_las_reglas"] = "#ff00ff"

    assert theme.scheme_from_dict(datos) == theme.OSCURO


def test_la_linea_de_base_puede_estar_apagada():
    datos = theme.scheme_to_dict(theme.OSCURO)
    datos["baseline"] = None

    assert theme.scheme_from_dict(datos).baseline is None


@pytest.mark.parametrize(
    "campo, valor",
    [
        ("background", 3),
        ("vary_signal_colors", "sí"),
        ("signal_palette", "#ffffff"),
        ("signal_palette", [1, 2]),
        ("baseline", 7),
    ],
)
def test_un_valor_con_el_que_no_se_puede_dibujar_avisa(campo: str, valor: object):
    datos = theme.scheme_to_dict(theme.CLARO)
    datos[campo] = valor

    with pytest.raises(UnknownColorSchemeError):
        theme.scheme_from_dict(datos)


def test_algo_que_no_es_un_diccionario_avisa():
    with pytest.raises(UnknownColorSchemeError):
        theme.scheme_from_dict(["#ffffff"])  # type: ignore[arg-type]


def test_guardar_algo_que_no_es_un_esquema_avisa():
    with pytest.raises(UnknownColorSchemeError):
        theme.scheme_to_dict({"background": "#ffffff"})  # type: ignore[arg-type]


# -- Qué cuenta como color ----------------------------------------------------------


@pytest.mark.parametrize("color", ["#112233", "#abc", "#11223344", "red", "w"])
def test_un_color_que_pyqtgraph_sabe_dibujar_es_valido(color: str):
    assert theme.is_valid_color(color)


@pytest.mark.parametrize("color", ["gris oscuro", "", "   ", None, 3, "#12"])
def test_lo_que_no_se_puede_dibujar_no_es_un_color(color: object):
    assert not theme.is_valid_color(color)


def test_un_esquema_con_un_color_mal_escrito_se_rechaza_al_leerlo():
    """**El error que llegaba como traza.** Antes sólo se comprobaba que fuera
    texto, así que «gris oscuro» se cargaba sin quejas y al aplicarlo el
    investigador veía `ValueError: Unable to convert gris oscuro to QColor`."""
    datos = theme.scheme_to_dict(theme.OSCURO)
    datos["background"] = "gris oscuro"

    with pytest.raises(UnknownColorSchemeError, match="background"):
        theme.scheme_from_dict(datos)


def test_una_paleta_con_un_color_mal_escrito_se_rechaza():
    datos = theme.scheme_to_dict(theme.OSCURO)
    datos["signal_palette"] = ["#ff0000", "verdecito"]

    with pytest.raises(UnknownColorSchemeError):
        theme.scheme_from_dict(datos)


def test_el_esquema_ecg_trae_la_grilla_cuadriculada():
    """Es lo que su nombre promete, y separarlo obligaría a elegir dos cosas."""
    assert theme.ECG.ecg_grid
    assert not theme.CLARO.ecg_grid
    assert not theme.OSCURO.ecg_grid


def test_un_esquema_guardado_antes_de_la_grilla_ecg_sigue_cargando():
    datos = theme.scheme_to_dict(theme.OSCURO)
    del datos["ecg_grid"]

    assert theme.scheme_from_dict(datos) == theme.OSCURO


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
        theme.OSCURO, signal_palette=("#ffff00", "#404040")
    )

    bajos = theme.low_contrast_elements(esquema)

    assert [que for que, _ in bajos] == ["el color 2 de los canales"]
    assert bajos[0][1] < theme.MIN_GRAPHIC_CONTRAST


def test_un_texto_poco_legible_se_detecta_con_el_umbral_del_texto():
    """3,5 a 1 alcanza para una curva y no para un texto."""
    esquema = dataclasses.replace(theme.CLARO, foreground="#8a8a8a")

    assert theme.contrast_ratio("#8a8a8a", theme.CLARO.background) > 3.0
    assert "el texto de los gráficos" in [que for que, _ in theme.low_contrast_elements(esquema)]


# -- El color de los iconos ------------------------------------------------------


@pytest.mark.parametrize("nombre", [n for n in theme.SCHEMES if n != "Claro"])
def test_los_iconos_toman_el_texto_del_esquema(nombre: str):
    esquema = theme.SCHEMES[nombre]

    assert theme.icon_ink(esquema) == esquema.foreground


def test_con_claro_los_iconos_siguen_al_sistema(qt_app):
    """Claro deja el aspecto nativo, que puede ser oscuro: con el negro del
    esquema, los iconos quedaban negros sobre una barra negra."""
    from PySide6.QtGui import QGuiApplication, QPalette

    esperado = QGuiApplication.palette().color(QPalette.ColorRole.WindowText).name()

    assert theme.icon_ink(theme.CLARO) == esperado


def test_el_color_de_los_iconos_pide_un_esquema():
    with pytest.raises(UnknownColorSchemeError):
        theme.icon_ink("Oscuro")  # type: ignore[arg-type]
