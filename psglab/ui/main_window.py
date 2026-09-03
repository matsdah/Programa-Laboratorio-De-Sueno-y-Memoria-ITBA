"""Ventana principal: arma el layout y conecta las piezas entre sí.

Distribución general, pensada para el rol UX/UI del pliego (sección 15):

    +--------------------------------------------------------------+
    |  Menú: Archivo | Ver | Herramientas | Análisis | Ayuda        |
    +--------------------------------------------------------------+
    |  Barra de herramientas (lupa, amplitud, ocupación, anotar)    |
    +------------------+-------------------------------------------+
    |  Selector de     |                                           |
    |  canales         |     Visualizador de la señal (30 s)       |
    |                  |                                           |
    +------------------+-------------------------------------------+
    |  Panel de scoring (W / N1 / N2 / N3 / R ... + Arousal)        |
    +--------------------------------------------------------------+
    |  Histograma de la noche completa                              |
    +--------------------------------------------------------------+
    |  Barra de estado: ventana 42 / 960 - 00:21:00                 |
    +--------------------------------------------------------------+

Cubre del pliego: V4_F de "Archivo de salida" (elegir cuál de los tres
archivos exportar). Además es el contenedor que reúne todas las demás
funcionalidades de la Parte 1, pero sin implementar ninguna: cada una vive en
su módulo y acá sólo se las conecta entre sí.
"""

from pathlib import Path

from PySide6.QtWidgets import QMainWindow

from psglab.core.session import Session


class MainWindow(QMainWindow):
    """Ventana principal del programa."""

    def __init__(self) -> None:
        """Crea la ventana con todos sus paneles, todavía sin registro abierto."""
        raise NotImplementedError("Pendiente: construir la ventana y sus paneles.")

    def _build_layout(self) -> None:
        """Crea los paneles y los ubica según el esquema de arriba."""
        raise NotImplementedError("Pendiente: armar el layout de la ventana.")

    def _build_menus(self) -> None:
        """Crea la barra de menú y las acciones."""
        raise NotImplementedError("Pendiente: armar los menús.")

    def _build_toolbar(self) -> None:
        """Crea la barra de herramientas a partir del registro de herramientas.

        Se arma recorriendo `psglab.tools.registry`, así que una herramienta
        nueva aparece sola sin tocar este archivo.
        """
        raise NotImplementedError("Pendiente: armar la barra desde el registro de herramientas.")

    def _connect_signals(self) -> None:
        """Conecta las señales de los paneles entre sí.

        Es el único lugar donde los paneles se enteran unos de otros: el
        visualizador no conoce al histograma, los dos pasan por acá.
        """
        raise NotImplementedError("Pendiente: conectar las señales de los paneles.")

    # -- Acciones del usuario -----------------------------------------------

    def open_recording(self, path: Path) -> None:
        """Abre un registro y prepara la sesión de trabajo.

        Muestra un error legible si el archivo no se puede leer, en vez de
        dejar caer una excepción: los usuarios no necesariamente tienen
        experiencia informática (pliego, sección 3).
        """
        raise NotImplementedError("Pendiente: leer el registro y crear la sesión.")

    def open_scoring(self, path: Path) -> None:
        """Importa un scoring existente sobre el registro abierto (V3_F)."""
        raise NotImplementedError("Pendiente: importar el scoring.")

    def export(self, kind: str, path: Path) -> None:
        """Exporta uno de los tres archivos de salida (V4_F).

        El diálogo de guardado propone el nombre de archivo que fija el pliego,
        tomándolo de `psglab.exporters.DEFAULT_FILENAMES`.

        Args:
            kind: "scoring", "annotations" o "information".
        """
        raise NotImplementedError("Pendiente: delegar en el exportador correspondiente.")

    def refresh(self) -> None:
        """Redibuja todos los paneles a partir del estado de la sesión.

        Se llama después de cualquier cambio: navegar, scorear, anotar o
        cambiar la amplitud.
        """
        raise NotImplementedError("Pendiente: redibujar los paneles.")

    @property
    def session(self) -> Session | None:
        """Sesión de trabajo actual, o None si no hay registro abierto."""
        raise NotImplementedError("Pendiente: devolver la sesión actual.")
