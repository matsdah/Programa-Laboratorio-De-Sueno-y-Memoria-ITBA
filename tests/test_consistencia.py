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
import unicodedata as _ud

import pytest

#: Raíz del repositorio, deducida de la ubicación de este archivo.
RAIZ = pathlib.Path(__file__).resolve().parent.parent

#: Qué módulos cubre cada archivo de test. Hace falta declararlo porque la
#: relación no es uno a uno: `test_exporters.py` cubre cuatro módulos.
#: Al agregar un archivo de test, agregar acá su fila.
COBERTURA_DE_TESTS: dict[str, tuple[str, ...]] = {
    "test_windows.py": ("psglab/core/windows.py",),
    "test_nomenclature.py": ("psglab/core/nomenclature.py",),
    "test_scoring.py": ("psglab/core/scoring.py",),
    "test_occupancy.py": ("psglab/tools/occupancy.py",),
    "test_exporters.py": (
        "psglab/exporters/scoring_txt.py",
        "psglab/exporters/annotations_txt.py",
        "psglab/exporters/information_txt.py",
        "psglab/exporters/statistics.py",
    ),
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
    """Cantidad de `raise NotImplementedError` de un archivo."""
    texto = archivo.read_text(encoding="utf-8")
    return len(re.findall(r"raise NotImplementedError", texto))


def stubs_de_la_parte_1() -> int:
    """Stubs pendientes de la Parte 1. `analysis/` es la Parte 2 y no cuenta."""
    return sum(
        contar_stubs(f) for f in modulos_del_paquete() if "analysis" not in f.parts
    )


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
    """Todos los `.md` versionados del repositorio."""
    return sorted(
        p
        for p in RAIZ.rglob("*.md")
        if ".venv" not in p.parts and ".git" not in p.parts
    )


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
    en_codigo = stubs_de_la_parte_1()

    en_items = sum(int(n) for n in re.findall(r"·\s*(\d+) stubs?", todo))
    assert en_items == en_codigo, (
        f"los ítems del TODO suman {en_items} stubs y en el código hay {en_codigo}"
    )

    filas = re.findall(
        r"\|\s*\[(\d)\.([^\]]*)\]\([^)]*\)\s*\|\s*[\d—-]+\s*\|\s*(\d+)\s*\|", todo
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
    modulos_reales = sum(
        1
        for f in modulos_del_paquete()
        if "analysis" not in f.parts and contar_stubs(f) > 0
    )
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


def test_cada_modulo_aparece_en_la_trazabilidad():
    """La tabla sirve para la pregunta inversa: qué se rompe si toco este archivo.

    Un módulo que no figura en ninguna fila no se puede responder.
    """
    texto = (RAIZ / "docs" / "TRAZABILIDAD.md").read_text(encoding="utf-8")
    citados = set(re.findall(r"`(psglab/[^`]+\.py)`", texto))
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
        if not (declara and asigna):
            continue
        if declara - asigna:
            problemas.append(
                f"{ruta_relativa(archivo)} declara {sorted(declara - asigna)} y la tabla no se los asigna"
            )
        if asigna - declara:
            problemas.append(
                f"{ruta_relativa(archivo)} no declara {sorted(asigna - declara)}, que la tabla sí le asigna"
            )
    assert not problemas, "\n".join(problemas)


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
            if not objetivo.exists():
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
        if any(ord(c) > 127 for c in _ud.normalize("NFD", linea))
    ]
    assert not culpables, f"líneas con caracteres no ASCII: {culpables[:5]}"


# -- Reglas de arquitectura -------------------------------------------------


def test_core_y_utils_no_conocen_la_interfaz():
    """Es la regla que sostiene todo lo demás.

    Si `core/` importara Qt, el modelo dejaría de poder testearse sin abrir una
    ventana y el testeo recurrente que pide el pliego se volvería inviable.
    """
    prohibidos = ("psglab.ui", "PySide6", "pyqtgraph")
    violaciones: list[str] = []
    for archivo in modulos_del_paquete():
        if archivo.parent.name not in ("core", "utils"):
            continue
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                if any(nodo.module.startswith(p) for p in prohibidos):
                    violaciones.append(f"{ruta_relativa(archivo)}:{nodo.lineno} importa {nodo.module}")
    assert not violaciones, "\n".join(violaciones)


def test_todas_las_firmas_llevan_type_hints():
    """Convención del proyecto: documentan el contrato y no se desactualizan."""
    faltantes: list[str] = []
    for archivo in modulos_del_paquete():
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for argumento in nodo.args.args:
                if argumento.arg not in ("self", "cls") and argumento.annotation is None:
                    faltantes.append(
                        f"{ruta_relativa(archivo)}:{nodo.lineno} {nodo.name}({argumento.arg})"
                    )
            if nodo.returns is None:
                faltantes.append(f"{ruta_relativa(archivo)}:{nodo.lineno} {nodo.name}() sin retorno")
    assert not faltantes, "\n".join(faltantes)


# -- El verde por omisión ---------------------------------------------------


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
        if "pytestmark" not in archivo_test.read_text(encoding="utf-8"):
            continue
        stubs = {m: contar_stubs(RAIZ / m) for m in modulos}
        if all(n == 0 for n in stubs.values()):
            pendientes.append(
                f"tests/{nombre} sigue salteado pero {', '.join(modulos)} ya no tiene stubs: "
                "borrá el pytestmark"
            )
    assert not pendientes, "\n".join(pendientes)


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
    for info in pkgutil.walk_packages(psglab.__path__, prefix="psglab."):
        try:
            importlib.import_module(info.name)
        except Exception as exc:  # noqa: BLE001 - interesa cualquier fallo
            fallos.append(f"{info.name}: {type(exc).__name__}: {exc}")
    assert not fallos, f"no se pudieron importar {len(fallos)} módulos: {fallos}"
