"""Interfaz común de los lectores de archivos y su registro.

Todo lector recibe una ruta y devuelve un `Recording`. El resto del programa
sólo llama a `read_recording()` y nunca sabe de qué formato vino la señal.

Para agregar un formato:

    1. Crear `psglab/readers/mi_formato.py`.
    2. Definir una clase que herede de `Reader`.
    3. Decorarla con `@register_reader`.

No hace falta modificar ningún archivo existente.

Importar un scoring ya existente **no** pasa por acá: `read_scoring()` es una
función suelta de `scoring_reader.py` y no un `Reader`, porque un scoring no
produce un `Recording`.

Cubre del pliego: es la base de V1_F y V2_F de "Importación de archivos".
"""

import importlib
import pkgutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Final

from psglab.core.recording import Recording
from psglab.utils.errors import UnsupportedFormatError

#: Lectores registrados, en orden de registro. Se llena solo a medida que se
#: importan los módulos de formato.
_REGISTRY: list[type["Reader"]] = []

#: Si `load_all_readers()` ya recorrió el paquete. Evita releer el directorio
#: en cada apertura de archivo.
_REGISTRY_CARGADO: bool = False

#: Clave de `Recording.metadata` donde un lector deja **lo que el investigador
#: tiene que saber aunque el archivo se haya podido abrir**: una lista de
#: mensajes en español, dirigidos a él. La ventana los muestra después de
#: abrir el registro.
#:
#: Existe desde el hito 33, por el EDF truncado: MNE lee lo que hay y avisa por
#: consola, así que abrir media noche no se distinguía de abrir una noche
#: entera. **No es un error**: el archivo se abre, porque lo que llegó puede ser
#: todo lo que el investigador tiene. Es de este módulo y no de un lector
#: porque la ventana no sabe de qué formato vino la señal.
IMPORT_WARNINGS_KEY: Final[str] = "import_warnings"


class Reader(ABC):
    """Lector de un formato de registro.

    Attributes:
        format_name: nombre del formato tal como se le muestra al usuario en
            el diálogo de apertura de archivos.
        extensions: extensiones que maneja, en minúscula y con punto.
    """

    format_name: str = ""
    extensions: tuple[str, ...] = ()

    def can_read(self, path: Path) -> bool:
        """Indica si este lector puede abrir el archivo.

        La implementación por defecto compara la extensión contra
        `extensions`. Un lector la sobrescribe sólo si necesita inspeccionar
        el contenido del archivo para decidir.

        Está implementada y no pendiente, a diferencia del resto del
        esqueleto, porque es infraestructura de despacho: sin ella
        `read_recording()` no puede elegir lector y el registro de formatos no
        funciona ni con un solo lector terminado.
        """
        return path.suffix.lower() in self.extensions

    @classmethod
    def warm_up(cls) -> None:
        """Paga por adelantado lo que la primera lectura tarda de más.

        **No hace nada por defecto**, como los métodos de evento de `Tool`: un
        lector que no tenga nada que adelantar no tiene que saber que esto
        existe.

        Lo que tiene que adelantar un lector que se apoya en MNE son sus
        importaciones perezosas: `mne.io` carga el módulo de cada formato recién
        la primera vez que se lo usa, y ahí adentro entran `mne.viz`,
        `matplotlib` y media `scipy`. Medido en el hito 33: de los 9,2 s de la
        primera lectura de un proceso, 8,65 eran eso, con la ventana congelada
        en lo primero que hace el usuario. La segunda lectura del mismo archivo
        tardaba 18 ms.

        La llama `warm_up_readers()` en el hilo de precalentamiento. Si el
        usuario abre un registro mientras tanto, el lock de importación de
        Python lo hace esperar lo que falte: no se importa dos veces.
        """

    @abstractmethod
    def read(self, path: Path) -> Recording:
        """Carga el archivo y devuelve el registro.

        La señal se devuelve siempre en microvoltios y con la clase de cada
        canal ya detectada (ver `channel_types.detect_channel_kind`).

        Lo que se pudo leer con reservas —un archivo que trae menos de lo que
        declara— se avisa en `metadata[IMPORT_WARNINGS_KEY]` y no se eleva. Lo
        que no depende del formato no hace falta que lo mire cada lector: las
        muestras sin valor las revisa `read_recording()` sobre el registro ya
        armado.

        Raises:
            UnreadableFileError: si el archivo está corrupto, o tan incompleto
                que no queda nada que leer.
        """


def register_reader(reader_cls: type[Reader]) -> type[Reader]:
    """Decorador que registra un lector para que el programa lo descubra.

    Implementado y no pendiente por la misma razón que `Reader.can_read`: es un
    decorador y se ejecuta al importar cada módulo de formato. Si elevara
    NotImplementedError, ningún lector podría importarse.

    Uso:
        @register_reader
        class EdfReader(Reader):
            ...
    """
    _REGISTRY.append(reader_cls)
    return reader_cls


def load_all_readers() -> None:
    """Importa todos los módulos de formato para que se registren.

    Una clase sólo se registra cuando su módulo se importa, y `__init__.py` no
    importa ninguno a propósito: mantener ahí una lista de importaciones sería
    justo el archivo que hay que tocar para agregar un formato, que es lo que
    este mecanismo evita. Sin esta función el registro quedaba vacío y
    `read_recording()` no encontraba **ningún** lector nunca.

    Implementada y no pendiente por la misma razón que `register_reader`: si
    fallara, el punto de extensión de formatos no existiría.

    Llamarla más de una vez no duplica nada ni vuelve a recorrer el paquete: la
    primera vez deja marcado que ya se hizo. Sin esa marca tampoco habría
    duplicados —importar un módulo ya importado no vuelve a ejecutar el
    decorador— pero cada llamada leería el directorio de nuevo, y
    `read_recording()` la llama en cada apertura de archivo.
    """
    global _REGISTRY_CARGADO
    if _REGISTRY_CARGADO:
        return

    import psglab.readers

    # Los que no son lectores de señal: ninguno registra un `Reader`, y los dos
    # de scoring leen otra cosa que un `Recording`.
    no_son_lectores = ("base", "channel_types", "scoring_reader", "scoring_formats")
    for module in pkgutil.iter_modules(psglab.readers.__path__):
        if module.name not in no_son_lectores:
            importlib.import_module(f"psglab.readers.{module.name}")
    _REGISTRY_CARGADO = True


def warm_up_readers() -> None:
    """Adelanta lo que la primera lectura de cada formato tarda de más.

    Recorre los lectores registrados y le pide a cada uno que caliente lo suyo:
    **qué hay que adelantar lo sabe el formato**, no esta función, igual que
    pasa con la lectura. Un lector nuevo no tiene que hacer nada si no tiene
    nada que pagar por adelantado.

    La llama la ventana en el hilo de precalentamiento, y nunca la suite: ver
    `MainWindow.warm_up_in_background()`.
    """
    for reader_cls in available_readers():
        reader_cls.warm_up()


def available_readers() -> list[type[Reader]]:
    """Todos los lectores registrados, en orden de registro.

    Devuelve las **clases**, igual que `tools.registry.available_tools()`. Los
    dos son los puntos de extensión del proyecto y conviene que se consuman de
    la misma forma; antes uno devolvía instancias y el otro clases, y la
    ventana principal iba a tener que tratarlos distinto sin motivo.
    """
    load_all_readers()
    return list(_REGISTRY)


def file_dialog_filter() -> str:
    """Filtro de formatos para el diálogo de apertura de archivos de Qt.

    Se construye a partir de los lectores registrados, así que un formato
    nuevo aparece solo en el diálogo sin tocar la interfaz.

    La primera entrada junta las extensiones de todos los formatos: es la que el
    diálogo ofrece por defecto y la que sirve el 99 % de las veces, porque el
    usuario quiere abrir "el registro" sin tener que acordarse de en qué formato
    se lo exportó el equipo. La última deja ver cualquier archivo, para el caso
    de una extensión inesperada.

    Devuelve **texto y nada más**: no importa Qt ni lo necesita. `readers/` es
    una de las cuatro capas que tienen que poder correr sin interfaz gráfica, y
    `test_las_capas_de_negocio_no_conocen_la_interfaz` lo verifica.
    """
    lectores = available_readers()
    todas = " ".join(sorted({f"*{ext}" for cls in lectores for ext in cls.extensions}))

    entradas = [f"Todos los formatos soportados ({todas})"] if todas else []
    entradas += [
        f"{cls.format_name} ({' '.join(f'*{ext}' for ext in cls.extensions)})"
        for cls in lectores
    ]
    entradas.append("Todos los archivos (*)")
    return ";;".join(entradas)


#: Cuántos canales sin valor se nombran en el aviso antes de resumir el resto.
#: Con un electrodo suelto son uno o dos; con un archivo mal convertido pueden
#: ser todos, y un cartel con treinta y dos nombres no se lee.
_CANALES_QUE_SE_NOMBRAN: Final[int] = 5


def _aviso_de_muestras_sin_valor(registro: Recording) -> str | None:
    """Qué decirle al investigador si el registro trae NaN o infinitos.

    **Es del despacho y no de un lector** (hito 33), por dos motivos. Uno, que
    ningún formato está a salvo: el EDF guarda enteros y no puede traerlos,
    pero un BrainVision en `IEEE_FLOAT_32` sí, y el formato que se agregue
    mañana no tiene por qué acordarse de mirarlo. Dos, que la regla de qué
    cuenta como muestra sin valor vive en `Recording.non_finite_channels()`, no
    acá.

    Returns:
        El mensaje, o None si el registro no tiene ninguna.
    """
    cuentas = registro.non_finite_channels()
    if not cuentas:
        return None
    muestras = registro.data.shape[1]
    if len(cuentas) == 1:
        canal, cuantas = next(iter(cuentas.items()))
        donde = f"en «{canal}»: {cuantas} de sus {muestras} muestras"
    else:
        nombrados = [
            f"{canal} ({cuantas})"
            for canal, cuantas in list(cuentas.items())[:_CANALES_QUE_SE_NOMBRAN]
        ]
        resto = len(cuentas) - len(nombrados)
        if resto:
            nombrados.append(f"y otros {resto}")
        donde = (
            f"en {len(cuentas)} de sus {len(registro.channels)} canales, sobre "
            f"{muestras} muestras cada uno: {', '.join(nombrados)}"
        )
    return (
        f"«{registro.file_path.name}» trae muestras sin valor (NaN o infinito) "
        f"{donde}. No se ven en la pantalla y contagian lo que las toque: "
        "filtrar las esparce por la señal, la referencia promedio las pasa a "
        "todos los canales y la PSD de esa época sale entera sin valor."
    )


def _agregar_aviso(registro: Recording, aviso: str) -> None:
    """Suma un aviso a los que el lector ya haya dejado, sin pisarlos.

    Un EDF truncado **y** con muestras sin valor tiene dos cosas que decir, y
    la ventana las muestra juntas.
    """
    anteriores = registro.metadata.get(IMPORT_WARNINGS_KEY)
    avisos = list(anteriores) if isinstance(anteriores, list) else []
    avisos.append(aviso)
    registro.metadata[IMPORT_WARNINGS_KEY] = avisos


def read_recording(path: Path) -> Recording:
    """Carga un registro eligiendo automáticamente el lector adecuado.

    Es la única función que el resto del programa necesita conocer para
    importar un archivo: elige el lector por `can_read()` y le pide el
    `read()`.

    **Y revisa lo que salió**, antes de devolverlo: si la señal trae muestras
    sin valor se suma el aviso de `_aviso_de_muestras_sin_valor()`. Cuesta 80
    ms sobre el registro de prueba de 22 h —el 3 % de lo que tarda abrirlo— y
    es lo que separa un archivo dañado de uno sano, que hasta el hito 33 se
    veían igual en la pantalla.

    Raises:
        UnsupportedFormatError: si ningún lector registrado maneja el archivo.
    """
    for reader_cls in available_readers():
        reader = reader_cls()
        if reader.can_read(path):
            registro = reader.read(path)
            aviso = _aviso_de_muestras_sin_valor(registro)
            if aviso is not None:
                _agregar_aviso(registro, aviso)
            return registro
    known_extensions = sorted({ext for cls in _REGISTRY for ext in cls.extensions})
    raise UnsupportedFormatError(
        f"No se puede abrir «{path.name}»: el formato no está soportado.",
        details=f"Extensiones conocidas: {', '.join(known_extensions) or 'ninguna'}",
    )
