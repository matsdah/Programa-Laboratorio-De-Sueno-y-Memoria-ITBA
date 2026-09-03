"""Constantes de configuración del programa.

Punto único de verdad para los valores que fija el pliego. Ningún otro módulo
debería escribir estos números a mano: si mañana el laboratorio quiere
ventanas de 20 segundos, se cambia acá y en ningún otro lado.

Cubre del pliego: valores de V1_P (ventana y grilla), V1_F de la herramienta
de amplitud (75 µV) y los nombres de los archivos de salida.
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

#: PENDIENTE DE CONFIRMACIÓN CON EL CLIENTE.
#: El pliego describe tres campos (nº de ventana, fase, arousal) pero el
#: ejemplo muestra sólo dos ("2 0"). Mientras no se confirme, el número de
#: ventana queda implícito en el orden de las líneas, como en el ejemplo.
SCORING_INCLUDES_WINDOW_NUMBER: Final[bool] = False
