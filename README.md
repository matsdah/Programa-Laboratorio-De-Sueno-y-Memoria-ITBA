# Programa Open Source — Laboratorio de Sueño y Memoria ITBA

Software libre y multiplataforma para **visualizar registros de polisomnografía (PSG),
hacer o corregir el scoring de sueño y anotar eventos**, con un módulo de análisis de
bioseñales (PSD, complejidad, conectividad).

Nace para resolver las limitaciones de los programas actuales: formatos de importación
limitados, scoring sólo manual, imposibilidad de anotar la señal, ausencia de métricas,
compatibilidad únicamente con Windows y precios excesivos.

> **Estado: la Parte 1 está terminada.** `python main.py` abre el programa:
> importa registros en EDF y BrainVision, muestra la señal en ventanas de
> 30 segundos, se navega y se scorea con el teclado, se anotan eventos, están
> las seis herramientas —lupa, banda de amplitud, ocupación, Übersicht,
> histograma y anotador— y se exportan los tres archivos de salida. Toda la
> lógica se testea **sin abrir una ventana**.
>
> Falta el **módulo de análisis de bioseñales** (`psglab/analysis/`), que es la
> Parte 2: esos módulos declaran su interfaz y elevan `NotImplementedError`.
>
> **Por dónde seguir: [`docs/TODO.md`](docs/TODO.md)**, que ordena el trabajo en
> hitos por dependencias y es el único lugar que lleva la cuenta de lo que
> falta.

---

## Instalación

Necesitás **Python 3.11 o superior**. Si no lo tenés, descargalo de
[python.org/downloads](https://www.python.org/downloads/) y, durante la instalación en
Windows, marcá la casilla **"Add Python to PATH"**.

```bash
# 1. Ubicate en la carpeta del proyecto
cd Programa-Laboratorio-De-Sueno-y-Memoria-ITBA

# 2. Creá un entorno virtual (aísla las dependencias del resto de tu computadora)
python -m venv .venv
#    En Debian, Ubuntu y WSL el binario se llama python3, no python:
python3 -m venv .venv
#    (si eso falla, falta el paquete: sudo apt install python3-venv)

# 3. Activalo
#    Windows (PowerShell):
.venv\Scripts\Activate.ps1
#    macOS / Linux:
source .venv/bin/activate

# 4. Comprobá que estás adentro ANTES de instalar: tiene que imprimir la
#    carpeta .venv del proyecto y no otra ruta.
python -c "import sys; print(sys.prefix)"

# 5. Instalá las dependencias
pip install -r requirements.txt
```

> **Un `.venv` por sistema operativo.** Si trabajás sobre la misma carpeta
> desde Windows y desde WSL, no compartas el entorno. Correr
> `python3 -m venv .venv` desde WSL **sobrescribe el `pyvenv.cfg`** del entorno
> de Windows y lo deja apuntando al intérprete de Linux. En el momento no avisa
> nada: el que falla es el comando siguiente, con
> `did not find executable at '/usr/bin\python.exe'`.
>
> Los paquetes ya instalados **no se pierden** —el daño es ese único archivo— y
> se repara regenerándolo desde Windows, sin reinstalar nada:
>
> ```bash
> python -m venv --upgrade .venv
> ```
>
> Para usar los dos a la vez, dale al de WSL un directorio propio con
> `python3 -m venv .venv-linux`. El `.gitignore` ya excluye cualquier `.venv*/`.

> **Y uno por versión de Python.** La misma rotura ocurre sin WSL de por medio:
> instalar otro Python —el instalador nuevo de python.org deja los suyos en
> `%LOCALAPPDATA%\Python\pythoncore-3.X-64`— y volver a correr
> `python -m venv .venv` sobre el entorno que ya existe le reescribe el
> `pyvenv.cfg` apuntando al intérprete nuevo, **sin tocar los paquetes**, que
> siguen compilados para el viejo.
>
> El síntoma no menciona el entorno para nada:
>
> ```
> No module named 'numpy._core._multiarray_umath'
> ```
>
> Se diagnostica mirando `.venv/pyvenv.cfg` —la línea `version` dice una cosa y
> los `.pyd` de `.venv/Lib/site-packages/numpy/_core/` dicen `cp312`, `cp314`,
> otra— y se repara sin reinstalar nada, apuntando `home` y `version` de vuelta
> al intérprete con el que se creó el entorno. Si eso no alcanza:
>
> ```bash
> python -m venv --clear .venv
> ```
>
> y reinstalar los requirements. **Nunca corras `python -m venv` sobre un
> `.venv` que ya existe** salvo con `--upgrade`, que es lo que sirve para esto.

> **Y uno por ruta.** El entorno tampoco sobrevive a que le renombren o le
> muevan la carpeta: cada `.exe` de `Scripts/` —`pip`, `pytest`,
> `pip-licenses`— lleva grabada adentro la ruta absoluta del intérprete. Después
> de un renombre fallan todos con `Fatal error in launcher: Unable to create
> process using '...'`, citando la ruta vieja.
>
> El `python.exe` del entorno **sí** sigue funcionando, así que `python -m pip` y
> `python -m pytest` no se enteran y el problema queda latente. Acá se descubrió
> recién al correr el `pip install` de esta misma sección.
>
> No hay nada que rescatar: se borra `.venv` y se rehace con los pasos de arriba.

> **En Windows, `Activate.ps1` falla la primera vez.** Es la Execution Policy de
> PowerShell, que de fábrica no deja correr ningún script: *"la ejecución de
> scripts está deshabilitada en este sistema"*. Se arregla dándole permiso a tu
> usuario —alcanza con eso, no hace falta administrador, y es una sola vez—:
>
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```
>
> **Lo caro no es el error sino lo que viene después.** El error se ve, se
> ignora, y todo lo demás aparenta funcionar: con el entorno sin activar,
> `pip install` instala en el Python global y `python main.py` arranca igual. El
> proyecto no falla hasta mucho más tarde, cuando ya nadie relaciona una cosa con
> la otra. Por eso el paso 4 existe.
>
> Si preferís no tocar la política, **no hace falta activar**. Invocar el
> intérprete del entorno por su ruta hace exactamente lo mismo, esquiva la
> política y no puede equivocarse de Python:
>
> ```powershell
> .venv\Scripts\python.exe -m pip install -r requirements.txt
> .venv\Scripts\python.exe -m pytest
> ```

Para correr los tests, instalá además las herramientas de desarrollo:

```bash
pip install -r requirements-dev.txt
```

Y sólo si vas a trabajar en la Parte 2 (el módulo de análisis), sus dos
dependencias propias, que son pesadas y no hacen falta para nada más:

```bash
pip install -r requirements-analysis.txt
```

## Ejecución

```bash
python main.py
```

## Estructura del proyecto

**Cada carpeta tiene su propio README** con el mapa de sus archivos, las reglas
que la gobiernan y cómo extenderla.

| Carpeta | Responsabilidad | |
|---|---|---|
| `main.py` | Punto de entrada. Sólo orquesta: crea la app y abre la ventana. | |
| [`psglab/`](psglab/README.md) | El paquete del programa: capas, `app.py` y `config.py`. | [→](psglab/README.md) |
| [`psglab/readers/`](psglab/readers/README.md) | Importación de archivos (BrainVision, EDF, scoring existente). | [→](psglab/readers/README.md) |
| [`psglab/core/`](psglab/core/README.md) | Modelo de datos y reglas de negocio. **No depende de la interfaz.** | [→](psglab/core/README.md) |
| [`psglab/ui/`](psglab/ui/README.md) | Interfaz gráfica: visualizador de ondas, navegación, panel de scoring. | [→](psglab/ui/README.md) |
| [`psglab/tools/`](psglab/tools/README.md) | Herramientas enchufables: lupa, Übersicht, amplitud, ocupación, histograma, anotación. | [→](psglab/tools/README.md) |
| [`psglab/exporters/`](psglab/exporters/README.md) | Archivos de salida: `Scoring.txt`, `Anotaciones.txt`, `Informacion.txt`. | [→](psglab/exporters/README.md) |
| [`psglab/analysis/`](psglab/analysis/README.md) | Parte 2: filtrado, ICA, impedancia, PSD, complejidad, conectividad. | [→](psglab/analysis/README.md) |
| [`psglab/utils/`](psglab/utils/README.md) | Unidades (µV) y errores propios. | [→](psglab/utils/README.md) |
| [`docs/`](docs/README.md) | Documentación, incluida la trazabilidad requisito → archivo. | [→](docs/README.md) |
| [`tests/`](tests/README.md) | Un test por componente. | [→](tests/README.md) |

**Regla de dependencias:** apuntan en una sola dirección —
`readers → core`, `tools → core`, `ui → core + tools`, `exporters → core`,
`analysis → core`. **`core/` nunca importa nada de `ui/`.** Gracias a eso el modelo, el
scoring y los exportadores se pueden testear sin abrir una ventana.

Para saber qué archivo implementa cada requisito del pliego, mirá
[docs/TRAZABILIDAD.md](docs/TRAZABILIDAD.md). Para las decisiones de arquitectura,
[docs/ARQUITECTURA.md](docs/ARQUITECTURA.md). Para una explicación general del programa,
[docs/EXPLICACION.txt](docs/EXPLICACION.txt).

## Cómo contribuir

Reglas del pliego (sección 7), de cumplimiento obligatorio:

1. **Los pull requests van a la branch `Add`, nunca a `Master`.**
2. **Toda pull request debe venir comentada** explicando qué cambió y por qué.
3. **El código va completamente comentado.** Cada módulo declara en su docstring qué
   requisitos del pliego cubre.
4. `main.py` se mantiene mínimo: la lógica nueva va en el módulo que le corresponde.
5. Cada componente agregado viene con su test en `tests/`.

```bash
git checkout Add
git pull
# ... trabajás ...
python -m pytest
git commit -m "Descripción clara del cambio"
```

## Testeo

```bash
python -m pytest
```

**Usá `python -m pytest`, no `pytest` a secas.** El proyecto no se instala como
paquete (no hay `pyproject.toml`), así que `psglab` sólo es importable porque
`python -m` agrega el directorio actual al camino de búsqueda. Con `pytest`
directo la recolección falla con `ModuleNotFoundError: No module named 'psglab'`.

Para correr un archivo o un test suelto:

```bash
python -m pytest tests/test_scoring.py
python -m pytest tests/test_scoring.py::test_el_arousal_es_independiente_de_la_fase
```

Los tests de `core/` y `exporters/` corren sin interfaz gráfica.

**Hoy no hay ningún test salteado**, pero la convención sigue en pie para la
Parte 2: los tests de un componente sin implementar se desactivan con
`pytestmark = pytest.mark.skip(...)` cerca del principio del archivo, y la
corrida informa esa parte como `skipped`. **Al implementar un componente hay que
borrar esa línea del test que le corresponde**, o el trabajo queda sin verificar
—y el chequeo de consistencia hace fallar la suite si el módulo ya está
terminado—. Para ver qué se salteó y
por qué:

```bash
python -m pytest -rs
```

## Integración continua

Cada push y cada pull request disparan
[el workflow de GitHub Actions](.github/workflows/ci.yml), que corre:

- **Los tests en Windows, macOS y Linux**, con Python 3.11 y 3.14. Es la única
  prueba real de que el programa es multiplataforma, que el pliego exige.
- **Los chequeos de consistencia** entre el código y la documentación, que viven
  en `tests/test_consistencia.py` y por lo tanto corren también en tu máquina
  con `python -m pytest`, antes de pushear.
- **La verificación de licencias**, que falla si entra una dependencia GPL. El
  pliego pide MIT y hasta ahora ese control dependía de que alguien se acordara
  de correrlo.

## Licencia

[MIT](LICENSE).

Todas las dependencias son compatibles con MIT (LGPL, BSD-3 y MIT).
**No se puede agregar PyQt5 ni PyQt6**: son GPL y forzarían a relicenciar el proyecto.
Usamos PySide6, que es el binding oficial de Qt bajo LGPL.
