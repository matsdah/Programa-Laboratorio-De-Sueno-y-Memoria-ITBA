# Incidente: caída de Qt con PySide6 6.12.0

**Abierto el 11 de octubre de 2026 (hora local; 12 de octubre UTC).** Al
integrar el PR [#171](https://github.com/matsdah/Programa-Laboratorio-De-Sueno-y-Memoria-ITBA/pull/171), el CI de Linux empezó a abortar durante la suite
con PySide6/Shiboken 6.12.0 y Python 3.11. El cambio del PR no introdujo una
falla reproducible en la combinación anterior.

## Evidencia y línea de tiempo

- El PR #171 pasó los **4983 tests aprobados y 25 salteados** en macOS con
  PySide6 6.11.2.
- Con las versiones más nuevas resueltas por el CI, Linux/Python 3.11 terminó
  dos veces con código 134 tras el reintento automático del mismo run. GitHub
  lo atribuyó a
  [`tests/test_entrega.py::test_exportar_escribe_el_scoring_y_despues_cierra`](https://github.com/matsdah/Programa-Laboratorio-De-Sueno-y-Memoria-ITBA/actions/runs/38190630204),
  un test de scoring. El test aislado pasó, pero ese nombre no demuestra que
  fallara su cuerpo: la traza posterior ubicó el aborto antes, al construir
  fixtures.
- El [run de diagnóstico](https://github.com/matsdah/Programa-Laboratorio-De-Sueno-y-Memoria-ITBA/actions/runs/38191535741)
  expuso `none_dealloc` durante la construcción de un fixture:
  `ConnectivityPanel` → `pyqtgraph.ColorBarItem` → `PlotItem` →
  `plotConfigTemplate_generic.retranslateUi`, línea 161. La evidencia apunta a
  un error nativo relacionado con el conteo de referencias; no identifica por
  sí sola qué cambio de upstream lo causa.
- Se excluyó únicamente PySide6/Shiboken 6.12.0 y se seleccionó PySide6 6.11.2.
  Con esa resolución, [los ocho checks del CI pasaron](https://github.com/matsdah/Programa-Laboratorio-De-Sueno-y-Memoria-ITBA/actions/runs/38191881930).
- El PR #171 se integró en `Add` como `5162d64`.

## Interpretación y alcance

La combinación del aborto nativo y `none_dealloc` es evidencia de un problema
de referencias. Además, en el sondeo controlado, cuatro setters Qt void
perdieron una referencia a `None` por llamada en PySide6 6.12.0 y no en
6.11.2. Esto reproduce un comportamiento específico de esa versión y de esas
llamadas, pero no demuestra que cada setter afectado cause el aborto original.
Las ruedas de PySide6, Shiboken y Qt cambiaron juntas entre las dos versiones,
así que los controles no identifican cuál componente contiene el defecto.
**No se confirmó un culpable exacto ni un arreglo upstream.**

La restricción vigente en `requirements.txt` es `PySide6>=6.6,!=6.12.0`: acota
el problema observado y permite resolver versiones posteriores. No demuestra
que 6.12.0 falle en todos los usos ni que 6.11.2 esté libre de cualquier
defecto. Se conserva la versión que pasó la matriz y se mantiene la
investigación reproducible en
[`scripts/diagnose_qt_refcount.py`](../scripts/diagnose_qt_refcount.py).

## Reproducción controlada

Los sondeos corrieron en Linux amd64 sobre `python:3.11-slim`, mediante Docker
amd64 en una Mac arm64. El digest observado para esa etiqueta fue
`python@sha256:e88e9763f943ec1834f992a4b51e0f24500486803e8bc534e5767af9ea65f6ce`;
los comandos de abajo usaron la etiqueta, no fijaron el digest. Las
comparaciones de `PlotItem` usaron CPython 3.11.17,
PySide6/Qt 6.12.0 o 6.11.2 y pyqtgraph 0.14.0. Los setters y controles de
traducción también se midieron con esas versiones; además, se repitió
`QObject.setObjectName()` y el modo de traductor parentado en un entorno limpio
con PySide6/Shiboken/Qt, sin instalar ni importar pyqtgraph. Cada modo corrió
en su propio proceso. El contenedor instaló las librerías de Qt del job Linux,
creó los entornos `/tmp/v612` y `/tmp/v611` y resolvió las versiones indicadas.
Estos son los argv de las primeras comparaciones que se ejecutaron dentro del
contenedor:

```bash
/tmp/v612/bin/python /probe.py --mode settext --iterations 500 --sample-every 50
/tmp/v612/bin/python /probe.py --mode tooltip --iterations 500 --sample-every 50
/tmp/v612/bin/python /probe.py --mode spinbox --iterations 500 --sample-every 50
/tmp/v612/bin/python /probe.py --mode objectname --iterations 500 --sample-every 50
/tmp/v611/bin/python /probe.py --mode settext --iterations 500 --sample-every 50
/tmp/v611/bin/python /probe.py --mode tooltip --iterations 500 --sample-every 50
/tmp/v611/bin/python /probe.py --mode spinbox --iterations 500 --sample-every 50
/tmp/v611/bin/python /probe.py --mode objectname --iterations 500 --sample-every 50
/tmp/v612/bin/python /probe.py --mode translate --translation native-es --iterations 500 --sample-every 50
/tmp/v612/bin/python /probe.py --mode translator-owner --drop-translator-wrapper --iterations 500 --sample-every 50
/tmp/v612/bin/python /probe.py --mode plotitem --iterations 20 --sample-every 1
/tmp/v611/bin/python /probe.py --mode translate --translation native-es --iterations 500 --sample-every 50
/tmp/v611/bin/python /probe.py --mode plotitem --iterations 20 --sample-every 1
/tmp/v612/bin/python /probe.py --mode translate --iterations 500 --sample-every 50
/tmp/v612/bin/python /probe.py --mode translator --iterations 500 --sample-every 50
```

En el entorno limpio sin pyqtgraph, los procesos adicionales fueron:

```bash
/tmp/v612/bin/python /probe.py --mode objectname --iterations 500 --sample-every 50
/tmp/v611/bin/python /probe.py --mode objectname --iterations 500 --sample-every 50
/tmp/v612/bin/python /probe.py --mode translator-owner --iterations 500 --sample-every 50
```

Esta fue la invocación completa de Docker para esos tres procesos:

```bash
docker run --rm --platform linux/amd64 -v /Users/fran/psglab-qt-refcount/scripts/diagnose_qt_refcount.py:/probe.py:ro -v qt-refcount-pip-cache:/root/.cache/pip python:3.11-slim sh -c 'apt-get update -qq && apt-get install -y -qq libegl1 libgl1 libxkbcommon0 libdbus-1-3 libglib2.0-0 libfontconfig1 libfreetype6 >/dev/null && python -m venv /tmp/v612 && /tmp/v612/bin/pip install -q PySide6==6.12.0 && python -m venv /tmp/v611 && /tmp/v611/bin/pip install -q PySide6==6.11.2 && /tmp/v612/bin/python /probe.py --mode objectname --iterations 500 --sample-every 50 && /tmp/v611/bin/python /probe.py --mode objectname --iterations 500 --sample-every 50 && /tmp/v612/bin/python /probe.py --mode translator-owner --iterations 500 --sample-every 50'
```

La salida de esos procesos confirmó `pyqtgraph_imported=false`.

En la revisión inicial del script, que agrupaba pruebas en modo `all`, el
traductor parentado con wrapper retenido se midió con
`/tmp/v612/bin/python /probe.py --mode all --iterations 500 --sample-every 50`:
la carga e instalación dieron resultado positivo y las 500 llamadas de esa
sección quedaron planas (delta 0).

Las llamadas a `QLabel.setText()`, `QWidget.setToolTip()`,
`QSpinBox.setValue()` y `QObject.setObjectName()` bajaron el conteo de
referencias de `None` exactamente en una por llamada en 6.12.0 (−500 en 500
llamadas para cada método); en 6.11.2 los cuatro conteos quedaron planos
(delta 0). Además, `QObject.setObjectName()` se repitió sin pyqtgraph instalado
ni importado: volvió a dar −500 en 6.12.0 y delta 0 en 6.11.2. En cambio,
`QCoreApplication.translate()` quedó plano en ambos
bindings con el traductor nativo español: el hit
`QDialogButtonBox/OK` devolvió `Aceptar`, el miss `Form/Peak` devolvió `Peak`,
y también quedó plano el conteo en el modo de traductor nativo parentado, tanto
con el wrapper Python retenido como después de descartarlo. Ese control del
traductor parentado se hizo con 6.12.0. Los cuatro modos de setters
ejercitaron llamadas Qt directas sin invocar código de PSGLab ni operaciones
de pyqtgraph. Estos controles acotan el hallazgo a las llamadas void de Qt
ejercitadas; no justifican cambios en la traducción ni en la aplicación para
reproducirlo.

`pyqtgraph.PlotItem()` bajó el conteo en 6.12.0 en exactamente 245 por
construcción/eliminación, desde 14141; la corrida acotada pidió 20 iteraciones
y se detuvo tras 17, al cruzar el umbral de 10000 (el conteo quedó en 9976).
En una corrida previa que pidió 500 iteraciones, la muestra de la iteración 50
ya mostraba −12250 (conteo 1894 desde 14144); el proceso luego terminó con
`none_dealloc` dentro de la operación, sin completar las 500. En 6.11.2, el
mismo sondeo acotado de 20 iteraciones subió 322 por operación. La corrida
acotada usó el piso predeterminado de 10000 de esa revisión del script. Son conteos globales
de referencias de `None`, no una medida directa de la fuga por sí sola; el
aumento en 6.11.2 puede reflejar referencias de objetos retenidos y no prueba
por sí mismo ausencia de errores o seguridad de memoria. La comparación con
`PlotItem` debe leerse junto a los controles de setters.

La medición del recuento requiere un `None` mortal. En CPython 3.12 y
posteriores, `None` es inmortal, así que este método no puede detectar la
deriva descrita; ver la [documentación de la API C de Python](https://docs.python.org/3/c-api/none.html#c.Py_None).

## Cuándo retirar la exclusión

Retirar `!=6.12.0` sólo después de que PySide6 6.12.0, con la corrección
correspondiente, termine sin aborto en el sondeo controlado y pase toda la
matriz Linux del CI. Una versión futura que ya admite la restricción actual se
evalúa por separado: puede seguir habilitada si la matriz Linux pasa, pero eso
no demuestra que 6.12.0 esté corregida. Registrar la versión, el entorno y los
enlaces a cada corrida antes de cambiar la selección.
