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
camino de búsqueda. Con `pytest` directo la recolección falla en los seis
archivos con `ModuleNotFoundError: No module named 'psglab'`.

## Mientras el proyecto sea un esqueleto

Los tests de los módulos que todavía no están implementados están
**desactivados**, con esta línea cerca del principio del archivo:

```python
pytestmark = pytest.mark.skip(reason="Esqueleto: la lógica todavía no está implementada.")
```

Los llevan cuatro de los seis archivos: `test_windows.py` corre desde que se
implementó `core/windows.py`, y `test_consistencia.py` no cubre ningún módulo,
así que corre siempre. Buena parte de la suite pasa entonces en verde sin haber
verificado nada del programa.

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
| `test_scoring.py` | Fases, arousals y cambio de nomenclatura. |
| `test_nomenclature.py` | Las dos nomenclaturas y la conversión entre ellas. |
| `test_windows.py` | Conversión entre ventanas, muestras y tiempo. |
| `test_occupancy.py` | La herramienta de ocupación horizontal. |
| `test_exporters.py` | El formato exacto de los archivos de salida. |

Los de `core/` y `exporters/` corren sin interfaz gráfica, que es justamente el
motivo por el que `core/` no importa nada de `ui/`.

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

- **Reactivar** (borrar el `pytestmark`): `test_nomenclature` (hito 1),
  `test_scoring` (2), `test_exporters` (5), `test_occupancy` (7).
  `test_windows` ya está reactivado.
- **Crear**: `test_units`, `test_recording` (1), `test_annotations` (2),
  `test_session` (3), `test_channel_types`, `test_readers` (4), y uno por
  herramienta (7).

`psglab/ui/` no lleva tests unitarios: es deliberado, no una omisión.
