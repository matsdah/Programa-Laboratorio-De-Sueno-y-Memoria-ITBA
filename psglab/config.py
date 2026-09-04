"""Constantes de configuración del programa.

Punto único de verdad de dos cosas distintas:

    1. Los valores que **fija el pliego**: la ventana de 30 s, la grilla, la
       banda de 75 µV, los nombres de los archivos de salida.
    2. Las decisiones que se tomaron sobre lo que el pliego **dejaba abierto**,
       en la segunda sección del archivo.

Ningún otro módulo debería escribir estos valores a mano: si mañana el
laboratorio quiere ventanas de 20 segundos, se cambia acá y en ningún otro
lado, y revertir una decisión es cambiar una línea.

Cubre del pliego: ningún ID propio. Es infraestructura: sostiene los valores de
V1_P y V2_F de "Diseño de la interfaz", V1_F de "Herramienta de amplitud" y los
tres IDs de "Archivo de salida". Por eso figura en la sección de módulos de
infraestructura de `docs/TRAZABILIDAD.md` y no en una fila de requisito.
"""

from typing import Final

# --------------------------------------------------------------------------
# Ventana de scoring
# --------------------------------------------------------------------------

#: Duración de la ventana de scoring, en segundos. El pliego la fija en 30 s.
WINDOW_SECONDS: Final[float] = 30.0

# --------------------------------------------------------------------------
# Grilla de fondo (pliego: "Diseño de la interfaz de visualización")
# --------------------------------------------------------------------------

#: Separación de las líneas visibles: divide la ventana en 10 fragmentos.
COARSE_GRID_SECONDS: Final[float] = 3.0

#: Separación de las líneas discretas: divide la ventana en 60 fragmentos.
FINE_GRID_SECONDS: Final[float] = 0.5

# --------------------------------------------------------------------------
# Amplitud (pliego: "Herramienta de amplitud")
# --------------------------------------------------------------------------

#: Altura de la banda de referencia, en microvoltios.
#: Es el criterio clásico de amplitud de ondas lentas.
AMPLITUDE_BAND_UV: Final[float] = 75.0

#: Escala vertical por defecto de cada canal, en microvoltios.
DEFAULT_SCALE_UV: Final[float] = 100.0

#: Factor por el que se multiplica o divide la amplitud con cada pulsación
#: de las flechas "Arriba" y "Abajo".
AMPLITUDE_STEP_FACTOR: Final[float] = 1.25

#: Límites de la escala para que el usuario no pueda dejarla inutilizable.
MIN_SCALE_UV: Final[float] = 1.0
MAX_SCALE_UV: Final[float] = 10_000.0

# --------------------------------------------------------------------------
# Herramienta Übersicht (pliego: "Herramienta Übersicht")
# --------------------------------------------------------------------------

#: Cantidad de ventanas mostradas antes y después de la actual por defecto.
OVERVIEW_WINDOWS_BEFORE: Final[int] = 1
OVERVIEW_WINDOWS_AFTER: Final[int] = 1

# --------------------------------------------------------------------------
# Archivos de salida (pliego: "Archivo de salida")
# --------------------------------------------------------------------------

SCORING_FILENAME: Final[str] = "Scoring.txt"
ANNOTATIONS_FILENAME: Final[str] = "Anotaciones.txt"
INFORMATION_FILENAME: Final[str] = "Informacion.txt"

#: Separador de campos de "Anotaciones.txt": Label | Puntos_Emp | Duracion_Puntos
ANNOTATIONS_SEPARATOR: Final[str] = "|"

#: Separador de campos de "Scoring.txt".
SCORING_SEPARATOR: Final[str] = " "

#: Confirmado con el cliente el 4 de septiembre de 2026.
#: El pliego describe tres campos (nº de ventana, fase, arousal) pero el
#: ejemplo muestra sólo dos ("2 0"), y vale el ejemplo: el número de ventana
#: queda implícito en el orden de las líneas.
#: Se conserva como constante y no se escribe a mano en el exportador, para
#: que revertirlo siga siendo cambiar una línea.
SCORING_INCLUDES_WINDOW_NUMBER: Final[bool] = False

# --------------------------------------------------------------------------
# Decisiones que el pliego dejaba abiertas
# --------------------------------------------------------------------------
#
# Las constantes de abajo resuelven puntos que el pliego no definía. Están acá,
# y no escritas a mano en el módulo que las usa, por dos motivos: cambiarlas es
# cambiar una línea, y el valor queda junto al motivo por el que se eligió.
#
# Todas están confirmadas con el cliente. Lo que todavía quede abierto está en
# docs/TODO.md, hito 0.

#: Confirmado con el cliente el 4 de septiembre de 2026.
#: Índice de la primera muestra del registro en "Anotaciones.txt", el "punto"
#: del pliego. Base 0, que es la del programa, la de numpy y la de MNE: así
#: exportar y reimportar no necesitan conversión.
#: Ojo si alguien procesa el archivo en MATLAB, que cuenta desde 1.
#: Afecta a `exporters/annotations_txt.py` y a `tools/annotator.py`.
ANNOTATION_SAMPLE_BASE: Final[int] = 0

#: Confirmado con el cliente el 4 de septiembre de 2026.
#: Qué hacer cuando dos líneas de la herramienta de ocupación se pisan en
#: horizontal. Se suman los aportes sin descontar la zona compartida, que es
#: leer "sumar la distancia horizontal total" al pie de la letra.
#: **Consecuencia buscada: el total puede pasar del 100 %.** No es un error de
#: cálculo, y la interfaz tiene que poder mostrarlo sin romperse.
#: Afecta a V2_F y V4_F de `tools/occupancy.py`.
OCCUPANCY_COUNTS_OVERLAP_ONCE: Final[bool] = False

#: Confirmado con el cliente el 4 de septiembre de 2026.
#: Si "Scoring.txt" arranca con una línea de comentario que declara la
#: nomenclatura con la que se scoreó, por ejemplo "# AASM".
#:
#: Hace falta porque **el archivo no es interpretable sin ese dato**: el código
#: "2" es S2 en Rechtschaffen y Kales y N2 en AASM. La primera decisión fue
#: registrarlo sólo en "Informacion.txt", pero V4_F deja exportar **uno solo**
#: de los tres archivos, y exportar nada más que el scoring es el caso más
#: común. Sin cabecera, ese archivo sale ambiguo.
#:
#: El pliego muestra líneas de datos y no prohíbe comentarios, y el lector ya
#: estaba diseñado para saltar hasta la primera línea con datos.
#: Afecta a `exporters/scoring_txt.py` y a `readers/scoring_reader.py`.
SCORING_INCLUDES_NOMENCLATURE_HEADER: Final[bool] = True

#: Prefijo de la línea de cabecera de "Scoring.txt". Un lector que no la espere
#: puede descartarla mirando este carácter, que es la convención de comentario
#: más difundida en archivos de texto.
SCORING_HEADER_PREFIX: Final[str] = "#"
