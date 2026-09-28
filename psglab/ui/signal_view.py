"""Visualizador de las ondas: el corazón de la interfaz.

Dibuja los canales visibles de la ventana de 30 segundos actual, con el
nombre y la clase de cada uno y la escala de amplitud en microvoltios a la
izquierda.

**Ese "a la izquierda" es literal desde el hito 37**, y no lo era antes: los
rótulos eran ítems de la escena apoyados sobre cada carril, o sea dentro del
área de trazo, y la señal se dibujaba encima. Hoy son el canalón
—`psglab/ui/channel_axis.py`—, que es el eje izquierdo del gráfico y por eso
tiene ancho propio que la señal no puede invadir.

Sobre la escala vertical: la relación píxeles/µV se mantiene explícita y no
se deja librada al tamaño de la ventana. El pliego pide, en el rol UX/UI,
"pensar en el tamaño de la pantalla con la deformación potencial de la onda";
si la escala dependiera del alto disponible, la misma señal se vería distinta
en dos computadoras y el criterio visual del scoring dejaría de ser
comparable entre personas.

Este módulo recorre el camino V1_P → V5_F del pliego: empieza mostrando los
canales fijos (ojos, C3, C4, EMG) y termina mostrando cualquier canal con
control de amplitud por canal. Es el mismo archivo el que evoluciona.

Cubre del pliego: V1_P, V2_P, V4_F, V5_F de "Visualización de la señal", y la
mitad de dibujo de V3_P (la elección de qué canales mostrar la resuelve
`psglab/ui/channel_selector.py`; acá se los dibuja). También V1_F de "Anotación
de la señal", por `sample_at_pixel()`: es la conversión que traduce el gesto del mouse
a la posición en muestras que guarda la anotación.

Lo que dibujan las herramientas encima de la señal vive en
`psglab/ui/overlay_items.py`, y la envolvente de las páginas largas en
`psglab/ui/envelope_cache.py`. Las dos le preguntan a esta clase lo único que
sabe ella: dónde está cada carril y cuántos carriles mide un microvoltio.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Final

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QFont

from psglab.config import WINDOW_SECONDS
from psglab.core.nomenclature import SleepStage, stage_label
from psglab.core.session import Session
from psglab.core.windows import (
    epoch_to_seconds,
    seconds_to_clock_time,
    seconds_to_sample_absolute,
    seconds_to_samples,
    seconds_to_view_fraction,
)
from psglab.tools.base import Overlay
from psglab.ui import theme
from psglab.ui.channel_axis import ChannelAxis, ChannelLane
from psglab.ui.envelope_cache import EnvelopeCache
from psglab.ui.grid import GridBackground
from psglab.ui.overlay_items import Z_DE_LA_BANDA, OverlayLayer
from psglab.utils.formatting import quantity
from psglab.utils.units import MICROVOLT

#: Separación vertical entre canales, en unidades del gráfico. Cada canal ocupa
#: su propio carril y la señal se dibuja dentro de él.
_ALTO_DE_CARRIL: float = 1.0

#: Qué fracción del carril llena una señal que alcanza justo `scale_uv`. Menos
#: de la mitad para que dos canales vecinos no se pisen cuando los dos están al
#: máximo de su escala.
_LLENADO_DEL_CARRIL: float = 0.45

#: Ancho mínimo, en columnas, con el que se calcula la envolvente.
#:
#: **Existe por el arranque.** Mientras se arma la ventana el gráfico todavía no
#: tiene ancho, y una envolvente de una columna son dos puntos: la primera
#: pantalla saldría como una raya. Con este piso sale bien aunque se dibuje
#: antes de tener tamaño, y pedir más cubetas que píxeles no cuesta nada visible.
_COLUMNAS_MINIMAS: int = 1000

class TimeAxis(pg.AxisItem):
    """El eje horizontal, en hora de la noche cuando el archivo la informa.

    **Decía «Segundos de la ventana» y numeraba de 1 a 29.** Un scorer no
    nombra un evento por el segundo que ocupa dentro de su época: lo nombra por
    la hora de la noche, que es además la unidad con la que la barra de
    navegación, la franja y el hipnograma ya hablan. Que el eje de la señal
    fuera el único en segundos relativos obligaba a hacer la cuenta a mano.

    **Cuando el archivo no informa su horario de inicio vuelve a los
    segundos**, con el rótulo y todo: es lo que pasa con un EDF anónimo, y
    numerar de 1 a 29 sigue siendo mejor que no decir nada.
    """

    #: Qué rótulo lleva el eje cuando no hay hora que mostrar. Con la hora
    #: puesta no lleva ninguno: «21:05» no necesita que le expliquen qué es.
    ROTULO_EN_SEGUNDOS: Final[str] = "Segundos de la ventana"

    def __init__(self) -> None:
        """Crea el eje en segundos, que es como arranca sin registro."""
        super().__init__(orientation="bottom")
        self._inicio: datetime | None = None
        self.setLabel(self.ROTULO_EN_SEGUNDOS)

    def set_start_time(self, start_time: datetime | None) -> None:
        """Le dice al eje cuándo empezó el registro, o `None` si no se sabe."""
        self._inicio = start_time
        self.showLabel(start_time is None)
        self.picture = None
        self.update()

    def start_time(self) -> datetime | None:
        """El horario de inicio con el que está numerando, o `None`."""
        return self._inicio

    def tickStrings(self, values: list[float], scale: float, spacing: float) -> list[str]:
        """Numera cada marca con la hora de la noche que le toca.

        El formato lo decide cuánto hay entre marcas: con marcas cada minuto o
        más, los segundos son ruido; con una página de milisegundos —que la
        escala de tiempo libre permite— hace falta la décima, o todas las
        marcas dirían lo mismo.
        """
        if self._inicio is None:
            return super().tickStrings(values, scale, spacing)
        etiquetas: list[str] = []
        for valor in values:
            momento = seconds_to_clock_time(float(valor) * scale, self._inicio)
            if momento is None:  # pragma: no cover - `_inicio` ya se comprobó
                etiquetas.append("")
            elif spacing >= 60.0:
                etiquetas.append(momento.strftime("%H:%M"))
            elif spacing >= 1.0:
                etiquetas.append(momento.strftime("%H:%M:%S"))
            else:
                decima = momento.microsecond // 100_000
                etiquetas.append(f"{momento.strftime('%H:%M:%S')},{decima}")
        return etiquetas


class SignalView(pg.PlotWidget):
    """Panel de visualización de las ondas."""

    def __init__(self) -> None:
        """Crea el visualizador vacío, sin registro."""
        # **El canalón se crea antes que el widget** y entra como el eje
        # izquierdo del gráfico: `PlotItem` sólo acepta ejes propios al
        # construirse, y es lo que le descuenta ancho al área de trazo.
        eje = ChannelAxis()
        eje_de_tiempo = TimeAxis()
        super().__init__(axisItems={"left": eje, "bottom": eje_de_tiempo})
        #: La columna de la izquierda con el nombre y la escala de cada canal.
        #: Ver `psglab/ui/channel_axis.py`.
        self.channel_axis: ChannelAxis = eje
        #: El eje de abajo, en hora de la noche. Ver `TimeAxis`.
        self.time_axis: TimeAxis = eje_de_tiempo
        self._session: Session | None = None
        self._window_index: int = 0
        self._curves: dict[str, pg.PlotCurveItem] = {}
        #: Lo que dibujan las herramientas. Ver `psglab/ui/overlay_items.py`.
        self.overlay_layer: OverlayLayer = OverlayLayer(self)
        #: La pestaña con el número de época y su fase. Ver `_marcar_la_pestana()`.
        self._pestana: pg.TextItem | None = None
        #: El relleno que tiene hoy la pestaña, para no repintarla si no cambió.
        self._relleno_de_la_pestana: str | None = None
        #: La banda que marca la epoca de scoring sobre la pagina visible.
        self._epoca: object | None = None
        #: La línea que marca por dónde va la reproducción. Se crea la primera
        #: vez que hace falta y después sólo se mueve. Ver `set_playhead()`.
        self._cursor: pg.InfiniteLine | None = None
        #: La envolvente de las páginas largas, por trozos alineados al
        #: registro. Ver `psglab/ui/envelope_cache.py`.
        self.envelope_cache: EnvelopeCache = EnvelopeCache()
        self._visible: list[str] = []
        #: La tipografía de los nombres de canal, o None para la de pyqtgraph.
        self._fuente: QFont | None = None

        item = self.getPlotItem()
        item.hideButtons()
        item.setMenuEnabled(False)
        item.setMouseEnabled(x=False, y=False)
        self.grid = GridBackground(item)
        # El nombre que lee un lector de pantalla, y el foco por teclado: sin
        # él, F6 no tendría dónde dejar el foco al volver a la señal.
        self.setAccessibleName("Señal")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.apply_scheme()

    @property
    def session(self) -> Session | None:
        """La sesión que se está dibujando, o None si no hay registro abierto."""
        return self._session

    @property
    def window_seconds(self) -> float:
        """Cuanto dura la **epoca de scoring**. Es la del pliego.

        **Sigue devolviendo `WINDOW_SECONDS` y no la pagina visible**, aunque
        desde el refactor las dos ya no coincidan. Distinguirlas por nombre es
        lo que evita que los tests que la usan como "el ancho de la pantalla"
        queden mintiendo en silencio: el ancho de la pantalla es
        `view_span_seconds`.
        """
        return WINDOW_SECONDS

    @property
    def view_span_seconds(self) -> float:
        """Cuanto dura la pagina que se esta mirando.

        Sin sesion devuelve la epoca, que es la pagina con la que el programa
        arranca.
        """
        if self._session is None:
            return WINDOW_SECONDS
        return self._session.viewport.span_seconds

    def set_session(self, session: Session) -> None:
        """Asocia el visualizador a una sesión de trabajo."""
        self._session = session
        self.time_axis.set_start_time(session.recording.start_time)
        self.set_visible_channels(session.visible_channels)
        self.show_window(session.current_window)

    def show_window(self, window_index: int) -> None:
        """Deja visible la época indicada y redibuja.

        Conserva el nombre y la firma que tenía cuando la ventana de 30 s era
        también la página: la llaman `MainWindow.refresh()` y `set_session()`.
        Lo que cambió es lo que significa. Antes era "dibujá estos 30 s"; ahora
        es **"ésta es la época actual; asegurate de que se vea"**.

        Mueve la página **lo mínimo**, así que con una página larga la época ya
        está adentro y la pantalla no se mueve. Es idempotente: si no hace falta
        moverse, `Session.set_viewport()` vuelve temprano y no avisa a nadie.

        Pide a `Recording.get_segment` sólo el tramo visible: no se copia ni se
        recorre el registro entero, que puede durar ocho horas.

        **Reproduciendo no mueve la página**: mientras se ve el cursor, la
        página es suya (`Session.move_playhead()`). Con la página de 30 s
        centrada en el cursor la época casi nunca entra entera, y `containing()`
        la sacaría del medio en cada cosa que redibuja —scorear, cambiar la
        amplitud— para que el paso siguiente la volviera a centrar.
        """
        if self._session is None:
            return
        self._window_index = window_index
        if self.playhead() is None:
            inicio, fin = epoch_to_seconds(
                window_index, self._session.recording.sampling_rate
            )
            self._session.set_viewport(self._session.viewport.containing(inicio, fin))
        self.draw_viewport()

    def draw_viewport(self) -> None:
        """Dibuja el tramo que dice la sesion que se esta mirando.

        **El eje horizontal esta en segundos absolutos desde el inicio del
        registro**, y no en segundos desde el inicio de la ventana como hasta el
        refactor. Es el sistema que comparten la epoca de scoring y la pagina
        visible, y el unico que le da a un punto de la senal siempre el mismo
        numero: bajo el contrato anterior, desplazar la vista le cambiaba la
        coordenada al mismo punto fisico, y un arrastre del mouse que cruzara un
        desplazamiento automatico producia un tramo corrido, plausible y
        equivocado.
        """
        if self._session is None:
            return
        registro = self._session.recording
        frecuencia = registro.sampling_rate
        pagina = self._session.viewport
        inicio, fin = seconds_to_samples(
            pagina.start_seconds, pagina.end_seconds, frecuencia, registro.n_samples
        )

        self.getPlotItem().setXRange(
            pagina.start_seconds, pagina.end_seconds, padding=0
        )
        self.grid.redraw(pagina.span_seconds, origin_seconds=pagina.start_seconds)
        self._marcar_epoca()

        # **Una sola vez y sin lista de canales**, que es lo que devuelve una
        # vista de `Recording.data` en lugar de una copia. Pedirlo canal por
        # canal, como antes, hace indexado por lista, que copia: sobre el
        # registro entero eran cientos de megabytes antes de dibujar un punto.
        #
        # **El registro entero y no la página**, desde el hito 49: las cubetas
        # se cuentan desde la primera muestra del registro, y la de un borde de
        # la página empieza antes de él. Sigue siendo una vista.
        bloque = registro.get_segment(0, registro.n_samples)
        columnas = self._columnas()
        self.envelope_cache.forget_if_changed(registro)

        for posicion, nombre in enumerate(self._visible):
            fila = registro.channel_by_name(nombre).index
            indices, tramo = self.envelope_cache.samples_to_draw(
                nombre, inicio, fin, bloque[fila], columnas
            )
            tiempos = (inicio + indices) / frecuencia
            escala = self._session.scale_uv(nombre)
            # **El desplazamiento se resta antes de escalar**, no después: es
            # lo que hace que un canal con la línea de base lejos del cero
            # —un termómetro, un canal de continua corrido— se pueda traer al
            # centro de su carril sin achicar la señal hasta perderla.
            desplazamiento = self._session.offset_uv(nombre)
            centro = -posicion * _ALTO_DE_CARRIL
            self._curves[nombre].setData(
                tiempos,
                centro + ((tramo - desplazamiento) / escala) * _LLENADO_DEL_CARRIL,
            )
        # **Los nombres de canal ya no siguen a la página.** Mientras eran
        # ítems de la escena había que arrastrarlos hasta el borde izquierdo en
        # cada dibujo, porque con el eje en segundos absolutos el cero queda
        # fuera de la pantalla desde la segunda época. Desde que son el
        # canalón viven fuera del área de trazo y la página no los mueve.
        self.update_amplitude_scale()

    def _columnas(self) -> int:
        """Cuántas columnas de píxeles tiene el área de dibujo, con un piso.

        Es lo único que `core/decimation.py` no puede saber, y la razón por la
        que la política de cuánto reducir vive acá y no allá.
        """
        ancho = int(self.getPlotItem().vb.width())
        return max(ancho, _COLUMNAS_MINIMAS)

    def _marcar_epoca(self) -> None:
        """Resalta la época que se va a scorear, sobre la página que se mira.

        **Es lo único que le dice al usuario qué hace la tecla `2`** cuando la
        página muestra cuatrocientas ochenta épocas. Con la página de 30 s la
        banda coincide con la pantalla entera y no molesta; con una página
        larga es la referencia que vuelve usable el scoring.

        Los bordes salen de `epoch_to_seconds()` y no de `índice * 30`: con
        256,125 Hz los dos difieren, y una banda corrida tres segundos le haría
        scorear al usuario una época distinta de la que está mirando.

        **La banda se crea una vez y después sólo se mueve.** Hasta el hito 25
        cada dibujo la sacaba de la escena y armaba otra, y eso era lo que hacía
        que la señal se repintara **dos veces por cuadro**: sacar y poner un
        ítem son dos cambios de escena, y el segundo llega cuando el primer
        repintado ya empezó. Medido con un filtro de eventos sobre el
        visualizador: con la banda recreada, 2,00 pinturas por cuadro; moviéndola,
        1,00. Un `LinearRegionItem` es además un ítem compuesto —dos líneas y una
        región—, así que se armaban tres objetos por cuadro.
        """
        if self._session is None:
            if self._epoca is not None:
                self._epoca.hide()
            if self._pestana is not None:
                self._pestana.hide()
            return

        inicio, fin = epoch_to_seconds(
            self._window_index, self._session.recording.sampling_rate
        )
        if self._epoca is None:
            self._epoca = pg.LinearRegionItem(
                values=(inicio, fin), movable=False, brush=self._pincel_de_la_epoca()
            )
            # Detrás de todo: marca dónde se scorea, no tapa la señal.
            self._epoca.setZValue(-20)
            self.getPlotItem().addItem(self._epoca)
            return

        # **La banda se esconde cuando cubriría la pantalla entera.** Con la
        # página de una época —que es la de arranque— la banda y la página son
        # lo mismo, así que no marca ningún tramo: le cambia el color al fondo
        # del visualizador. Lo mostró una captura, y no se ve desde el código.
        pagina = self._session.viewport
        self._epoca.setVisible(
            pagina.start_seconds < inicio or pagina.end_seconds > fin
        )
        # `setRegion` no hace nada si la época es la misma, así que reproducir
        # —que mueve la página y no la época— no le pide nada a la escena.
        if self._epoca.getRegion() != (inicio, fin):
            self._epoca.setRegion((inicio, fin))
        # **La pestaña se recorta contra el borde de la página.** Con una
        # página más corta que la época, el comienzo de la época queda fuera de
        # la pantalla y la pestaña se iba con él.
        self._marcar_la_pestana(max(inicio, pagina.start_seconds))

    def _marcar_la_pestana(self, inicio: float) -> None:
        """Escribe en el borde de la banda qué época es y en qué fase está.

        **La banda decía dónde se scorea y no qué se scorea** (hito 34): con la
        página larga hay que mirar la barra de abajo para saber en qué época
        cayó el resaltado, y la fase sólo se ve en el panel de scoring, que
        puede estar cerrado.

        **Se crea una vez y después sólo se mueve**, como la banda y el cursor,
        y el texto se rearma sólo cuando cambió: reproducir mueve la página sin
        cambiar de época, así que en el camino caliente esto no le pide nada a
        la escena.

        La época va en base 1, como en la barra de estado y en los archivos de
        salida; la conversión se hace acá, al mostrar.

        **Dice «Ventana» y no «Época»** (hito 64): era el único lugar del
        programa que la llamaba distinto que la barra de estado, la franja, el
        scoring y el pliego. Y **toma el color de la fase** cuando la ventana
        está scoreada, el mismo de la franja y el hipnograma: confirma lo que
        se acaba de scorear sin leer la letra.
        """
        if self._session is None:
            return
        fase = self._session.scoring.get(self._window_index).stage
        texto = f"Ventana {self._window_index + 1}"
        if fase is not SleepStage.UNSCORED:
            texto = f"{texto} · {stage_label(fase)}"
        if self._pestana is None:
            # **Rellena y no texto suelto**: es una pestaña colgada del borde de
            # la banda, como en el diseño.
            self._pestana = pg.TextItem(texto, anchor=(0, 0))
            # **Encima de la grilla y de las bandas de anotación** (hito 64). A
            # −19 estaba debajo de la grilla, que le dibujaba sus líneas por
            # encima; a −5, debajo de las bandas, que son semitransparentes y
            # la teñían: con el color de la fase, un «W» debajo de un spindle
            # verde se leía como otra fase. Queda debajo de los rótulos de las
            # bandas. Tapa la señal sólo si una curva sube hasta el medio
            # carril de margen de arriba, que es donde vive la pestaña.
            self._pestana.setZValue(Z_DE_LA_BANDA + 0.5)
            self.getPlotItem().addItem(self._pestana)
        elif self._pestana.toPlainText() != texto:
            self._pestana.setText(texto)
        self._pintar_la_pestana(fase)
        self._pestana.setPos(inicio, self.epoch_tab_top())

    def _pintar_la_pestana(self, fase: SleepStage) -> None:
        """El relleno de la pestaña: el color de la fase, o el acento sin scorear.

        La tinta la elige `theme.ink_over()` midiendo contra el relleno, que es
        la misma función que decide la del botón de la fase marcada. Un esquema
        sin escala de fases la deja en el acento.
        """
        if self._pestana is None:
            return
        esquema = theme.current()
        relleno = (
            esquema.color_for_stage(fase.value) if fase is not SleepStage.UNSCORED else None
        ) or esquema.accent
        if relleno == self._relleno_de_la_pestana:
            return
        self._relleno_de_la_pestana = relleno
        self._pestana.setColor(theme.ink_over(esquema, relleno))
        self._pestana.fill = pg.mkBrush(relleno)
        self._pestana.updateTextPos()

    def epoch_tab_fill(self) -> str | None:
        """El color de relleno de la pestaña de la ventana actual, o None si
        todavía no hay pestaña. Para verificar en un test qué se pinta."""
        return self._relleno_de_la_pestana if self._pestana is not None else None

    def epoch_tab_top(self) -> float:
        """La altura a la que se apoya la pestaña: el borde de arriba del eje.

        El eje vertical son carriles y no microvoltios —uno por canal, el
        primero en 0— así que arriba de todo es 0,5, que es el mismo medio
        carril de margen que reserva `set_visible_channels()`.
        """
        return 0.5

    def mark_window(self, window_index: int) -> None:
        """Mueve la banda a otra época **sin tocar la página**.

        `show_window()` también mueve la banda, pero antes le pide a la sesión
        que la época entre en pantalla, y eso es lo que la reproducción no
        puede permitir: con una página de menos de 30 s, `containing()` la
        llevaría al comienzo de la época y el cursor dejaría el medio.
        """
        self._window_index = window_index
        self._marcar_epoca()

    def set_playhead(self, seconds: float | None) -> None:
        """Pone la línea de la reproducción en ese instante, o la oculta.

        **Una sola línea, creada una vez y después movida**, por lo que midió el
        hito 25 con la banda de la época: sacar un ítem de la escena y poner
        otro son dos cambios, y el segundo llega cuando el primer repintado ya
        empezó. La reproducción la mueve veinticinco veces por segundo.

        Args:
            seconds: segundos desde el inicio del registro, o `None` para
                ocultarla al pausar.
        """
        if seconds is None:
            if self._cursor is not None:
                self._cursor.hide()
            return
        if self._cursor is None:
            self._cursor = pg.InfiniteLine(
                pos=seconds, angle=90, movable=False, pen=self._pluma_del_cursor()
            )
            # Encima de las curvas: es por donde va la lectura.
            self._cursor.setZValue(20)
            self.getPlotItem().addItem(self._cursor)
            return
        self._cursor.setValue(seconds)
        self._cursor.show()

    def playhead(self) -> float | None:
        """Dónde está la línea de la reproducción, o `None` si no se ve."""
        if self._cursor is None or not self._cursor.isVisible():
            return None
        return float(self._cursor.value())

    def _pluma_del_cursor(self) -> object:
        """La línea del cursor, con el color de las curvas de los paneles."""
        return pg.mkPen(theme.current().accent, width=2)

    def _pincel_de_la_epoca(self) -> object:
        """El relleno de la banda, translúcido para no tapar la señal.

        **El color es el del resaltado del contexto**, que es el que el diseño
        le da a la época actual; translúcido y no opaco porque con la página de
        una época la banda cubre la pantalla entera, y opaca cambiaría el fondo
        del visualizador en vez de marcar un tramo.
        """
        color = pg.mkColor(theme.current().overview_current)
        color.setAlpha(120)
        return pg.mkBrush(color)

    def refresh(self) -> None:
        """Redibuja la ventana actual con la configuración vigente."""
        if self._session is None:
            return
        self.show_window(self._session.current_window)

    def apply_font(self, font: QFont) -> None:
        """Cambia la tipografía de los nombres de canal.

        **Hace falta aparte** porque los nombres son ítems de pyqtgraph, que no
        siguen a la tipografía de la aplicación: cambiarla desde la
        configuración dejaba los menús con la letra nueva y los carriles con la
        vieja.
        """
        self._fuente = QFont(font)
        self.channel_axis.set_fonts(self._fuente)

    def apply_scheme(self) -> None:
        """Vuelve a pintar todo con el esquema de color que esté en uso.

        Se la llama al construir el visualizador y cada vez que el usuario
        elige otro esquema. Hace falta un método explícito porque
        `pg.setConfigOption()` sólo alcanza a los `PlotWidget` que se creen
        después: los que ya existen se quedan con el fondo con el que nacieron.

        Las curvas se vuelven a crear en vez de repintarse porque la pluma de una
        curva no se cambia sin volver a pedirla, y rehacerlas es más
        corto que recorrerlas —son unas pocas decenas, y esto ocurre cuando el
        usuario elige un esquema, no en el camino caliente de la flecha—.
        """
        esquema = theme.current()
        self.setBackground(esquema.background)

        item = self.getPlotItem()
        pluma = pg.mkPen(esquema.foreground)
        # **El izquierdo queda afuera**: es el canalón, que elige sus dos
        # tintas del esquema y se deja sin línea. Con la pluma de acá encima
        # volvía a dibujar la regla vertical que el diseño no tiene.
        for nombre_de_eje in ("bottom", "top", "right"):
            eje = item.getAxis(nombre_de_eje)
            eje.setPen(pluma)
            eje.setTextPen(pluma)
        self.channel_axis.apply_scheme(esquema)

        # La banda de la época ya no se rehace en cada dibujo, así que su color
        # hay que cambiarlo acá: es lo único que la ataba al esquema.
        if self._epoca is not None:
            self._epoca.setBrush(self._pincel_de_la_epoca())
        if self._pestana is not None and self._session is not None:
            self._relleno_de_la_pestana = None
            self._pintar_la_pestana(self._session.scoring.get(self._window_index).stage)
        if self._cursor is not None:
            self._cursor.setPen(self._pluma_del_cursor())

        # Sin canales no hay nada que rehacer, y forzar un redibujo acá dejaría
        # la grilla dibujada sobre un visualizador vacío, que hoy no la tiene.
        if self._visible:
            self.set_visible_channels(self._visible)

    # -- Lo que dibujan las herramientas ------------------------------------

    def set_overlays(self, overlays: Sequence[Overlay]) -> None:
        """Deja dibujado lo que las herramientas quieren mostrar encima.

        Recibe **estado completo, no un delta**. Lo dibuja `overlay_layer`, que
        reutiliza lo que ya estaba con la misma geometría: ver
        `psglab/ui/overlay_items.py`. La ventana principal la llama cuando una
        herramienta avisa por `Tool.notify_changed()`.
        """
        self.overlay_layer.set_overlays(overlays)

    def overlay_signature(self) -> object:
        """Todo lo que cambia cómo se dibuja un overlay, sin ser el overlay.

        La página, los canales visibles con la escala y el desplazamiento de
        cada uno, y el esquema. Si nada de eso cambió, un overlay ya dibujado se
        puede dejar como está.
        """
        if self._session is None:
            return None
        return (
            self._session.viewport,
            tuple(
                (nombre, self._session.scale_uv(nombre), self._session.offset_uv(nombre))
                for nombre in self._visible
            ),
            # **El esquema entero y no su nombre**: uno armado a partir de otro
            # —con `dataclasses.replace()`— se llama igual y pinta distinto.
            theme.current(),
        )

    @property
    def visible_channels(self) -> list[str]:
        """Los canales dibujados, de arriba hacia abajo."""
        return list(self._visible)

    def channel_font(self) -> QFont | None:
        """La tipografía de los nombres de canal, o None si es la de pyqtgraph."""
        return self._fuente

    # -- Los carriles ---------------------------------------------------------
    #
    # Cada canal ocupa un carril de alto `_ALTO_DE_CARRIL`, el primero en 0 y
    # los demás hacia abajo. Un microvoltio mide en carriles lo que dice la
    # escala del canal, y una **posición** se mide además desde su
    # desplazamiento vertical; una **longitud**, no.

    def lane_center(self, channel_name: str) -> float | None:
        """Dónde está dibujado el eje de un canal, o None si no está visible."""
        if channel_name not in self._visible:
            return None
        return -self._visible.index(channel_name) * _ALTO_DE_CARRIL

    def to_lanes(self, microvolts: float, channel_name: str | None) -> float:
        """Una **posición** en µV, en carriles desde el eje de su canal.

        Es la misma cuenta que dibuja la señal, desplazamiento incluido, y por
        eso lo que dibujan las herramientas cae exactamente sobre la onda.
        """
        if self._session is None or channel_name is None:
            return microvolts
        desplazado = microvolts - self._session.offset_uv(channel_name)
        return (desplazado / self._session.scale_uv(channel_name)) * _LLENADO_DEL_CARRIL

    def height_to_lanes(self, microvolts: float, channel_name: str | None) -> float:
        """Una **longitud** en µV, en carriles: sin restar el desplazamiento.

        Es lo que mide en pantalla una altura —la de la banda de amplitud—, y
        por eso no depende de dónde esté centrado el canal.
        """
        if self._session is None or channel_name is None:
            return microvolts
        return (microvolts / self._session.scale_uv(channel_name)) * _LLENADO_DEL_CARRIL

    def array_to_lanes(self, microvolts: np.ndarray, channel_name: str) -> np.ndarray:
        """`to_lanes()` para un array entero, sin recorrerlo en Python."""
        if self._session is None:
            return microvolts
        desplazado = microvolts - self._session.offset_uv(channel_name)
        return (desplazado / self._session.scale_uv(channel_name)) * _LLENADO_DEL_CARRIL

    # -- Canales (V3_P, V4_F) ----------------------------------------------

    def set_visible_channels(self, channel_names: list[str]) -> None:
        """Define qué canales se dibujan y en qué orden vertical."""
        item = self.getPlotItem()
        for curva in self._curves.values():
            item.removeItem(curva)
        self._curves.clear()

        esquema = theme.current()
        self._visible = list(channel_names)
        # **Las líneas de cero las dibuja la grilla.** Una por canal, y hasta el
        # hito 25 cada una era un objeto de la escena que costaba lo mismo por
        # cuadro que una línea de grilla. Van debajo de la señal: dibujadas
        # encima, un canal plano se confundiría con su propia referencia.
        self.grid.set_baselines(
            [-posicion * _ALTO_DE_CARRIL for posicion in range(len(self._visible))],
            esquema.baseline,
        )
        for posicion, nombre in enumerate(self._visible):
            color = esquema.color_for_channel(posicion)

            # **Antes no se pedía ninguna pluma**, así que pyqtgraph usaba la
            # suya: todos los canales salían del mismo gris claro y con ocho
            # apilados no se distinguía uno de otro.
            #
            # **`PlotCurveItem` y no `PlotDataItem`**: aquél es la curva y éste
            # es un envoltorio que además maneja puntos, relleno y decimación
            # propia, ninguno de los cuales se usa acá. Medido sobre un paso de
            # reproducción con página de 30 s: 28 ms contra 19 con el registro
            # de prueba, y 68 contra 58 con 32 canales a 1000 Hz.
            curva = pg.PlotCurveItem(pen=pg.mkPen(color, width=1))
            item.addItem(curva)
            self._curves[nombre] = curva

        # **El rótulo de cada canal es el canalón y ya no un ítem de la
        # escena.** Mientras vivía adentro del gráfico se dibujaba encima de su
        # propia señal y no se leía; ver `psglab/ui/channel_axis.py`.
        self.update_amplitude_scale()

        if self._visible:
            item.setYRange(
                -(len(self._visible) - 1) * _ALTO_DE_CARRIL - 0.5, 0.5, padding=0
            )
        self.refresh()

    # -- Amplitud (V2_P, V5_F) ---------------------------------------------

    def increase_amplitude(self) -> None:
        """Aumenta la amplitud y actualiza la escala mostrada (flecha Arriba).

        La cuenta la hace `Session`, que es donde vive la regla —incluido que
        aumentar la amplitud **baje** el número de `scale_uv`—; acá sólo se
        redibuja.
        """
        if self._session is None:
            return
        self._session.increase_amplitude()
        self.refresh()

    def decrease_amplitude(self) -> None:
        """Reduce la amplitud y actualiza la escala mostrada (flecha Abajo)."""
        if self._session is None:
            return
        self._session.decrease_amplitude()
        self.refresh()

    def channel_detail(self, channel_name: str) -> str:
        """La segunda línea del canalón: la escala de ese canal.

        Ejemplo: "100 µV". Va separada del nombre porque las dos cosas no
        pesan lo mismo: el nombre es lo que se busca y esto es lo que se
        consulta.

        **Llevaba también la clase y se le sacó.** Con un registro de verdad
        —«Resp oro-nasal», clase «Respiratorio»— la línea no entraba en el
        canalón y salía cortada con puntos suspensivos, que es peor que no
        decirla. La clase se sigue viendo al lado del nombre en el selector de
        canales, que es donde la pone el diseño y con lo que V4_F queda cubierto.

        Sin registro abierto queda vacía, y con un canal que el registro ya no
        tiene, también: el rótulo se queda con el nombre y el dibujo sigue.

        **Con la unidad del canal** (hito 70). Decía «µV» para todos, y una
        temperatura en DegC salía como «37 µV»: el programa convierte a
        microvoltios lo eléctrico, pero lo demás queda en la unidad del
        archivo, que es la que mide su escala. Sin unidad declarada va el
        número solo, que es lo que se sabe.
        """
        if self._session is None:
            return ""
        try:
            escala = self._session.scale_uv(channel_name)
            unidad = self._session.recording.channel_by_name(channel_name).unit
        except Exception:  # noqa: BLE001 - un canal que ya no está no rompe el dibujo
            return ""
        if unidad == MICROVOLT:
            return quantity(escala, MICROVOLT, 0)
        # Tres cifras, sin notación científica: un termómetro puede ir por
        # décimas, y un marcador de eventos, por miles.
        if escala >= 100:
            return quantity(escala, unidad, 0)
        return quantity(escala, unidad, significant=3)

    def update_amplitude_scale(self) -> None:
        """Rearma los rótulos del canalón con la escala vigente.

        La escala tiene que reflejar la amplitud real de cada canal: si el
        usuario cambió la ganancia de un solo canal, la referencia de ese
        canal cambia y la de los demás no (V5_F).

        **Rearma los dos renglones y no sólo el número**: son el mismo rótulo,
        y mantener dos caminos —uno para el nombre y otro para la escala— era
        garantizar que alguno quedara viejo.
        """
        esquema = theme.current()
        self.channel_axis.set_lanes(
            [
                ChannelLane(
                    name=nombre,
                    detail=self.channel_detail(nombre),
                    color=esquema.color_for_channel(posicion),
                    position=-posicion * _ALTO_DE_CARRIL,
                )
                for posicion, nombre in enumerate(self._visible)
            ]
        )

    # -- Coordenadas --------------------------------------------------------
    #
    # El visualizador es el **único** que convierte **desde píxeles**, porque
    # es el único que conoce el ancho de la pantalla y la ventana que está
    # dibujando:
    #
    #     píxeles  --seconds_at_pixel-->         segundos  (0 .. 30)
    #     píxeles  --window_fraction_at_pixel--> fracción  (0 .. 1)
    #     píxeles  --sample_at_pixel-->          muestras  (0 .. n_samples)
    #
    # Las conversiones **entre unidades no gráficas** —segundos, fracción,
    # muestras, ventanas— no van acá sino en `psglab/core/windows.py`, que es
    # su único lugar y se puede testear sin abrir una ventana. Estos tres
    # métodos son un píxel→unidad y después una llamada a `windows`; no
    # reimplementan la aritmética.
    #
    # Las herramientas nunca reciben píxeles: la ventana principal convierte
    # antes de avisarles. `ViewerTool` recibe segundos, `OccupancyLine` guarda
    # fracciones y el anotador guarda muestras. Ver `psglab/tools/base.py`.

    def seconds_at_pixel(self, x_pixel: float) -> float:
        """Segundos **desde el inicio del registro** bajo una coordenada horizontal.

        Es la unidad que reciben los metodos de mouse de `ViewerTool`, asi que
        esta conversion es la que aplica la ventana principal antes de avisarle
        a la herramienta activa.

        **Devolvia segundos desde el inicio de la ventana de 30 s.** Cambio con
        la escala de tiempo libre, donde esa referencia deja de ser unica: hay
        una epoca y hay una pagina, y solo el registro es comun a las dos.

        Se recorta contra los bordes de la pagina: un clic en el margen del
        grafico daria un segundo fuera de lo que se esta mirando, y de ahi
        saldria una muestra que no corresponde a nada de lo dibujado.
        """
        vista = self.getPlotItem().vb
        segundos = float(vista.mapSceneToView(QPointF(float(x_pixel), 0.0)).x())
        if self._session is None:
            return min(self.window_seconds, max(0.0, segundos))
        pagina = self._session.viewport
        return min(pagina.end_seconds, max(pagina.start_seconds, segundos))

    def channel_at_pixel(self, y_pixel: float) -> str | None:
        """Sobre qué canal está el cursor, o None si no hay ninguno visible.

        **Es el conversor que faltaba** (hito 45), y su ausencia era un bug
        silencioso: `microvolts_at_pixel()` acepta un canal desde el hito 9,
        pero nadie se lo pasaba nunca, así que caía siempre en el primero
        visible. Con tres canales, el centro del tercer carril —donde la señal
        vale cero— llegaba a las herramientas como −444 µV, medidos contra la
        ganancia de otro canal. Nada fallaba: el número era plausible.

        Invierte la geometría de `lane_center()`, que apila los carriles
        en `-indice * _ALTO_DE_CARRIL`.

        **Se recorta al carril más cercano en vez de contestar None** arriba
        del primero o debajo del último. Ahí sigue habiendo que contestar algo
        —el mouse está sobre el gráfico— y el carril más cercano es la
        respuesta honesta; None significa que no hay ningún canal a la vista.
        """
        if not self._visible:
            return None
        vista = self.getPlotItem().vb
        y_grafico = float(vista.mapSceneToView(QPointF(0.0, float(y_pixel))).y())
        indice = int(round(-y_grafico / _ALTO_DE_CARRIL))
        return self._visible[min(max(indice, 0), len(self._visible) - 1)]

    def microvolts_at_pixel(
        self, y_pixel: float, channel_name: str | None = None
    ) -> float:
        """Microvoltios bajo una coordenada vertical, medidos sobre un canal.

        **Es el cuarto conversor, y faltaba.** `ViewerTool` documenta que
        recibe la `y` en microvoltios, y hasta el hito 9 la ventana principal le
        pasaba la coordenada cruda del gráfico —carriles, de 0 a 1— porque un
        comentario daba por sentado que ninguna herramienta la usaba. La usan
        tres: la banda de amplitud la toma como centro, la ocupación la guarda
        en sus líneas y la lupa ubica su círculo con ella.

        El síntoma más caro era de la ocupación: su tolerancia de clic estaba
        en microvoltios y se comparaba contra un rango de 0 a 1, así que
        **cualquier clic dentro del rango horizontal de una línea la borraba**
        en vez de empezar otra. El hito 19 cerró la otra mitad del mismo
        problema: esa tolerancia era además un número fijo, así que volvía a
        romperse con la amplitud subida. Hoy es
        `occupancy.TOLERANCIA_DE_CLIC_EN_ESCALAS`, una fracción de `scale_uv`.

        Es la inversa exacta de `to_lanes()`, que es la cuenta con la que se
        dibuja la señal, así que ida y vuelta dan el mismo número.

        Args:
            y_pixel: coordenada vertical en el sistema de la **escena**.
            channel_name: canal contra el que medir. Sin él, el primero
                visible, que es la referencia que usan los overlays sin canal.

        Returns:
            Microvoltios respecto del eje de ese canal. Positivo hacia arriba.
        """
        vista = self.getPlotItem().vb
        y_grafico = float(vista.mapSceneToView(QPointF(0.0, float(y_pixel))).y())
        canal = channel_name or (self._visible[0] if self._visible else None)
        if canal is None:
            return 0.0
        centro = self.lane_center(canal)
        if centro is None:
            return 0.0
        return self._a_microvoltios(y_grafico - centro, canal)

    def _a_microvoltios(self, carriles: float, channel_name: str | None) -> float:
        """La inversa de `to_lanes()`. Está al lado suyo a propósito.

        Separarlas garantizaba que alguna de las dos se olvidara del factor de
        llenado el día que cambiara.
        """
        if self._session is None or channel_name is None:
            return carriles
        en_uv = (carriles / _LLENADO_DEL_CARRIL) * self._session.scale_uv(channel_name)
        return en_uv + self._session.offset_uv(channel_name)

    def view_fraction_at_pixel(self, x_pixel: float) -> float:
        """Posicion dentro de la **pagina visible**, de 0 (inicio) a 1 (final).

        La usa el medidor de ocupacion, que mide proporciones del ancho y no
        tiempos: con esta unidad el porcentaje sigue siendo correcto aunque el
        usuario redimensione la ventana del programa.

        **Se llamaba `window_fraction_at_pixel` y media contra los 30 s de la
        epoca.** Se renombro en vez de cambiarle la semantica en silencio, que
        habria sido lo peor de los dos mundos: el mismo nombre midiendo contra
        otra cosa.

        Es un pixel a segundos y despues `core.windows`: la aritmetica entre
        unidades no graficas vive alla y no se reimplementa aca.
        """
        if self._session is None:
            return seconds_to_view_fraction(
                self.seconds_at_pixel(x_pixel), 0.0, self.window_seconds
            )
        pagina = self._session.viewport
        return seconds_to_view_fraction(
            self.seconds_at_pixel(x_pixel), pagina.start_seconds, pagina.span_seconds
        )

    def sample_at_pixel(self, x_pixel: float) -> int:
        """Muestra del registro que cae bajo una coordenada horizontal.

        La usa el anotador, que guarda las posiciones en muestras porque es lo
        que exige "Anotaciones.txt" y lo único que sobrevive a un cambio de
        zoom.

        Igual que la anterior: píxel→segundos y después `core.windows`, que es
        quien sabe sumar el desplazamiento sobre el borde real de la ventana.
        Calcularlo como `ventana * 30 * fs` deja la anotación en la ventana de
        al lado cuando la frecuencia no es redonda.
        """
        if self._session is None:
            return 0
        return seconds_to_sample_absolute(
            self.seconds_at_pixel(x_pixel),
            self._session.recording.sampling_rate,
        )
