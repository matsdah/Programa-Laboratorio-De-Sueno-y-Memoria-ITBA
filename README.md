# Programa Open Source — Laboratorio de Sueño y Memoria ITBA

Software libre y multiplataforma para **visualizar registros de polisomnografía (PSG),
hacer o corregir el scoring de sueño y anotar eventos**, con un módulo de análisis de
bioseñales (PSD, complejidad, conectividad).

Nace para resolver las limitaciones de los programas actuales: formatos de importación
limitados, scoring sólo manual, imposibilidad de anotar la señal, ausencia de métricas,
compatibilidad únicamente con Windows y precios excesivos.

> **Estado: esqueleto.** La estructura del proyecto está creada, pero la lógica todavía
> no está implementada. Los módulos declaran su interfaz y elevan `NotImplementedError`.

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

| Carpeta | Responsabilidad |
|---|---|
| `main.py` | Punto de entrada. Sólo orquesta: crea la app y abre la ventana. |
| `psglab/readers/` | Importación de archivos (BrainVision, EDF, scoring existente). |
| `psglab/core/` | Modelo de datos y reglas de negocio. **No depende de la interfaz.** |
| `psglab/ui/` | Interfaz gráfica: visualizador de ondas, navegación, panel de scoring. |
| `psglab/tools/` | Herramientas enchufables: lupa, Übersicht, amplitud, ocupación, histograma, anotación. |
| `psglab/exporters/` | Archivos de salida: `Scoring.txt`, `Anotaciones.txt`, `Informacion.txt`. |
| `psglab/analysis/` | Parte 2: filtrado, ICA, impedancia, PSD, complejidad, conectividad. |
| `psglab/utils/` | Unidades (µV) y errores propios. |
| `docs/` | Documentación, incluida la trazabilidad requisito → archivo. |
| `tests/` | Un test por componente. |

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
pytest
git commit -m "Descripción clara del cambio"
```

## Testeo

```bash
pytest
```

Los tests de `core/` y `exporters/` corren sin interfaz gráfica.

## Licencia

[MIT](LICENSE).

Todas las dependencias son compatibles con MIT (LGPL, BSD-3 y MIT).
**No se puede agregar PyQt5 ni PyQt6**: son GPL y forzarían a relicenciar el proyecto.
Usamos PySide6, que es el binding oficial de Qt bajo LGPL.
