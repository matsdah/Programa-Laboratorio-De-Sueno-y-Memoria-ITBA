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
| `filters.py` | Filtrado de la señal cruda. `FilterSettings`, `apply_filters()`, `default_for(kind, sampling_rate)`, `settings_for_kinds()`. | V1_F de "Filtración" |
| `ica.py` | Componentes independientes: ajustar, ver topografía y curso temporal, y aplicar excluyendo componentes. | V5_F de "Filtración" |
| `reference.py` | Re-referenciación, incluida la referencia promedio. | "Rereferenciar" |
| `derivation.py` | Canales nuevos calculados a partir de los existentes (`derive`, `derive_montage`). | "Derivar" |
| `impedance.py` | Control de impedancia de los electrodos y canales por encima del límite. | V1_F de "Impedancia" |
| `psd.py` | Densidad espectral de potencia y potencia por banda, absoluta o relativa. | V1_F de "PSD" |
| `complexity.py` | Entropía de muestra y de permutación, Lempel-Ziv, dimensión fractal de Higuchi. | "Complejidad" |
| `connectivity.py` | Conectividad entre canales, por ventana o promediada. | "Conectividad de la señal" |
| `mne_bridge.py` | El puente `Recording` ↔ `mne.io.Raw` en las dos direcciones, y la escala volts ↔ µV. | — (infraestructura) |

Varias funciones vienen en dos sabores: una sobre una ventana concreta
(`compute_psd`, `compute_connectivity`) y otra sobre el registro entero
(`band_powers_by_window`, `complexity_by_window`, `connectivity_by_window`). La
segunda es la que alimenta los gráficos a lo largo de la noche.

## Lo que la interfaz no ofrece, a propósito

**No todo lo público de esta carpeta tiene un botón**, y cuando no lo tiene hay
que decirlo acá: si no, la única forma de saberlo es no encontrarlo en el menú.
La política es de la interfaz y no del módulo, así que las funciones siguen
existiendo y testeadas para los scripts del laboratorio.

| Función | Por qué no está en el menú |
|---|---|
| `derivation.derive_montage()` | El menú deriva de a un par con `derive()`, que es el pedido real. Un montaje entero se escribe en un script. Decidido en el hito 19. |
| `complexity.sample_entropy()` | Medida sobre el registro real tarda más de cinco minutos contra menos de cinco segundos las otras tres. `MEDIDAS_RAPIDAS` la deja fuera del barrido. |

`ui/main_window.py` **no debe importar lo que no llama**: hasta el hito 19
importaba `derive_montage` sin usarla, y eso hacía parecer consumido un camino
muerto.

## Dependencias propias de esta capa

| Paquete | Licencia | Para qué | Dónde se declara |
|---|---|---|---|
| `mne` | BSD-3 | Filtrado, ICA, re-referenciado | `requirements.txt` |
| `scipy` | BSD-3 | PSD y estadística | `requirements.txt` |
| `mne-connectivity` | BSD-3 | Conectividad | `requirements-analysis.txt` |
| `antropy` | BSD-3 | Entropías y dimensión fractal | `requirements-analysis.txt` |

`mne` y `scipy` viven en `requirements.txt` porque la Parte 1 también los
necesita: `mne` lee BrainVision y EDF, y `scipy` filtra. Las dos exclusivas de
esta capa son las otras dos, y para trabajar acá hay que instalarlas aparte:

```bash
pip install -r requirements-analysis.txt
```

**Están en su propio archivo, pero eso ya no significa que sean opcionales.**
`antropy` arrastra `numba` y `llvmlite`, y `mne-connectivity` arrastra
`netCDF4`, `xarray`, `pandas` y `scikit-learn`, así que se separaron cuando
ningún test las importaba y el CI las instalaba seis veces a cambio de cero
verificación. **Desde el hito 10 sí hay tests que las importan**, y el CI las
instala en los dos jobs: quedan en su propio archivo porque el techo
`numpy<2.6` que necesita `numba` vive ahí y no hay por qué atarle las manos a
la Parte 1, que no tiene ese problema.

Correr la suite sin ellas no saltea nada: falla. Los imports son diferidos a
nivel de función, así que el error sale recién al ejecutarse el test.

Se apoya en implementaciones ya validadas por la comunidad científica en vez de
reescribir los algoritmos con menos horas de revisión encima.

## Ambigüedad abierta

**Impedancias:** falta saber **cuál de las tres vías usa el laboratorio**. Las
tres están implementadas en `impedance.py`, así que lo que la respuesta decide
es qué se le ofrece primero al investigador, no qué se puede hacer.

Lo que sí quedó medido: **BrainVision las trae** —en la sección `[Comment]` del
`.vhdr`, ya en kΩ— y **EDF no puede**, porque el estándar no tiene el campo. Por
eso la vía del archivo aparte no es un extra: es la única disponible para todo
registro en EDF. Ver [`docs/EXPLICACION.txt`](../../docs/EXPLICACION.txt),
sección 8.

## Funcionalidades futuras

Fuera del alcance actual, confirmado con el cliente: **detección de potencial
evocado** y **acoplamiento de husos de sueño**. Cuando se retomen, entran como
módulos nuevos en este paquete.

`yasa` (BSD-3) es el candidato natural para husos, ondas lentas y acoplamiento
huso-onda lenta. Hoy no se instala, justamente porque está fuera del alcance.

## Estado

**Terminada.** Pendientes **0 stubs**: los ocho módulos están implementados y
con test propio. El [TODO](../../docs/TODO.md) lleva las dos Partes desde el
hito 10 —antes cubría sólo la Parte 1, y esta carpeta quedaba afuera— y sus
hitos 10 a 16 son los de acá.
