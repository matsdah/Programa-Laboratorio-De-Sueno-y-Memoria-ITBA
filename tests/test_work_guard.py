"""Tests del guardián del trabajo, armado **sin la ventana principal**.

Hasta el hito 79 exportar y el cartel del trabajo sin exportar eran la mitad
del mixin `window_files.py`, y probarlos era armar la ventana entera y abrir un
registro por el disco. `WorkGuard` recibe la ventana sólo como dueña de sus
carteles, y lo que es de ella —el cartel de un error, la pregunta de reemplazar
un archivo— le llega por una señal o por una función. Acá se miran las reglas:
qué cuenta como trabajo sin exportar, qué pasa con cada respuesta del cartel, y
que exportar marque el trabajo como exportado sólo si se escribió.

Que el menú, Ctrl+S y cerrar la ventana pasen por acá lo sigue verificando
`test_entrega.py`.
"""

from pathlib import Path

import numpy as np
import pytest
from PySide6.QtWidgets import QFileDialog, QMainWindow

from psglab.core.annotations import Annotation, AnnotationSet
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.ui.work_guard import WorkGuard

FRECUENCIA = 100.0
VENTANAS = 2


def _sesion(carpeta: Path) -> Session:
    registro = Recording(
        file_path=carpeta / "noche.edf",
        channels=[Channel("C3", ChannelKind.EEG, "µV", 0)],
        data=np.zeros((1, int(VENTANAS * 30 * FRECUENCIA))),
        sampling_rate=FRECUENCIA,
    )
    return Session(registro, Scoring(VENTANAS, Nomenclature.AASM), AnnotationSet())


def anotar(sesion: Session) -> None:
    sesion.annotations.add_label("Spindle")
    sesion.annotations.add(Annotation("Spindle", 100, 50))


class Guardian:
    """El guardián con lo que la ventana le daría, y lo que le avisó."""

    def __init__(self, ventana: QMainWindow) -> None:
        self.fallas: list[tuple[object, object]] = []
        self.confirmaciones: list[str] = []
        self.confirma = True
        self.reciente: str | None = None
        self.guardian = WorkGuard(
            ventana, ventana.statusBar(), self._confirmar, lambda: self.reciente
        )
        self.guardian.failed.connect(lambda error, que: self.fallas.append((error, que)))

    def _confirmar(self, _titulo: str, pregunta: str, _boton: str, _info: str) -> bool:
        self.confirmaciones.append(pregunta)
        return self.confirma


@pytest.fixture
def ventana(qt_app):
    """Una `QMainWindow` cualquiera, por su barra de estado: no la principal."""
    ventana = QMainWindow()
    yield ventana
    ventana.deleteLater()


@pytest.fixture
def armado(ventana: QMainWindow) -> Guardian:
    return Guardian(ventana)


@pytest.fixture
def sesion(armado: Guardian, tmp_path: Path) -> Session:
    sesion = _sesion(tmp_path)
    armado.guardian.attach(sesion)
    return sesion


@pytest.fixture
def respuesta(monkeypatch):
    """Contesta el cartel del trabajo sin exportar, que es modal."""
    estado: dict[str, object] = {"respuesta": "cancelar", "preguntas": []}

    def responder(_guardian: WorkGuard, haciendo: str, en_juego: list[str]) -> str:
        estado["preguntas"].append((haciendo, list(en_juego)))
        return str(estado["respuesta"])

    monkeypatch.setattr(WorkGuard, "ask", responder)
    return estado


@pytest.fixture
def guardar_en(monkeypatch):
    """Contesta el diálogo de guardado con la ruta que se ponga en la lista."""
    rutas: list[str] = []
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *_a, **_k: (rutas.pop(0) if rutas else "", "")),
    )
    return rutas


# -- Qué cuenta como trabajo sin exportar ------------------------------------


def test_sin_registro_no_hay_nada_en_juego(armado: Guardian):
    assert armado.guardian.unexported() == []


def test_scoring_y_anotaciones_cuentan_en_ese_orden(armado: Guardian, sesion: Session):
    """El scoring primero: es el trabajo principal."""
    anotar(sesion)
    sesion.scoring.set_stage(0, SleepStage.N2)

    assert armado.guardian.unexported() == ["scoring", "annotations"]


# -- Exportar -------------------------------------------------------------------


def test_exportar_escribe_y_marca_el_trabajo(
    armado: Guardian, sesion: Session, tmp_path: Path, ventana: QMainWindow
):
    sesion.scoring.set_stage(0, SleepStage.N2)
    destino = tmp_path / "Scoring.txt"

    assert armado.guardian.export("scoring", destino)

    assert destino.exists()
    assert armado.guardian.unexported() == []
    assert ventana.statusBar().currentMessage() == "Se exportó Scoring.txt"


def test_si_el_disco_falla_el_trabajo_sigue_sin_exportar(
    armado: Guardian, sesion: Session, tmp_path: Path
):
    """Recién cuando se escribió: si falló, cerrar tiene que seguir preguntando."""
    sesion.scoring.set_stage(0, SleepStage.N2)

    assert not armado.guardian.export("scoring", tmp_path / "no-existe" / "Scoring.txt")

    ((_error, que),) = armado.fallas
    assert que == "exportar «Scoring.txt»"
    assert armado.guardian.unexported() == ["scoring"]


def test_un_archivo_de_salida_que_no_existe_se_rechaza(
    armado: Guardian, sesion: Session, tmp_path: Path
):
    assert not armado.guardian.export("otra cosa", tmp_path / "x.txt")

    assert len(armado.fallas) == 1


def test_sin_la_extension_se_agrega_y_se_pregunta_si_pisa(
    armado: Guardian, sesion: Session, tmp_path: Path, guardar_en: list[str]
):
    """El diálogo preguntó por «noche» y el que se escribe es «noche.txt»."""
    sesion.scoring.set_stage(0, SleepStage.N2)
    (tmp_path / "noche.txt").write_text("de antes", encoding="utf-8")
    armado.confirma = False
    guardar_en.append(str(tmp_path / "noche"))

    armado.guardian.export_dialog("scoring")

    assert armado.confirmaciones == ["«noche.txt» ya existe. ¿Reemplazarlo?"]
    assert (tmp_path / "noche.txt").read_text(encoding="utf-8") == "de antes"


# -- El cartel del trabajo sin exportar -------------------------------------------


def test_sin_trabajo_en_juego_no_pregunta(
    armado: Guardian, sesion: Session, respuesta: dict
):
    assert armado.guardian.can_discard("cerrar el programa")

    assert respuesta["preguntas"] == []


@pytest.mark.parametrize("contesta, sigue", [("descartar", True), ("cancelar", False)])
def test_descartar_sigue_y_cancelar_no(
    armado: Guardian, sesion: Session, respuesta: dict, contesta: str, sigue: bool
):
    sesion.scoring.set_stage(0, SleepStage.N2)
    respuesta["respuesta"] = contesta

    assert armado.guardian.can_discard("cerrar el programa") is sigue

    assert respuesta["preguntas"] == [("cerrar el programa", ["scoring"])]


def test_exportar_abre_un_dialogo_por_cada_cosa_y_sigue(
    armado: Guardian,
    sesion: Session,
    respuesta: dict,
    guardar_en: list[str],
    tmp_path: Path,
):
    sesion.scoring.set_stage(0, SleepStage.N2)
    anotar(sesion)
    respuesta["respuesta"] = "exportar"
    guardar_en += [str(tmp_path / "Scoring.txt"), str(tmp_path / "Anotaciones.txt")]

    assert armado.guardian.can_discard("abrir «otra.edf»")

    assert (tmp_path / "Scoring.txt").exists()
    assert (tmp_path / "Anotaciones.txt").exists()


def test_exportar_y_cancelar_el_dialogo_no_sigue(
    armado: Guardian, sesion: Session, respuesta: dict, guardar_en: list[str]
):
    """Cancelar un diálogo deja todo como estaba."""
    sesion.scoring.set_stage(0, SleepStage.N2)
    respuesta["respuesta"] = "exportar"

    assert not armado.guardian.can_discard("cerrar el programa")

    assert armado.guardian.unexported() == ["scoring"]


# -- La carpeta de los diálogos ------------------------------------------------


def test_los_dialogos_arrancan_en_la_carpeta_del_registro(
    armado: Guardian, sesion: Session, tmp_path: Path
):
    assert armado.guardian.working_folder() == str(tmp_path)


def test_sin_registro_arrancan_en_la_del_ultimo_reciente(
    armado: Guardian, tmp_path: Path
):
    armado.reciente = str(tmp_path / "ayer.edf")

    assert armado.guardian.working_folder() == str(tmp_path)


def test_sin_ninguna_carpeta_elige_el_sistema(armado: Guardian, tmp_path: Path):
    armado.reciente = str(tmp_path / "no-existe" / "ayer.edf")

    assert armado.guardian.working_folder() == ""
