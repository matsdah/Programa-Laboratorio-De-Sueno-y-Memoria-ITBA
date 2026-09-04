# `analysis/` — Parte 2: procesamiento y métricas

Filtrado, ICA, impedancia, re-referenciado, derivaciones, PSD, complejidad y
conectividad.

## Las dos reglas de esta capa

**1. Ninguna función modifica el registro original.** Todas reciben un
`Recording` y devuelven o bien un `Recording` nuevo, o bien números. El usuario
tiene que poder comparar la señal filtrada con la cruda, y volver atrás si el
filtro no fue el adecuado.

**2. Ninguna función conoce la interfaz gráfica.** Los análisis se pueden correr
desde un script del laboratorio sin abrir el programa.

## Los archivos

| Archivo | De qué se ocupa | Pliego |
|---|---|---|
| `filters.py` | Filtrado de la señal cruda. `FilterSettings`, `apply_filters()`, `default_for(kind)`. | V1_F de "Filtración" |
| `ica.py` | Componentes independientes: ajustar, ver topografía y curso temporal, y aplicar excluyendo componentes. | V5_F de "Filtración" |
| `reference.py` | Re-referenciación, incluida la referencia promedio. | "Rereferenciar" |
| `derivation.py` | Canales nuevos calculados a partir de los existentes (`derive`, `derive_montage`). | "Derivar" |
| `impedance.py` | Control de impedancia de los electrodos y canales por encima del límite. | V1_F de "Impedancia" |
| `psd.py` | Densidad espectral de potencia y potencia por banda, absoluta o relativa. | V1_F de "PSD" |
| `complexity.py` | Entropía de muestra y de permutación, Lempel-Ziv, dimensión fractal de Higuchi. | "Complejidad" |
| `connectivity.py` | Conectividad entre canales, por ventana o promediada. | "Conectividad de la señal" |

Varias funciones vienen en dos sabores: una sobre una ventana concreta
(`compute_psd`, `compute_connectivity`) y otra sobre el registro entero
(`band_powers_by_window`, `complexity_by_window`, `connectivity_by_window`). La
segunda es la que alimenta los gráficos a lo largo de la noche.

## Dependencias propias de esta capa

Se instalan con `requirements-dev.txt`, no con `requirements.txt`:

| Paquete | Licencia | Para qué |
|---|---|---|
| `mne` | BSD-3 | Filtrado, ICA, re-referenciado |
| `mne-connectivity` | BSD-3 | Conectividad |
| `antropy` | BSD-3 | Entropías y dimensión fractal |
| `scipy` | BSD-3 | PSD y estadística |

Se apoya en implementaciones ya validadas por la comunidad científica en vez de
reescribir los algoritmos con menos horas de revisión encima.

## Ambigüedad abierta

**Impedancias:** los archivos EDF y BrainVision no siempre las traen. Falta
definir de dónde salen — de ahí que `impedance.py` tenga tanto
`read_impedances()` (del registro) como `load_impedances_from_file()` (de un
archivo aparte). Ver [`docs/EXPLICACION.txt`](../../docs/EXPLICACION.txt),
sección 8.

## Funcionalidades futuras

Fuera del alcance actual, confirmado con el cliente: **detección de potencial
evocado** y **acoplamiento de husos de sueño**. Cuando se retomen, entran como
módulos nuevos en este paquete.

`yasa` (BSD-3) es el candidato natural para husos, ondas lentas y acoplamiento
huso-onda lenta. Hoy no se instala, justamente porque está fuera del alcance.
