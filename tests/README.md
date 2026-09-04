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
camino de búsqueda. Con `pytest` directo la recolección falla en los cinco
archivos con `ModuleNotFoundError: No module named 'psglab'`.

## Mientras el proyecto sea un esqueleto

Los 42 tests están **desactivados**, con esta línea al tope de cada archivo:

```python
pytestmark = pytest.mark.skip(reason="Esqueleto: la lógica todavía no está implementada.")
```

La corrida informa `42 skipped` y pasa en verde sin haber verificado nada.

**Al implementar un componente hay que borrar esa línea del archivo de test que
le corresponde.** Si no, el trabajo queda sin verificar y la suite sigue dando
verde por omisión, que es peor que dar rojo.

## Los archivos

| Archivo | Qué verifica |
|---|---|
| `conftest.py` | Fixtures compartidas: señal sintética y nombres de canal. |
| `test_scoring.py` | Fases, arousals y cambio de nomenclatura. |
| `test_nomenclature.py` | Las dos nomenclaturas y la conversión entre ellas. |
| `test_windows.py` | Conversión entre ventanas, muestras y tiempo. |
| `test_occupancy.py` | La herramienta de ocupación horizontal. |
| `test_exporters.py` | El formato exacto de los archivos de salida. |

Los de `core/` y `exporters/` corren sin interfaz gráfica, que es justamente el
motivo por el que `core/` no importa nada de `ui/`.

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
