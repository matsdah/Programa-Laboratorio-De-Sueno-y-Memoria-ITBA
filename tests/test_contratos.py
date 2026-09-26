"""Que ningún método público escape del `except` de la interfaz.

`psglab/utils/errors.py` hace una promesa de la que cuelga todo el manejo de
errores del programa: la ventana principal atrapa **una sola clase**,
`PsgLabError`, y convierte lo que salga en un cartel legible. Cualquier
`AttributeError`, `TypeError` o `KeyError` crudo atraviesa ese `except` y el
investigador termina viendo una traza de Python.

Una auditoría encontró **seis caminos** que escapaban así, y todos tenían la
misma forma: la guarda funcionaba y el `raise` era el que explotaba al armar el
mensaje. `Scoring.set_stage(0, "N2")` daba `AttributeError: 'str' object has no
attribute 'value'` — el rechazo era correcto y la explicación del rechazo,
imposible.

Este archivo recorre cada método público de los módulos implementados con
entradas hostiles y afirma que lo que sale hereda de `PsgLabError`.

La tabla es explícita a propósito, y desde
`test_consistencia.py::test_cada_metodo_publico_de_negocio_tiene_su_fila_de_contrato`
un método público sin fila hace fallar la suite, igual que pasa con
`COBERTURA_DE_TESTS`.

**Durante mucho tiempo eso fue mentira.** Este docstring lo prometía y no había
ningún chequeo: `CONTRATOS` sólo aparecía acá adentro, y lo único que se
verificaba era que las rutas nombradas existieran. La tabla cubría 5 de los 9
módulos terminados. Al escribir el chequeo que faltaba aparecieron **13 métodos
más** que dejaban escapar `TypeError`, `KeyError` o `AttributeError` crudos, más
del doble de los que había encontrado a mano la auditoría, incluido `stage_code`,
que alimenta la línea de `Scoring.txt`.

El alcance son las **tres** capas donde vive la regla de negocio: `core/`,
`utils/` y `analysis/`. Esta última entró en el hito 10, por el mismo argumento
que las otras dos: un `ValueError` de scipy o de MNE atraviesa el `except` de la
ventana igual que uno de `core/`. `readers/`, `tools/` y `exporters/` quedan
afuera; `tools/` tiene un test por herramienta, y de `ui/` se testea lo que no
dibuja. Las excepciones se declaran en `SIN_CONTRATO`, con el motivo: hoy son
`windows.py`, que documenta que no valida porque quien llama ya validó, `clamp`,
que declara la misma precondición, y `memoria_suficiente`, que no recibe datos
sino el texto que va a aparecer en el cartel.
"""

from pathlib import Path

import numpy as np
import pytest

from psglab.core import nomenclature as nom
from psglab.core.annotations import es_color_de_clase, marks_to_annotations
from psglab.core.annotations import Annotation, AnnotationSet
from psglab.core.nomenclature import Nomenclature, SleepStage
from psglab.core.recording import Channel, ChannelKind, Recording
from psglab.core.scoring import Scoring
from psglab.analysis import (
    complexity,
    connectivity,
    derivation,
    filters,
    ica,
    impedance,
    mne_bridge,
    psd,
    reference,
)
from psglab.core.session import Session
from psglab.core.decimation import bucket_size_for, envelope_by_bucket_size
from psglab.core.viewport import Viewport
from psglab.utils import units, validation
from psglab.utils.errors import InvalidRecordingError, PsgLabError

#: Valores que nunca deberían llegar, y que llegan igual: un lector con un bug,
#: una cabecera que no trae el campo, un parser que se olvidó de convertir.
HOSTILES = (None, "texto", 3.5, [], {}, object())

#: Un espectro cualquiera, para las filas de `psd.py` que reciben arrays.
FRECUENCIAS = np.linspace(0.0, 50.0, 51)
POTENCIAS = np.ones((1, 51))

#: Una señal cualquiera, para las filas de `complexity.py`. Corta a
#: propósito: la entropía de muestra es O(n²).
SEÑAL = np.sin(np.linspace(0.0, 20.0, 400))


def _con_una() -> AnnotationSet:
    """Un conjunto con una sola anotación, para reemplazarla."""
    conjunto = AnnotationSet()
    conjunto.add(Annotation("Arousal", 0, 10))
    return conjunto


def registro(canales: int = 2, muestras: int = 3000, fs: float = 100.0) -> Recording:
    """Un registro válido de una ventana, para partir de algo sano."""
    return Recording(
        file_path=Path("sintetico.edf"),
        channels=[Channel(f"C{i}", ChannelKind.EEG, "µV", i) for i in range(canales)],
        data=np.zeros((canales, muestras)),
        sampling_rate=fs,
    )


def sesion() -> Session:
    return Session(registro(), Scoring(1, Nomenclature.AASM), AnnotationSet())


def anotaciones() -> AnnotationSet:
    """Un conjunto con una anotación válida, para las filas que consultan.

    Ojo con el orden de los campos: `Annotation(label, onset, duration)`.
    Construirla al revés la hace rechazar en `add()`, y entonces la fila
    informa un `PsgLabError` que vino del armado y no de lo que se quería
    probar: verde por omisión.
    """
    conjunto = AnnotationSet()
    conjunto.add(Annotation("Arousal", 0, 100))
    return conjunto


#: Cada fila es (nombre legible, función que recibe un valor hostil).
#:
#: **Al agregar un método público a un módulo implementado hay que agregar su
#: fila**, o `test_consistencia.py` hace fallar la suite.
def pagina() -> Viewport:
    """Una página de una época sobre una hora de registro."""
    return Viewport.clamped(0.0, 30.0, 3600.0)


CONTRATOS: dict[str, list[tuple[str, object]]] = {
    "psglab/core/recording.py": [
        ("Recording(data=...)", lambda v: Recording(Path("x.edf"), [Channel("C0", ChannelKind.EEG, "µV", 0)], v, 100.0)),
        ("Recording(sampling_rate=...)", lambda v: Recording(Path("x.edf"), [Channel("C0", ChannelKind.EEG, "µV", 0)], np.zeros((1, 10)), v)),
        ("Recording(channels=...)", lambda v: Recording(Path("x.edf"), v, np.zeros((1, 10)), 100.0)),
        ("Recording(file_path=...)", lambda v: Recording(v, [Channel("C0", ChannelKind.EEG, "µV", 0)], np.zeros((1, 10)), 100.0)),
        ("channel_by_name", lambda v: registro().channel_by_name(v)),
        ("content_limit_hz", lambda v: registro().content_limit_hz(v)),
        ("channels_of_kind", lambda v: registro().channels_of_kind(v)),
        ("get_segment(channel_names=...)", lambda v: registro().get_segment(0, 10, [v])),
        ("get_segment(start_sample=...)", lambda v: registro().get_segment(v, 10)),
        ("get_segment(stop_sample=...)", lambda v: registro().get_segment(0, v)),
        ("flat_channels(channel_names=...)", lambda v: registro().flat_channels(0, 10, [v])),
        ("flat_channels(start_sample=...)", lambda v: registro().flat_channels(v, 10)),
        ("Recording(original_sampling_rate=...)", lambda v: Recording(Path("x.edf"), [Channel("C0", ChannelKind.EEG, "µV", 0, v)], np.zeros((1, 10)), 100.0)),
    ],
    "psglab/core/scoring.py": [
        ("Scoring(nomenclature=...)", lambda v: Scoring(3, v)),
        ("Scoring(n_windows=...)", lambda v: Scoring(v, Nomenclature.AASM)),
        ("set_stage(stage=...)", lambda v: Scoring(3, Nomenclature.AASM).set_stage(0, v)),
        ("set_arousal(arousal=...)", lambda v: Scoring(3, Nomenclature.AASM).set_arousal(0, v)),
        ("get", lambda v: Scoring(3, Nomenclature.AASM).get(v)),
        ("change_nomenclature", lambda v: Scoring(3, Nomenclature.AASM).change_nomenclature(v)),
    ],
    "psglab/core/nomenclature.py": [
        ("check_nomenclature", lambda v: nom.check_nomenclature(v)),
        ("stages_of", lambda v: nom.stages_of(v)),
        ("is_valid(stage=...)", lambda v: nom.is_valid(v, Nomenclature.AASM)),
        ("is_valid(nomenclature=...)", lambda v: nom.is_valid(SleepStage.N2, v)),
        ("convert(stage=...)", lambda v: nom.convert(v, Nomenclature.AASM)),
        ("convert(target=...)", lambda v: nom.convert(SleepStage.N2, v)),
        ("stage_label", lambda v: nom.stage_label(v)),
        ("stage_code", lambda v: nom.stage_code(v)),
        ("stage_from_code(code=...)", lambda v: nom.stage_from_code(v, Nomenclature.AASM)),
        ("stage_from_code(nomenclature=...)", lambda v: nom.stage_from_code(2, v)),
    ],
    "psglab/core/annotations.py": [
        ("add(onset=...)", lambda v: AnnotationSet().add(Annotation("Arousal", v, 10))),
        ("add(duration=...)", lambda v: AnnotationSet().add(Annotation("Arousal", 0, v))),
        ("color_of", lambda v: AnnotationSet().color_of(v)),
        ("es_color_de_clase", lambda v: es_color_de_clase(v)),
        ("marks_to_annotations(marks=...)", lambda v: marks_to_annotations(v, 100.0, 1000)),
        ("marks_to_annotations(marks=[...])", lambda v: marks_to_annotations([v], 100.0, 1000)),
        ("marks_to_annotations(sampling_rate=...)", lambda v: marks_to_annotations([], v, 1000)),
        ("marks_to_annotations(n_samples=...)", lambda v: marks_to_annotations([], 100.0, v)),
        ("remove_at", lambda v: AnnotationSet().remove_at(v)),
        ("replace(old=...)", lambda v: AnnotationSet().replace(v, Annotation("Arousal", 0, 10))),
        ("replace(new=...)", lambda v: _con_una().replace(Annotation("Arousal", 0, 10), v)),
        ("add(annotation=...)", lambda v: AnnotationSet().add(v)),
        ("add(label=...)", lambda v: AnnotationSet().add(Annotation(v, 0, 10))),
        ("add_label(label=...)", lambda v: AnnotationSet().add_label(v)),
        ("add_label(color=...)", lambda v: AnnotationSet().add_label("Arousal", v)),
        ("remove", lambda v: anotaciones().remove(v)),
        ("in_range(start_sample=...)", lambda v: anotaciones().in_range(v, 100)),
        ("in_range(stop_sample=...)", lambda v: anotaciones().in_range(0, v)),
    ],
    "psglab/core/decimation.py": [
        ("bucket_size_for(n_samples=...)", lambda v: bucket_size_for(v, 10)),
        ("bucket_size_for(n_buckets=...)", lambda v: bucket_size_for(100, v)),
        ("envelope_by_bucket_size(samples=...)", lambda v: envelope_by_bucket_size(v, 10)),
        (
            "envelope_by_bucket_size(bucket_size=...)",
            lambda v: envelope_by_bucket_size(np.zeros(100), v),
        ),
    ],
    "psglab/core/viewport.py": [
        ("Viewport(start=...)", lambda v: Viewport(v, 30.0, 3600.0)),
        ("Viewport(span=...)", lambda v: Viewport(0.0, v, 3600.0)),
        ("Viewport(duration=...)", lambda v: Viewport(0.0, 30.0, v)),
        ("Viewport.clamped(start=...)", lambda v: Viewport.clamped(v, 30.0, 3600.0)),
        ("Viewport.clamped(span=...)", lambda v: Viewport.clamped(0.0, v, 3600.0)),
        ("Viewport.clamped(duration=...)", lambda v: Viewport.clamped(0.0, 30.0, v)),
        ("with_span", lambda v: pagina().with_span(v)),
        ("with_start", lambda v: pagina().with_start(v)),
        ("with_center", lambda v: pagina().with_center(v)),
        ("zoomed", lambda v: pagina().zoomed(v)),
        ("zoomed_at(factor=...)", lambda v: pagina().zoomed_at(v, 10.0)),
        ("zoomed_at(anchor=...)", lambda v: pagina().zoomed_at(0.5, v)),
        ("panned", lambda v: pagina().panned(v)),
        ("for_duration", lambda v: pagina().for_duration(v)),
        ("containing(start=...)", lambda v: pagina().containing(v, 10.0)),
        ("containing(end=...)", lambda v: pagina().containing(0.0, v)),
        ("replaced", lambda v: pagina().replaced(span_seconds=v)),
    ],
    "psglab/core/session.py": [
        ("Session(recording=...)", lambda v: Session(v, Scoring(1, Nomenclature.AASM), AnnotationSet())),
        ("Session(scoring=...)", lambda v: Session(registro(), v, AnnotationSet())),
        ("Session(annotations=...)", lambda v: Session(registro(), Scoring(1, Nomenclature.AASM), v)),
        ("Session(default_scale_uv=...)", lambda v: Session(registro(), Scoring(1, Nomenclature.AASM), AnnotationSet(), v)),
        ("go_to_window", lambda v: sesion().go_to_window(v)),
        ("scale_uv", lambda v: sesion().scale_uv(v)),
        ("set_scale_uv(scale=...)", lambda v: sesion().set_scale_uv("C0", v)),
        ("offset_uv", lambda v: sesion().offset_uv(v)),
        ("set_offset_uv(channel=...)", lambda v: sesion().set_offset_uv(v, 0.0)),
        ("set_offset_uv(offset=...)", lambda v: sesion().set_offset_uv("C0", v)),
        ("center_offsets", lambda v: sesion().center_offsets(v)),
        ("fit_to_pane", lambda v: sesion().fit_to_pane(v)),
        ("set_visible_channels", lambda v: sesion().set_visible_channels([v])),
        ("set_selected_channels", lambda v: sesion().set_selected_channels([v])),
        ("increase_amplitude(factor=...)", lambda v: sesion().increase_amplitude(v)),
        ("decrease_amplitude(factor=...)", lambda v: sesion().decrease_amplitude(v)),
        ("set_active_tool", lambda v: sesion().set_active_tool(v)),
        ("add_window_listener", lambda v: sesion().add_window_listener(v)),
        ("set_viewport", lambda v: sesion().set_viewport(v)),
        ("move_playhead", lambda v: sesion().move_playhead(v)),
        ("add_view_listener", lambda v: sesion().add_view_listener(v)),
        ("set_scoring", lambda v: sesion().set_scoring(v)),
        ("set_recording", lambda v: sesion().set_recording(v)),
    ],
    "psglab/analysis/derivation.py": [
        ("derive(recording=...)", lambda v: derivation.derive(v, "C0", "C1")),
        ("derive(channel_a=...)", lambda v: derivation.derive(registro(), v, "C1")),
        ("derive(channel_b=...)", lambda v: derivation.derive(registro(), "C0", v)),
        ("derive(name=...)", lambda v: derivation.derive(registro(), "C0", "C1", v)),
        ("derive_montage(recording=...)", lambda v: derivation.derive_montage(v, [])),
        ("derive_montage(pairs=...)", lambda v: derivation.derive_montage(registro(), v)),
    ],
    "psglab/analysis/filters.py": [
        ("apply_filters(recording=...)", lambda v: filters.apply_filters(v, {})),
        ("apply_filters(settings=...)", lambda v: filters.apply_filters(registro(), v)),
        ("settings_for_kinds(recording=...)", lambda v: filters.settings_for_kinds(v, {})),
        ("settings_for_kinds(by_kind=...)", lambda v: filters.settings_for_kinds(registro(), v)),
        ("default_for(kind=...)", lambda v: filters.default_for(v)),
        ("default_for(sampling_rate=...)", lambda v: filters.default_for(ChannelKind.EEG, v)),
        ("validate(settings=...)", lambda v: filters.validate(v, 256.0)),
        ("validate(sampling_rate=...)", lambda v: filters.validate(filters.FilterSettings(lowpass_hz=20.0), v)),
    ],
    "psglab/analysis/impedance.py": [
        ("read_impedances", lambda v: impedance.read_impedances(v)),
        ("load_impedances_from_file", lambda v: impedance.load_impedances_from_file(v)),
        ("channels_above_limit(impedances=...)", lambda v: impedance.channels_above_limit(v)),
        ("channels_above_limit(limit_kohm=...)", lambda v: impedance.channels_above_limit({"C0": 4.0}, v)),
        ("impedance_report(impedances=...)", lambda v: impedance.impedance_report(v)),
        ("impedance_report(limit_kohm=...)", lambda v: impedance.impedance_report({"C0": 4.0}, v)),
        ("impedance_report(channels=...)", lambda v: impedance.impedance_report({"C0": 4.0}, 5.0, v)),
    ],
    "psglab/analysis/ica.py": [
        ("fit_ica(recording=...)", lambda v: ica.fit_ica(v)),
        ("fit_ica(n_components=...)", lambda v: ica.fit_ica(registro(), v)),
        ("component_topography(ica=...)", lambda v: ica.component_topography(v, 0)),
        ("component_topography(component=...)", lambda v: ica.component_topography(object(), v)),
        ("component_time_course(ica=...)", lambda v: ica.component_time_course(v, 0, registro())),
        ("component_time_course(recording=...)", lambda v: ica.component_time_course(object(), 0, v)),
        ("explained_variance(ica=...)", lambda v: ica.explained_variance(v, registro())),
        ("explained_variance(recording=...)", lambda v: ica.explained_variance(object(), v)),
        ("apply_ica(recording=...)", lambda v: ica.apply_ica(v, object(), [])),
        ("apply_ica(ica=...)", lambda v: ica.apply_ica(registro(), v, [])),
        ("apply_ica(exclude=...)", lambda v: ica.apply_ica(registro(), object(), v)),
    ],
    "psglab/analysis/complexity.py": [
        ("sample_entropy(signal=...)", lambda v: complexity.sample_entropy(v)),
        ("sample_entropy(m=...)", lambda v: complexity.sample_entropy(SEÑAL, v)),
        ("sample_entropy(r=...)", lambda v: complexity.sample_entropy(SEÑAL, 2, v)),
        ("permutation_entropy(signal=...)", lambda v: complexity.permutation_entropy(v)),
        ("permutation_entropy(order=...)", lambda v: complexity.permutation_entropy(SEÑAL, v)),
        ("lempel_ziv_complexity", lambda v: complexity.lempel_ziv_complexity(v)),
        ("higuchi_fractal_dimension(signal=...)", lambda v: complexity.higuchi_fractal_dimension(v)),
        ("higuchi_fractal_dimension(k_max=...)", lambda v: complexity.higuchi_fractal_dimension(SEÑAL, v)),
        ("complexity_by_window(recording=...)", lambda v: complexity.complexity_by_window(v, ["C0"])),
        ("complexity_by_window(channels=...)", lambda v: complexity.complexity_by_window(registro(), v)),
        ("complexity_by_window(measure=...)", lambda v: complexity.complexity_by_window(registro(), ["C0"], v)),
    ],
    "psglab/analysis/connectivity.py": [
        ("compute_connectivity(recording=...)", lambda v: connectivity.compute_connectivity(v)),
        ("compute_connectivity(channels=...)", lambda v: connectivity.compute_connectivity(registro(), v)),
        ("compute_connectivity(band=...)", lambda v: connectivity.compute_connectivity(registro(), None, v)),
        ("compute_connectivity(method=...)", lambda v: connectivity.compute_connectivity(registro(), None, (0.5, 4.0), v)),
        ("compute_connectivity(window_index=...)", lambda v: connectivity.compute_connectivity(registro(), None, (0.5, 4.0), "wpli", v)),
        ("connectivity_by_window(recording=...)", lambda v: connectivity.connectivity_by_window(v, ["C0", "C1"], (0.5, 4.0))),
        ("connectivity_by_window(channels=...)", lambda v: connectivity.connectivity_by_window(registro(), v, (0.5, 4.0))),
        ("connectivity_by_window(band=...)", lambda v: connectivity.connectivity_by_window(registro(), ["C0", "C1"], v)),
        ("connectivity_by_window(method=...)", lambda v: connectivity.connectivity_by_window(registro(), ["C0", "C1"], (0.5, 4.0), v)),
        ("average_connectivity", lambda v: connectivity.average_connectivity(v)),
    ],
    "psglab/analysis/psd.py": [
        ("validate_band", lambda v: psd.validate_band(v)),
        ("compute_psd(recording=...)", lambda v: psd.compute_psd(v)),
        ("compute_psd(channels=...)", lambda v: psd.compute_psd(registro(), v)),
        ("compute_psd(window_index=...)", lambda v: psd.compute_psd(registro(), None, v)),
        ("compute_psd(method=...)", lambda v: psd.compute_psd(registro(), None, None, v)),
        ("describe_method(method=...)", lambda v: psd.describe_method(v)),
        ("band_power(band=...)", lambda v: psd.band_power(FRECUENCIAS, POTENCIAS, v)),
        ("band_power(relative=...)", lambda v: psd.band_power(FRECUENCIAS, POTENCIAS, (1.0, 4.0), v)),
        ("band_powers_by_window(recording=...)", lambda v: psd.band_powers_by_window(v, ["C0"])),
        ("band_powers_by_window(channels=...)", lambda v: psd.band_powers_by_window(registro(), v)),
        ("band_powers_by_window(bands=...)", lambda v: psd.band_powers_by_window(registro(), ["C0"], v)),
    ],
    "psglab/analysis/reference.py": [
        ("rereference(recording=...)", lambda v: reference.rereference(v, ["C0"])),
        ("rereference(reference_channels=...)", lambda v: reference.rereference(registro(), v)),
        ("average_reference(recording=...)", lambda v: reference.average_reference(v)),
        ("average_reference(kind_only=...)", lambda v: reference.average_reference(registro(), v)),
    ],
    "psglab/analysis/mne_bridge.py": [
        ("to_raw", lambda v: mne_bridge.to_raw(v)),
        ("from_raw(raw=...)", lambda v: mne_bridge.from_raw(v, registro())),
        ("from_raw(original=...)", lambda v: mne_bridge.from_raw(object(), v)),
        ("unidad_de_salida", lambda v: mne_bridge.unidad_de_salida(v)),
    ],
    "psglab/utils/units.py": [
        ("conversion_factor", lambda v: units.conversion_factor(v)),
        ("to_microvolts(unit=...)", lambda v: units.to_microvolts(1.0, v)),
        ("format_amplitude(value_uv=...)", lambda v: units.format_amplitude(v)),
        ("format_amplitude(decimals=...)", lambda v: units.format_amplitude(1.0, v)),
        ("normalize_unit_name", lambda v: units.normalize_unit_name(v)),
        ("is_electrical", lambda v: units.is_electrical(v)),
    ],
    "psglab/utils/validation.py": [
        ("check_finite(value=...)", lambda v: validation.check_finite(v, error=InvalidRecordingError, message="m", details="d")),
        ("check_index(value=...)", lambda v: validation.check_index(v, error=InvalidRecordingError, message="m", details="d")),
    ],
    "psglab/utils/errors.py": [
        ("PsgLabError(message=...)", lambda v: PsgLabError(v)),
        ("PsgLabError(details=...)", lambda v: PsgLabError("m", v)),
    ],
}

CASOS = [
    (modulo, nombre, llamada, hostil)
    for modulo, filas in CONTRATOS.items()
    for nombre, llamada in filas
    for hostil in HOSTILES
]


#: Las guardas que **tienen que rechazar**, con el valor concreto que no puede
#: pasar. La tabla de arriba no alcanza: dice qué tipo de error sale *si* se
#: rechaza, y eso deja verde a un módulo que no rechace nada.
#:
#: Se descubrió generando mutantes del árbol de sintaxis: cuatro guardas de tipo
#: se podían borrar enteras —`if not isinstance(...)` por `if False`— sin que la
#: suite lo notara. La consecuencia de cada una está en su comentario; ninguna
#: falla de forma visible, que es lo que las hace caras.
RECHAZOS_OBLIGATORIOS: list[tuple[str, object, object]] = [
    # Hito 48. **Aceptaban los seis valores hostiles**, y la auditoría de los
    # tests las encontró por eso: sus filas en CONTRATOS eran indistinguibles de
    # un test vacío. La del color además llegaba hasta un bug: el visualizador
    # le concatena la transparencia al texto, y `red` más `55` no es un color.
    ("set_active_tool con algo que no es un nombre", 3.5,
     lambda v: sesion().set_active_tool(v)),
    ("set_active_tool con un nombre en blanco", "   ",
     lambda v: sesion().set_active_tool(v)),
    ("add_label con un color que no es #rrggbb", "red",
     lambda v: AnnotationSet().add_label("Huso", v)),
    ("add_label con un color de ocho dígitos", "#e6754aff",
     lambda v: AnnotationSet().add_label("Huso", v)),
    # Hito 48. **La fila de CONTRATOS no alcanzaba**, y la auditoría de los
    # tests mostró por qué: construye un `Scoring` recién creado, y la
    # validación vivía dentro de la comprensión que traduce las fases ya
    # scoreadas. Sin ninguna scoreada el bucle no itera, así que la fila pasaba
    # en verde mientras el objeto se quedaba con una cadena donde va un enum y
    # el siguiente `export_scoring()` moría con un `AttributeError` crudo.
    ("change_nomenclature con algo que no es una nomenclatura", "basura",
     lambda v: Scoring(3, Nomenclature.AASM).change_nomenclature(v)),
    # Hito 27. `clamp` documenta que no valida: un NaN que pasara de la guarda
    # llegaría a la página como centro, y la reproducción dibujaría la nada
    # veinticinco veces por segundo.
    ("move_playhead con NaN", float("nan"),
     lambda v: sesion().move_playhead(v)),
    # Hito 26. Sin la guarda, un método que no existe caía en la rama del
    # multitaper y el panel describía un cálculo que nadie había hecho.
    ("describe_method con un método que no existe", "fft",
     lambda v: psd.describe_method(v)),
    # Fase 8 del refactor. **Desde que las bandas las escribe el usuario**, una
    # banda invertida es lo esperable de un error de tipeo, y aceptarla integra
    # un rango vacío: la tabla mostraría potencia cero sin ningún aviso.
    ("validate_band con los extremos invertidos", (12.0, 8.0),
     lambda v: psd.validate_band(v)),
    # Fase 7 del refactor. **Mientras se arma la ventana el grafico no tiene
    # ancho**, y ese cero llega como cantidad de cubetas. Sin la guarda sale un
    # ZeroDivisionError, que la ventana principal no sabe atrapar.
    # Desde el hito 49 la cantidad de cubetas la recibe `bucket_size_for()`.
    ("bucket_size_for sin cubetas", 0,
     lambda v: bucket_size_for(1000, v)),
    # `True` es un `int` para Python: sin excluirlo pasaria como una cubeta y
    # la noche entera se dibujaria como dos puntos.
    ("bucket_size_for con un booleano como cubetas", True,
     lambda v: bucket_size_for(1000, v)),
    # Hito 49. Una cubeta de cero muestras es un `reshape` imposible, y el
    # ValueError de numpy atravesaria la ventana.
    ("envelope_by_bucket_size con cubetas vacias", 0,
     lambda v: envelope_by_bucket_size(np.zeros(1000), v)),
    # `Recording.data` es una matriz de canales, y pasarla entera es el error
    # esperable. `argmin` sobre dos dimensiones no falla: devuelve otra cosa.
    ("envelope_by_bucket_size con una matriz de canales", np.zeros((2, 1000)),
     lambda v: envelope_by_bucket_size(v, 10)),
    # Hito 12. **La guarda que MNE no hace.** Se midió: con un pasa-altos de 40
    # y un pasa-bajos de 10, MNE acepta el par, arma una banda eliminada, no
    # emite ningún aviso y devuelve la señal sin atenuar nada. Borrar esta
    # guarda deja al investigador convencido de que filtró.
    ("validate con el pasa-altos por encima del pasa-bajos", 40.0,
     lambda v: filters.validate(filters.FilterSettings(highpass_hz=v, lowpass_hz=10.0), 256.0)),
    # Cero es "sin filtro" para MNE, así que aceptarlo es aceptar en silencio
    # un filtro que no se aplica.
    ("validate con un corte en cero", 0.0,
     lambda v: filters.validate(filters.FilterSettings(highpass_hz=v), 256.0)),
    # `default_for` devuelve una copia. Si devolviera la fila compartida, quien
    # edite lo que recibió le cambia los valores por defecto al programa entero.
    ("default_for con una cadena", "EEG", lambda v: filters.default_for(v)),
    # Un canal sin nombre utilizable se aceptaba y reventaba mucho después, en
    # cualquier lado que pidiera canales por nombre, que es toda la interfaz.
    ("Recording con un canal sin nombre", None,
     lambda v: Recording(Path("x.edf"), [Channel(v, ChannelKind.EEG, "µV", 0)],
                         np.zeros((1, 10)), 100.0)),
    # `channels_of_kind` compara con `is`, así que la cadena "EEG" devolvía la
    # lista vacía: "mostrar todos los EEG" (V3_P) afirmaría que no hay ninguno.
    ("channels_of_kind con una cadena", "EEG",
     lambda v: registro().channels_of_kind(v)),
    # Un tramo que empieza antes del registro devolvía señal **del final**,
    # porque numpy lee el índice negativo como "desde el final".
    ("get_segment desde antes del registro", -1,
     lambda v: registro().get_segment(v, 10)),
    # Hito 50. Con 3.5 el que explotaba era el índice de numpy, con un
    # TypeError crudo; la guarda de rango comparaba bien y lo dejaba pasar.
    ("get_segment con un extremo fraccionario", 3.5,
     lambda v: registro().get_segment(0, v)),
    # `True` es un `int` para Python y se leía como la muestra 1.
    ("get_segment con un booleano como extremo", True,
     lambda v: registro().get_segment(v, 10)),
    # La nomenclatura como cadena se aceptaba y daba `KeyError: 'AASM'` la
    # primera vez que alguien asignaba una fase, lejos de donde estaba el bug.
    ("Scoring con la nomenclatura como cadena", "AASM",
     lambda v: Scoring(3, v)),
    # El arousal se guardaba tal cual: "si" terminaría escrito en Scoring.txt.
    ("set_arousal con una cadena", "si",
     lambda v: Scoring(3, Nomenclature.AASM).set_arousal(0, v)),
    # Segunda tanda. `stage_code` alimenta la línea de `Scoring.txt`: una fase
    # que no es fase escribiría basura en el archivo del investigador.
    ("stage_code con una cadena", "N2", lambda v: nom.stage_code(v)),
    # `stages_of` da las filas del histograma; con una nomenclatura equivocada
    # daba `KeyError` y la ventana principal mostraba una traza.
    ("stages_of con una cadena", "AASM", lambda v: nom.stages_of(v)),
    # La unidad llega de la cabecera de un EDF o un BrainVision. Es entrada
    # externa, no un valor que arme el programa.
    ("normalize_unit_name con None", None, lambda v: units.normalize_unit_name(v)),
    # El factor cero dividía por cero al subir la amplitud.
    ("increase_amplitude con factor cero", 0, lambda v: sesion().increase_amplitude(v)),
    # Una etiqueta que no es texto se usaba como clave de un diccionario.
    ("add_label con None", None, lambda v: AnnotationSet().add_label(v)),
    # Guardar algo que no es una anotación reventaba al pedirle `.label`.
    ("add con algo que no es una anotación", "Arousal", lambda v: AnnotationSet().add(v)),
    # Hito 52. Reemplazar por algo que no es una anotación tiene que rechazarse
    # **antes** de sacar la vieja: si no, se pierde el evento que se corregía.
    ("replace por algo que no es una anotación", "Arousal",
     lambda v: _con_una().replace(Annotation("Arousal", 0, 10), v)),
    # Hito 4. La frecuencia original de un canal se muestra al lado de su
    # nombre: un NaN se leería como "nan Hz" en la lista de canales, y un cero
    # afirmaría que el canal no trae ninguna muestra por segundo.
    ("Channel con frecuencia original NaN", float("nan"),
     lambda v: Recording(Path("x.edf"), [Channel("C0", ChannelKind.EEG, "µV", 0, v)],
                         np.zeros((1, 10)), 100.0)),
    ("Channel con frecuencia original cero", 0,
     lambda v: Recording(Path("x.edf"), [Channel("C0", ChannelKind.EEG, "µV", 0, v)],
                         np.zeros((1, 10)), 100.0)),
    # Hito 33. **Una banda bien formada que no se puede medir.** Sin la guarda,
    # mne-connectivity elevaba `ValueError` y el cartel no salía: la traza iba a
    # la consola. El registro es de 100 Hz, así que Nyquist queda en 50.
    ("compute_connectivity con una banda sobre Nyquist", (60.0, 90.0),
     lambda v: connectivity.compute_connectivity(registro(), None, v, "wpli", 0)),
    ("compute_connectivity con una banda más angosta que la resolución", (10.05, 10.15),
     lambda v: connectivity.compute_connectivity(registro(), None, v, "wpli", 0)),
    # Y la noche no puede tragárselo como si fueran ventanas cortas: saldría
    # entera en NaN sin avisar.
    ("connectivity_by_window con una banda sobre Nyquist", (60.0, 90.0),
     lambda v: connectivity.connectivity_by_window(registro(), ["C0", "C1"], v)),
]


@pytest.mark.parametrize(
    ("modulo", "nombre", "llamada", "hostil"),
    CASOS,
    ids=[f"{n}[{h!r}]" for _, n, _, h in CASOS],
)
def test_una_entrada_hostil_sale_como_error_del_programa(modulo, nombre, llamada, hostil):
    """Si el valor se rechaza, tiene que rechazarse con un `PsgLabError`.

    No se exige que **todo** valor hostil sea rechazado: algunos son legítimos
    para algunas firmas —un `3.5` de escala es un número finito y válido— y
    aceptarlos está bien. Lo que no está bien es rechazarlo con una traza.
    """
    try:
        llamada(hostil)
    except PsgLabError:
        pass
    except Exception as error:  # noqa: BLE001 - es justamente lo que se persigue
        pytest.fail(
            f"{nombre} con {hostil!r} elevó {type(error).__name__}, que no hereda de "
            f"PsgLabError y escaparía del except de la interfaz: {error}"
        )


@pytest.mark.parametrize(
    ("nombre", "valor", "llamada"),
    RECHAZOS_OBLIGATORIOS,
    ids=[n for n, _, _ in RECHAZOS_OBLIGATORIOS],
)
def test_una_guarda_de_tipo_no_se_puede_borrar_sin_que_nada_avise(nombre, valor, llamada):
    """El complemento del test de arriba: acá el valor **no puede** pasar.

    Aceptar en silencio es la peor de las tres salidas. Un `TypeError` crudo al
    menos se ve; un valor aceptado sigue viaje y reaparece mucho más lejos,
    convertido en señal equivocada, en una lista vacía o en una línea rara de
    `Scoring.txt`.
    """
    with pytest.raises(PsgLabError):
        llamada(valor)


def test_la_tabla_cubre_los_modulos_implementados():
    """Una fila que apunte a un módulo inexistente dejaría de proteger nada."""
    raiz = Path(__file__).resolve().parent.parent
    inexistentes = [m for m in CONTRATOS if not (raiz / m).exists()]
    assert not inexistentes, f"la tabla nombra módulos que no existen: {inexistentes}"
