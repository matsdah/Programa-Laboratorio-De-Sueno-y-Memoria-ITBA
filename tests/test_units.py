"""Tests de la conversión de unidades a microvoltios.

Todo el programa trabaja en µV y la conversión se hace **una sola vez**, al
importar el registro. Si este módulo se equivoca, la señal queda mal escalada de
punta a punta: el scoring sale mal y nadie lo nota mirando la pantalla, porque
una señal escalada por mil sigue pareciendo una señal.

Por eso los casos que más importan acá no son los factores —que son
aritmética— sino los de **entrada sucia**: las cabeceras de EDF y BrainVision
escriben la unidad de formas variadas, y confundir "no reconozco esto" con "esto
vale 1" es la falla cara.
"""

import pytest

from psglab.utils.errors import UnknownUnitError
from psglab.utils.units import (
    MICROVOLT,
    TO_MICROVOLTS,
    conversion_factor,
    format_amplitude,
    normalize_unit_name,
    to_microvolts,
)
from psglab.utils import units


# -- Los factores -----------------------------------------------------------


def test_los_voltios_se_convierten_por_un_millon():
    assert to_microvolts(1.0, "V") == pytest.approx(1e6)


def test_los_milivoltios_se_convierten_por_mil():
    """Es el caso del pliego, que escribe "mV" donde quiere decir µV."""
    assert to_microvolts(1.0, "mV") == pytest.approx(1e3)


def test_los_microvoltios_no_se_tocan():
    """Convertir a la misma unidad tiene que ser exactamente identidad."""
    assert to_microvolts(75.0, "µV") == 75.0


def test_el_signo_negativo_se_conserva():
    """La señal oscila alrededor de cero: media onda es negativa."""
    assert to_microvolts(-2.5, "mV") == pytest.approx(-2500.0)


def test_convertir_delega_en_el_factor():
    """No puede haber dos caminos que discrepen.

    `to_microvolts` no vuelve a mirar la tabla: multiplica por lo que devuelve
    `conversion_factor`.
    """
    assert to_microvolts(3.0, "mV") == pytest.approx(3.0 * conversion_factor("mV"))


# -- La entrada sucia -------------------------------------------------------


def test_los_dos_caracteres_mu_son_distintos_de_verdad():
    """Se ven iguales en pantalla, así que hay que afirmarlo por código.

    Si alguien los intercambiara sin querer al editar el módulo, la
    normalización dejaría de hacer nada y ningún otro test lo notaría.
    """
    assert ord(units._MU_GRIEGA) == 0x03BC
    assert ord(units._SIGNO_MICRO) == 0x00B5
    assert units._MU_GRIEGA != units._SIGNO_MICRO


def test_las_dos_mu_dan_el_mismo_resultado():
    """El caso que motiva todo el módulo.

    Las cabeceras de EDF y BrainVision usan uno u otro carácter según quién las
    haya escrito. Sin unificarlos, la mitad de los archivos válidos parecería
    traer una unidad desconocida.
    """
    con_signo_micro = f"{units._SIGNO_MICRO}V"
    con_mu_griega = f"{units._MU_GRIEGA}V"

    assert con_signo_micro != con_mu_griega
    assert to_microvolts(10.0, con_signo_micro) == to_microvolts(10.0, con_mu_griega)


def test_la_mu_griega_mayuscula_tambien_se_normaliza():
    """Fija el orden de los pasos de `normalize_unit_name`.

    U+039C baja a U+03BC con `lower()`, y recién entonces el reemplazo la
    alcanza. Si el reemplazo fuera primero, esta unidad quedaría sin normalizar.
    """
    assert normalize_unit_name("ΜV") == normalize_unit_name("µv")


def test_las_mayusculas_no_importan():
    assert conversion_factor("MV") == conversion_factor("mv")


def test_los_espacios_no_importan():
    """Las cabeceras suelen traer la unidad con relleno."""
    assert normalize_unit_name("  u V  ") == "uv"


def test_las_variantes_escritas_con_palabras_se_reconocen():
    """"microvolt" y "uV" son la misma unidad escrita distinto."""
    assert conversion_factor("microvolt") == conversion_factor("uV")
    assert conversion_factor("millivolts") == conversion_factor("mV")


# -- Lo que no se reconoce --------------------------------------------------


def test_una_unidad_desconocida_falla_en_vez_de_asumir_un_factor():
    """La decisión de diseño del módulo, y la razón por la que existe el error.

    Asumir 1.0 dejaría pasar una señal mal escalada. Fallar detiene la
    importación, que es lo barato.
    """
    with pytest.raises(UnknownUnitError):
        to_microvolts(1.0, "banana")


def test_el_error_de_unidad_le_habla_al_investigador():
    """Mensaje en español con la unidad del archivo, causa técnica aparte."""
    with pytest.raises(UnknownUnitError) as excepcion:
        conversion_factor("banana")

    assert "banana" in excepcion.value.message
    assert excepcion.value.details is not None
    assert "uv" in excepcion.value.details


def test_una_unidad_vacia_no_se_reconoce():
    """Una cabecera sin unidad no es lo mismo que una cabecera en µV."""
    with pytest.raises(UnknownUnitError):
        conversion_factor("")


def test_la_tabla_esta_normalizada():
    """Una clave con mayúsculas o con la mu griega sería inalcanzable.

    `conversion_factor` busca la unidad ya normalizada, así que una clave que no
    esté en esa forma no se podría encontrar nunca.
    """
    sin_normalizar = [c for c in TO_MICROVOLTS if normalize_unit_name(c) != c]
    assert not sin_normalizar, f"claves inalcanzables en TO_MICROVOLTS: {sin_normalizar}"


# -- El texto que ve el usuario ---------------------------------------------


def test_la_amplitud_se_muestra_con_su_unidad():
    """Es la escala que el pliego pide mostrar en el visualizador (V1_P)."""
    assert format_amplitude(75.0) == f"75 {MICROVOLT}"


def test_la_amplitud_se_redondea_a_entero_por_defecto():
    """En la escala del visualizador los decimales son ruido."""
    assert format_amplitude(74.6) == f"75 {MICROVOLT}"


def test_se_pueden_pedir_decimales():
    """Se elige un valor que no caiga en el filo del redondeo.

    Con 74.55 este test fallaría, y no por un defecto del formateo: 74.55 no es
    representable en binario y queda apenas por debajo, así que redondea a 74.5.
    Fijar acá el modo de redondeo sería testear la aritmética de punto flotante,
    no el módulo.
    """
    assert format_amplitude(12.34, decimals=1) == f"12.3 {MICROVOLT}"


def test_el_simbolo_sale_de_la_constante_y_no_de_un_literal():
    """Si mañana cambia el símbolo, tiene que cambiar en un solo lugar."""
    assert format_amplitude(1.0).endswith(MICROVOLT)
