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


# -- La copia de recuperación (hito 79) -------------------------------------------


@pytest.fixture
def perfil(armado: Guardian, tmp_path: Path) -> Path:
    """La carpeta de las copias, como la prende la ventana del usuario."""
    carpeta = tmp_path / "perfil"
    armado.guardian.enable_recovery(carpeta)
    return carpeta


@pytest.fixture
def recupera(monkeypatch):
    """Contesta la pregunta de recuperar, que es modal."""
    estado: dict[str, object] = {"respuesta": True, "preguntas": []}

    def responder(_guardian: WorkGuard, _escrita, ventanas: int, anotaciones: int) -> bool:
        estado["preguntas"].append((ventanas, anotaciones))
        return bool(estado["respuesta"])

    monkeypatch.setattr(WorkGuard, "ask_recovery", responder)
    return estado


def copias_en(carpeta: Path) -> list[Path]:
    return sorted(carpeta.glob("*.json")) if carpeta.exists() else []


def test_sin_prenderla_no_se_escribe_nada(armado: Guardian, sesion: Session):
    """La ventana de los tests no escribe en el perfil de quien corre la suite."""
    sesion.scoring.set_stage(0, SleepStage.N2)

    armado.guardian.save_recovery()

    assert armado.guardian.recovery_path() is None


def test_con_trabajo_sin_exportar_se_escribe_la_copia(
    armado: Guardian, sesion: Session, perfil: Path
):
    sesion.scoring.set_stage(0, SleepStage.N2)

    armado.guardian.save_recovery()

    assert copias_en(perfil) == [armado.guardian.recovery_path()]


def test_sin_trabajo_no_hay_copia(armado: Guardian, sesion: Session, perfil: Path):
    armado.guardian.save_recovery()

    assert copias_en(perfil) == []


def test_exportar_todo_borra_la_copia(
    armado: Guardian, sesion: Session, perfil: Path, tmp_path: Path
):
    """Lo exportado ya está a salvo en su archivo."""
    sesion.scoring.set_stage(0, SleepStage.N2)
    armado.guardian.save_recovery()

    armado.guardian.export("scoring", tmp_path / "Scoring.txt")
    armado.guardian.save_recovery()

    assert copias_en(perfil) == []


@pytest.mark.parametrize("contesta", ["descartar", "exportar"])
def test_cuando_el_usuario_decide_la_copia_sobra(
    armado: Guardian,
    sesion: Session,
    perfil: Path,
    respuesta: dict,
    guardar_en: list[str],
    tmp_path: Path,
    contesta: str,
):
    """La que sobrevive es la de un cierre que nadie decidió."""
    sesion.scoring.set_stage(0, SleepStage.N2)
    armado.guardian.save_recovery()
    respuesta["respuesta"] = contesta
    guardar_en.append(str(tmp_path / "Scoring.txt"))

    assert armado.guardian.can_discard("cerrar el programa")

    assert copias_en(perfil) == []


def test_cancelar_conserva_la_copia(
    armado: Guardian, sesion: Session, perfil: Path, respuesta: dict
):
    sesion.scoring.set_stage(0, SleepStage.N2)
    armado.guardian.save_recovery()

    assert not armado.guardian.can_discard("cerrar el programa")

    assert len(copias_en(perfil)) == 1


def _despues_de_un_corte(armado: Guardian, tmp_path: Path) -> Session:
    """Scorea, deja la copia y abre el mismo registro como si nada."""
    anterior = armado.guardian._session
    anterior.scoring.set_stage(0, SleepStage.N2)
    anterior.scoring.set_stage(1, SleepStage.N3)
    anotar(anterior)
    armado.guardian.save_recovery()
    nueva = _sesion(tmp_path)
    armado.guardian.attach(nueva)
    return nueva


def test_al_reabrir_el_mismo_registro_se_ofrece_y_se_recupera(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict, tmp_path: Path
):
    nueva = _despues_de_un_corte(armado, tmp_path)

    assert armado.guardian.offer_recovery()

    assert recupera["preguntas"] == [(2, 1)]
    assert nueva.scoring.get(1).stage is SleepStage.N3
    assert len(nueva.annotations.all()) == 1
    # Sigue sin exportar, y la copia sigue ahí hasta que el usuario decida.
    assert armado.guardian.unexported() == ["scoring", "annotations"]
    assert len(copias_en(perfil)) == 1


def test_descartarla_la_borra_y_no_se_vuelve_a_preguntar(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict, tmp_path: Path
):
    nueva = _despues_de_un_corte(armado, tmp_path)
    recupera["respuesta"] = False

    assert not armado.guardian.offer_recovery()
    assert not armado.guardian.offer_recovery()

    assert recupera["preguntas"] == [(2, 1)]
    assert nueva.scoring.scored_windows() == 0
    assert copias_en(perfil) == []


def test_una_copia_rota_se_borra_sin_preguntar(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict, tmp_path: Path
):
    """Pudo quedar cortada por el mismo corte de luz."""
    _despues_de_un_corte(armado, tmp_path)
    ruta = armado.guardian.recovery_path()
    ruta.write_text(ruta.read_text(encoding="utf-8")[:40], encoding="utf-8")

    assert not armado.guardian.offer_recovery()

    assert recupera["preguntas"] == []
    assert copias_en(perfil) == []


def test_otro_registro_no_ve_la_copia(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict, tmp_path: Path
):
    """Una por registro: la de esta noche no se le ofrece a otra."""
    sesion.scoring.set_stage(0, SleepStage.N2)
    armado.guardian.save_recovery()
    otra = tmp_path / "otra"
    otra.mkdir()
    armado.guardian.attach(_sesion(otra))

    assert not armado.guardian.offer_recovery()

    assert recupera["preguntas"] == []
    assert len(copias_en(perfil)) == 1


# -- El cartel de recuperar, sin reemplazarlo (hito 81) ------------------------


@pytest.fixture
def aprieta(monkeypatch):
    """Arma el cartel de verdad y aprieta el botón que se pida, sin mostrarlo.

    Todos los demás tests reemplazan `ask_recovery()` entero, así que el texto
    y los botones del cartel no los verificaba nadie. Esto reemplaza sólo el
    `exec()` modal: guarda lo que dice el cartel y hace clic donde se le diga.
    """
    from PySide6.QtWidgets import QMessageBox

    estado: dict[str, object] = {"boton": "Recuperar", "textos": []}

    def exec_(cartel: QMessageBox) -> int:
        estado["textos"].append(f"{cartel.text()} {cartel.informativeText()}")
        (boton,) = [b for b in cartel.buttons() if b.text() == estado["boton"]]
        boton.click()
        return 0

    monkeypatch.setattr(QMessageBox, "exec", exec_)
    return estado


@pytest.mark.parametrize("boton, recupera", [("Recuperar", True), ("Descartar", False)])
def test_el_cartel_de_recuperar_devuelve_lo_que_se_aprieta(
    armado: Guardian, sesion: Session, aprieta, boton: str, recupera: bool
):
    from datetime import datetime

    aprieta["boton"] = boton

    respuesta = armado.guardian.ask_recovery(datetime(2026, 9, 28, 23, 5), 3, 1)

    assert respuesta is recupera
    (texto,) = aprieta["textos"]
    assert sesion.recording.file_path.name in texto
    assert "3 ventanas scoreadas" in texto
    assert "1 anotación" in texto
    assert "28/09 a las 23:05" in texto
