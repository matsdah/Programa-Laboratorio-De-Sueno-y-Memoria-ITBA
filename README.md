# Programa Open Source — Laboratorio de Sueño y Memoria ITBA

Software libre y multiplataforma para **visualizar registros de polisomnografía (PSG),
hacer o corregir el scoring de sueño y anotar eventos**, con un módulo de análisis de
bioseñales (PSD, complejidad, conectividad).

Nace para resolver las limitaciones de los programas actuales: formatos de importación
limitados, scoring sólo manual, imposibilidad de anotar la señal, ausencia de métricas,
compatibilidad únicamente con Windows y precios excesivos.

> **Estado: esqueleto.** La estructura del proyecto está creada, pero la lógica todavía
> no está implementada. Los módulos declaran su interfaz y elevan `NotImplementedError`.
>
> **Por dónde seguir: [`docs/TODO.md`](docs/TODO.md)**, que ordena los stubs
> pendientes de la Parte 1 en hitos por dependencias y es el único lugar que
> lleva la cuenta de lo que falta.

---

## Instalación

Necesitás **Python 3.11 o superior**. Si no lo tenés, descargalo de
[python.org/downloads](https://www.python.org/downloads/) y, durante la instalación en
Windows, marcá la casilla **"Add Python to PATH"**.

```bash
# 1. Ubicate en la carpeta del proyecto
cd "Lab Del Sueño"

# 2. Creá un entorno virtual (aísla las dependencias del resto de tu computadora)
python -m venv .venv

# 3. Activalo
#    Windows (PowerShell):
.venv\Scripts\Activate.ps1
#    macOS / Linux:
source .venv/bin/activate

# 4. Instalá las dependencias
pip install -r requirements.txt
```

Para trabajar en la Parte 2 (análisis) o correr los tests, instalá además:

```bash
pip install -r requirements-dev.txt
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

Los tests de los componentes que todavía no están implementados están
desactivados con `pytestmark = pytest.mark.skip(...)` cerca del principio del
archivo, así que la corrida informa una parte de la suite como `skipped`. **Al
implementar un componente hay que borrar esa línea del test que le
corresponde**, o el trabajo queda sin verificar —y el chequeo de consistencia
hace fallar la suite si el módulo ya está terminado—. Para ver qué se salteó y
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
