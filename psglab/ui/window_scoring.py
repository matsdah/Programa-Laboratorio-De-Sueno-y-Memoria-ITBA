"""La ventana y el scoring: scorear, las fases sugeridas y el hipnograma.

Asignar la fase y el arousal de la ventana actual, cambiar de nomenclatura,
pedir y confirmar las fases sugeridas (hito 75) y dibujar el hipnograma con su
eje, sus colores y la curva de las sugeridas.

**Es un pedazo de `MainWindow`** (hito 76), no una pieza aparte: la clase de
acá no hereda de nada y no se instancia sola. `MainWindow` la hereda junto con
las otras seis, **antes de `QMainWindow`** para que sus métodos le ganen a los
de Qt. Todas comparten el estado que arma `MainWindow.__init__`, así que la
partición es por tema y no por dependencias: el código se leía en un archivo
de 4300 líneas y 170 métodos, y ahora cada tema tiene el suyo.

Cubre del pliego: V2_F del "Histograma" (`_marcas_del_histograma` dibuja el
eje horizontal, en hora real o de 1 a VENMAX). Las fases sugeridas no tienen ID:
son el «scoring automático» de las motivaciones del pliego.
"""

from pathlib import Path

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog

from psglab.core.nomenclature import Nomenclature, SleepStage, stage_label, stages_of
from psglab.analysis.auto_scoring import default_channels, suggest_stages
from psglab.core.windows import window_to_clock_time
from psglab.tools.histogram import HistogramTool
from psglab.tools.overview import OverviewTool
from psglab.ui import theme
from psglab.ui.menus import menu_path
from psglab.ui.shortcuts import install_shortcuts
from psglab.utils.errors import PsgLabError

#: Qué parte de la separación entre dos filas del hipnograma ocupa la barra de
#: color de una fase. Menos de la mitad a propósito: la barra tiene que leerse
#: como una marca sobre su fila y no como un bloque que tape la curva.
_GROSOR_DE_LA_FASE: float = 0.34

#: Desde qué confianza una fase sugerida es «segura» (hito 75). **Medido**:
#: contra un experto, sobre la noche SC4001 de la Sleep-EDF, las sugeridas con
#: al menos 80 % acertaron el 93 % y eran algo más de la mitad; el resto
#: acertó bastante menos. Ver `analysis/auto_scoring.py`.
_CONFIANZA_SEGURA: float = 0.8

#: Opacidad, en hexadecimal, con que la franja de posición pinta una ventana
#: con fase sugerida: el color de la fase, apagado (hito 75).
_OPACIDAD_DE_LA_SUGERIDA: str = "55"


class ScoringMixin:
    """Lo de `MainWindow` que scorea y dibuja el hipnograma.
    """

    def _reload_histogram(self) -> None:
        """Vuelve a leer la noche entera desde el scoring.

        Después de importar, el histograma tiene guardadas las barras del
        scoring anterior: `update_window()` sirve para una tecla, no para
        cambiar el archivo debajo."""
        herramienta = self._tools.get("histogram")
        if isinstance(herramienta, HistogramTool) and self._session is not None:
            herramienta.activate(self._session)

    def toggle_arousal(self) -> None:
        """Tecla A: marca o desmarca el arousal de la ventana actual (V2_F)."""
        if self._session is None:
            return
        ventana = self._session.current_window
        actual = self._session.scoring.get(ventana).arousal
        self._set_arousal(not actual)

    def score_current_window(self, stage: SleepStage) -> None:
        """Asigna una fase a la ventana actual (V1_F de "Scoring")."""
        if self._session is None:
            return
        try:
            self._session.scoring.set_stage(self._session.current_window, stage)
        except PsgLabError as error:
            self._show_error(error, "scorear la ventana")
            return
        self._update_histogram_window(self._session.current_window)
        # **La Übersicht cachea sus ventanas** y las rearma al cambiar de
        # época, no al scorear: sin esto, el chip de la fase recién puesta no
        # aparecía hasta la próxima flecha. Es lo mismo que ya hacía anotar, y
        # por el mismo motivo.
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.refresh()
        # **Pasa sola a la ventana siguiente** (hito 64), salvo en la última y
        # mientras se reproduce: ahí la época la lleva el cursor, y saltar
        # adelantaría la reproducción una ventana por cada tecla.
        if (
            self._preferencias.advance_after_scoring
            and self._cabezal is None
            and self._session.current_window < self._session.n_windows - 1
        ):
            self.go_to_next_window()
            return
        self.refresh()

    def _elegir_nomenclatura(self, path: Path) -> Nomenclature | None:
        """Pregunta con qué nomenclatura se scoreó un archivo que no lo dice.

        Arranca en la del registro abierto, que es la respuesta más probable:
        quien importa un scoring suele haberlo hecho con la misma que usa acá.
        `None` si el usuario cancela.
        """
        opciones = [n.value for n in Nomenclature]
        actual = self._session.scoring.nomenclature if self._session else None
        inicial = opciones.index(actual.value) if actual is not None else 0
        elegida, acepto = QInputDialog.getItem(
            self,
            "Importar scoring",
            f"«{path.name}» no dice con qué nomenclatura se scoreó.\n"
            "¿Con cuál se hizo?",
            opciones,
            inicial,
            False,
        )
        if not acepto:
            return None
        return next(n for n in Nomenclature if n.value == elegida)

    def request_stage_suggestions(self) -> None:
        """Pide al clasificador la fase de las ventanas sin scorear (hito 75).

        **Sugiere, no scorea**: lo que vuelve se guarda en la capa de las
        sugeridas de `Scoring`, que no se exporta ni pisa lo elegido a mano.
        Se confirma después, con las entradas de al lado.

        Pregunta antes porque tarda —entre siete y veinte segundos sobre las
        22 horas de la Sleep-EDF, según cuán ocupada esté la máquina— y dice
        con qué canales: un EMG que no se usa por lento explica por qué R sale
        peor. Corre en otro hilo, como la ICA: no cambia la señal.
        """
        if self._session is None:
            return
        registro = self._session.recording
        scoring = self._session.scoring
        sin_scorear = scoring.n_windows - scoring.scored_windows()
        if sin_scorear == 0:
            self.statusBar().showMessage(
                "Todas las ventanas ya están scoreadas: no queda nada que sugerir.", 8000
            )
            return
        try:
            canales = default_channels(registro)
        except PsgLabError as error:
            self._show_error(error, "sugerir las fases")
            return
        usados = ", ".join(f"«{c}»" for c in (canales.eeg, canales.eog, canales.emg) if c)
        # La ruta sale del menú armado, como en los paneles vacíos: renombrar
        # la entrada no puede dejar al cartel mandando a buscar algo que no está.
        confirmar = menu_path(self, "accept_safe_suggestions")
        detalle = (
            f"Las propone el clasificador de YASA a partir de {usados}. Quedan como "
            "sugerencias: no se exportan ni cambian lo que ya está scoreado. Se "
            "confirman scoreando cada ventana"
            + (f" o desde «{confirmar}»." if confirmar else ".")
        )
        if canales.too_slow:
            lentos = ", ".join(f"«{c}»" for c in canales.too_slow)
            varios = len(canales.too_slow) > 1
            detalle += (
                f" No se {'usan' if varios else 'usa'} {lentos}: "
                f"{'se grabaron' if varios else 'se grabó'} a 80 Hz o menos."
            )
        if not self._confirmar(
            "Sugerir las fases",
            f"¿Sugerir la fase de {sin_scorear} "
            f"{'ventana' if sin_scorear == 1 else 'ventanas'} sin scorear?",
            "Sugerir",
            informativo=detalle,
        ):
            return

        def calcular() -> object:
            return suggest_stages(registro, canales.eeg, canales.eog, canales.emg)

        self._en_segundo_plano(
            "Calculando las fases sugeridas",
            calcular,
            self._guardar_las_sugeridas,
            accion="sugerir las fases",
        )

    def _guardar_las_sugeridas(self, resultado: object) -> None:
        """Guarda lo que devolvió el clasificador y lo dibuja."""
        if self._session is None or not isinstance(resultado, list):
            return
        scoring = self._session.scoring
        try:
            scoring.set_suggestions(resultado)
        except PsgLabError as error:
            self._show_error(error, "sugerir las fases")
            return
        self._reload_histogram()
        self.refresh()
        seguras = self._sugeridas_con(_CONFIANZA_SEGURA)
        self.statusBar().showMessage(
            f"Se sugirió la fase de {scoring.pending_suggestions()} ventanas; "
            f"{seguras} con una confianza de al menos {round(_CONFIANZA_SEGURA * 100)} %.",
            8000,
        )

    def _sugeridas_con(self, minima: float) -> int:
        """Cuántas sugeridas pendientes tienen al menos esa confianza."""
        if self._session is None:
            return 0
        scoring = self._session.scoring
        return sum(
            1
            for indice in range(scoring.n_windows)
            if (sugerida := scoring.suggestion(indice)) is not None
            and sugerida.confidence >= minima
        )

    def accept_safe_suggestions(self) -> None:
        """Confirma las fases sugeridas con al menos 80 % de confianza."""
        self._confirmar_las_sugeridas(_CONFIANZA_SEGURA)

    def accept_all_suggestions(self) -> None:
        """Confirma todas las fases sugeridas."""
        self._confirmar_las_sugeridas(0.0)

    def _confirmar_las_sugeridas(self, minima: float) -> None:
        """Pasa a scoring las sugeridas con al menos esa confianza.

        **Pregunta antes**, porque desde ahí son scoring como cualquier otro:
        se exportan, y deshacerlas es volver a scorear ventana por ventana.
        """
        if self._session is None:
            return
        cuantas = self._sugeridas_con(minima)
        if cuantas == 0:
            self.statusBar().showMessage("No hay fases sugeridas para confirmar.", 8000)
            return
        umbral = (
            f" con una confianza de al menos {round(minima * 100)} %" if minima > 0 else ""
        )
        if not self._confirmar(
            "Confirmar las fases sugeridas",
            f"¿Confirmar {cuantas} "
            f"{'fase sugerida' if cuantas == 1 else 'fases sugeridas'}{umbral}?",
            "Confirmar",
            informativo=(
                "Pasan a ser scoring como cualquier otro: se exportan y se pueden "
                "cambiar ventana por ventana. Las ventanas ya scoreadas no se tocan."
            ),
        ):
            return
        try:
            confirmadas = self._session.scoring.accept_suggestions(minima)
        except PsgLabError as error:
            self._show_error(error, "confirmar las fases sugeridas")
            return
        self._reload_histogram()
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.refresh()
        self.refresh()
        self.statusBar().showMessage(
            f"Se {'confirmó' if confirmadas == 1 else 'confirmaron'} {confirmadas} "
            f"{'fase' if confirmadas == 1 else 'fases'}.",
            8000,
        )

    def discard_suggestions(self) -> None:
        """Descarta las fases sugeridas. **Sin preguntar**: no se pierde nada
        que no se pueda volver a pedir, y lo scoreado no se toca."""
        if self._session is None:
            return
        scoring = self._session.scoring
        if scoring.pending_suggestions() == 0:
            self.statusBar().showMessage("No hay fases sugeridas para descartar.", 8000)
            return
        scoring.clear_suggestions()
        self._reload_histogram()
        self.refresh()
        self.statusBar().showMessage("Se descartaron las fases sugeridas.", 8000)

    def _set_arousal(self, arousal: bool) -> None:
        """Marca o desmarca el arousal de la ventana actual (V2_F).

        **Con su `except`, como los otros catorce.** Una excepción que sale de
        un slot de Qt no cierra el programa: la imprime en la consola y el
        usuario no ve nada, que es peor que un cartel. Hoy los datos que llegan
        acá los arma la propia interfaz, pero eso deja de ser cierto en cuanto
        un panel se desincroniza del registro después de `set_recording()`.
        """
        if self._session is None:
            return
        try:
            self._session.scoring.set_arousal(self._session.current_window, arousal)
        except PsgLabError as error:
            self._show_error(error, "marcar el arousal")
            return
        self.refresh()

    def _change_nomenclature(self, nomenclature: Nomenclature) -> None:
        """Cambiar de nomenclatura sobre un registro ya scoreado pierde
        información, así que **se pregunta antes**.

        El panel no puede preguntarlo: no conoce el scoring y no sabe si hay
        algo que perder. Acá sí.
        """
        if self._session is None:
            return
        if self._session.scoring.scored_windows() > 0:
            if not self._confirmar(
                "Cambiar de nomenclatura",
                "¿Convertir el scoring que ya hiciste?",
                "Convertir",
                informativo="La conversión entre nomenclaturas pierde información: "
                "S3 y S4 se funden en N3, y volver atrás no puede distinguirlas.",
            ):
                self.scoring_panel.set_nomenclature(self._session.scoring.nomenclature)
                return
        self._session.scoring.change_nomenclature(nomenclature)
        self.scoring_panel.set_nomenclature(nomenclature)
        install_shortcuts(self, self._session)
        self.refresh()

    def _update_histogram_window(self, window_index: int) -> None:
        herramienta = self._tools.get("histogram")
        if isinstance(herramienta, HistogramTool):
            herramienta.update_window(window_index)

    def _redraw_histogram(self) -> None:
        """Dibuja el hipnograma a partir de lo que publica su herramienta.

        La herramienta no dibuja —no conoce Qt— y devuelve una fase por
        ventana; acá se convierte en barras. El orden vertical lo fija
        `stages_of()`, así que cambiar de nomenclatura reordena el eje solo
        (V3_F del histograma).

        **Lo no scoreado queda en blanco, que es lo que pide V1_P.** Se dibuja
        como `NaN` y no como cero, y ésa es toda la diferencia: `connect="finite"`
        omite los puntos que no son finitos, así que el trazo se corta y la
        ventana sin scorear no deja marca.

        Hasta acá se mapeaba a **cero**, con lo cual `connect="finite"` no podía
        hacer nada —ningún valor era no finito— y lo no anotado se dibujaba como
        una línea en la base, por debajo de la fase más baja. Un tramo sin mirar
        se leía como una fase más, que es justo lo que el pliego no quiere: el
        histograma tiene el tamaño de la noche desde el arranque y hay que poder
        ver qué falta.
        """
        herramienta = self._tools.get("histogram")
        if not isinstance(herramienta, HistogramTool) or self._session is None:
            return
        barras = herramienta.bars()
        if not barras:
            return

        orden = list(stages_of(self._session.scoring.nomenclature))
        altura = {fase: float(len(orden) - posicion) for posicion, fase in enumerate(orden)}
        item = self.histogram_view.getPlotItem()
        item.clear()
        item.plot(
            range(len(barras)),
            # `nan` para lo que no es una fila del histograma: `UNSCORED` no
            # tiene altura porque `stages_of()` no la incluye, y ésa es
            # exactamente la ausencia que hay que dibujar.
            [altura.get(fase, float("nan")) for fase in barras],
            stepMode="right",
            connect="finite",
        )
        self._pintar_las_fases(herramienta, altura)
        self._dibujar_las_sugeridas(herramienta, altura)
        # La franja de posición se pinta con lo mismo: una fase tiene que verse
        # igual en los dos lugares, y las dos salen de `bars()`. Las sugeridas
        # van con el color de su fase, apagado (hito 75).
        esquema = theme.current()
        sugeridas = herramienta.suggested_bars() or (SleepStage.UNSCORED,) * len(barras)
        self.navigation.set_scoring(
            [
                esquema.color_for_stage(fase.value)
                if fase is not SleepStage.UNSCORED
                else _apagado(esquema.color_for_stage(sugerida.value))
                for fase, sugerida in zip(barras, sugeridas)
            ]
            if esquema.stage_colors
            else []
        )
        item.setYRange(0, len(orden) + 0.5, padding=0)
        # `stage_label()` y no `str(fase)`: el segundo da "SleepStage.WAKE".
        # Es el mismo nombre que usan el panel de scoring y `Informacion.txt`.
        item.getAxis("left").setTicks(
            [[(altura[fase], stage_label(fase)) for fase in orden]]
        )
        item.getAxis("bottom").setTicks([self._marcas_del_histograma(len(barras))])

    def _pintar_las_fases(
        self, herramienta: HistogramTool, altura: dict[SleepStage, float]
    ) -> None:
        """Le pone a cada tramo del hipnograma el color de su fase (hito 34).

        **Sobre la curva y no en vez de ella.** La curva es la que resuelve lo
        no scoreado con `NaN`, que es V1_P, y la que deja ver de un vistazo la
        forma de la noche; el color es lo que deja reconocer una fase sin leer
        el eje. Un esquema sin escala de fases no pinta nada y el hipnograma se
        ve como antes.

        **Un solo ítem de escena para todos los tramos**, y tramos en vez de
        ventanas: es la misma cuenta del hito 25 con la grilla, sobre un panel
        que se redibuja en cada cambio de época.
        """
        esquema = theme.current()
        if not esquema.stage_colors:
            return
        tramos = [
            (inicio, cuantas, esquema.color_for_stage(fase.value), altura.get(fase))
            for inicio, cuantas, fase in herramienta.runs()
        ]
        # Una fase que el esquema no conoce, o que no es una fila del eje, no
        # se pinta: el color inventado sería peor que la curva sola.
        dibujables = [t for t in tramos if t[2] is not None and t[3] is not None]
        if not dibujables:
            return
        self.histogram_view.getPlotItem().addItem(
            pg.BarGraphItem(
                x0=[inicio for inicio, _, _, _ in dibujables],
                x1=[inicio + cuantas for inicio, cuantas, _, _ in dibujables],
                y0=[y - _GROSOR_DE_LA_FASE / 2 for _, _, _, y in dibujables],
                height=_GROSOR_DE_LA_FASE,
                pen=None,
                brushes=[color for _, _, color, _ in dibujables],
            )
        )

    def _dibujar_las_sugeridas(
        self, herramienta: HistogramTool, altura: dict[SleepStage, float]
    ) -> None:
        """Las fases sugeridas, como una curva punteada aparte (hito 75).

        **Punteada y en la tinta del texto, sin el color de las fases**: tiene
        que leerse de un vistazo que eso no lo scoreó nadie. Sólo aparece sobre
        las ventanas sin scorear, así que nunca se superpone con la curva de lo
        elegido a mano.
        """
        sugeridas = herramienta.suggested_bars()
        if not any(fase is not SleepStage.UNSCORED for fase in sugeridas):
            return
        self.histogram_view.getPlotItem().plot(
            range(len(sugeridas)),
            [altura.get(fase, float("nan")) for fase in sugeridas],
            stepMode="right",
            connect="finite",
            pen=pg.mkPen(theme.current().foreground, width=1, style=Qt.PenStyle.DashLine),
        )

    def _preparar_el_eje_de_la_metrica(self) -> None:
        """Le da al eje de la métrica las marcas del hipnograma (hito 54).

        **Son los dos gráficos de la noche entera** y el de la métrica decía
        «Ventana» aunque el hipnograma estuviera en hora: se leían en unidades
        distintas. Salen de `_marcas_del_histograma()`, corridas a base 1, que
        es como la métrica numera sus ventanas. También le pone la marca de la
        época actual, que de otro modo aparecería recién con la próxima flecha.
        """
        if self._session is None:
            return
        herramienta = self._tools.get("histogram")
        en_hora = (
            isinstance(herramienta, HistogramTool)
            and herramienta.uses_clock_time
            and self._session.recording.start_time is not None
        )
        marcas = [
            (posicion + 1, texto)
            for posicion, texto in self._marcas_del_histograma(self._session.n_windows)
        ]
        self.metric_panel.set_time_ticks(marcas, en_hora)
        self.metric_panel.set_current_window(self._session.current_window)

    def _marcas_del_histograma(self, cuantas: int) -> list[tuple[float, str]]:
        """Las marcas del eje horizontal del hipnograma (V2_F).

        **Faltaba entero.** `set_time_axis()` prendía un booleano que no leía
        nadie y el eje se dibujaba con los índices crudos de `range()`, o sea
        base 0 y sin marcas: ni la hora real ni el 1 a VENMAX que pide el
        pliego.

        Las dos variantes salen del mismo lugar: `core.windows`. La hora real
        viene de `window_to_clock_time()`, que devuelve `None` si el archivo no
        informó a qué hora empezó, y ahí se cae al número de ventana en vez de
        inventar una hora.

        Los números de ventana van en **base 1**, que es la regla del proyecto
        para todo lo que se muestra.
        """
        herramienta = self._tools.get("histogram")
        if self._session is None or cuantas <= 0:
            return []
        en_hora = isinstance(herramienta, HistogramTool) and herramienta.uses_clock_time
        inicio = self._session.recording.start_time

        # Una decena de marcas alcanza para leer una noche entera sin que se
        # pisen los textos. Se calcula el paso en vez de fijarlo: un registro de
        # cinco ventanas y uno de tres mil necesitan cosas distintas.
        paso = max(1, cuantas // 10)
        marcas: list[tuple[float, str]] = []
        for ventana in range(0, cuantas, paso):
            if en_hora and inicio is not None:
                hora = window_to_clock_time(ventana, inicio)
                texto = hora.strftime("%H:%M") if hora is not None else str(ventana + 1)
            else:
                texto = str(ventana + 1)
            marcas.append((float(ventana), texto))
        return marcas

    def set_histogram_time_axis(self, use_clock_time: bool) -> None:
        """Cambia el eje del hipnograma entre hora real y número de ventana.

        La herramienta se niega a poner la hora real si el registro no informa
        a qué hora empezó, y tiene razón: un eje con una hora inventada se lee
        como si fuera cierta. Acá eso se convierte en un cartel.
        """
        herramienta = self._tools.get("histogram")
        if not isinstance(herramienta, HistogramTool):
            return
        try:
            herramienta.set_time_axis(use_clock_time)
        except PsgLabError as error:
            self._show_error(error, "cambiar el eje del hipnograma")
            return
        self._redraw_histogram()
        self._preparar_el_eje_de_la_metrica()


def _apagado(color: str | None) -> str | None:
    """Un color `#rrggbb` con la opacidad de las sugeridas, como `#aarrggbb`.

    Es la forma que entiende `QColor`. Otro formato vuelve `None` y la ventana
    queda sin pintar, que es mejor que un color inventado.
    """
    if color is None or len(color) != 7 or not color.startswith("#"):
        return None
    return f"#{_OPACIDAD_DE_LA_SUGERIDA}{color[1:]}"
