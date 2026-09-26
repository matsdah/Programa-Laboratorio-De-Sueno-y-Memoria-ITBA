"""Tests de las anotaciones de eventos sobre la señal.

Las anotaciones son lo que el usuario marca a mano sobre el registro, así que
son datos que no se pueden reconstruir si se pierden. Los tests que más importan
acá no son los de contar, sino los que fijan **qué anotación se borra** y **cuál
se dibuja**: equivocarse en cualquiera de los dos borra o esconde trabajo del
investigador sin que nada avise.
"""

import pytest

from psglab.core.annotations import (
    PALETTE,
    Annotation,
    AnnotationSet,
    es_color_de_clase,
    marks_to_annotations,
)
from psglab.utils.errors import InvalidAnnotationError, UnknownAnnotationLabelError


@pytest.fixture
def anotaciones() -> AnnotationSet:
    """Conjunto vacío con las tres clases de fábrica."""
    return AnnotationSet()


def evento(onset: int, duracion: int = 100, label: str = "Arousal") -> Annotation:
    """Una anotación mínima, para los tests que sólo miran posiciones."""
    return Annotation(label=label, onset_sample=onset, duration_samples=duracion)


# -- La anotación en sí -----------------------------------------------------


def test_el_final_es_el_inicio_mas_la_duracion():
    assert evento(1000, 250).end_sample == 1250


def test_dos_anotaciones_iguales_son_iguales_y_hashables():
    """`Annotation` es frozen para poder ir en un conjunto.

    Es lo que necesita el anotador para saber cuál está debajo del clic.
    """
    assert evento(10) == evento(10)
    assert len({evento(10), evento(10)}) == 1


# -- El orden, que es lo que le da sentido a remove_at -----------------------


def test_las_anotaciones_salen_ordenadas_por_inicio(anotaciones):
    """Se agregan desordenadas a propósito: el usuario anota como quiere."""
    for inicio in (5000, 100, 2500):
        anotaciones.add(evento(inicio))

    assert [a.onset_sample for a in anotaciones.all()] == [100, 2500, 5000]


def test_remove_at_borra_la_que_señala_el_indice_de_all(anotaciones):
    """El test que justifica que la lista se guarde ordenada.

    Si se guardaran por orden de creación y `all()` ordenara al salir, el índice
    que ve el anotador y el que usa `remove_at` apuntarían a anotaciones
    distintas, y el usuario vería desaparecer una banda que no tocó.
    """
    for inicio in (5000, 100, 2500):
        anotaciones.add(evento(inicio))

    senalada = anotaciones.all()[1]
    anotaciones.remove_at(1)

    assert senalada not in anotaciones.all()
    assert [a.onset_sample for a in anotaciones.all()] == [100, 5000]


def test_remove_borra_la_primera_de_dos_identicas(anotaciones):
    """Son indistinguibles por definición, así que cuál se borra da igual."""
    anotaciones.add(evento(100))
    anotaciones.add(evento(100))
    anotaciones.remove(evento(100))
    assert len(anotaciones.all()) == 1


def test_borrar_una_anotacion_que_no_esta_falla(anotaciones):
    """Un borrado silencioso escondería un bug del anotador."""
    with pytest.raises(InvalidAnnotationError):
        anotaciones.remove(evento(999))


@pytest.mark.parametrize("indice", [1, -1, 5])
def test_remove_at_con_una_posicion_que_no_existe_falla(anotaciones, indice):
    """El −1 importa: en Python cuenta desde el final.

    Sin la guarda, `remove_at(-1)` borraría la última anotación de la noche en
    vez de avisar que el índice está mal.
    """
    anotaciones.add(evento(100))
    with pytest.raises(InvalidAnnotationError):
        anotaciones.remove_at(indice)


def test_all_devuelve_una_copia(anotaciones):
    """Desordenar la lista interna rompería el índice de `remove_at`."""
    anotaciones.add(evento(100))
    anotaciones.add(evento(200))

    prestada = anotaciones.all()
    prestada.reverse()

    assert [a.onset_sample for a in anotaciones.all()] == [100, 200]


# -- Lo que no se deja agregar ----------------------------------------------


def test_no_se_puede_anotar_con_una_clase_sin_registrar(anotaciones):
    """Una clase inventada terminaría en `Anotaciones.txt` sin significado."""
    with pytest.raises(UnknownAnnotationLabelError):
        anotaciones.add(evento(100, label="Husos raros"))


def test_una_anotacion_antes_del_registro_se_rechaza(anotaciones):
    with pytest.raises(InvalidAnnotationError):
        anotaciones.add(evento(-1))


@pytest.mark.parametrize("duracion", [0, -50])
def test_una_anotacion_que_no_cubre_ninguna_muestra_se_rechaza(anotaciones, duracion):
    """La duración cero se rechaza a propósito, no por descuido.

    El pliego pide marcar el evento con una banda sobre la señal, y una banda
    sin ancho no se puede dibujar ni solapar con nada: `in_range` nunca la
    devolvería, así que el usuario la crearía y no la vería jamás.
    """
    with pytest.raises(InvalidAnnotationError):
        anotaciones.add(evento(100, duracion))


def test_una_clase_sin_nombre_se_rechaza(anotaciones):
    with pytest.raises(InvalidAnnotationError):
        anotaciones.add_label("   ")


# -- Las clases y sus colores -----------------------------------------------


def test_las_clases_de_fabrica_estan_registradas(anotaciones):
    assert anotaciones.labels() == ["Arousal", "Complejo K", "Spindle"]


def test_toda_clase_registrada_tiene_color(anotaciones):
    """Es lo que le permite a `color_of` cumplir su firma `-> str`."""
    for clase in anotaciones.labels():
        assert anotaciones.color_of(clase).startswith("#")


def test_los_colores_se_asignan_por_orden_de_registro(anotaciones):
    """Determinístico: dos registros abiertos seguidos se ven igual."""
    assert anotaciones.color_of("Arousal") == PALETTE[0]
    assert anotaciones.color_of("Spindle") == PALETTE[2]

    anotaciones.add_label("Husos lentos")
    assert anotaciones.color_of("Husos lentos") == PALETTE[3]


def test_se_puede_elegir_el_color_de_una_clase_nueva(anotaciones):
    anotaciones.add_label("Apnea", color="#123456")
    assert anotaciones.color_of("Apnea") == "#123456"


def test_registrar_dos_veces_la_misma_clase_no_falla(anotaciones):
    """Es algo que el usuario teclea; que explote sería hostil."""
    anotaciones.add_label("Apnea")
    anotaciones.add_label("Apnea")
    assert anotaciones.labels().count("Apnea") == 1


def test_volver_a_registrar_con_color_reemplaza_el_anterior(anotaciones):
    anotaciones.add_label("Apnea")
    anotaciones.add_label("Apnea", color="#abcdef")
    assert anotaciones.color_of("Apnea") == "#abcdef"


def test_pedir_el_color_de_una_clase_que_no_existe_falla(anotaciones):
    with pytest.raises(UnknownAnnotationLabelError):
        anotaciones.color_of("Husos raros")


# -- Qué se dibuja en la ventana actual -------------------------------------


def test_una_anotacion_que_cruza_el_borde_entra(anotaciones):
    """Empieza antes de la ventana y termina adentro: hay que dibujarla."""
    anotaciones.add(evento(900, 200))  # 900..1100
    assert len(anotaciones.in_range(1000, 2000)) == 1


def test_una_anotacion_que_termina_justo_donde_empieza_el_tramo_no_entra(anotaciones):
    """El tramo es semiabierto, igual que `windows.window_to_samples`.

    Si entrara, la misma anotación se dibujaría en dos ventanas seguidas.
    """
    anotaciones.add(evento(800, 200))  # 800..1000
    assert anotaciones.in_range(1000, 2000) == []


def test_una_anotacion_que_empieza_justo_donde_termina_el_tramo_no_entra(anotaciones):
    anotaciones.add(evento(2000, 100))
    assert anotaciones.in_range(1000, 2000) == []


def test_una_anotacion_contenida_entera_entra(anotaciones):
    anotaciones.add(evento(1200, 100))
    assert len(anotaciones.in_range(1000, 2000)) == 1


def test_las_anotaciones_del_tramo_salen_ordenadas(anotaciones):
    anotaciones.add(evento(1800))
    anotaciones.add(evento(1100))
    assert [a.onset_sample for a in anotaciones.in_range(1000, 2000)] == [1100, 1800]


# -- Lo que consume Informacion.txt -----------------------------------------


def test_se_cuentan_las_anotaciones_por_clase(anotaciones):
    anotaciones.add(evento(100, label="Arousal"))
    anotaciones.add(evento(200, label="Arousal"))
    anotaciones.add(evento(300, label="Spindle"))

    assert anotaciones.count_by_label() == {"Arousal": 2, "Spindle": 1}


def test_una_clase_sin_anotaciones_no_aparece_en_la_cuenta(anotaciones):
    """`Informacion.txt` omite lo que no corresponde, no escribe ceros."""
    anotaciones.add(evento(100, label="Arousal"))
    assert "Complejo K" not in anotaciones.count_by_label()


def test_un_conjunto_vacio_no_cuenta_nada(anotaciones):
    assert anotaciones.count_by_label() == {}
    assert anotaciones.all() == []


def test_una_anotacion_completamente_fuera_del_tramo_no_entra(anotaciones):
    """El agujero más caro que tenía el conjunto de tests.

    Todos los casos de `in_range` tocaban o cruzaban el tramo, así que ninguno
    distinguía `<` de `!=`. Con `!=`, una anotación en 100..150 consultada con
    `in_range(1000, 2000)` **entra**: toda anotación de la noche se dibujaría en
    todas las ventanas.
    """
    anotaciones.add(evento(100, 50))
    assert anotaciones.in_range(1000, 2000) == []
    assert len(anotaciones.in_range(0, 200)) == 1


def test_una_anotacion_posterior_al_tramo_tampoco(anotaciones):
    """La otra mitad de la comparación, por el mismo motivo."""
    anotaciones.add(evento(5000, 50))
    assert anotaciones.in_range(1000, 2000) == []


def test_se_puede_borrar_la_primera_anotacion(anotaciones):
    """Nadie llamaba `remove_at(0)`.

    Con la guarda escrita `0 < index`, la primera anotación de la noche quedaría
    inalcanzable y la suite no se enteraría.
    """
    anotaciones.add(evento(100))
    anotaciones.add(evento(200))
    anotaciones.remove_at(0)
    assert [a.onset_sample for a in anotaciones.all()] == [200]


def test_una_anotacion_de_una_sola_muestra_se_acepta(anotaciones):
    """Es la duración mínima que el mensaje de error promete aceptar.

    El parametrize de duraciones inválidas usa 0 y −50; nunca 1, así que el
    borde no estaba fijado.
    """
    anotaciones.add(evento(100, 1))
    assert anotaciones.all()[0].duration_samples == 1


def test_una_anotacion_en_la_primera_muestra_se_acepta(anotaciones):
    """Un evento marcado en el punto 0 del registro es legítimo."""
    anotaciones.add(evento(0, 10))
    assert anotaciones.all()[0].onset_sample == 0


def test_dos_anotaciones_en_la_misma_muestra_conservan_el_orden_de_creacion(anotaciones):
    """Es el desempate del que depende que `remove_at` señale lo que el usuario ve.

    Con `bisect_left` en vez de `bisect_right` el orden se invierte, y ningún
    test lo notaba porque los dos casos existentes usaban anotaciones idénticas,
    indistinguibles por definición.
    """
    anotaciones.add(evento(500, label="Arousal"))
    anotaciones.add(evento(500, label="Spindle"))
    assert [a.label for a in anotaciones.all()] == ["Arousal", "Spindle"]


def test_registrar_dos_veces_una_clase_no_le_cambia_el_color(anotaciones):
    """El test que había sólo contaba las clases, no miraba el color.

    Sin la guarda, re-registrar una clase le asigna el color siguiente de la
    paleta y el usuario ve cambiar de color todas sus bandas por haber tecleado
    dos veces el mismo nombre.
    """
    anotaciones.add_label("Apnea")
    color = anotaciones.color_of("Apnea")
    anotaciones.add_label("Apnea")
    assert anotaciones.color_of("Apnea") == color


# -- El color de una clase es exactamente #rrggbb (hito 48) ------------------


@pytest.mark.parametrize("color", ["#e6754a", "#E6754A", "#000000", "#ffffff"])
def test_un_color_de_seis_digitos_sirve(color: str):
    assert es_color_de_clase(color)


@pytest.mark.parametrize(
    "color",
    ["red", "#abc", "#e6754aff", "e6754a", "#e6754", "#ggg000", " #e6754a", "", None, 3],
)
def test_lo_que_no_es_seis_digitos_no_sirve(color):
    """**Aunque pyqtgraph sepa dibujarlo.** `red`, `#abc` y `#e6754aff` son
    colores para él; no lo son para la banda de una anotación, porque el
    visualizador le concatena la transparencia al texto."""
    assert not es_color_de_clase(color)


def test_la_paleta_de_fabrica_cumple_su_propia_regla():
    """Si un color de fábrica no la cumpliera, la primera clase que el usuario
    creara sin elegir color fallaría."""
    assert all(es_color_de_clase(color) for color in PALETTE)


def test_una_clase_con_un_color_que_no_es_seis_digitos_se_rechaza(anotaciones):
    """**Hasta el hito 48 se aceptaba cualquier cosa**, y un archivo de
    preferencias editado a mano con `red` llegaba hasta el dibujo, donde la
    banda de la anotación elevaba un `ValueError` crudo."""
    with pytest.raises(InvalidAnnotationError):
        anotaciones.add_label("Huso", "red")


def test_un_color_rechazado_no_deja_la_clase_a_medias(anotaciones):
    """Se valida antes de tocar nada: la clase no queda registrada sin color."""
    with pytest.raises(InvalidAnnotationError):
        anotaciones.add_label("Huso", "red")

    assert "Huso" not in anotaciones.labels()


def test_sin_color_la_clase_sigue_tomando_uno_de_la_paleta(anotaciones):
    """`None` no es un color inválido: quiere decir «el que siga»."""
    anotaciones.add_label("Huso")

    assert es_color_de_clase(anotaciones.color_of("Huso"))


# -- Corregir es reemplazar (hito 52) ---------------------------------------


def test_reemplazar_cambia_una_por_otra(anotaciones):
    vieja = evento(100)
    anotaciones.add(vieja)

    anotaciones.replace(vieja, evento(100, label="Spindle"))

    assert [a.label for a in anotaciones.all()] == ["Spindle"]


def test_la_reemplazante_va_a_su_lugar_por_inicio(anotaciones):
    """**La promesa de orden sobrevive a corregir**: mover el comienzo de una
    anotación más allá de otra la cambia de lugar, y `remove_at()` depende de
    que el índice sea la posición en `all()`."""
    primera, segunda = evento(100), evento(500)
    anotaciones.add(primera)
    anotaciones.add(segunda)

    anotaciones.replace(primera, evento(900))

    assert [a.onset_sample for a in anotaciones.all()] == [500, 900]


def test_una_reemplazante_invalida_no_toca_nada(anotaciones):
    """**Valida antes de sacar la vieja.** Si no, un reemplazo que falla a la
    mitad le costaría al investigador el evento que quería corregir."""
    vieja = evento(100)
    anotaciones.add(vieja)

    with pytest.raises(InvalidAnnotationError):
        anotaciones.replace(vieja, evento(100, duracion=0))

    assert anotaciones.all() == [vieja]


def test_una_clase_sin_registrar_tampoco(anotaciones):
    vieja = evento(100)
    anotaciones.add(vieja)

    with pytest.raises(UnknownAnnotationLabelError):
        anotaciones.replace(vieja, evento(100, label="Inventada"))

    assert anotaciones.all() == [vieja]


def test_reemplazar_una_que_no_esta_avisa(anotaciones):
    """Un reemplazo silencioso de algo inexistente agregaría una anotación que
    nadie hizo."""
    with pytest.raises(InvalidAnnotationError):
        anotaciones.replace(evento(100), evento(200))

    assert anotaciones.all() == []


# -- En muestras enteras (hito 71) ------------------------------------------


@pytest.mark.parametrize(
    ("inicio", "duracion"), [(10.5, 100), (10, 3.2)], ids=["inicio", "duracion"]
)
def test_una_anotacion_en_fracciones_de_muestra_se_rechaza(anotaciones, inicio, duracion):
    """`Anotaciones.txt` guarda puntos del registro, que son enteros: una
    fracción no es un lugar de la señal. Se aceptaba."""
    with pytest.raises(InvalidAnnotationError):
        anotaciones.add(Annotation("Arousal", inicio, duracion))



# -- Las marcas del archivo como anotaciones (hito 73) ------------------------


def test_una_marca_pasa_de_segundos_a_muestras():
    (anotacion,) = marks_to_annotations([(1.5, 0.25, "Stimulus/S  1")], 100.0, 1000)

    assert anotacion == Annotation("Stimulus/S  1", 150, 25)


def test_una_marca_sin_duracion_ocupa_una_muestra():
    """Un marcador de estímulo es un instante, y una anotación sin ancho no
    se podría dibujar."""
    (anotacion,) = marks_to_annotations([(0.5, 0.0, "Estímulo")], 100.0, 1000)

    assert anotacion.duration_samples == 1


@pytest.mark.parametrize("inicio", [-1.0, 10.0, 25.0], ids=["antes", "en-el-final", "despues"])
def test_una_marca_fuera_del_registro_se_saltea(inicio):
    """La de un archivo truncado no tiene dónde ir."""
    assert marks_to_annotations([(inicio, 1.0, "Marca")], 100.0, 1000) == []


def test_una_marca_que_se_pasa_del_final_se_recorta():
    (anotacion,) = marks_to_annotations([(9.5, 5.0, "Larga")], 100.0, 1000)

    assert anotacion.end_sample == 1000


def test_una_marca_sin_descripcion_se_saltea():
    assert marks_to_annotations([(1.0, 1.0, "   ")], 100.0, 1000) == []


def test_la_clase_va_sin_los_espacios_de_los_bordes():
    (anotacion,) = marks_to_annotations([(1.0, 1.0, "  Arousal ")], 100.0, 1000)

    assert anotacion.label == "Arousal"


@pytest.mark.parametrize(
    "marca",
    [(1.0, 1.0), ("uno", 1.0, "M"), (1.0, float("nan"), "M"), (1.0, 1.0, 3)],
    ids=["dos-campos", "inicio-texto", "duracion-nan", "descripcion-numero"],
)
def test_una_marca_mal_formada_se_rechaza(marca):
    with pytest.raises(InvalidAnnotationError):
        marks_to_annotations([marca], 100.0, 1000)
