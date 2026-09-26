"""Tests de las tipografías que el programa trae consigo.

Lo que importa es que estén, que la licencia viaje con ellas, que sean **una
sola familia** con cifras de ancho fijo (hito 77), y que **si faltan el
programa arranque igual**: una tipografía es una preferencia visual, no una
dependencia.
"""

from pathlib import Path

import pytest
from PySide6.QtGui import QFont, QFontInfo, QFontMetricsF

pytest.importorskip("PySide6")

import psglab.ui.fonts as fonts  # noqa: E402
from psglab.utils.errors import UnknownTypeRoleError  # noqa: E402


def test_registra_una_sola_familia(qt_app):
    """**Una sola desde el hito 77**: Plex Mono se sacó porque dos familias en
    la misma pantalla se veían desprolijas.

    **No se compara contra `[UI_FONT_FAMILY]`**, porque en Linux la lista trae
    un nombre más y es de la misma familia. El archivo de la semi-negrita tiene
    dos: el tipográfico, «IBM Plex Sans» con estilo SemiBold, y el heredado,
    «IBM Plex Sans SmBld», para los programas que sólo conocen regular, negrita
    e itálica. Windows y macOS dan el primero; fontconfig expone los dos, y Qt
    registra los dos. Lo que el test tiene que rechazar es otra familia, como
    Plex Mono, y ésa no empieza con el nombre de Sans."""
    familias = fonts.register_bundled_fonts()

    assert fonts.UI_FONT_FAMILY in familias
    assert all(f.startswith(fonts.UI_FONT_FAMILY) for f in familias), familias


@pytest.mark.parametrize("rol", ["titulo", "rotulo", "chip"])
def test_la_negrita_es_la_de_verdad(qt_app, rol: str):
    """**La semi-negrita sale del archivo, no la inventa Qt** (hito 78). Es
    la otra mitad de lo de arriba: con el nombre heredado a la vista, Qt podría
    no encontrarla bajo «IBM Plex Sans» y engordar la regular, que se lee peor.
    No pasa —se mira el estilo que usa de verdad—, y este test lo sostiene."""
    fonts.register_bundled_fonts()

    assert QFontInfo(fonts.font_for(rol, base())).styleName() == "SemiBold"


def test_registrar_dos_veces_no_las_vuelve_a_cargar(qt_app):
    """Qt no deduplica: el mismo archivo registrado dos veces se carga dos."""
    primera = fonts.register_bundled_fonts()
    cargados = dict(fonts._registradas)

    segunda = fonts.register_bundled_fonts()

    assert segunda == primera
    assert fonts._registradas == cargados


def test_la_de_la_interfaz_tambien(qt_app):
    """Es la de fábrica desde el hito 34, así que un nombre mal escrito dejaría
    la ventana entera con la tipografía que Qt eligiera."""
    assert fonts.UI_FONT_FAMILY in fonts.register_bundled_fonts()


def test_una_familia_registrada_esta_disponible(qt_app):
    fonts.register_bundled_fonts()

    assert fonts.available_family() == fonts.UI_FONT_FAMILY


def test_una_familia_que_no_existe_no_lo_esta(qt_app):
    """**Es lo que separa degradar a lo conocido de degradar a cualquier cosa**:
    `QFont.setFamily()` con un nombre que no existe no avisa, y Qt sustituye
    por lo que le parece."""
    assert fonts.available_family("Una Que No Existe") is None


def test_una_carpeta_que_no_existe_no_impide_arrancar(qt_app, tmp_path: Path):
    assert fonts.register_bundled_fonts(tmp_path / "no-existe") == []


def test_un_archivo_roto_se_saltea(qt_app, tmp_path: Path):
    (tmp_path / fonts.FONT_FILES[0]).write_bytes(b"esto no es una tipografia")

    assert fonts.register_bundled_fonts(tmp_path) == []


def test_estan_todos_los_archivos():
    faltan = [nombre for nombre in fonts.FONT_FILES if not (fonts.FONTS_DIR / nombre).is_file()]

    assert faltan == []


def test_la_licencia_viaja_con_los_archivos():
    """La OFL permite empaquetarlas con un programa MIT a condición de esto."""
    licencia = (fonts.FONTS_DIR / "OFL.txt").read_text(encoding="utf-8")

    assert "SIL OPEN FONT LICENSE Version 1.1" in licencia


# -- La escala tipográfica (hito 43) -----------------------------------------


def base(puntos: int = 13) -> QFont:
    """Una tipografía base como la que tiene la aplicación."""
    fuente = QFont()
    fuente.setPointSize(puntos)
    return fuente


def test_los_ocho_roles_usan_la_misma_familia(qt_app):
    """**Es la promesa del módulo.** Se mira la `QFont` que sale y no la tabla:
    una segunda familia se colaría por `font_for()` aunque la tabla no la
    nombre."""
    fonts.register_bundled_fonts()

    familias = {fonts.font_for(rol, base()).family() for rol in fonts.ROLES}

    assert familias == {fonts.UI_FONT_FAMILY}


@pytest.mark.parametrize("rol", ["lectura", "chip", "ausente", "titulo"])
def test_las_cifras_tienen_ancho_fijo(qt_app, rol: str):
    """**Es lo que hizo sobrar a Plex Mono** (hito 77): una lectura que cambia
    —la hora, la ventana, los µV— no puede saltar de ancho mientras se navega.
    Se mide con la tipografía cargada en Qt, en los tres estilos que el
    programa trae: regular, semi-negrita e itálica. Si una versión nueva de
    los archivos trajera cifras proporcionales, esto lo dice."""
    fonts.register_bundled_fonts()
    metricas = QFontMetricsF(fonts.font_for(rol, base(24)))

    anchos = {round(metricas.horizontalAdvance(cifra), 3) for cifra in "0123456789"}

    assert len(anchos) == 1


def test_los_pasos_se_cuentan_desde_el_tamano_base(qt_app):
    """Subir el tamaño en Configuración tiene que agrandar la interfaz entera
    sin romper ninguna proporción."""
    chica = fonts.font_for("secundario", base(11))
    grande = fonts.font_for("secundario", base(17))

    assert chica.pointSize() == 10
    assert grande.pointSize() == 16


def test_un_paso_no_achica_hasta_lo_ilegible(qt_app):
    """Con el tamaño base en su mínimo, un paso de −2 llegaría ahí."""
    assert fonts.font_for("chip", base(6)).pointSize() >= fonts.MIN_POINT_SIZE


def test_el_chip_va_en_semi_negrita(qt_app):
    """Era Plex Mono, que a dos puntos menos que la base se sostenía por su
    trazo parejo; Plex Sans regular a ese tamaño, blanca sobre el relleno del
    chip, se afina (hito 77)."""
    assert fonts.font_for("chip", base()).bold()


def test_el_rol_ausente_va_en_italica(qt_app):
    """Inclinada quiere decir «esto no lo midió ni lo eligió nadie», que hasta
    el hito 43 lo cargaba el gris —y el gris ya decía «esto es secundario»."""
    assert fonts.font_for("ausente", base()).italic()
    assert not fonts.font_for("secundario", base()).italic()


def test_el_rotulo_lleva_espaciado_entre_letras(qt_app):
    """Va en mayúsculas, y sin aire se apelmaza. Es el único rol que lo pide."""
    rotulo = fonts.font_for("rotulo", base())

    assert rotulo.letterSpacing() > 0
    assert fonts.font_for("cuerpo", base()).letterSpacing() == 0


def test_la_base_no_se_toca(qt_app):
    """Devuelve una `QFont` nueva: la de la aplicación la comparten todos."""
    original = base(13)

    fonts.font_for("titulo", original)

    assert original.pointSize() == 13
    assert not original.bold()


def test_un_rol_que_no_existe_se_rechaza(qt_app):
    """El nombre lo escribe quien dibuja, y un error de tipeo es la causa
    habitual: el mensaje los enumera, como hace `icons.icon()`."""
    with pytest.raises(UnknownTypeRoleError) as error:
        fonts.font_for("inventado", base())

    assert "rotulo" in str(error.value.details)


def test_un_tamano_en_pixeles_no_se_desplaza_en_puntos(qt_app):
    """Qt devuelve −1 en `pointSize()` cuando la tipografía se fijó en
    píxeles: desplazarlo daría un tamaño de otra unidad."""
    en_pixeles = QFont()
    en_pixeles.setPixelSize(20)

    assert fonts.font_for("chip", en_pixeles).pixelSize() == 20
