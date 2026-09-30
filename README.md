# Programa Open Source — Laboratorio de Sueño y Memoria ITBA

Software libre para visualizar registros de polisomnografía (PSG),
hacer o corregir el scoring de sueño y anotar eventos, con un módulo de análisis de
bioseñales (PSD, complejidad, conectividad).

---

## Instalación

**Python 3.11 o superior** requerido.
> Se puede descargar desde: [python.org/downloads](https://www.python.org/downloads/). Para Windows: durante la instalación marcá la casilla **"Add Python to PATH"**.

```bash
# 1. Ubicate en la carpeta del proyecto
cd Programa-Laboratorio-De-Sueno-y-Memoria-ITBA


# 2. Creá un entorno virtual
python -m venv .venv          # Windows y macOS
python3 -m venv .venv         # Debian, Ubuntu y WSL; si falla: sudo apt install python3-venv


# 3. Activalo

# Para Windows (PowerShell):
.venv\Scripts\Activate.ps1

# macOS / Linux:
source .venv/bin/activate


# 4. Comprobá que estás adentro: tiene que imprimir la carpeta .venv del proyecto
python -c "import sys; print(sys.prefix)"


# 5. Instalá las dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -r requirements-analysis.txt
brew install libomp             # para macOS
```

> **Si `Activate.ps1` falla** con *"la ejecución de scripts está deshabilitada"*,
> es la Execution Policy de PowerShell. Se arregla una sola vez, sin
> administrador, con `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. O se
> evita activar: `.venv\Scripts\python.exe -m pip install ...` hace lo mismo.
> No lo ignores: sin el entorno activo, `pip` instala en el Python global.

> **Un `.venv` por sistema operativo, por versión de Python y por ruta.** Correr
> `python -m venv .venv` sobre uno que ya existe —desde WSL, o con otro Python—
> le reescribe el `pyvenv.cfg` y lo rompe sin avisar. Los paquetes ya
> instalados **no se pierden** y se repara desde el sistema que lo creó, sin
> reinstalar nada:
>
> ```bash
> python -m venv --upgrade .venv
> ```
>
> Para WSL usá otro directorio (`python3 -m venv .venv-linux`). Si renombrás o
> movés la carpeta del proyecto, borrá `.venv` y rehacelo.

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
| [`psglab/core/`](psglab/core/README.md) | Modelo de datos y reglas de negocio. *No depende de la interfaz.* | [→](psglab/core/README.md) |
| [`psglab/ui/`](psglab/ui/README.md) | Interfaz gráfica: visualizador de ondas, navegación, panel de scoring. | [→](psglab/ui/README.md) |
| [`psglab/tools/`](psglab/tools/README.md) | Lupa, Übersicht, amplitud, ocupación, histograma, anotación. | [→](psglab/tools/README.md) |
| [`psglab/exporters/`](psglab/exporters/README.md) | Archivos de salida: `Scoring.txt`, `Anotaciones.txt`, `Informacion.txt`. | [→](psglab/exporters/README.md) |
| [`psglab/analysis/`](psglab/analysis/README.md) | Filtrado, ICA, impedancia, PSD, complejidad, conectividad. | [→](psglab/analysis/README.md) |
| [`psglab/utils/`](psglab/utils/README.md) | Unidades (µV) y errores propios. | [→](psglab/utils/README.md) |
| [`docs/`](docs/README.md) | Documentación. | [→](docs/README.md) |
| [`tests/`](tests/README.md) | Test por componente. | [→](tests/README.md) |
| `.githooks/` | El hook de coautores; ver [Coautores en cada commit](#coautores-en-cada-commit). | |

Para saber qué archivo implementa cada requisito del pliego, mirá
[docs/TRAZABILIDAD.md](docs/TRAZABILIDAD.md). Para las decisiones de arquitectura,
[docs/ARQUITECTURA.md](docs/ARQUITECTURA.md). Para una explicación general del programa,
[docs/EXPLICACION.txt](docs/EXPLICACION.txt).

## Cómo contribuir

1. **Los pull requests van a la branch `Add`, nunca a `Master`**, y vienen
   comentados explicando qué cambió y por qué. La de `Add` a `Master` la
   revisa además Claude (ver [Integración continua](#integración-continua)).
2. Cada módulo declara en su docstring qué requisitos del pliego cubre.
3. `main.py` se mantiene mínimo, y cada componente nuevo viene con su test en `tests/`.

### Coautores en cada commit

Cada commit lleva al resto del equipo como `Co-authored-by:`. Las líneas las
agrega el hook [`.githooks/prepare-commit-msg`](.githooks/prepare-commit-msg),
que se activa **una vez por clon**:

```bash
git config core.hooksPath .githooks
```

Si aparecés como tu propio coautor, declarate con
`git config coautores.yo <tu-login-de-github>`. Para sumar a alguien al equipo,
se agrega una línea a la lista `MIEMBROS` del hook.

## Testeo

```bash
python -m pytest
```

**Usá `python -m pytest`, no `pytest` a secas**: sin `pyproject.toml`, `psglab`
sólo es importable porque `python -m` agrega el directorio actual al camino de
búsqueda, y con `pytest` directo falla con `No module named 'psglab'`.

Para correr un archivo o un test suelto:

```bash
python -m pytest tests/test_scoring.py
python -m pytest tests/test_scoring.py::test_el_arousal_es_independiente_de_la_fase
```

Para ver qué se salteó y por qué:

```bash
python -m pytest -rs
```

## Integración continua

[El workflow de GitHub Actions](.github/workflows/ci.yml) corre:

- **Tests en Windows, macOS y Linux**, con Python 3.11 y 3.14.
- **Verificación de licencias**, que falla si entra una dependencia GPL.

**Sólo dispara en `Add` y en `Master`**: un push a tu rama de trabajo no corre
nada hasta que abras la pull request, así que antes de pushear corré
`python -m pytest`. Si reapuntás una pull request a otra base, cerrala y
reabrila: cambiar la base no vuelve a disparar el CI.

Las pull requests contra `Master` pasan además por
[una revisión de Claude](.github/workflows/claude-review.yml), que comenta el
diff y **bloquea el merge** si encuentra un bug o una regla dura de
`CLAUDE.md` rota. Necesita el secret `CLAUDE_CODE_OAUTH_TOKEN`.

## Licencia

[MIT](LICENSE).

Todas las dependencias son compatibles con MIT (LGPL, BSD-3 y MIT).
Las tipografías IBM Plex que trae el programa van bajo la SIL Open Font License 1.1,
que permite distribuirlas con él; su licencia viaja con los archivos, en
[`psglab/resources/fonts/OFL.txt`](psglab/resources/fonts/OFL.txt).
Usa PySide6, que es el binding oficial de Qt bajo LGPL.
**No se puede agregar PyQt5 ni PyQt6**: son GPL y forzarían a relicenciar el proyecto.
