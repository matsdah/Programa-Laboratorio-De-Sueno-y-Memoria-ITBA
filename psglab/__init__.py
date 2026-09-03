"""Paquete principal del programa de scoring de sueño del Laboratorio ITBA.

Este archivo se mantiene sin importaciones pesadas a propósito: así
`import psglab` funciona aunque todavía no estén instaladas PySide6 o MNE, y
los tests de `psglab.core` pueden correr sin interfaz gráfica.

Subpaquetes:
    readers    - importación de archivos de registro
    core       - modelo de datos y reglas de negocio (sin dependencia de la UI)
    ui         - interfaz gráfica
    tools      - herramientas enchufables del visualizador
    exporters  - archivos de salida
    analysis   - Parte 2: procesamiento y métricas de la señal
    utils      - unidades y errores propios
"""

__version__ = "0.1.0"
__license__ = "MIT"
