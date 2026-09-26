"""La ventana y las anotaciones: anotar con el mouse o con el teclado.

Terminar un tramo arrastrado y preguntar su clase, el menú de una anotación
—cambiar de clase, borrar—, anotar la ventana actual con el teclado (hito 62) e
importar las marcas del registro (hito 73). El modelo es `core/annotations.py`
y el modo del mouse, `tools/annotator.py`.

**Es un pedazo de `MainWindow`** (hito 76), no una pieza aparte: la clase de
acá no hereda de nada y no se instancia sola. `MainWindow` la hereda junto con
las otras seis, **antes de `QMainWindow`** para que sus métodos le ganen a los
de Qt. Todas comparten el estado que arma `MainWindow.__init__`, así que la
partición es por tema y no por dependencias: el código se leía en un archivo
de 4300 líneas y 170 métodos, y ahora cada tema tiene el suyo.

Cubre del pliego: ningún ID. Las funcionalidades de anotación tienen su fila
en los módulos de `core/` y `tools/` que las implementan; ésta es la
infraestructura que las conecta con la ventana.
"""

from collections import Counter

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QInputDialog, QMenu

from psglab.core.annotations import Annotation, marks_to_annotations
from psglab.core.windows import window_to_samples
from psglab.readers.base import MARKS_KEY
from psglab.tools.annotator import AnnotatorTool
from psglab.tools.overview import OverviewTool
from psglab.utils.errors import PsgLabError

#: Las entradas del menú del clic derecho sobre una banda.
_CAMBIAR_CLASE = "Cambiar clase…"

_BORRAR = "Borrar"


class AnnotationMixin:
    """Lo de `MainWindow` que anota: con el mouse, con el teclado y desde el archivo.
    """

    def _finish_annotation(self, herramienta: AnnotatorTool) -> None:
        """Pregunta la clase del evento recién seleccionado y lo anota (V1_F).

        El pliego pide **asignarle o crear una clase**, así que el diálogo es
        editable: la lista ofrece las que ya existen y el usuario puede escribir
        una nueva, que se registra con su color antes de anotar.

        Cancelar deja el tramo pendiente sin anotar, que es lo que espera quien
        se arrepiente a mitad del gesto. No se lo borra: volver a soltar el
        mouse lo reemplaza.
        """
        if self._session is None:
            return
        pendiente = herramienta.pending_selection_samples
        if pendiente is None:
            return
        self._preguntar_clase_y_anotar(herramienta, *pendiente)

    def _preguntar_clase_y_anotar(
        self, herramienta: AnnotatorTool, inicio: int, duracion: int
    ) -> None:
        """Pregunta la clase de un tramo y lo anota.

        Es el final común del arrastre con el mouse y de «Anotar la ventana
        actual» con el teclado (hito 62): los dos llegan con un tramo en
        muestras y lo demás es igual.
        """
        if self._session is None:
            return
        clases = self._session.annotations.labels()
        clase, acepto = QInputDialog.getItem(
            self,
            "Anotar evento",
            "Clase del evento (se puede escribir una nueva):",
            clases,
            0,
            True,
        )
        if not acepto or not clase.strip():
            return
        clase = clase.strip()

        try:
            if clase not in clases:
                herramienta.add_label(clase)
            herramienta.create_annotation(clase, inicio, duracion)
        except PsgLabError as error:
            self._show_error(error, "anotar el evento")
            return
        # El panel de contexto marca los eventos que caen en cada ventana
        # (V3_F), y anotar no mueve de ventana: hay que pedirle que se
        # rederive o el evento recién creado no aparece hasta la próxima flecha.
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.refresh()
        self.statusBar().showMessage(f"Se anotó «{clase}»", 5000)

    def _menu_de_anotacion(
        self, herramienta: AnnotatorTool, segundos: float, donde: QPoint
    ) -> None:
        """El clic derecho sobre una banda: cambiarle la clase o borrarla.

        **Hasta el hito 52 el clic derecho borraba**, con confirmación, y era lo
        único que se podía hacer con una anotación hecha. Un clic derecho donde
        no hay nada no hace nada.
        """
        anotacion = herramienta.annotation_at(segundos)
        if anotacion is None:
            return
        self._ofrecer_cambios(herramienta, anotacion, donde)

    def _ofrecer_cambios(
        self, herramienta: AnnotatorTool, anotacion: Annotation, donde: QPoint
    ) -> None:
        """El menú de una anotación: cambiarle la clase o borrarla."""
        eleccion = self._elegir_en_un_menu(
            [_CAMBIAR_CLASE, _BORRAR], donde
        )
        if eleccion == _CAMBIAR_CLASE:
            self._cambiar_clase(herramienta, anotacion)
        elif eleccion == _BORRAR:
            self._borrar_anotacion(herramienta, anotacion)

    # -- Anotar con el teclado (hito 62) ------------------------------------
    #
    # **Anotar era lo único del pliego que exigía mouse**: arrastrar sobre la
    # señal para crear, clic derecho para corregir. WCAG 2.1.1 pide que todo
    # se pueda con el teclado, y la unidad natural del teclado es la época,
    # que es lo que mueven las flechas.

    def annotate_current_window(self) -> None:
        """E: anota la ventana actual entera y pregunta su clase.

        **Enciende el modo «Anotar»** si no lo estaba, igual que elegirlo del
        menú: la herramienta es la que sabe anotar, y dejarla encendida es lo
        que permite después corregir con Mayús+F10 o con el mouse.
        """
        herramienta = self._anotador_encendido()
        if herramienta is None or self._session is None:
            return
        inicio, fin = self._muestras_de_la_ventana_actual()
        self._preguntar_clase_y_anotar(herramienta, inicio, fin - inicio)

    def annotation_menu_for_current_window(self) -> None:
        """Mayús+F10 o la tecla Menú, con el foco en la señal: el menú del
        clic derecho para la anotación de la ventana actual.

        Si hay varias se elige **la más corta**, con la misma regla que el
        clic derecho: la larga se puede alcanzar desde otra ventana, la corta
        no. Sin ninguna, la barra de estado lo dice en vez de no hacer nada.
        """
        herramienta = self._anotador_encendido()
        if herramienta is None or self._session is None:
            return
        inicio, fin = self._muestras_de_la_ventana_actual()
        en_la_ventana = self._session.annotations.in_range(inicio, fin)
        if not en_la_ventana:
            self.statusBar().showMessage("No hay ninguna anotación en esta ventana", 5000)
            return
        anotacion = min(en_la_ventana, key=lambda candidata: candidata.duration_samples)
        vista = self.signal_view.viewport()
        self._ofrecer_cambios(herramienta, anotacion, vista.mapToGlobal(vista.rect().center()))

    def _anotador_encendido(self) -> AnnotatorTool | None:
        """La herramienta de anotar, encendida por el mismo camino que el menú."""
        herramienta = self._tools.get("annotator")
        accion = self._tool_actions.get("annotator")
        if not isinstance(herramienta, AnnotatorTool) or accion is None:
            return None
        if not accion.isChecked():
            accion.setChecked(True)
        return herramienta

    def _muestras_de_la_ventana_actual(self) -> tuple[int, int]:
        """Dónde empieza y termina la ventana actual, recortada al registro."""
        registro = self._session.recording
        inicio, fin = window_to_samples(self._session.current_window, registro.sampling_rate)
        return inicio, min(fin, registro.n_samples)

    def _elegir_en_un_menu(self, opciones: list[str], donde: QPoint) -> str | None:
        """Muestra un menú contextual y devuelve lo que se eligió, o `None`.

        Aparte para que los tests lo contesten sin abrirlo: es modal, y sin
        nadie que elija la suite se colgaría.
        """
        menu = QMenu(self)
        for opcion in opciones:
            menu.addAction(opcion)
        elegida = menu.exec(donde)
        return elegida.text() if elegida is not None else None

    def _cambiar_clase(self, herramienta: AnnotatorTool, anotacion: Annotation) -> None:
        """Pregunta la clase nueva de una anotación hecha y se la cambia.

        El diálogo es el mismo que al anotar —editable, así que una clase nueva
        se puede escribir— pero arranca en la clase que tiene. Elegir la misma
        no hace nada.
        """
        if self._session is None:
            return
        clases = self._session.annotations.labels()
        actual = clases.index(anotacion.label) if anotacion.label in clases else 0
        clase, acepto = QInputDialog.getItem(
            self,
            "Cambiar la clase",
            "Clase del evento (se puede escribir una nueva):",
            clases,
            actual,
            True,
        )
        clase = clase.strip()
        if not acepto or not clase or clase == anotacion.label:
            return
        try:
            if clase not in clases:
                herramienta.add_label(clase)
            herramienta.change_label(anotacion, clase)
        except PsgLabError as error:
            self._show_error(error, "cambiar la clase")
            return
        self._refrescar_contexto()
        self.statusBar().showMessage(
            f"«{anotacion.label}» pasó a ser «{clase}»", 5000
        )

    def _avisar_borde_movido(self, herramienta: AnnotatorTool) -> None:
        """Después de soltar un borde arrastrado: la Übersicht y el aviso."""
        movida = herramienta.moved_annotation
        if movida is None:
            return
        self._refrescar_contexto()
        self.statusBar().showMessage(f"Se corrigió el tramo de «{movida.label}»", 5000)

    def _cursor_del_anotador(
        self, herramienta: AnnotatorTool, segundos: float, evento: QMouseEvent
    ) -> None:
        """↔ sobre el borde de una banda, que es lo único que dice que se puede
        arrastrar. Mientras se arrastra, el cursor no cambia."""
        if evento.buttons() != Qt.MouseButton.NoButton:
            return
        viewport = self.signal_view.viewport()
        if herramienta.edge_at(segundos) is not None:
            viewport.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            viewport.unsetCursor()

    def _borrar_anotacion(self, herramienta: AnnotatorTool, anotacion: Annotation) -> None:
        """Borra una anotación, confirmándolo antes.

        **Pregunta** porque no hay deshacer, y una anotación es trabajo del
        investigador. Desde el hito 52 se llega eligiendo «Borrar» en el menú
        del clic derecho, así que un clic de más ya no borra solo; la pregunta
        se conservó igual, porque elegir mal en un menú también es un clic.
        """
        if not self._confirmar(
            "Borrar la anotación",
            f"¿Borrar la anotación «{anotacion.label}»?",
            "Borrar",
            informativo="No se puede deshacer.",
            destructivo=True,
        ):
            return
        try:
            herramienta.delete_annotation(anotacion)
        except PsgLabError as error:
            self._show_error(error, "borrar la anotación")
            return
        # Igual que al anotar: la Übersicht marca qué ventanas tienen eventos.
        contexto = self._tools.get("overview")
        if isinstance(contexto, OverviewTool):
            contexto.refresh()
        self.statusBar().showMessage(f"Se borró «{anotacion.label}»", 5000)

    def import_file_marks(self) -> None:
        """Agrega como anotaciones las marcas que trae el archivo (hito 73).

        Un BrainVision trae los marcadores de su `.vmrk` y un EDF+ sus
        anotaciones. **Los lectores los guardaban y nada los leía**, aunque el
        docstring del de BrainVision prometía convertirlos en anotaciones «si
        el usuario lo pide»: es lo que hace esto.

        **Sólo a pedido, y preguntando antes** cuántas son de cada clase. Un
        registro puede traer cientos de marcas de estímulo, y al abrir no se
        sabe si interesan. Las que ya están —misma clase, mismo tramo— no se
        repiten, así que importar dos veces no duplica nada.
        """
        if self._session is None:
            return
        registro = self._session.recording
        marcas = registro.metadata.get(MARKS_KEY)
        try:
            nuevas = marks_to_annotations(
                list(marcas) if isinstance(marcas, list) else [],
                registro.sampling_rate,
                registro.n_samples,
            )
        except PsgLabError as error:
            self._show_error(error, "importar las marcas del registro")
            return
        conjunto = self._session.annotations
        ya_estan = set(conjunto.all())
        nuevas = [a for a in dict.fromkeys(nuevas) if a not in ya_estan]
        if not nuevas:
            self.statusBar().showMessage(
                f"«{registro.file_path.name}» no trae marcas que no estén ya anotadas.",
                8000,
            )
            return
        cuentas = Counter(anotacion.label for anotacion in nuevas)
        detalle = ", ".join(f"{clase} ({cuantas})" for clase, cuantas in cuentas.most_common())
        if not self._confirmar(
            "Importar las marcas del registro",
            f"¿Agregar {len(nuevas)} {'marca' if len(nuevas) == 1 else 'marcas'} "
            f"de «{registro.file_path.name}» como anotaciones?",
            "Importar",
            informativo=detalle,
        ):
            return
        try:
            for anotacion in nuevas:
                conjunto.add_label(anotacion.label)
                conjunto.add(anotacion)
        except PsgLabError as error:
            self._show_error(error, "importar las marcas del registro")
            return
        self._redibujar_overlays()
        self.refresh()
        self.statusBar().showMessage(
            f"Se {'agregó' if len(nuevas) == 1 else 'agregaron'} {len(nuevas)} "
            f"{'anotación' if len(nuevas) == 1 else 'anotaciones'} desde las marcas del registro.",
            8000,
        )
