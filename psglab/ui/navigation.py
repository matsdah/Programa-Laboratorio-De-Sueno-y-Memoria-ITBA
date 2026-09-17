"""Navegación entre ventanas: la barra inferior del programa.

El pliego pide poder avanzar y retroceder tanto con las flechas del teclado como
con botones del mouse, y ver siempre en qué ventana se está y cuántas hay en
total.

El refactor de la interfaz la llevó a la forma de la referencia: botones
compactos con icono en vez de dos botones de texto, los saltos a la primera y a
la última ventana —que antes sólo se conseguían apretando una flecha cientos de
veces—, el control de amplitud al lado, y sobre todo una **franja de posición**
que muestra dónde cae la ventana actual dentro de la noche y deja saltar a
cualquier punto con un clic.

El hito 24 le sumó los botones que mueven la **página** en vez de la época, y
los de la reproducción: ≪ ‹ ⏯ › ≫ y la velocidad. La reproducción la maneja
`playback.py`; acá sólo están el botón y el selector.

Los atajos de teclado no se definen acá sino en `shortcuts.py`, para tener un
único lugar donde se sabe qué hace cada tecla.

**Los botones piden, no navegan.** Ninguno toca la sesión: emiten una señal y
quien la escucha decide. Es lo que mantiene en `core/` la regla de qué ventana
existe y cuál no.

Cubre del pliego: V1_F de "Navegación en la señal"; la parte de "número de
ventana actual y total" de V1_P de "Visualización".
"""

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from psglab.ui import theme
from psglab.ui.icons import icon
from psglab.ui.playback import DEFAULT_SPEED, PLAYBACK_SPEEDS, speed_text

#: Alto de la franja de posición, en píxeles. Alcanza para verla y para poder
#: pegarle un clic sin apuntar.
ALTO_DE_LA_FRANJA: int = 14

#: Lado del botón de la barra. Compacto a propósito: son once y comparten fila
#: con la velocidad, la franja, la posición y el horario.
LADO_DEL_BOTON: int = 26


class PositionStrip(QWidget):
    """Dónde cae la ventana actual dentro de la noche entera.

    Es la única pieza del programa que muestra la posición **en proporción** y
    no como número. Un "ventana 412 de 960" hay que interpretarlo; una marca a
    media franja se ve.

    Se pinta con `QPainter` y no con pyqtgraph por lo mismo que el panel de
    contexto: son dos rectángulos, y un `PlotWidget` para eso traería ejes,
    márgenes y un menú contextual que habría que apagar.
    """

    #: Se emite con la ventana a la que el usuario quiere ir (base 0).
    window_requested = Signal(int)

    def __init__(self) -> None:
        """Crea la franja vacía, sin registro."""
        super().__init__()
        self._window_index = 0
        self._n_windows = 0
        self.setFixedHeight(ALTO_DE_LA_FRANJA)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_position(self, window_index: int, n_windows: int) -> None:
        """Mueve la marca."""
        self._window_index = window_index
        self._n_windows = n_windows
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Dibuja el fondo y la marca de la ventana actual."""
        esquema = theme.current()
        pintor = QPainter(self)
        pintor.fillRect(self.rect(), QColor(esquema.overview_background))

        if self._n_windows <= 0:
            pintor.end()
            return

        ancho = self.width()
        # **Un ancho mínimo de dos píxeles.** Sobre 2650 ventanas la marca mide
        # menos de un píxel y desaparece, que es justo cuando más falta hace.
        ancho_marca = max(2.0, ancho / self._n_windows)
        x = (self._window_index / self._n_windows) * ancho
        pintor.fillRect(
            QRectF(x, 0, ancho_marca, self.height()),
            QColor(esquema.overview_current_border),
        )
        pintor.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Un clic pide la ventana que cae bajo el cursor.

        El recorte contra la última ventana es el mismo que hace
        `HistogramTool.on_click()`, y por el mismo motivo: un clic en el borde
        derecho da fracción 1,0, y `int(1.0 * total)` es una ventana que no
        existe.
        """
        if self._n_windows <= 0 or self.width() <= 0:
            return
        fraccion = event.position().x() / self.width()
        ventana = min(int(fraccion * self._n_windows), self._n_windows - 1)
        self.window_requested.emit(max(ventana, 0))


class NavigationBar(QWidget):
    """Botones de época, de página y de reproducción, amplitud, franja e
    indicadores.

    **Hay dos juegos de flechas y no se pueden confundir.** Los triángulos
    llenos mueven la **época**, que es lo que el pliego llama ventana y lo que
    se scorea. Los chevrones (‹ ≪) mueven la **página**, lo que se ve, sin
    tocar la época: son los mismos pasos que Mayús+← → y Ctrl+← →.
    """

    #: Se emite cuando el usuario pide ir a una ventana concreta (base 0).
    window_requested = Signal(int)
    #: Se emiten cuando pide más o menos amplitud. Van sin argumento: cuánto
    #: cambia por paso lo decide `Session`, no un widget.
    amplitude_up_requested = Signal()
    amplitude_down_requested = Signal()
    #: Se emite con cuánto mover la página, en fracciones de su propio ancho:
    #: −1 y +1 son una página entera, −0,5 y +0,5 media.
    page_pan_requested = Signal(float)
    #: Se emite al apretar reproducir o pausar.
    playback_toggle_requested = Signal()
    #: Se emite con la velocidad elegida, como múltiplo del tiempo real.
    playback_speed_changed = Signal(float)

    def __init__(self) -> None:
        """Crea la barra completa, todavía sin registro."""
        super().__init__()
        self._window_index = 0
        self._n_windows = 0
        self._reproduciendo = False
        #: Los últimos límites de la página: (al principio, al final, entera).
        #: None hasta que se abre un registro.
        self._limites: tuple[bool, bool, bool] | None = None

        self._primera = self._boton("primera", "Primera ventana")
        self._anterior = self._boton("anterior", "Ventana anterior")
        self._siguiente = self._boton("siguiente", "Ventana siguiente")
        self._ultima = self._boton("ultima", "Última ventana")
        self._pagina_atras = self._boton("pagina-atras", "Una página hacia atrás")
        self._media_atras = self._boton("media-atras", "Media página hacia atrás")
        self._reproducir = self._boton("reproducir", "Reproducir")
        self._media_adelante = self._boton("media-adelante", "Media página hacia adelante")
        self._pagina_adelante = self._boton("pagina-adelante", "Una página hacia adelante")
        self._mas_amplitud = self._boton("amplitud-mas", "Aumentar la amplitud")
        self._menos_amplitud = self._boton("amplitud-menos", "Reducir la amplitud")

        #: Qué icono lleva cada botón, para volver a dibujarlos al cambiar de
        #: esquema. El de reproducir no está: su icono depende del estado.
        self._iconos: dict[QPushButton, str] = {
            self._primera: "primera",
            self._anterior: "anterior",
            self._siguiente: "siguiente",
            self._ultima: "ultima",
            self._pagina_atras: "pagina-atras",
            self._media_atras: "media-atras",
            self._media_adelante: "media-adelante",
            self._pagina_adelante: "pagina-adelante",
            self._mas_amplitud: "amplitud-mas",
            self._menos_amplitud: "amplitud-menos",
        }

        self.speed_selector = QComboBox()
        self.speed_selector.setToolTip("Velocidad de reproducción")
        self.speed_selector.setAccessibleName("Velocidad de reproducción")
        self.speed_selector.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        for velocidad in PLAYBACK_SPEEDS:
            self.speed_selector.addItem(speed_text(velocidad), velocidad)
        self.speed_selector.setCurrentIndex(PLAYBACK_SPEEDS.index(DEFAULT_SPEED))

        self.strip = PositionStrip()
        self._posicion = QLabel("Sin registro")
        self._horario = QLabel("")

        self._primera.clicked.connect(lambda: self._pedir(0))
        self._anterior.clicked.connect(lambda: self._pedir(self._window_index - 1))
        self._siguiente.clicked.connect(lambda: self._pedir(self._window_index + 1))
        self._ultima.clicked.connect(lambda: self._pedir(self._n_windows - 1))
        for boton, fraccion in (
            (self._pagina_atras, -1.0),
            (self._media_atras, -0.5),
            (self._media_adelante, 0.5),
            (self._pagina_adelante, 1.0),
        ):
            boton.clicked.connect(
                lambda _=False, f=fraccion: self.page_pan_requested.emit(f)
            )
        self._reproducir.clicked.connect(self.playback_toggle_requested.emit)
        self.speed_selector.currentIndexChanged.connect(
            lambda _: self.playback_speed_changed.emit(self.speed_selector.currentData())
        )
        self._mas_amplitud.clicked.connect(self.amplitude_up_requested.emit)
        self._menos_amplitud.clicked.connect(self.amplitude_down_requested.emit)
        self.strip.window_requested.connect(self.window_requested.emit)

        caja = QHBoxLayout(self)
        caja.setContentsMargins(4, 2, 4, 2)
        for boton in (self._primera, self._anterior, self._siguiente, self._ultima):
            caja.addWidget(boton)
        caja.addSpacing(12)
        for boton in (
            self._pagina_atras,
            self._media_atras,
            self._reproducir,
            self._media_adelante,
            self._pagina_adelante,
        ):
            caja.addWidget(boton)
        caja.addWidget(self.speed_selector)
        caja.addSpacing(12)
        for boton in (self._menos_amplitud, self._mas_amplitud):
            caja.addWidget(boton)
        caja.addSpacing(12)
        caja.addWidget(self.strip, stretch=1)
        caja.addSpacing(12)
        caja.addWidget(self._posicion)
        caja.addWidget(self._horario)

        self.set_position(0, 0)

    def _boton(self, nombre: str, ayuda: str) -> QPushButton:
        """Un botón compacto con su icono y su tooltip.

        El tooltip no es decorativo: son once iconos y, sin él, la diferencia
        entre "anterior" y "primera" hay que deducirla del dibujo.

        **Un clic no le saca el foco a la señal** (`TabFocus`): si se lo sacara,
        Espacio dejaría de reproducir después de apretar cualquier botón. Se
        siguen alcanzando con Tab.
        """
        boton = QPushButton()
        boton.setIcon(icon(nombre, theme.icon_ink(theme.current())))
        boton.setToolTip(ayuda)
        boton.setAccessibleName(ayuda)
        boton.setFixedSize(LADO_DEL_BOTON, LADO_DEL_BOTON)
        boton.setFlat(True)
        boton.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        return boton

    def apply_scheme(self) -> None:
        """Vuelve a dibujar los iconos con el color del esquema en uso.

        Un icono es un mapa de bits ya pintado: cambiar de esquema oscuro a
        claro sin esto deja los triángulos claros sobre fondo claro.
        """
        color = theme.icon_ink(theme.current())
        for boton, nombre in self._iconos.items():
            boton.setIcon(icon(nombre, color))
        self._reproducir.setIcon(icon(self._icono_de_reproducir(), color))
        self.strip.update()

    def set_playing(self, playing: bool) -> None:
        """Muestra el botón como «reproducir» o como «pausar»."""
        self._reproduciendo = bool(playing)
        ayuda = "Pausar" if self._reproduciendo else "Reproducir"
        self._reproducir.setIcon(
            icon(self._icono_de_reproducir(), theme.icon_ink(theme.current()))
        )
        self._reproducir.setToolTip(ayuda)
        self._reproducir.setAccessibleName(ayuda)
        # Al detenerse en el final, el botón tiene que apagarse: los límites se
        # calcularon mientras todavía reproducía.
        self._aplicar_limites()

    def _icono_de_reproducir(self) -> str:
        return "pausa" if self._reproduciendo else "reproducir"

    def set_page_bounds(self, at_start: bool, at_end: bool, whole: bool) -> None:
        """Habilita los botones de página según dónde está la página.

        Args:
            at_start: si la página empieza con el registro.
            at_end: si llega a su final.
            whole: si muestra el registro entero.

        **Reproducir queda habilitado mientras se reproduce**, aunque la página
        llegue al final: es el botón con que se pausa, y deshabilitarlo dejaría
        al usuario sin forma de detenerla con el mouse.
        """
        self._limites = (bool(at_start), bool(at_end), bool(whole))
        self._aplicar_limites()

    def _aplicar_limites(self) -> None:
        """Habilita los botones de página con los últimos límites recibidos."""
        if self._n_windows <= 0 or self._limites is None:
            return
        at_start, at_end, whole = self._limites
        self._pagina_atras.setEnabled(not at_start)
        self._media_atras.setEnabled(not at_start)
        self._media_adelante.setEnabled(not at_end)
        self._pagina_adelante.setEnabled(not at_end)
        self._reproducir.setEnabled(
            self._reproduciendo or not (at_end or whole)
        )

    def set_position(self, window_index: int, n_windows: int) -> None:
        """Actualiza el indicador de posición y la franja.

        Se muestra en base 1, que es como cuenta el usuario: la ventana 0
        interna se muestra como "Ventana 1 de 960".

        **Es el único lugar donde se suma ese 1.** Adentro del programa las
        ventanas son base 0 de punta a punta; convertir al mostrar y no antes es
        lo que evita que la cuenta se corra en algún camino intermedio.

        Los botones de página no dependen de la época sino de la página, así
        que los habilita `set_page_bounds()`. Acá sólo se apagan cuando no hay
        registro.
        """
        self._window_index = window_index
        self._n_windows = n_windows
        if n_windows <= 0:
            self._posicion.setText("Sin registro")
        else:
            self._posicion.setText(f"Ventana {window_index + 1} de {n_windows}")
        self.strip.set_position(window_index, n_windows)

        hay_registro = n_windows > 0
        self._primera.setEnabled(hay_registro and window_index > 0)
        self._anterior.setEnabled(hay_registro and window_index > 0)
        self._siguiente.setEnabled(hay_registro and window_index < n_windows - 1)
        self._ultima.setEnabled(hay_registro and window_index < n_windows - 1)
        self._mas_amplitud.setEnabled(hay_registro)
        self._menos_amplitud.setEnabled(hay_registro)
        if not hay_registro:
            self._limites = None
            for boton in (
                self._pagina_atras,
                self._media_atras,
                self._reproducir,
                self._media_adelante,
                self._pagina_adelante,
            ):
                boton.setEnabled(False)

    def set_clock_time(self, label: str | None) -> None:
        """Muestra el horario real de la ventana actual, si se conoce.

        Args:
            label: horario ya formateado, o None si el registro no informa el
                horario de inicio.

        Con `None` se **oculta** en vez de mostrar un guión o un cero: un
        horario vacío en pantalla invita a leerlo como medianoche.
        """
        self._horario.setText(label or "")
        self._horario.setVisible(label is not None)

    def _pedir(self, window_index: int) -> None:
        """Pide una ventana, si existe.

        **Pide, no navega.** El panel no toca la sesión: emite la señal y quien
        la escucha decide. Es lo que mantiene la regla —qué ventana existe y
        cuál no— en `core/`.
        """
        if 0 <= window_index < self._n_windows:
            self.window_requested.emit(window_index)
