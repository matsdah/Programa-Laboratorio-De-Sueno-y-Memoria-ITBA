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
python3 -m venv .venv         # si eso falla, falta el paquete: sudo apt install python3-venv.


# 3. Activalo

# Para Windows (PowerShell):
.venv\Scripts\Activate.ps1

# macOS / Linux:
source .venv/bin/activate


# 4. Instalá las dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -r requirements-analysis.txt
brew install libomp             # para macOS
```

> Los paquetes ya instalados **no se pierden** y
> se repara regenerándolo desde Windows, sin reinstalar nada:
>
> ```bash
> python -m venv --upgrade .venv
> ```

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

Para saber qué archivo implementa cada requisito del pliego, mirá
[docs/TRAZABILIDAD.md](docs/TRAZABILIDAD.md). Para las decisiones de arquitectura,
[docs/ARQUITECTURA.md](docs/ARQUITECTURA.md). Para una explicación general del programa,
[docs/EXPLICACION.txt](docs/EXPLICACION.txt).

## Testeo

```bash
python -m pytest
```
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

## Licencia

[MIT](LICENSE).

Todas las dependencias son compatibles con MIT (LGPL, BSD-3 y MIT).
Las tipografías IBM Plex que trae el programa van bajo la SIL Open Font License 1.1,
que permite distribuirlas con él; su licencia viaja con los archivos, en
[`psglab/resources/fonts/OFL.txt`](psglab/resources/fonts/OFL.txt).
Usa PySide6, que es el binding oficial de Qt bajo LGPL.
