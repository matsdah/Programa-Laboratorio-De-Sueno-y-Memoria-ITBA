# `tests/` — un test por componente

## Cómo se corren

**Siempre con `python -m pytest`, nunca con `pytest` a secas.**

```bash
python -m pytest
python -m pytest tests/test_scoring.py
python -m pytest tests/test_scoring.py::test_el_arousal_es_independiente_de_la_fase
python -m pytest -rs
```

El proyecto no se instala como paquete (no hay `pyproject.toml`), así que
`psglab` sólo es importable porque `python -m` agrega el directorio actual al
camino de búsqueda. Con `pytest` directo la recolección falla en los veintinueve
archivos que importan `psglab` al cargarse, con
`ModuleNotFoundError: No module named 'psglab'`.

## Los tests que se apagan, y por qué hoy no hay ninguno

Los tests de los módulos que todavía no están implementados están
**desactivados**, con esta línea cerca del principio del archivo:

```python
pytestmark = pytest.mark.skip(reason="Esqueleto: la lógica todavía no está implementada.")
```

La llevan **los tests de los hitos que todavía no se abrieron**: hoy ninguno.
El último era el de la ocupación, y el hito 7 lo reactivó, así que **la suite ya
no informa ningún salteado** en una máquina con los registros de prueba.

**Los números concretos —cuántos se recolectan y cuántos se saltean— no se
escriben acá**, porque un número a mano en este archivo se desactualiza con el
primer módulo que se implemente. Ya pasó: decía `42 skipped` mucho después de
que dejaran de ser 42. Para verlos, la corrida:

```bash
python -m pytest -rs
```

**Al implementar un componente hay que borrar esa línea del archivo de test que
le corresponde.** Si no, el trabajo queda sin verificar y la suite sigue dando
verde por omisión, que es peor que dar rojo.

## Los archivos

| Archivo | Qué verifica |
|---|---|
| `conftest.py` | Fixtures compartidas: señal sintética y nombres de canal. |
| `test_consistencia.py` | **El repositorio, no un componente.** Ver abajo. |
| `test_errors.py` | Que el mensaje y la causa técnica viajen separados, y que un solo `except` las atrape todas. |
| `test_validation.py` | Que un NaN no atraviese una guarda numérica. |
| `test_contratos.py` | Que ningún método público escape del `except` de la interfaz. |
| `test_units.py` | La conversión a microvoltios, sobre todo con entrada sucia. |
| `test_windows.py` | Conversión entre ventanas, muestras y tiempo. |
| `test_nomenclature.py` | Las dos nomenclaturas, la conversión entre ellas y los códigos de `Scoring.txt`. |
| `test_recording.py` | El registro en memoria y lo que no deja construir. |
| `test_scoring.py` | Fases, arousals y cambio de nomenclatura. |
| `test_session.py` | Navegación, canales y amplitud, sin abrir una ventana. |
| `test_annotations.py` | Los eventos sobre la señal: qué se borra y qué se dibuja. |
| `test_channel_types.py` | Que cada canal se clasifique solo: EEG, EOG, EMG, ECG u otro. |
| `test_readers.py` | El despacho por formato, y que la señal de un EDF y un BrainVision salga en la escala correcta. |
| `test_scoring_reader.py` | Importar un scoring ya hecho sin adivinar con qué nomenclatura se escribió. |
| `test_registry.py` | El registro de herramientas y su clase base: el punto de extensión. |
| `test_amplitude_band.py` | La banda de 75 µV, y sobre qué canal se dibuja. |
| `test_occupancy.py` | La ocupación horizontal: los ejemplos del pliego y el gesto del mouse. |
| `test_magnifier.py` | La lupa y su contador de picos, que se cuenta sin dibujar nada. |
| `test_annotator.py` | Anotar un evento, y que los segundos lleguen a la muestra correcta. |
| `test_overview.py` | El panel de contexto: qué ventanas muestra y qué eventos caen en ellas. |
| `test_histogram.py` | El hipnograma de la noche y la navegación por clic. |
| `test_shortcuts.py` | Los atajos, y que los de fase se deriven de la nomenclatura. |
| `test_grid.py` | La grilla de fondo: cuántas líneas y dónde caen. |
| `test_overview_panel.py` | El panel de contexto: qué ventanas entran, cuál es la actual y dónde va cada una. |
| `test_signal_view.py` | Las tres conversiones desde píxeles, que es de donde salen las unidades de las herramientas. |
| `test_exporters.py` | El formato exacto de los archivos de salida. |
| `test_mne_bridge.py` | El puente con MNE: que ida y vuelta devuelva lo mismo, y que un termómetro no se escale como si fuera un EEG. |
| `test_derivation.py` | Las derivaciones: una resta exacta, y qué clase y qué unidad lleva el canal nuevo. |
| `test_reference.py` | La re-referenciación: el canal de referencia en cero, y la suma de los EEG en cero. |
| `test_entrega.py` | La comprobación de entrega: abrir, navegar, scorear y exportar **por la ventana**, no por las piezas. |

Los de `core/` y `exporters/` corren sin interfaz gráfica, que es justamente el
motivo por el que `core/` no importa nada de `ui/`.

## Las fixtures, y por qué la señal ya existe

`synthetic_signal` y `channel_names` fijan un contrato que conviene conocer
antes de escribir un test nuevo: cuatro canales de diez minutos —**exactamente
veinte ventanas de 30 segundos**, un número cómodo para verificar las cuentas a
mano—, con C3 a 1 Hz, C4 a 10 Hz, el EOG a 0,5 Hz y el EMG a 30 Hz, y nombres
10-20 para que la detección automática de clase tenga qué detectar.

`test_recording.py` fue su primer consumidor y `test_readers.py` el siguiente:
no hizo falta inventar otra señal.

## `test_consistencia.py` no testea un componente

Es la excepción del directorio: verifica invariantes **del repositorio entero**,
no de un módulo. Que las cuentas del TODO cierren contra el código, que los
enlaces de la documentación no apunten a la nada, que los IDs del pliego que
declara cada módulo coincidan con `TRAZABILIDAD.md` en las dos direcciones, que
`EXPLICACION.txt` siga en ASCII, que las capas de negocio no hayan empezado a
importar Qt.

La regla que ordena los IDs, y que es la que más se rompía sola:

> Un módulo nombra un ID en su docstring **si y sólo si** `TRAZABILIDAD.md` se
> lo asigna a ese archivo.

Un módulo que no cubre ninguno no los nombra —ni siquiera para decir que no los
cubre, porque el chequeo los lee de esa línea y no distingue una mención de una
declaración— y a cambio tiene que figurar en la tabla de módulos de
infraestructura o en una fila de la Parte 2 sin ID.

Existe porque el equipo pasó a ser de tres personas. Con una, revisar eso a mano
alcanza; con tres, la documentación se desincroniza más rápido de lo que alguien
la mira. No es una hipótesis: dos auditorías seguidas encontraron divergencias
introducidas pocos días antes.

Dos de sus tests merecen mención:

- **`test_ningun_modulo_terminado_tiene_su_test_salteado`** cierra el agujero más
  silencioso del repositorio. Si alguien implementa un módulo y se olvida de
  borrar el `pytestmark`, la suite sigue informando "passed" y el trabajo queda
  sin verificar. Necesita el mapa `COBERTURA_DE_TESTS`: **al agregar un archivo
  de test hay que agregarle su fila**, y hay un test que lo verifica.
- **`test_todos_los_modulos_del_paquete_se_pueden_importar`** es lo único que
  ejercita `psglab/ui/`, porque la interfaz no lleva tests unitarios. Sin él, un
  error de importación en la capa gráfica —una biblioteca de sistema que falta
  en Linux— no aparecería hasta que alguien abriera el programa.

## Señal sintética, nunca datos reales

Las fixtures de `conftest.py` generan el registro **en el momento**. Nunca se
suben registros de participantes al repositorio.

Además de la privacidad, hay una razón técnica: **un registro sintético tiene el
resultado correcto conocido de antemano.** Si se genera una onda de 10 Hz, la
PSD tiene que dar un pico en 10 Hz, y eso se puede afirmar en un test. Con un
registro real no habría contra qué comparar.

La fixture `synthetic_signal` son diez minutos de cuatro canales en µV, cada uno
con una frecuencia coherente con el tipo de señal que representa:

| Canal | Frecuencia | Por qué |
|---|---|---|
| `C3` | 1 Hz | Delta, sueño lento |
| `C4` | 10 Hz | Alfa |
| `EOG-izq` | 0,5 Hz | Movimientos oculares lentos |
| `EMG-menton` | 30 Hz | Actividad muscular |

Diez minutos son **exactamente 20 ventanas de 30 segundos**, un número cómodo
para verificar los cálculos a mano.

Los nombres cubren las cuatro clases que el pliego nombra en V1_P y sirven
además para testear la detección automática de clase (V4_F): "C3" tiene que
detectarse como EEG por su nombre 10-20, y "EMG-menton" como EMG por su prefijo.

## Al agregar un componente

Regla del pliego (sección 7): **cada componente agregado viene con su test.**

Los nombres de los tests son frases en español que describen la regla que se
verifica, no `test_funcion_1`:

```python
def test_se_puede_scorear_una_ventana_alejada_sin_pasar_por_las_anteriores(scoring):
    ...
```

El nombre es lo que aparece cuando el test falla, así que tiene que decir **qué
regla se rompió**, no qué función se llamó.

## Estado

El [TODO](../docs/TODO.md) lleva la cuenta. Cada módulo que se implementa
arrastra su test, y **eso es parte de darlo por terminado**:

**De la Parte 1 no queda ninguno por escribir ni por reactivar.** Los nueve de
los hitos 1 a 3 —`test_units`, `test_windows`, `test_nomenclature`,
`test_recording`, `test_errors`, `test_validation`, `test_scoring`,
`test_annotations` y `test_session`—, los tres del hito 4, `test_exporters` del
hito 5, los tres de `ui/` del hito 6 y los siete del hito 7 están todos
corriendo, y `test_exporters` cubre los cuatro exportadores, `statistics.py` e
`information_txt.py` incluidos.

Lo que queda es la **Parte 2**: `psglab/analysis/` no tiene ningún test todavía,
y sus ocho módulos siguen en stubs.

**De `psglab/ui/` se testea lo que no dibuja** —los atajos, la grilla y las tres
conversiones desde píxeles—, y el dibujo no. Es deliberado y está explicado en
[`ui/README.md`](../psglab/ui/README.md#estado).
