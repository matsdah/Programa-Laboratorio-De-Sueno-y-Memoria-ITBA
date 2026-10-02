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

import json
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from psglab.analysis.derivation import derive
from psglab.core.annotations import Annotation, AnnotationSet
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.core.session import Session
from psglab.core import recovery
from psglab.exporters.atomic import write_text_atomically
from psglab.ui.work_guard import WorkGuard
from psglab.utils.errors import PsgLabError

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
    estado: dict[str, object] = {"respuesta": True, "preguntas": [], "modos": []}

    def responder(
        _guardian: WorkGuard, _escrita, ventanas: int, anotaciones: int,
        legacy: bool = False, derived: bool = False,
    ) -> bool:
        estado["preguntas"].append((ventanas, anotaciones))
        estado["modos"].append((legacy, derived))
        return bool(estado["respuesta"])

    monkeypatch.setattr(WorkGuard, "ask_recovery", responder)
    return estado


def copias_en(carpeta: Path) -> list[Path]:
    return sorted(carpeta.glob("*.json")) if carpeta.exists() else []


def _copia_v1(sesion: Session) -> dict[str, object]:
    """La forma que escribía recovery.snapshot() antes del formato 2.

    Se construye sin llamar al snapshot actual para no disfrazar una copia
    nueva cambiándole sólo el número de formato.
    """
    registro = sesion.recording
    ventanas = [sesion.scoring.get(i) for i in range(sesion.scoring.n_windows)]
    anotaciones = sesion.annotations
    return {
        "formato": 1,
        "registro": {
            "archivo": registro.file_path.name,
            "frecuencia": float(registro.sampling_rate),
            "muestras": int(registro.n_samples),
            "canales": registro.channel_names(),
        },
        "ventana": sesion.current_window,
        "nomenclatura": sesion.scoring.nomenclature.name,
        "fases": [ventana.stage.name for ventana in ventanas],
        "arousals": [i for i, ventana in enumerate(ventanas) if ventana.arousal],
        "clases": [[clase, anotaciones.color_of(clase)] for clase in anotaciones.labels()],
        "anotaciones": [
            [a.label, a.onset_sample, a.duration_samples, list(a.channels), a.color]
            for a in anotaciones.all()
        ],
    }


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


def test_provisorio_viejo_no_desvia_la_copia_de_recuperacion(
    armado: Guardian, sesion: Session, perfil: Path, tmp_path: Path
):
    ruta = armado.guardian.recovery_path()
    assert ruta is not None
    ruta.parent.mkdir(parents=True)
    ajeno = tmp_path / "ajeno.txt"
    ajeno.write_text("intacto", encoding="utf-8")
    provisorio_viejo = ruta.with_suffix(".tmp")
    try:
        provisorio_viejo.symlink_to(ajeno)
    except (OSError, NotImplementedError):
        pytest.skip("Este sistema no permite crear symlinks")

    sesion.scoring.set_stage(0, SleepStage.N2)
    armado.guardian.save_recovery()

    assert ajeno.read_text(encoding="utf-8") == "intacto"
    assert provisorio_viejo.is_symlink()
    assert ruta.is_file()
    assert not ruta.is_symlink()
    assert json.loads(ruta.read_text(encoding="utf-8"))["fases"][0] == "N2"


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


def test_una_copia_rota_se_conserva_aparte_sin_preguntar(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict, tmp_path: Path
):
    """Pudo quedar cortada por el mismo corte de luz."""
    _despues_de_un_corte(armado, tmp_path)
    ruta = armado.guardian.recovery_path()
    ruta.write_text(ruta.read_text(encoding="utf-8")[:40], encoding="utf-8")

    assert not armado.guardian.offer_recovery()

    assert recupera["preguntas"] == []
    assert ruta not in copias_en(perfil)
    apartadas = list(perfil.glob("*.invalid-*.json"))
    assert len(apartadas) == 1
    assert apartadas[0].read_text(encoding="utf-8")


def test_copia_v1_sin_derivaciones_se_ofrece_y_recupera(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict, tmp_path: Path
):
    sesion.scoring.set_stage(0, SleepStage.N2)
    sesion.scoring.set_arousal(1, True)
    sesion.annotations.add_label("Spindle", "#123456")
    sesion.annotations.add(Annotation("Spindle", 100, 50, ("C3",)))
    sesion.go_to_window(1)
    copia = _copia_v1(sesion)
    assert set(copia["registro"]) == {"archivo", "frecuencia", "muestras", "canales"}
    assert "derivaciones" not in copia
    ruta = armado.guardian.recovery_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(copia), encoding="utf-8")
    texto_v1 = ruta.read_bytes()
    nueva = _sesion(tmp_path)
    armado.guardian.attach(nueva)

    assert armado.guardian.offer_recovery()

    assert recupera["preguntas"] == [(2, 1)]
    assert recupera["modos"] == [(True, False)]
    assert nueva.scoring.get(0).stage is SleepStage.N2
    assert nueva.scoring.get(1).arousal
    assert nueva.annotations.all() == sesion.annotations.all()
    assert nueva.current_window == 1
    assert armado.guardian.unexported() == ["scoring", "annotations"]
    archivos_v1 = list(perfil.glob("*.migrated-v1-*.json"))
    assert len(archivos_v1) == 1
    assert archivos_v1[0].read_bytes() == texto_v1

    armado.guardian.save_recovery()

    assert json.loads(ruta.read_text(encoding="utf-8"))["formato"] == 2
    assert archivos_v1[0].read_bytes() == texto_v1


def test_rechazar_copia_v1_la_conserva_sin_recuperar(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict, tmp_path: Path,
    monkeypatch,
):
    avisos = []
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *_args: avisos.append(_args[-1]))
    )
    sesion.scoring.set_stage(0, SleepStage.N2)
    copia = _copia_v1(sesion)
    ruta = armado.guardian.recovery_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(copia), encoding="utf-8")
    nueva = _sesion(tmp_path)
    armado.guardian.attach(nueva)
    recupera["respuesta"] = False

    assert not armado.guardian.offer_recovery()

    assert recupera["modos"] == [(True, False)]
    assert nueva.scoring.scored_windows() == 0
    assert not ruta.exists()
    apartadas = list(perfil.glob("*.declined-v1-*.json"))
    assert len(apartadas) == 1
    assert json.loads(apartadas[0].read_text(encoding="utf-8")) == copia
    assert str(apartadas[0]) in avisos[-1]
    assert not armado.fallas


def test_copia_v1_vacia_informa_ruta_conservada(
    armado: Guardian, sesion: Session, perfil: Path, tmp_path: Path
):
    copia = _copia_v1(sesion)
    ruta = armado.guardian.recovery_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(copia), encoding="utf-8")
    nueva = _sesion(tmp_path)
    armado.guardian.attach(nueva)

    assert not armado.guardian.offer_recovery()

    (apartada,) = perfil.glob("*.empty-*.json")
    assert str(apartada) in armado.fallas[-1][0].message


def test_copia_v2_vacia_se_aparta_sin_abrir_cartel(
    armado: Guardian, sesion: Session, perfil: Path
):
    ruta = armado.guardian.recovery_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(recovery.snapshot(sesion)), encoding="utf-8")

    assert not armado.guardian.offer_recovery()

    assert armado.fallas == []
    assert len(list(perfil.glob("*.empty-*.json"))) == 1


def test_si_no_se_puede_apartar_v1_vacia_informa_que_sigue_en_origen(
    armado: Guardian, sesion: Session, perfil: Path, tmp_path: Path, monkeypatch
):
    ruta = armado.guardian.recovery_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(_copia_v1(sesion)), encoding="utf-8")
    nueva = _sesion(tmp_path)
    armado.guardian.attach(nueva)
    reemplazo = Path.replace

    def impedir(origen: Path, destino: Path):
        if ".empty-" in destino.name:
            raise OSError("sin permiso")
        return reemplazo(origen, destino)

    monkeypatch.setattr(Path, "replace", impedir)
    assert not armado.guardian.offer_recovery()

    mensaje = armado.fallas[-1][0].message
    assert str(ruta) in mensaje
    assert "sigue en su ubicación original" in mensaje
    assert ruta.exists()
    assert list(perfil.glob("*.empty-*.json")) == []


def test_si_falla_archivar_v1_no_se_sobrescribe_ni_se_borra_la_unica_copia(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict,
    tmp_path: Path, monkeypatch,
):
    sesion.scoring.set_stage(0, SleepStage.N2)
    copia = _copia_v1(sesion)
    ruta = armado.guardian.recovery_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(copia), encoding="utf-8")
    nueva = _sesion(tmp_path)
    armado.guardian.attach(nueva)
    archivar = armado.guardian._archive_legacy_copy

    def falla_archivo(_ruta: Path, _contenido: bytes) -> Path:
        raise OSError("disco lleno")

    monkeypatch.setattr(armado.guardian, "_archive_legacy_copy", falla_archivo)
    assert armado.guardian.offer_recovery()
    assert nueva.scoring.get(0).stage is SleepStage.N2

    armado.guardian.save_recovery()
    nueva.mark_scoring_exported()
    armado.guardian.discard_recovery()

    assert json.loads(ruta.read_text(encoding="utf-8")) == copia
    assert list(perfil.glob("*.migrated-v1-*.json")) == []
    assert len(armado.fallas) == 1
    assert str(ruta) in str(armado.fallas[0][0])

    monkeypatch.setattr(armado.guardian, "_archive_legacy_copy", archivar)
    armado.guardian.discard_recovery()

    assert not ruta.exists()
    archivos_v1 = list(perfil.glob("*.migrated-v1-*.json"))
    assert len(archivos_v1) == 1
    assert json.loads(archivos_v1[0].read_text(encoding="utf-8")) == copia


def test_si_falla_escribir_v2_el_archivo_v1_y_su_archivo_se_conservan(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict,
    tmp_path: Path, monkeypatch,
):
    sesion.scoring.set_stage(0, SleepStage.N2)
    copia = _copia_v1(sesion)
    ruta = armado.guardian.recovery_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(copia), encoding="utf-8")
    original = ruta.read_bytes()
    armado.guardian.attach(_sesion(tmp_path))
    assert armado.guardian.offer_recovery()
    escribir = write_text_atomically

    def falla_escritura(_ruta: Path, _texto: str) -> None:
        raise OSError("disco lleno")

    monkeypatch.setattr("psglab.ui.work_guard.write_text_atomically", falla_escritura)
    armado.guardian.save_recovery()

    assert ruta.read_bytes() == original
    (archivo_v1,) = perfil.glob("*.migrated-v1-*.json")
    assert archivo_v1.read_bytes() == original

    monkeypatch.setattr("psglab.ui.work_guard.write_text_atomically", escribir)
    armado.guardian.save_recovery()

    assert json.loads(ruta.read_text(encoding="utf-8"))["formato"] == 2
    assert archivo_v1.read_bytes() == original


def test_copia_v1_con_canales_derivados_se_conserva_y_se_aparta(
    armado: Guardian, sesion: Session, perfil: Path, tmp_path: Path
):
    original = sesion.recording
    procesado = Recording(
        original.file_path,
        [*original.channels, Channel("C3-M1", ChannelKind.EEG, "µV", 1)],
        np.vstack([original.data, np.ones_like(original.data)]),
        original.sampling_rate,
    )
    sesion.set_recording(procesado)
    sesion.scoring.set_stage(0, SleepStage.N2)
    copia = _copia_v1(sesion)
    ruta = armado.guardian.recovery_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(copia), encoding="utf-8")
    armado.guardian.attach(_sesion(tmp_path))

    assert not armado.guardian.offer_recovery()

    assert not ruta.exists()
    apartadas = list(perfil.glob("*.mismatch-*.json"))
    assert len(apartadas) == 1
    assert json.loads(apartadas[0].read_text(encoding="utf-8"))["formato"] == 1
    assert len(armado.fallas) == 1
    assert str(apartadas[0]) in str(armado.fallas[0][0])


def test_copia_v1_invalida_no_se_ofrece_ni_toca_la_sesion(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict, tmp_path: Path
):
    sesion.scoring.set_stage(0, SleepStage.N2)
    copia = _copia_v1(sesion)
    copia["anotaciones"] = [["Spindle", 100, 50, ["canal-ausente"], None]]
    ruta = armado.guardian.recovery_path()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(copia), encoding="utf-8")
    nueva = _sesion(tmp_path)
    armado.guardian.attach(nueva)

    assert not armado.guardian.offer_recovery()

    assert recupera["preguntas"] == []
    assert nueva.scoring.scored_windows() == 0
    assert nueva.annotations.all() == []
    assert not ruta.exists()
    apartadas = list(perfil.glob("*.invalid-*.json"))
    assert len(apartadas) == 1
    assert json.loads(apartadas[0].read_text(encoding="utf-8")) == copia


def test_reintenta_apartar_copia_rota_antes_de_escribir_el_nuevo_trabajo(
    armado: Guardian, sesion: Session, perfil: Path, monkeypatch
):
    avisos = []
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *_args: avisos.append(_args[-1]))
    )
    ruta = armado.guardian.recovery_path()
    ruta.parent.mkdir(parents=True)
    ruta.write_text("{ roto", encoding="utf-8")
    reemplazo = Path.replace
    fallar_una_vez = True

    def reemplazar_una_vez(origen: Path, destino: Path):
        nonlocal fallar_una_vez
        if fallar_una_vez and ".invalid-" in destino.name:
            fallar_una_vez = False
            raise OSError("fallo transitorio")
        return reemplazo(origen, destino)

    monkeypatch.setattr(Path, "replace", reemplazar_una_vez)
    assert not armado.guardian.offer_recovery()
    assert ruta.read_text(encoding="utf-8") == "{ roto"

    sesion.scoring.set_stage(0, SleepStage.N2)
    armado.guardian.save_recovery()

    apartadas = list(perfil.glob("*.invalid-*.json"))
    assert len(apartadas) == 1
    assert apartadas[0].read_text(encoding="utf-8") == "{ roto"
    assert ruta.exists()
    assert json.loads(ruta.read_text(encoding="utf-8"))["fases"][0] == "N2"
    assert len(avisos) == 1
    assert str(apartadas[0]) in avisos[0]


def test_si_no_se_puede_apartar_la_copia_autoguardado_no_la_pisa(
    armado: Guardian, sesion: Session, perfil: Path, monkeypatch
):
    ruta = armado.guardian.recovery_path()
    assert ruta is not None
    ruta.parent.mkdir(parents=True)
    ruta.write_text("{ roto", encoding="utf-8")
    reemplazo = Path.replace

    def impedir_apartarla(origen: Path, destino: Path):
        if ".invalid-" in destino.name:
            raise OSError("el perfil no admite renombrar")
        return reemplazo(origen, destino)

    monkeypatch.setattr(Path, "replace", impedir_apartarla)
    assert not armado.guardian.offer_recovery()

    sesion.scoring.set_stage(0, SleepStage.N2)
    armado.guardian.save_recovery()

    assert ruta.read_text(encoding="utf-8") == "{ roto"
    assert list(perfil.glob("*.invalid-*.json")) == []


def test_timer_pausado_no_escribe_ni_borra_durante_el_cartel(
    armado: Guardian, sesion: Session, perfil: Path
):
    sesion.scoring.set_stage(0, SleepStage.N2)
    armado.guardian.save_recovery()
    ruta = armado.guardian.recovery_path()
    antes = ruta.read_text(encoding="utf-8")

    armado.guardian.pause_recovery()
    sesion.mark_scoring_exported()
    armado.guardian.save_recovery()

    assert ruta.exists()
    assert ruta.read_text(encoding="utf-8") == antes
    armado.guardian.resume_recovery()


def test_fingerprint_queda_cacheada_en_guardian(
    armado: Guardian, sesion: Session, perfil: Path, monkeypatch
):
    """El reloj no vuelve a recorrer la señal completa cada diez segundos."""
    sesion.scoring.set_stage(0, SleepStage.N2)

    def no_recalcular(_registro):
        raise AssertionError("la huella ya se calculó al abrir")

    monkeypatch.setattr("psglab.ui.work_guard.recovery.fingerprint", no_recalcular)
    armado.guardian.save_recovery()

    assert armado.guardian.recovery_path().exists()


def test_copia_tras_cambiar_senal_identifica_el_registro_original(
    armado: Guardian, sesion: Session, perfil: Path
):
    original = sesion.recording
    sesion_original = Session(
        original, Scoring(VENTANAS, Nomenclature.AASM), AnnotationSet()
    )
    identidad_original = recovery.snapshot(sesion_original)["registro"]
    procesado = Recording(
        original.file_path,
        [*original.channels, Channel("C3-M1", ChannelKind.EEG, "µV", 1)],
        np.vstack([original.data, np.ones_like(original.data)]),
        original.sampling_rate,
    )
    sesion.set_recording(procesado)
    sesion.scoring.set_stage(0, SleepStage.N2)

    armado.guardian.save_recovery()

    ruta = armado.guardian.recovery_path()
    assert ruta is not None
    copia = json.loads(ruta.read_text(encoding="utf-8"))
    assert copia["registro"] == identidad_original
    assert recovery.matches(copia, original)
    assert not recovery.matches(copia, procesado)


def test_el_reloj_no_borra_la_copia_durante_el_cartel_modal(
    armado: Guardian, sesion: Session, perfil: Path, monkeypatch
):
    sesion.scoring.set_stage(0, SleepStage.N2)
    armado.guardian.save_recovery()
    ruta = armado.guardian.recovery_path()
    abierta = _sesion(sesion.recording.file_path.parent)
    armado.guardian.attach(abierta)

    def preguntar(*_args):
        armado.guardian.save_recovery()  # Simula el timeout en el loop modal.
        return True

    monkeypatch.setattr(WorkGuard, "ask_recovery", preguntar)
    assert armado.guardian.offer_recovery()
    assert ruta.exists()


def test_si_falla_el_rollback_la_copia_sigue_a_salvo(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict, tmp_path: Path,
    monkeypatch,
):
    sesion.scoring.set_stage(0, SleepStage.N2)
    armado.guardian.save_recovery()
    ruta = armado.guardian.recovery_path()
    contenido = ruta.read_text(encoding="utf-8")
    nueva = _sesion(tmp_path)
    armado.guardian.attach(nueva)

    def fallar_restore(*_args):
        raise PsgLabError("falló la restauración")

    def fallar_rollback():
        raise PsgLabError("falló la reversión")

    monkeypatch.setattr("psglab.ui.work_guard.recovery.restore", fallar_restore)
    assert not armado.guardian.offer_recovery(
        lambda _copia: _sesion(tmp_path).recording,
        lambda candidato: nueva.set_recording(candidato),
        fallar_rollback,
    )

    assert not ruta.exists()
    apartadas = list(perfil.glob("*.restore-failed-*.json"))
    assert len(apartadas) == 1
    assert apartadas[0].read_text(encoding="utf-8") == contenido
    assert str(apartadas[0]) in armado.fallas[-1][0].message


def test_copia_invalida_con_montaje_no_cambia_la_sesion_antes_de_rechazarla(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict
):
    original = sesion.recording
    candidato = derive(original, "C3", "C3", name="C3-C3")
    trabajo = Session(
        candidato, Scoring(VENTANAS, Nomenclature.AASM), AnnotationSet()
    )
    trabajo.scoring.set_stage(0, SleepStage.N2)
    copia = recovery.snapshot(trabajo, armado.guardian.source_identity)
    copia["anotaciones"] = [["Spindle", 100, 50, ["canal-inexistente"], None]]
    ruta = armado.guardian.recovery_path()
    assert ruta is not None
    ruta.parent.mkdir(parents=True)
    ruta.write_text(json.dumps(copia), encoding="utf-8")
    aplicaciones = []

    assert not armado.guardian.offer_recovery(
        lambda _copia: candidato,
        lambda registro: aplicaciones.append(registro),
    )

    assert recupera["preguntas"] == [(1, 1)]
    assert recupera["modos"] == [(False, True)]
    assert aplicaciones == []
    assert sesion.recording is original
    assert sesion.scoring.scored_windows() == 0
    assert sesion.annotations.all() == []
    assert len(list(perfil.glob("*.restore-failed-*.json"))) == 1


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


def test_misma_ruta_y_forma_con_senal_alterada_aparta_la_copia(
    armado: Guardian, sesion: Session, perfil: Path, recupera: dict, tmp_path: Path
):
    sesion.scoring.set_stage(0, SleepStage.N2)
    armado.guardian.save_recovery()
    ruta = armado.guardian.recovery_path()
    contenido = ruta.read_text(encoding="utf-8")
    nueva = _sesion(tmp_path)
    nueva.recording.data[0, nueva.recording.n_samples // 2] = 1.0
    armado.guardian.attach(nueva)

    assert not armado.guardian.offer_recovery()

    assert recupera["preguntas"] == []
    assert not ruta.exists()
    apartadas = list(perfil.glob("*.mismatch-*.json"))
    assert len(apartadas) == 1
    assert apartadas[0].read_text(encoding="utf-8") == contenido


# -- El cartel de recuperar, sin reemplazarlo (hito 81) ------------------------


@pytest.fixture
def aprieta(monkeypatch):
    """Arma el cartel de verdad y aprieta el botón que se pida, sin mostrarlo.

    Todos los demás tests reemplazan `ask_recovery()` entero, así que el texto
    y los botones del cartel no los verificaba nadie. Esto reemplaza sólo el
    `exec()` modal: guarda lo que dice el cartel y hace clic donde se le diga.
    """
    from PySide6.QtWidgets import QMessageBox

    estado: dict[str, object] = {"boton": "Recuperar", "textos": [], "botones": [], "defaults": []}

    def exec_(cartel: QMessageBox) -> int:
        estado["textos"].append(f"{cartel.text()} {cartel.informativeText()}")
        estado["botones"].append([b.text() for b in cartel.buttons()])
        estado["defaults"].append(cartel.defaultButton().text())
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
    assert "3 ventanas con trabajo" in texto
    assert "1 anotación" in texto
    assert "28/09 a las 23:05" in texto
    assert "filtros, la ICA y la re-referencia no se vuelven a aplicar" in texto


def test_el_cartel_v1_advierte_que_no_puede_verificar_la_senal(
    armado: Guardian, sesion: Session, perfil: Path, aprieta
):
    from datetime import datetime

    aprieta["boton"] = "Conservar copia"

    assert not armado.guardian.ask_recovery(
        datetime(2026, 9, 28, 23, 5), 2, 1, legacy=True
    )

    (texto,) = aprieta["textos"]
    assert "formato anterior" in texto
    assert "no se puede comprobar que la señal sea la misma" in texto
    assert "filtros, la ICA y la re-referencia no se vuelven a aplicar" in texto
    assert str(perfil) in texto
    assert aprieta["botones"] == [["Recuperar", "Conservar copia"]]
    assert aprieta["defaults"] == ["Conservar copia"]


def test_el_cartel_de_montaje_advierte_sobre_filtros_previos(
    armado: Guardian, sesion: Session, aprieta
):
    from datetime import datetime

    assert armado.guardian.ask_recovery(
        datetime(2026, 9, 28, 23, 5), 2, 1, derived=True
    )

    (texto,) = aprieta["textos"]
    assert "canales derivados" in texto
    assert "filtros antes del montaje" in texto
    assert "puede verse diferente" in texto
