"""Invariantes del repositorio: que el código y la documentación no se separen.

A diferencia del resto de `tests/`, este archivo no testea un componente del
programa sino **el repositorio entero**. Verifica lo que el proyecto se exige a
sí mismo y que hasta ahora se comprobaba a mano en cada revisión: que las
cuentas del TODO cierren, que los enlaces no apunten a la nada, que los IDs del
pliego que declara cada módulo coincidan con `docs/TRAZABILIDAD.md`.

Existe porque el equipo pasó a ser de tres personas. Con una, revisar a mano
alcanza; con tres, la documentación se desincroniza más rápido de lo que nadie
la mira. La evidencia es del propio proyecto: dos auditorías seguidas
encontraron divergencias introducidas pocos días antes.

Está en `tests/` y no en un script aparte para que corra con
`python -m pytest`, antes de pushear, y no sólo cuando el CI rechaza el pull
request.
"""

import ast
import pathlib
import re
import unicodedata

import pytest

#: La documentación escribe las cantidades chicas con palabras, así que hay que
#: poder compararlas contra un número.
NUMEROS_EN_PALABRAS: dict[str, int] = {
    "cero": 0, "un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
    "trece": 13, "catorce": 14, "quince": 15, "dieciséis": 16, "diecisiete": 17,
    "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21,
    "veintidós": 22, "veintitrés": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiséis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
    "treinta": 30, "treinta y uno": 31, "treinta y un": 31, "treinta y dos": 32, "treinta y tres": 33,
    "treinta y cuatro": 34, "treinta y cinco": 35, "treinta y seis": 36,
    "treinta y siete": 37, "treinta y ocho": 38, "treinta y nueve": 39,
    "cuarenta": 40,
}

#: Raíz del repositorio, deducida de la ubicación de este archivo.
RAIZ = pathlib.Path(__file__).resolve().parent.parent

#: Qué módulos cubre cada archivo de test. Hace falta declararlo porque la
#: relación no es uno a uno: `test_exporters.py` cubre cuatro módulos.
#: Al agregar un archivo de test, agregar acá su fila.
COBERTURA_DE_TESTS: dict[str, tuple[str, ...]] = {
    "test_windows.py": ("psglab/core/windows.py",),
    "test_errors.py": ("psglab/utils/errors.py",),
    "test_validation.py": ("psglab/utils/validation.py",),
    "test_units.py": ("psglab/utils/units.py",),
    "test_recording.py": ("psglab/core/recording.py",),
    "test_annotations.py": ("psglab/core/annotations.py",),
    "test_session.py": ("psglab/core/session.py",),
    "test_nomenclature.py": ("psglab/core/nomenclature.py",),
    "test_scoring.py": ("psglab/core/scoring.py",),
    "test_channel_types.py": ("psglab/readers/channel_types.py",),
    "test_readers.py": (
        "psglab/readers/base.py",
        "psglab/readers/edf.py",
        "psglab/readers/brainvision.py",
    ),
    "test_scoring_reader.py": ("psglab/readers/scoring_reader.py",),
    "test_amplitude_band.py": ("psglab/tools/amplitude_band.py",),
    "test_magnifier.py": ("psglab/tools/magnifier.py",),
    "test_annotator.py": ("psglab/tools/annotator.py",),
    "test_overview.py": ("psglab/tools/overview.py",),
    "test_histogram.py": ("psglab/tools/histogram.py",),
    "test_shortcuts.py": ("psglab/ui/shortcuts.py",),
    "test_signal_view.py": ("psglab/ui/signal_view.py",),
    "test_grid.py": ("psglab/ui/grid.py",),
    "test_registry.py": (
        "psglab/tools/registry.py",
        "psglab/tools/base.py",
    ),
    "test_occupancy.py": ("psglab/tools/occupancy.py",),
    # `information_txt.py` y `statistics.py` estuvieron fuera de esta fila hasta
    # el hito 5, porque `test_exporters.py` no los importaba y declararlos
    # cubiertos contaba 9 stubs como verificados mientras nadie exigía un test
    # para ellos. Entraron cuando el archivo pasó a cubrirlos de verdad, que es
    # lo que `test_la_tabla_de_cobertura_declara_lo_que_el_test_importa` exige.
    # `test_entrega.py` no cubre un módulo: recorre el camino completo del
    # usuario por `MainWindow`. Se le declaran los módulos que ejercita de
    # punta a punta, que son los que dejarían de estar verificados si el
    # archivo se apagara.
    "test_overview_panel.py": ("psglab/ui/overview_panel.py",),
    "test_psd.py": ("psglab/analysis/psd.py",),
    "test_psd_panel.py": ("psglab/ui/psd_panel.py",),
    "test_derivation.py": ("psglab/analysis/derivation.py",),
    "test_reference.py": ("psglab/analysis/reference.py",),
    "test_mne_bridge.py": ("psglab/analysis/mne_bridge.py",),
    "test_entrega.py": (
        "psglab/app.py",
        "psglab/ui/main_window.py",
    ),
    "test_exporters.py": (
        "psglab/exporters/scoring_txt.py",
        "psglab/exporters/annotations_txt.py",
        "psglab/exporters/statistics.py",
        "psglab/exporters/information_txt.py",
    ),
    # `test_contratos.py` cruza todos los módulos implementados: no cubre uno
    # solo, verifica una promesa transversal —que nada escape del `except` de la
    # interfaz— así que no le corresponde una fila de cobertura por módulo.
    "test_contratos.py": (),
    # `test_consistencia.py` no cubre ningún módulo: testea el repositorio.
}


# -- Utilidades compartidas -------------------------------------------------


def modulos_del_paquete() -> list[pathlib.Path]:
    """Todos los `.py` de `psglab/`, sin los `__init__.py`."""
    return sorted(
        f for f in (RAIZ / "psglab").rglob("*.py") if f.name != "__init__.py"
    )


def ruta_relativa(archivo: pathlib.Path) -> str:
    """Ruta con barras normales, como se la escribe en la documentación."""
    return archivo.relative_to(RAIZ).as_posix()


def contar_stubs(archivo: pathlib.Path) -> int:
    """Cantidad de `raise NotImplementedError` de un archivo.

    Se cuenta sobre el árbol de sintaxis y no sobre el texto: un comentario o un
    docstring que mencione la frase —`tools/registry.py` explica por qué **no**
    eleva `NotImplementedError`— inflaría el conteo y haría fallar el chequeo de
    cuentas del TODO por un motivo que no es el real.
    """
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    return sum(
        1
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Raise) and _nombre_de_excepcion(nodo) == "NotImplementedError"
    )


def _nombre_de_excepcion(nodo: ast.Raise) -> str:
    """Nombre de la excepción que eleva un `raise`, con o sin argumentos."""
    excepcion = nodo.exc
    if isinstance(excepcion, ast.Call):
        excepcion = excepcion.func
    return excepcion.id if isinstance(excepcion, ast.Name) else ""


def stubs_pendientes() -> int:
    """Todos los stubs del paquete, de la Parte 1 y de la Parte 2.

    **Antes excluía `analysis/`**, y era deliberado: la Parte 2 estaba fuera del
    TODO, así que contarla habría hecho fallar la comparación contra un
    documento que no la nombraba. Cerrada la Parte 1, el TODO pasa a ser la cola
    de la Parte 2 y ese filtro dejaba sin control justo lo único que falta.
    """
    return sum(contar_stubs(f) for f in modulos_del_paquete())


def docstring_de(archivo: pathlib.Path) -> str:
    """Docstring de módulo, o cadena vacía si no tiene."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    return ast.get_docstring(arbol) or ""


def ids_declarados(archivo: pathlib.Path) -> set[str]:
    """IDs del pliego que el módulo dice cubrir en su docstring."""
    bloque = re.search(
        r"Cubre del pliego:(.+?)(?:\n\n|$)", docstring_de(archivo), re.S
    )
    return set(re.findall(r"V\d+_[PF]", bloque.group(1))) if bloque else set()


def ids_de_la_trazabilidad() -> dict[str, set[str]]:
    """IDs que `TRAZABILIDAD.md` le asigna a cada archivo.

    Contempla las dos tablas, que no tienen la misma forma: la de la Parte 1
    arranca con el ID y la de la Parte 2 lo lleva en la segunda columna, después
    de la sección.
    """
    texto = (RAIZ / "docs" / "TRAZABILIDAD.md").read_text(encoding="utf-8")
    asignados: dict[str, set[str]] = {}
    patrones = (
        r"^\|\s*(V\d+_[PF])\s*\|[^|]*\|([^|]*)\|",           # Parte 1
        r"^\|[^|]*\|\s*(V\d+_[PF])\s*\|[^|]*\|([^|]*)\|",    # Parte 2
    )
    for patron in patrones:
        for fila in re.finditer(patron, texto, re.M):
            for archivo in re.findall(r"`(psglab/[^`]+\.py)`", fila.group(2)):
                asignados.setdefault(archivo, set()).add(fila.group(1))
    return asignados


def archivos_markdown() -> list[pathlib.Path]:
    """Todos los `.md` versionados del repositorio.

    Se excluye cualquier directorio que empiece con un punto y los que genera
    una corrida: `.pytest_cache/README.md` lo escribe pytest y está en el
    `.gitignore`, pero se colaba en el chequeo de enlaces y podía poner en rojo
    el CI del proyecto por un archivo que no es del proyecto.
    """
    generados = {"build", "dist", "htmlcov", "venv", "env", "node_modules"}
    return sorted(
        p
        for p in RAIZ.rglob("*.md")
        if not any(parte.startswith(".") or parte in generados for parte in p.parts)
    )


def documentos_versionados() -> list[pathlib.Path]:
    """Los `.md` **y `docs/EXPLICACION.txt`**, que es documentación igual.

    Estaba afuera de todos los chequeos de prosa por ser un `.txt`, y la
    segunda auditoría lo encontró siendo el **último sobreviviente** de la
    afirmación de que el programa no abría: la misma frase se corrigió en
    `CLAUDE.md` y en el `README.md` dos veces, y acá siguió intacta. Es, además,
    el documento escrito para el cliente.
    """
    return [*archivos_markdown(), RAIZ / "docs" / "EXPLICACION.txt"]


def sin_acentos(texto: str) -> str:
    """El texto en minúsculas y sin tildes ni diéresis.

    `EXPLICACION.txt` se escribe en ASCII a propósito —hay un chequeo que lo
    exige—, así que buscarle "ambigüedad abierta" con diéresis no podía
    encontrar nada nunca. Comparar normalizado es lo que hace que incluirlo
    sirva de algo.
    """
    return "".join(
        c
        for c in unicodedata.normalize("NFD", texto.lower())
        if unicodedata.category(c) != "Mn"
    )


def existe_respetando_mayusculas(destino: pathlib.Path) -> bool:
    """Si el archivo existe **con exactamente esa caja** en el nombre.

    `Path.exists()` no alcanza: en Windows y macOS el sistema de archivos no
    distingue mayúsculas, así que un enlace a `TODO.md` escrito `todo.md` pasa
    en la máquina de quien lo escribió y falla en el `ubuntu-latest` del CI.
    Comparar contra la entrada real del directorio da el mismo resultado en los
    tres sistemas.
    """
    if not destino.exists():
        return False
    actual = destino
    while actual != RAIZ and actual.parent != actual:
        if actual.name not in {hijo.name for hijo in actual.parent.iterdir()}:
            return False
        actual = actual.parent
    return True


def ancla(titulo: str) -> str:
    """Ancla que genera GitHub para un encabezado."""
    limpio = re.sub(r"[^\w\s-]", "", titulo.strip().lower(), flags=re.UNICODE)
    return re.sub(r"\s+", "-", limpio)


# -- Cuentas del TODO -------------------------------------------------------


def test_las_cuentas_del_todo_coinciden_con_el_codigo():
    """Los stubs que declara el TODO tienen que ser los que hay.

    Se comparan tres fuentes que se escriben por separado y tienen que decir lo
    mismo: la suma de los ítems, la tabla de progreso y el código. Si alguien
    implementa un módulo y no actualiza el TODO, la diferencia salta acá.
    """
    todo = (RAIZ / "docs" / "TODO.md").read_text(encoding="utf-8")
    en_codigo = stubs_pendientes()

    en_items = sum(int(n) for n in re.findall(r"·\s*(\d+) stubs?", todo))
    assert en_items == en_codigo, (
        f"los ítems del TODO suman {en_items} stubs y en el código hay {en_codigo}"
    )

    # **`\d+` y no `\d`.** Con un solo dígito, la fila de un hito 10 no
    # matcheaba y sus stubs desaparecían de la suma **en silencio**, que es peor
    # que fallar: la tabla decía una cosa y el chequeo comparaba otra.
    filas = re.findall(
        r"\|\s*\[(\d+)\.([^\]]*)\]\([^)]*\)\s*\|\s*[\d—-]+\s*\|\s*(\d+)\s*\|", todo
    )
    en_filas = sum(int(fila[2]) for fila in filas)
    assert en_filas == en_codigo, (
        f"las filas de la tabla suman {en_filas} stubs y en el código hay {en_codigo}"
    )

    # La fila de totales se escribe a mano y aparte de las de cada hito, así que
    # puede quedar vieja cuando las otras se actualizan. Verificarla no es
    # redundante: es la que más se lee y la que nadie recalcula.
    total = re.search(r"\|\s*\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*(\d+)\*\*\s*\|", todo)
    assert total is not None, "no se encontró la fila de totales de la tabla de progreso"
    modulos_declarados, stubs_declarados = int(total.group(1)), int(total.group(2))
    modulos_reales = sum(1 for f in modulos_del_paquete() if contar_stubs(f) > 0)
    assert stubs_declarados == en_codigo, (
        f"la fila de totales dice {stubs_declarados} stubs y en el código hay {en_codigo}"
    )
    assert modulos_declarados == modulos_reales, (
        f"la fila de totales dice {modulos_declarados} módulos y hay {modulos_reales}"
    )

    # El texto de arriba del documento repite el número: si se actualiza la
    # tabla y no el párrafo, el primero que lo lea se lleva el dato viejo.
    parrafo = re.search(r"Quedan \*\*(\d+) stubs\*\*.*?en (\d+) módulos", todo, re.S)
    assert parrafo is not None, "no se encontró el resumen de stubs al principio del TODO"
    assert int(parrafo.group(1)) == en_codigo, (
        f"el resumen dice {parrafo.group(1)} stubs y en el código hay {en_codigo}"
    )
    assert int(parrafo.group(2)) == modulos_reales, (
        f"el resumen dice {parrafo.group(2)} módulos y hay {modulos_reales}"
    )


def test_las_cuentas_de_los_readme_de_carpeta_coinciden_con_el_codigo():
    """Cada carpeta lleva su propia cuenta de stubs, y ninguna se verificaba.

    El chequeo de arriba compara `TODO.md` contra el código, pero los siete
    README de carpeta tienen su línea "Pendientes **N stubs**" escrita a mano.
    Se desincronizaron dos veces en una sola tanda de trabajo.

    Se verifica también **la cantidad de módulos** que declara la misma frase,
    porque verificar sólo los stubs no alcanzó: durante el hito 1, cuatro commits
    seguidos reescribieron esa línea de `psglab/README.md` actualizando el número
    de stubs y ninguno tocó el de módulos, que quedó cuatro commits en 29 cuando
    ya eran 26. El chequeo miraba justo la mitad de la frase que sí cambiaba.
    """
    problemas: list[str] = []
    for readme in sorted((RAIZ / "psglab").rglob("README.md")):
        texto = readme.read_text(encoding="utf-8")
        declarado = re.search(r"Pendientes \*\*(\d+) stubs?\*\*", texto)
        if declarado is None:
            # Antes esto era un `continue`, y ahí estaba el agujero: borrar o
            # reformular la línea —"Tiene 26 stubs", que es lo que decía
            # `analysis/README.md`— sacaba esa carpeta del control sin que nada
            # avisara. Justo la carpeta con más stubs pendientes.
            problemas.append(
                f"{ruta_relativa(readme)} no declara sus stubs con la frase que el "
                "chequeo reconoce: 'Pendientes **N stubs**'"
            )
            continue
        # El README de la raíz del paquete cuenta la **Parte 1**, así que deja
        # afuera `analysis/`, que es la Parte 2. Los de cada carpeta cuentan su
        # propia carpeta.
        es_raiz = readme.parent == RAIZ / "psglab"
        propios = [
            f
            for f in readme.parent.rglob("*.py")
            if f.name != "__init__.py" and not (es_raiz and "analysis" in f.parts)
        ]
        real = sum(contar_stubs(f) for f in propios)
        if int(declarado.group(1)) != real:
            problemas.append(
                f"{ruta_relativa(readme)} dice {declarado.group(1)} stubs y en la carpeta hay {real}"
            )

        modulos = re.search(r"Pendientes \*\*\d+ stubs?\*\* en (\d+) módulos", texto)
        if modulos is not None:
            con_stubs = sum(1 for f in propios if contar_stubs(f) > 0)
            if int(modulos.group(1)) != con_stubs:
                problemas.append(
                    f"{ruta_relativa(readme)} dice {modulos.group(1)} módulos con stubs "
                    f"y hay {con_stubs}"
                )
    assert not problemas, "\n".join(problemas)


def test_lo_que_tests_readme_dice_de_la_suite_es_cierto():
    """`tests/README.md` describe la suite y **nada lo verificaba**.

    El chequeo de arriba sólo entra a `psglab/`, así que este archivo quedaba
    fuera de todo control. Sobrevivieron cinco afirmaciones falsas a la vez:
    decía que había seis archivos de test cuando eran nueve, que cuatro llevaban
    `pytestmark` cuando eran tres, mandaba crear tests que ya existían y
    reactivar uno ya reactivado.

    Se verifican las dos cantidades que se pueden contar. El resto de la prosa
    sigue sin auditarse, pero éstas son las que envejecen en cada hito.
    """
    texto = (RAIZ / "tests" / "README.md").read_text(encoding="utf-8")
    archivos = sorted((RAIZ / "tests").glob("test_*.py"))
    desactivados = [p for p in archivos if esta_desactivado(p)]

    problemas: list[str] = []

    # "la recolección falla en los ocho archivos que importan psglab": el número
    # va en palabras y puede quedar partido por un salto de línea.
    # **Varias palabras, no una.** En español los números a partir de treinta
    # y uno se escriben separados, y con `\w+` la frase dejaba de matchear
    # al pasar de treinta archivos de test: el chequeo se caía con un
    # mensaje sobre la frase que faltaba, y la frase estaba.
    cantidad = re.search(r"en los\s+([a-záéíóúñ]+(?:\s+[a-záéíóúñ]+)*?)\s+archivos", texto)
    if cantidad is None:
        problemas.append("tests/README.md ya no dice en cuántos archivos falla la recolección")
    else:
        con_import = sum(1 for p in archivos if importa_psglab_al_cargarse(p))
        if NUMEROS_EN_PALABRAS.get(cantidad.group(1)) != con_import:
            problemas.append(
                f"tests/README.md dice '{cantidad.group(1)}' archivos y son {con_import}"
            )

    # Cada archivo de test tiene que tener **su fila en la tabla**, no una
    # mención cualquiera: buscar la subcadena en el archivo entero daba verde
    # aunque la fila no existiera, porque el nombre aparece en el ejemplo de
    # `python -m pytest tests/test_scoring.py` de la primera sección.
    # **Lista y no conjunto.** Comparando conjuntos, una fila repetida es
    # invisible: la segunda auditoría encontró `test_occupancy.py` dos veces,
    # con descripciones distintas, y borrar la repetida no movió la suite.
    filas = [
        nombre
        for linea in texto.splitlines()
        if linea.lstrip().startswith("|")
        for nombre in re.findall(r"`(test_\w+\.py)`", linea)
    ]
    repetidas = sorted({n for n in filas if filas.count(n) > 1})
    if repetidas:
        problemas.append(f"tests/README.md repite filas en su tabla: {repetidas}")
    en_la_tabla = set(filas)
    for archivo in archivos:
        if archivo.name not in en_la_tabla:
            problemas.append(f"tests/README.md no lista {archivo.name} en su tabla")
    sobrantes = en_la_tabla - {a.name for a in archivos}
    if sobrantes:
        problemas.append(f"tests/README.md lista archivos que ya no existen: {sorted(sobrantes)}")

    declarados = re.search(r"La llevan \*\*[^*]+\*\*:([^.]*)\.", texto)
    if declarados is None:
        problemas.append("tests/README.md ya no dice qué tests están desactivados")
    else:
        nombrados = {f"{n}.py" for n in re.findall(r"`(test_\w+)`", declarados.group(1))}
        reales = {p.name for p in desactivados}
        if nombrados != reales:
            problemas.append(
                f"tests/README.md dice que están desactivados {sorted(nombrados)} "
                f"y los desactivados son {sorted(reales)}"
            )

    assert not problemas, "\n".join(problemas)


# -- Trazabilidad -----------------------------------------------------------


def test_cada_modulo_declara_que_ids_del_pliego_cubre():
    """Es la línea que alimenta `TRAZABILIDAD.md`.

    Los módulos de infraestructura también la llevan, diciendo explícitamente
    que no cubren ningún ID y por qué. Sin eso no hay forma de distinguir "no
    cubre nada" de "alguien se olvidó".
    """
    sin_linea = [
        ruta_relativa(f) for f in modulos_del_paquete() if "Cubre del pliego" not in docstring_de(f)
    ]
    assert not sin_linea, f"módulos sin 'Cubre del pliego': {sin_linea}"


def test_los_paquetes_y_el_punto_de_entrada_tambien_la_llevan():
    """`psglab/README.md` la exige a "cada módulo", sin excepciones.

    El chequeo de arriba no los alcanza porque `modulos_del_paquete()` excluye
    los `__init__.py` y no sale de `psglab/`, y esa función no se puede tocar:
    es la que alimenta todas las cuentas de stubs del TODO. Va aparte.

    `main.py` es el caso que más llamaba la atención: es el único archivo
    ejecutable del proyecto y ningún chequeo del repositorio lo miraba.
    """
    archivos = [RAIZ / "main.py", *sorted((RAIZ / "psglab").rglob("__init__.py"))]
    sin_linea = [
        ruta_relativa(f) for f in archivos if "Cubre del pliego" not in docstring_de(f)
    ]
    assert not sin_linea, f"archivos sin 'Cubre del pliego': {sin_linea}"


def test_cada_modulo_aparece_en_la_trazabilidad():
    """La tabla sirve para la pregunta inversa: qué se rompe si toco este archivo.

    Un módulo que no figura en ninguna fila no se puede responder. Se exige que
    la mención esté **dentro de una fila de tabla** y no en cualquier parte del
    documento: nombrado al pasar en un párrafo, el archivo no queda trazado y el
    chequeo daría verde igual.
    """
    texto = (RAIZ / "docs" / "TRAZABILIDAD.md").read_text(encoding="utf-8")
    citados: set[str] = set()
    for linea in texto.splitlines():
        if linea.lstrip().startswith("|"):
            citados.update(re.findall(r"`(psglab/[^`]+\.py)`", linea))
    ausentes = [ruta_relativa(f) for f in modulos_del_paquete() if ruta_relativa(f) not in citados]
    assert not ausentes, f"módulos sin fila en TRAZABILIDAD.md: {ausentes}"


def test_los_ids_coinciden_en_las_dos_direcciones():
    """Docstring y tabla tienen que decir lo mismo, mirado desde los dos lados.

    Verificar una sola dirección no alcanza, y no es una hipótesis: el chequeo
    manual que se usaba antes sólo miraba docstring -> tabla, y por eso informó
    en verde dos divergencias reales que la tabla asignaba y el docstring no
    declaraba.
    """
    asignados = ids_de_la_trazabilidad()
    problemas: list[str] = []
    for archivo in modulos_del_paquete():
        declara = ids_declarados(archivo)
        asigna = asignados.get(ruta_relativa(archivo), set())
        if declara - asigna:
            problemas.append(
                f"{ruta_relativa(archivo)} declara {sorted(declara - asigna)} y la tabla no se los asigna"
            )
        if asigna - declara:
            problemas.append(
                f"{ruta_relativa(archivo)} no declara {sorted(asigna - declara)}, que la tabla sí le asigna"
            )
    assert not problemas, "\n".join(problemas)


def modulos_declarados_sin_ids() -> set[str]:
    """Archivos que `TRAZABILIDAD.md` declara **a propósito** sin ningún ID.

    Son de dos clases: los de la tabla de módulos de infraestructura, y los de
    la Parte 2 cuya fila lleva `—` en la columna de ID porque el pliego no los
    numera.
    """
    texto = (RAIZ / "docs" / "TRAZABILIDAD.md").read_text(encoding="utf-8")
    declarados: set[str] = set()

    infraestructura = texto.partition("## Módulos de infraestructura")[2]
    for linea in infraestructura.splitlines():
        if linea.lstrip().startswith("|"):
            declarados.update(re.findall(r"`(psglab/[^`]+\.py)`", linea))

    for linea in texto.splitlines():
        if re.match(r"^\|[^|]*\|\s*—\s*\|", linea):
            declarados.update(re.findall(r"`(psglab/[^`]+\.py)`", linea))

    return declarados


def test_un_modulo_sin_ids_esta_declarado_como_infraestructura():
    """Distingue "no cubre ningún ID, a propósito" de "alguien se olvidó".

    El chequeo anterior compara los IDs del docstring contra los de la tabla, y
    si los dos lados están vacíos no tiene nada que comparar. Antes eso se
    resolvía salteando esos módulos, y el salteo terminó tapando una divergencia
    real: `config.py` nombraba tres IDs en la misma frase en la que decía no
    cubrir ninguno, y como la tabla no le asignaba nada, quedaba exento.

    En vez de saltear, se exige que la ausencia esté **declarada** en
    `TRAZABILIDAD.md`, que es el documento que ya codifica la respuesta.
    """
    asignados = ids_de_la_trazabilidad()
    declarados = modulos_declarados_sin_ids()
    huerfanos = [
        ruta_relativa(f)
        for f in modulos_del_paquete()
        if not asignados.get(ruta_relativa(f)) and ruta_relativa(f) not in declarados
    ]
    assert not huerfanos, (
        "estos módulos no tienen ningún ID asignado y tampoco están declarados como "
        f"infraestructura ni como fila sin ID de la Parte 2: {huerfanos}"
    )


# -- Documentación ----------------------------------------------------------


def test_ningun_enlace_de_la_documentacion_apunta_a_la_nada():
    """Incluidas las anclas dentro de un archivo, que son las que más se rompen.

    Renombrar un encabezado no rompe nada visible hasta que alguien hace clic.
    """
    archivos = archivos_markdown()
    anclas = {
        p: {ancla(t) for t in re.findall(r"^#{1,6}\s+(.*)$", p.read_text(encoding="utf-8"), re.M)}
        for p in archivos
    }
    rotos: list[str] = []
    for md in archivos:
        for destino in re.findall(r"\]\(([^)]+)\)", md.read_text(encoding="utf-8")):
            if destino.startswith(("http://", "https://", "mailto:")):
                continue
            ruta, _, anc = destino.partition("#")
            objetivo = (md.parent / ruta).resolve() if ruta else md.resolve()
            if not existe_respetando_mayusculas(objetivo):
                rotos.append(f"{ruta_relativa(md)} -> {destino} (no existe el archivo)")
                continue
            destino_md = next((p for p in archivos if p.resolve() == objetivo), None)
            if anc and destino_md is not None and anc not in anclas[destino_md]:
                rotos.append(f"{ruta_relativa(md)} -> {destino} (no existe el ancla)")
    assert not rotos, "\n".join(rotos)


def test_la_explicacion_se_mantiene_en_ascii():
    """`EXPLICACION.txt` se escribe sin acentos a propósito.

    El propio archivo lo dice: es para que se lea igual en cualquier sistema
    operativo y con cualquier editor. Un acento que se cuela al editarlo rompe
    esa promesa sin que nadie lo note.
    """
    texto = (RAIZ / "docs" / "EXPLICACION.txt").read_text(encoding="utf-8")
    culpables = [
        (numero, linea)
        for numero, linea in enumerate(texto.splitlines(), 1)
        if any(ord(c) > 127 for c in unicodedata.normalize("NFD", linea))
    ]
    assert not culpables, f"líneas con caracteres no ASCII: {culpables[:5]}"


#: Valor de cada constante del pliego, tal como lo escribiría alguien a mano en
#: un texto para el usuario. Si un módulo importa la constante y además escribe
#: el número al lado, el día que la constante cambie el texto va a mentir.
CONSTANTES_DEL_PLIEGO: dict[str, tuple[str, ...]] = {
    "WINDOW_SECONDS": ("30 s", "30 segundos"),
    "COARSE_GRID_SECONDS": ("3 s", "3 segundos"),
    "FINE_GRID_SECONDS": ("0,5 s", "0,5 segundos"),
    "AMPLITUDE_BAND_UV": ("75 µV", "75µV", "75 uV"),
}


def literales_visibles(archivo: pathlib.Path) -> list[tuple[int, str]]:
    """Cadenas del módulo que **no** son docstrings.

    La distinción es la que hace útil al chequeo: los docstrings explican el
    pliego y nombran sus números a propósito —es documentación, y está bien—,
    mientras que una cadena asignada a un atributo termina en la pantalla del
    investigador.
    """
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            primero = nodo.body[0] if nodo.body else None
            if isinstance(primero, ast.Expr) and isinstance(primero.value, ast.Constant):
                if isinstance(primero.value.value, str):
                    docstrings.add(id(primero.value))
    return [
        (nodo.lineno, nodo.value)
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Constant)
        and isinstance(nodo.value, str)
        and id(nodo) not in docstrings
    ]


def test_las_constantes_del_pliego_no_se_escriben_a_mano():
    """`config.py` es el punto único de verdad, y lo era a medias.

    Tres textos que ve el usuario repetían el número al lado de la constante,
    en archivos que ya la importaban: la banda decía "75 µV" y los fondos de la
    grilla decían "3 segundos" y "0,5 segundos". Cambiar `config.py` los dejaba
    mintiendo, que es peor que no tener la constante.

    Sólo se miran las cadenas que no son docstrings: un docstring que explique
    el pliego nombra sus números a propósito.
    """
    problemas: list[str] = []
    for archivo in modulos_del_paquete():
        importadas = {
            nombre
            for _, modulo in modulos_importados(archivo)
            if modulo == "psglab.config"
            for nombre in CONSTANTES_DEL_PLIEGO
            if nombre in archivo.read_text(encoding="utf-8")
        }
        if not importadas:
            continue
        for linea, texto in literales_visibles(archivo):
            for constante in importadas:
                for escritura in CONSTANTES_DEL_PLIEGO[constante]:
                    if escritura in texto:
                        problemas.append(
                            f"{ruta_relativa(archivo)}:{linea} escribe {escritura!r} a mano "
                            f"pudiendo derivarlo de config.{constante}"
                        )
    assert not problemas, "\n".join(problemas)


def test_la_marca_de_pendiente_que_citan_los_documentos_existe_en_el_codigo():
    """Tres documentos citaban textualmente una marca que el código no usaba.

    Decían `PENDIENTE DE CONFIRMACIÓN`; en el código dice `PENDIENTE DE
    DEFINICIÓN CON EL CLIENTE`. Nadie lo notó porque el comando que proponían
    buscaba sólo el prefijo `PENDIENTE DE` y encontraba la marca igual, pero
    buscar la frase prometida no devolvía nada.
    """
    codigo = " ".join(
        " ".join(f.read_text(encoding="utf-8").split()) for f in modulos_del_paquete()
    )
    faltantes: list[str] = []
    for md in documentos_versionados():
        if md.name.startswith("AUDITORIA"):
            continue  # Son fotos fechadas: citan a propósito lo que estaba mal.
        for marca in re.findall(r"`(PENDIENTE DE [^`]+)`", md.read_text(encoding="utf-8")):
            # La marca puede venir partida en dos líneas por el ancho del
            # párrafo, así que se compara sin los saltos.
            if " ".join(marca.split()) not in codigo:
                faltantes.append(
                    f"{ruta_relativa(md)} cita la marca {' '.join(marca.split())!r}, "
                    "que no está en el código"
                )
    assert not faltantes, "\n".join(faltantes)


def test_una_ambiguedad_declarada_abierta_lo_esta_de_verdad():
    """La deriva concreta que produjo el cierre del hito 0.

    El cliente respondió las ocho preguntas abiertas, la noticia llegó a
    `config.py` y al TODO, y siete README de carpeta siguieron pidiendo
    confirmar lo que ya estaba confirmado.

    La regla no es prohibir la frase —hay una ambigüedad realmente abierta, la
    de las impedancias— sino exigir que quien la use **nombre el módulo que la
    espera**, y que ese módulo lleve de verdad la marca `PENDIENTE DE`. Una
    ambigüedad que ya se cerró no tiene ningún módulo así al que apuntar.

    `TODO.md` queda exento porque es el documento que lleva el estado, y
    `AUDITORIA.md` porque es una foto de lo que estaba mal.
    """
    con_marca = {
        ruta_relativa(f)
        for f in modulos_del_paquete()
        if "PENDIENTE DE" in docstring_de(f)
    }
    prohibidas = ("ambiguedad abierta", "ambiguedades abiertas", "hasta que el cliente confirme")
    apariciones: list[str] = []
    for md in documentos_versionados():
        if md.name == "TODO.md" or md.name.startswith("AUDITORIA"):
            continue
        texto = md.read_text(encoding="utf-8")
        if not any(frase in sin_acentos(texto) for frase in prohibidas):
            continue
        nombrados = {f"psglab/{m}" for m in re.findall(r"`(\w+\.py)`", texto)}
        nombrados.update(re.findall(r"`(psglab/[^`]+\.py)`", texto))
        if not any(any(m.endswith(c.split("/")[-1]) for m in nombrados) for c in con_marca):
            apariciones.append(
                f"{ruta_relativa(md)} declara una ambigüedad abierta pero no nombra "
                f"ningún módulo con la marca PENDIENTE DE (los que la tienen: {sorted(con_marca)})"
            )
    assert not apariciones, (
        "las ambigüedades del pliego se cerraron con el cliente el 4 de septiembre de "
        "2026, salvo la de las impedancias; el estado vive en docs/TODO.md, hito 0:\n"
        + "\n".join(apariciones)
    )


def test_ningun_documento_repite_un_parrafo():
    """Un párrafo copiado dentro del mismo archivo es una desincronización futura.

    Cuando alguien corrija uno de los dos, el otro queda diciendo lo viejo. Pasó
    en `ui/README.md`, que explicaba dos veces por qué la capa no lleva tests.

    Se miran sólo los párrafos largos: los títulos de tabla y las frases cortas
    se repiten con toda razón.
    """
    repetidos: list[str] = []
    for md in documentos_versionados():
        vistos: dict[str, int] = {}
        for bloque in re.split(r"\n\s*\n", md.read_text(encoding="utf-8")):
            normalizado = " ".join(bloque.split())
            if len(normalizado) < 200 or normalizado.startswith(("|", "```")):
                continue
            vistos[normalizado] = vistos.get(normalizado, 0) + 1
        for texto, veces in vistos.items():
            if veces > 1:
                repetidos.append(f"{ruta_relativa(md)} repite {veces} veces: {texto[:70]}...")
    assert not repetidos, "\n".join(repetidos)


def test_los_requirements_que_nombra_la_documentacion_existen():
    """Al separar las dependencias de la Parte 2 en su propio archivo, los que
    lo nombran mal no fallan hasta que alguien copia el comando y no funciona.
    """
    nombrados: set[str] = set()
    for documento in [*archivos_markdown(), RAIZ / "docs" / "EXPLICACION.txt"]:
        nombrados.update(
            re.findall(r"(requirements[\w-]*\.txt)", documento.read_text(encoding="utf-8"))
        )
    inexistentes = sorted(n for n in nombrados if not (RAIZ / n).exists())
    assert not inexistentes, f"la documentación nombra requirements que no existen: {inexistentes}"


# -- Reglas de arquitectura -------------------------------------------------


#: Capas que tienen que poder correr sin interfaz gráfica. `core` y `utils`
#: sostienen el modelo; `readers` y `exporters` están acá porque de ellos
#: depende el corte del hito 5: leer un registro, scorearlo y exportar los tres
#: archivos desde un script, sin abrir una ventana.
#:
#: **`tools` y `analysis` entraron en el hito 10.** Las dos declaran no conocer
#: la interfaz —`tools/base.py` explica que por eso `Tool` no hereda de
#: `QObject`, y `analysis/README.md` lo pone como su regla 2— y ninguna de las
#: dos lo tenía verificado: la regla estaba escrita en tres documentos y no la
#: miraba nadie. Lo anotó la segunda auditoría como hueco mediano.
CAPAS_SIN_INTERFAZ = ("core", "utils", "readers", "exporters", "tools", "analysis")


def modulos_importados(archivo: pathlib.Path) -> list[tuple[int, str]]:
    """Todo lo que importa un archivo, en las dos formas de la sintaxis.

    Mirar sólo `ast.ImportFrom` dejaba pasar `import pyqtgraph as pg`, que es
    exactamente cómo lo importan los módulos de `ui/`: la regla más importante
    del proyecto se podía violar con la forma de import más común.
    """
    importados: list[tuple[int, str]] = []
    for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.append((nodo.lineno, nodo.module))
        elif isinstance(nodo, ast.Import):
            importados.extend((nodo.lineno, alias.name) for alias in nodo.names)
    return importados


def test_las_capas_de_negocio_no_conocen_la_interfaz():
    """Es la regla que sostiene todo lo demás.

    Si `core/` importara Qt, el modelo dejaría de poder testearse sin abrir una
    ventana y el testeo recurrente que pide el pliego se volvería inviable.

    Se recorre la ruta entera y no sólo el directorio padre, para que un
    subpaquete futuro —`core/algo/x.py`— quede cubierto igual.
    """
    prohibidos = ("psglab.ui", "PySide6", "pyqtgraph")
    violaciones: list[str] = []
    for archivo in modulos_del_paquete():
        if not any(capa in archivo.parts for capa in CAPAS_SIN_INTERFAZ):
            continue
        for linea, modulo in modulos_importados(archivo):
            if any(modulo == p or modulo.startswith(p + ".") for p in prohibidos):
                violaciones.append(f"{ruta_relativa(archivo)}:{linea} importa {modulo}")
    assert not violaciones, "\n".join(violaciones)


def argumentos_de(nodo: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.arg]:
    """Todos los argumentos de una firma, de las cinco clases que hay.

    Mirar sólo `args` dejaba afuera los posicionales puros, los que van después
    de `*`, y `*args` / `**opciones`: una firma como
    `def f(*, umbral, **opciones) -> None` pasaba el chequeo con cero
    anotaciones. Como éste es el único sustituto de un verificador de tipos que
    tiene el proyecto, el hueco importaba.
    """
    firma = nodo.args
    opcionales = [a for a in (firma.vararg, firma.kwarg) if a is not None]
    return [*firma.posonlyargs, *firma.args, *firma.kwonlyargs, *opcionales]


def test_todas_las_firmas_llevan_type_hints():
    """Convención del proyecto: documentan el contrato y no se desactualizan."""
    faltantes: list[str] = []
    for archivo in modulos_del_paquete():
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for argumento in argumentos_de(nodo):
                if argumento.arg not in ("self", "cls") and argumento.annotation is None:
                    faltantes.append(
                        f"{ruta_relativa(archivo)}:{nodo.lineno} {nodo.name}({argumento.arg})"
                    )
            if nodo.returns is None:
                faltantes.append(f"{ruta_relativa(archivo)}:{nodo.lineno} {nodo.name}() sin retorno")
    assert not faltantes, "\n".join(faltantes)


# -- El verde por omisión ---------------------------------------------------


def importa_psglab_al_cargarse(archivo_test: pathlib.Path) -> bool:
    """Si el archivo importa `psglab` a nivel de módulo.

    Son los que fallan al recolectar con `pytest` a secas.
    `test_consistencia.py` no está entre ellos: lo importa dentro de una función.
    """
    arbol = ast.parse(archivo_test.read_text(encoding="utf-8"))
    for nodo in arbol.body:
        if isinstance(nodo, ast.ImportFrom) and (nodo.module or "").startswith("psglab"):
            return True
        if isinstance(nodo, ast.Import) and any(a.name.startswith("psglab") for a in nodo.names):
            return True
    return False


def esta_desactivado(archivo_test: pathlib.Path) -> bool:
    """Si un archivo de test está apagado entero, de cualquiera de las formas.

    Se mira el árbol de sintaxis y no el texto. Buscar la cadena encontraba la
    palabra hasta en un comentario o en un docstring —este mismo archivo habla
    de `allow_module_level` al explicarlo, y se daba a sí mismo por
    desactivado—, y al revés no distinguía un `pytestmark` de verdad de una
    mención.
    """
    arbol = ast.parse(archivo_test.read_text(encoding="utf-8"))
    for nodo in arbol.body:
        if isinstance(nodo, (ast.Assign, ast.AnnAssign)):
            destinos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
            if any(isinstance(d, ast.Name) and d.id == "pytestmark" for d in destinos):
                return True
        # `pytest.skip("...", allow_module_level=True)` suelto en el módulo.
        if isinstance(nodo, ast.Expr) and isinstance(nodo.value, ast.Call):
            if any(k.arg == "allow_module_level" for k in nodo.value.keywords):
                return True

    # Y la tercera forma, que es **la que el propio mensaje de este chequeo
    # recomienda**: saltear test por test. Sin esto, alguien que siguiera ese
    # consejo sacaba el archivo del control por completo y volvía el verde por
    # omisión que el chequeo existe para combatir. Va a pasar en el hito 5, donde
    # `test_exporters.py` cubre cuatro módulos que no se terminan a la vez.
    funciones = [
        n
        for n in arbol.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_")
    ]
    return bool(funciones) and all(_tiene_skip(f) for f in funciones)


def _tiene_skip(funcion: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Si la función lleva un `@pytest.mark.skip` (con o sin argumentos)."""
    for decorador in funcion.decorator_list:
        nodo = decorador.func if isinstance(decorador, ast.Call) else decorador
        if isinstance(nodo, ast.Attribute) and nodo.attr in ("skip", "skipif"):
            return True
    return False


def test_ningun_modulo_terminado_tiene_su_test_salteado():
    """El modo de falla más silencioso que tiene este repositorio.

    Mientras un módulo es un esqueleto, su test está desactivado con
    `pytestmark = pytest.mark.skip(...)` y la suite pasa en verde sin verificar
    nada. Si alguien lo implementa y se olvida de borrar esa línea, **el trabajo
    queda sin verificar y nada avisa**: `pytest` sigue informando "passed".

    Este test cierra ese agujero. En cuanto un módulo se queda sin stubs, su
    archivo de test tiene que estar activo.
    """
    pendientes: list[str] = []
    for nombre, modulos in COBERTURA_DE_TESTS.items():
        archivo_test = RAIZ / "tests" / nombre
        if not archivo_test.exists():
            continue
        if not esta_desactivado(archivo_test):
            continue
        terminados = [m for m in modulos if contar_stubs(RAIZ / m) == 0]
        if not terminados:
            continue
        if len(terminados) == len(modulos):
            pendientes.append(
                f"tests/{nombre} sigue salteado pero {', '.join(modulos)} ya no tiene stubs: "
                "borrá la desactivación del archivo"
            )
        else:
            pendientes.append(
                f"tests/{nombre} saltea el archivo entero, pero {', '.join(terminados)} ya "
                "no tiene stubs: la desactivación en bloque no sirve para un archivo que "
                "cubre varios módulos a medio terminar. Saltear test por test los que "
                "todavía no se pueden verificar."
            )
    assert not pendientes, "\n".join(pendientes)


#: Módulos de la Parte 1 que **no llevan test propio**, por decisión y no por
#: olvido: los widgets de `psglab/ui/` no se pueden verificar sin mirar una
#: pantalla —está registrado en su README— y `app.py` es su constructor.
#: `config.py` son constantes: no hay comportamiento que testear.
#:
#: **`shortcuts.py`, `grid.py` y `signal_view.py` salieron en el hito 6.** La regla
#: se había fijado con la carpeta vacía; al escribirla se vio que esos dos no
#: dibujan nada —uno deriva teclas de la nomenclatura y el otro calcula
#: posiciones— y que son justo donde algo se rompe en silencio.
SIN_TEST_PROPIO: frozenset[str] = frozenset(
    {
        "psglab/app.py",
        "psglab/config.py",
        "psglab/ui/main_window.py",
        "psglab/ui/navigation.py",
        "psglab/ui/scoring_panel.py",
        "psglab/ui/channel_selector.py",
    }
)


def promesas_de_test_del_todo() -> dict[str, set[str]]:
    """Qué archivo de test promete `TODO.md` para cada módulo.

    Se lee por bloques: cada ítem `- [ ] **psglab/algo.py**` abre uno, y las
    líneas sangradas que le siguen son suyas. Es donde vive la promesa "Test:
    **crear** `tests/test_algo.py`".
    """
    todo = (RAIZ / "docs" / "TODO.md").read_text(encoding="utf-8")
    prometidos: dict[str, set[str]] = {}
    actuales: list[str] = []
    for linea in todo.splitlines():
        modulos = re.findall(r"`(psglab/[^`]+\.py)`", linea)
        if re.match(r"^\s*- \[[ x]\]", linea) and modulos:
            actuales = modulos
        elif re.match(r"^\s*- \[[ x]\]", linea) and not linea.startswith("  "):
            actuales = []
        for modulo in actuales:
            prometidos.setdefault(modulo, set()).update(
                re.findall(r"`tests/(test_\w+\.py)`", linea)
            )
    return prometidos


def test_todo_modulo_tiene_test_o_lo_tiene_prometido():
    """El pliego pide un test por componente. Faltaba verificar el lado inverso.

    Ya estaba verificado que todo archivo de test tuviera su fila en
    `COBERTURA_DE_TESTS`; nadie verificaba que todo módulo tuviera test. Un
    módulo sin test no se notaba de ninguna forma.

    No se exige que el test **exista** —eso sería exigir el proyecto terminado y
    dejaría el CI en rojo durante siete hitos— sino que su ausencia esté
    registrada: o el módulo ya tiene test, o es una excepción declarada, o
    `TODO.md` dice cuál va a ser. El estado sigue viviendo en el TODO, que es
    quien lo posee.
    """
    cubiertos = {m for modulos in COBERTURA_DE_TESTS.values() for m in modulos}
    prometidos = promesas_de_test_del_todo()
    huerfanos = [
        ruta_relativa(f)
        for f in modulos_del_paquete()
        if ruta_relativa(f) not in cubiertos
        and ruta_relativa(f) not in SIN_TEST_PROPIO
        and not prometidos.get(ruta_relativa(f))
    ]
    assert not huerfanos, (
        "estos módulos de la Parte 1 no tienen test, no figuran como excepción en "
        f"SIN_TEST_PROPIO y el TODO no promete ninguno: {huerfanos}"
    )


def test_las_cuentas_de_tests_del_todo_coinciden_con_la_suite(request: pytest.FixtureRequest):
    """Lo que faltaba: se auditaban las cuentas de stubs, no las de tests.

    Por eso `TODO.md` pudo decir "15 tests en verde" cuando eran 17, y
    `tests/README.md` prometer `42 skipped` mucho después de que dejaran de ser
    42. Los números de stubs los verificaba un test y los de tests no.

    No se cuentan los `def test_` del archivo: la suite recolecta más casos que
    funciones, porque hay `parametrize`. Se cuenta lo que pytest recolectó de
    verdad.
    """
    archivos_de_test = {p.name for p in (RAIZ / "tests").glob("test_*.py")}
    recolectados: dict[str, int] = {}
    for item in request.session.items:
        recolectados[pathlib.Path(item.location[0]).name] = (
            recolectados.get(pathlib.Path(item.location[0]).name, 0) + 1
        )

    if set(recolectados) != archivos_de_test:
        pytest.skip(
            "sólo tiene sentido en una corrida completa: `python -m pytest` sin "
            "argumentos, que es la que hace el CI"
        )

    todo = (RAIZ / "docs" / "TODO.md").read_text(encoding="utf-8")
    problemas: list[str] = []
    for nombre, declarados in re.findall(
        r"`tests/(test_\w+\.py)`,?\s*\*\*(\d+) tests? en verde\*\*", todo
    ):
        real = recolectados.get(nombre, 0)
        if int(declarados) != real:
            problemas.append(
                f"TODO.md dice {declarados} tests para tests/{nombre} y la suite recolecta {real}"
            )
    assert not problemas, "\n".join(problemas)


def test_la_tabla_de_cobertura_declara_lo_que_el_test_importa():
    """Declarar un módulo cubierto sin importarlo cuenta stubs como verificados.

    Ya pasó: `test_exporters.py` figuraba cubriendo `information_txt.py` y
    `statistics.py` sin importarlos, y esos 9 stubs quedaban contados como
    testeados mientras nadie exigía un test para ellos. Se corrigió a mano y no
    se dejó ninguna red; ésta es la red.
    """
    problemas: list[str] = []
    for nombre, modulos in COBERTURA_DE_TESTS.items():
        archivo = RAIZ / "tests" / nombre
        if not archivo.exists() or not modulos:
            continue
        importados = {m for _, m in modulos_importados(archivo)}
        for modulo in modulos:
            esperado = modulo.removesuffix(".py").replace("/", ".")
            if not any(i == esperado or i.startswith(esperado + ".") for i in importados):
                problemas.append(
                    f"tests/{nombre} declara cubrir {modulo} y no lo importa"
                )
    assert not problemas, "\n".join(problemas)


def test_la_tabla_de_cobertura_nombra_modulos_que_existen():
    """Si se renombra un módulo, el mapa de arriba tiene que seguirlo.

    Un mapa que apunta a un archivo inexistente haría que el test anterior mire
    para otro lado y deje de proteger nada.
    """
    inexistentes = [
        m for modulos in COBERTURA_DE_TESTS.values() for m in modulos if not (RAIZ / m).exists()
    ]
    assert not inexistentes, f"la tabla de cobertura nombra módulos que no existen: {inexistentes}"


@pytest.mark.parametrize("archivo", sorted(p.name for p in (RAIZ / "tests").glob("test_*.py")))
def test_cada_archivo_de_test_esta_en_la_tabla_de_cobertura(archivo: str):
    """Un test nuevo sin fila en la tabla quedaría fuera del chequeo anterior."""
    conocidos = set(COBERTURA_DE_TESTS) | {"test_consistencia.py"}
    assert archivo in conocidos, (
        f"tests/{archivo} no figura en COBERTURA_DE_TESTS: agregá su fila para que "
        "el chequeo de tests salteados lo cubra"
    )

# -- Contratos de error -----------------------------------------------------


#: Métodos públicos de `core/` y `utils/` que **no** llevan fila en `CONTRATOS`,
#: con el motivo. No es una lista de pendientes: son decisiones documentadas en
#: el propio módulo, y meterlos en la tabla obligaría a agregarles guardas que
#: esas decisiones descartaron a propósito. Se declaran acá en vez de saltearse
#: en silencio, que es la diferencia entre una excepción y un agujero.
SIN_CONTRATO: dict[str, str] = {
    "psglab/core/windows.py": (
        "su docstring declara las precondiciones: es aritmética pura, no valida sus "
        "argumentos y eleva ZeroDivisionError a propósito con una frecuencia corrupta. "
        "Quien llama ya validó —Session.go_to_window() eleva WindowOutOfRangeError "
        "antes de llegar acá— y repetir la comprobación en el camino caliente, que se "
        "recorre en cada pulsación de flecha, no aporta nada."
    ),
    "psglab/utils/validation.py::clamp": (
        "documenta que un valor no finito es un error de programación y no algo que el "
        "usuario pueda provocar: quien llama tiene que haber pasado antes por "
        "check_finite."
    ),
}


def contratos_declarados() -> dict[str, set[str]]:
    """Qué nombres ejercita cada módulo en la tabla `CONTRATOS`.

    Se lee el árbol de sintaxis de `tests/test_contratos.py` en vez de
    importarlo: lo que interesa es **qué se llama adentro de cada lambda**, no
    el resultado de llamarla.
    """
    arbol = ast.parse((RAIZ / "tests" / "test_contratos.py").read_text(encoding="utf-8"))
    tabla = None
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.AnnAssign) and getattr(nodo.target, "id", "") == "CONTRATOS":
            tabla = nodo.value
    assert isinstance(tabla, ast.Dict), "tests/test_contratos.py ya no define CONTRATOS como dict"

    declarados: dict[str, set[str]] = {}
    for clave, filas in zip(tabla.keys, tabla.values):
        nombres: set[str] = set()
        for hijo in ast.walk(filas):
            if isinstance(hijo, ast.Attribute):
                nombres.add(hijo.attr)
            elif isinstance(hijo, ast.Name):
                nombres.add(hijo.id)
        declarados[clave.value] = nombres
    return declarados


def metodos_que_reciben_algo(archivo: pathlib.Path) -> list[tuple[str, str]]:
    """Métodos públicos del módulo que pueden recibir un valor hostil.

    Devuelve pares (nombre legible, token que la tabla tiene que nombrar). Para
    un `__init__` el token es la clase, porque en la tabla se lo llama
    construyendo: `Scoring(3, v)`.

    Los que no reciben nada quedan afuera: a una propiedad sin argumentos no hay
    con qué atacarla, y exigirle una fila sería ruido.
    """
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    encontrados: list[tuple[str, str]] = []
    for nodo in arbol.body:
        candidatos: list[tuple[str, str, ast.FunctionDef]] = []
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)) and not nodo.name.startswith("_"):
            candidatos = [(nodo.name, nodo.name, nodo)]
        elif isinstance(nodo, ast.ClassDef):
            for hijo in nodo.body:
                if not isinstance(hijo, ast.FunctionDef):
                    continue
                if hijo.name == "__init__":
                    candidatos.append((f"{nodo.name}.__init__", nodo.name, hijo))
                elif not hijo.name.startswith("_"):
                    candidatos.append((f"{nodo.name}.{hijo.name}", hijo.name, hijo))
        for legible, token, funcion in candidatos:
            recibe = [a for a in argumentos_de(funcion) if a.arg not in ("self", "cls")]
            if recibe:
                encontrados.append((legible, token))
    return encontrados


def test_cada_metodo_publico_de_negocio_tiene_su_fila_de_contrato():
    """Lo que el docstring de `test_contratos.py` prometía y nadie verificaba.

    Ese archivo decía que un método público sin fila hace fallar este test,
    "igual que pasa con `COBERTURA_DE_TESTS`". No era cierto: `CONTRATOS` sólo
    aparecía dentro de `test_contratos.py`, y lo único que se comprobaba era que
    las rutas nombradas existieran. La tabla cubría 5 de los 9 módulos
    terminados, y los 34 métodos que faltaban no se notaban de ninguna forma.

    Al escribirlo aparecieron **13 métodos** que dejaban escapar `TypeError`,
    `KeyError` o `AttributeError` crudos —más del doble de los que había
    encontrado a mano la auditoría—, incluido `stage_code`, que alimenta la
    línea de `Scoring.txt`. Dos de ellos, los del constructor de `Session`, no
    los encontró ninguna sonda escrita a mano sino este chequeo.

    Sólo se exige de `core/` y `utils/`, donde vive la regla de negocio.
    `tools/` tiene un test por herramienta, y de `ui/` se testea lo que no
    dibuja.
    """
    declarados = contratos_declarados()
    faltantes: list[str] = []
    for archivo in modulos_del_paquete():
        relativa = ruta_relativa(archivo)
        # **`analysis` entró en el hito 10.** El argumento es el mismo que para
        # `core/`: `MainWindow` atrapa una sola clase, así que un `ValueError`
        # de scipy o de MNE que escape de una función de análisis le llega al
        # investigador como traza. La exigencia aparece módulo por módulo, no de
        # golpe, porque los que todavía tienen stubs se saltean abajo.
        if not any(capa in archivo.parts for capa in ("core", "utils", "analysis")):
            continue
        if contar_stubs(archivo) or relativa in SIN_CONTRATO:
            continue
        cubiertos = declarados.get(relativa, set())
        for legible, token in metodos_que_reciben_algo(archivo):
            if f"{relativa}::{legible.split('.')[-1]}" in SIN_CONTRATO:
                continue
            if token not in cubiertos:
                faltantes.append(f"{relativa}::{legible}")
    assert not faltantes, (
        "estos métodos públicos pueden recibir un valor hostil y no tienen fila en "
        "CONTRATOS de tests/test_contratos.py, así que nada verifica que lo rechacen "
        f"con un PsgLabError: {faltantes}"
    )


def test_las_exenciones_de_contrato_siguen_existiendo():
    """Una exención que apunte a algo borrado tapa un módulo nuevo por accidente.

    **Se valida también el símbolo, no sólo el archivo.** La versión anterior
    cortaba en `::` y miraba nada más el `.py`, así que renombrar `clamp` dejaba
    la exención en pie apuntando a una función que ya no existe: silenciosa,
    y lista para eximir a cualquier cosa que algún día se llamara igual.
    """
    problemas: list[str] = []
    for objetivo in SIN_CONTRATO:
        archivo, _, simbolo = objetivo.partition("::")
        ruta = RAIZ / archivo
        if not existe_respetando_mayusculas(ruta):
            problemas.append(f"{objetivo}: el archivo no existe")
            continue
        if not simbolo:
            continue
        definidos = {
            nodo.name
            for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8")))
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        if simbolo not in definidos:
            problemas.append(f"{objetivo}: {archivo} ya no define {simbolo!r}")
    assert not problemas, "SIN_CONTRATO exime cosas que no existen:\n" + "\n".join(
        problemas
    )


# -- Que el paquete entero se pueda importar --------------------------------


def test_todos_los_modulos_del_paquete_se_pueden_importar():
    """Es lo único que ejercita la capa `ui/`, y por eso lo único que prueba
    que PySide6 funciona en el sistema donde se corre.

    Ningún otro test importa `psglab.ui`: la interfaz no lleva tests unitarios
    a propósito. Sin esta comprobación, un error de importación en `ui/` —una
    biblioteca de sistema que falta en Linux, un import mal escrito— no
    aparecería hasta que alguien abriera el programa.

    Sólo se importan los módulos. No se crea ninguna `QApplication`, que es lo
    que necesitaría una pantalla y no funcionaría en un servidor de integración
    continua.
    """
    import importlib
    import pkgutil

    import psglab

    fallos: list[str] = []

    def anotar_subpaquete_roto(nombre: str) -> None:
        """`walk_packages` **suprime** el error de un subpaquete si no se le pasa
        esto, y deja de emitir sus hijos: el test se ponía verde justo cuando
        `psglab/ui/__init__.py` fallara, que es el escenario que dice cubrir.
        """
        fallos.append(f"{nombre}: no se pudo importar el subpaquete, sus módulos no se probaron")

    encontrados = 0
    for info in pkgutil.walk_packages(
        psglab.__path__, prefix="psglab.", onerror=anotar_subpaquete_roto
    ):
        encontrados += 1
        try:
            importlib.import_module(info.name)
        except Exception as exc:  # noqa: BLE001 - interesa cualquier fallo
            fallos.append(f"{info.name}: {type(exc).__name__}: {exc}")

    assert not fallos, f"no se pudieron importar {len(fallos)} módulos: {fallos}"

    # Si el recorrido devolviera muy pocos módulos, algo lo cortó y el test
    # estaría pasando sin haber probado nada.
    esperados = len(modulos_del_paquete())
    assert encontrados >= esperados, (
        f"el recorrido encontró {encontrados} módulos y en el disco hay {esperados}: "
        "algo cortó la enumeración del paquete"
    )


# -- Que las tablas no nombren lo que ya no existe ---------------------------


def test_la_trazabilidad_no_nombra_archivos_que_ya_no_existen():
    """El chequeo inverso, que faltaba.

    `test_cada_modulo_aparece_en_la_trazabilidad` va de módulo a tabla y atrapa
    el módulo nuevo sin fila. Al revés no había nada: una fila que nombre un
    archivo renombrado o borrado quedaba invisible, y la tabla existe
    justamente para responder qué requisitos rompe tocar un archivo. Con la
    fila apuntando a la nada, esa pregunta se responde mal.

    `COBERTURA_DE_TESTS` y `SIN_CONTRATO` ya tenían su chequeo de existencia;
    éste le da el mismo trato a la trazabilidad.
    """
    trazabilidad = RAIZ / "docs" / "TRAZABILIDAD.md"
    texto = trazabilidad.read_text(encoding="utf-8")
    inexistentes = sorted(
        {
            citado
            for linea in texto.splitlines()
            if linea.lstrip().startswith("|")
            for citado in re.findall(r"`(psglab/[^`]+\.py|main\.py)`", linea)
            if not existe_respetando_mayusculas(RAIZ / citado)
        }
    )
    assert not inexistentes, (
        "docs/TRAZABILIDAD.md nombra en sus tablas archivos que no existen: "
        f"{inexistentes}"
    )


def test_las_exenciones_de_test_propio_siguen_existiendo():
    """Lo mismo para `SIN_TEST_PROPIO`.

    Una exención que nombra un archivo borrado no molesta a nadie, y por eso se
    queda: el día que alguien cree un módulo con ese nombre, arranca exento de
    tener test sin que nadie lo haya decidido.
    """
    inexistentes = sorted(
        ruta for ruta in SIN_TEST_PROPIO if not existe_respetando_mayusculas(RAIZ / ruta)
    )
    assert not inexistentes, (
        f"SIN_TEST_PROPIO exime archivos que ya no existen: {inexistentes}"
    )


def test_cada_readme_de_carpeta_nombra_sus_archivos():
    """La tabla "Los archivos" de cada README, en las dos direcciones.

    Es el patrón de `test_cada_modulo_aparece_en_la_trazabilidad` aplicado a los
    ocho README de `psglab/`. Sin él, un módulo nuevo puede quedar fuera del
    mapa de su propia carpeta —que es lo primero que lee quien llega— y una fila
    puede sobrevivir al archivo que describe.

    Vale una **fila de tabla o un encabezado propio**: la raíz del paquete
    documenta sus dos archivos sueltos con una sección cada uno, y eso es
    inventario igual. Lo que no cuenta es la mención al pasar en un párrafo,
    que no pretende serlo.
    """
    problemas: list[str] = []
    for readme in sorted(RAIZ.joinpath("psglab").rglob("README.md")):
        carpeta = readme.parent
        propios = sorted(
            f.name for f in carpeta.glob("*.py") if f.name != "__init__.py"
        )
        if not propios:
            continue
        inventariados: set[str] = set()
        for linea in readme.read_text(encoding="utf-8").splitlines():
            pelada = linea.lstrip()
            if pelada.startswith("|") or pelada.startswith("#"):
                inventariados.update(re.findall(r"`([a-z_0-9]+\.py)`", linea))
        for archivo in propios:
            if archivo not in inventariados:
                problemas.append(
                    f"{ruta_relativa(readme)} no inventaría {archivo}: no lo nombra "
                    "ni en una fila de tabla ni en un encabezado"
                )
        sobrantes = sorted(n for n in inventariados if n not in propios)
        if sobrantes:
            problemas.append(
                f"{ruta_relativa(readme)} inventaría archivos que la carpeta no "
                f"tiene: {sobrantes}"
            )
    assert not problemas, "\n".join(problemas)
