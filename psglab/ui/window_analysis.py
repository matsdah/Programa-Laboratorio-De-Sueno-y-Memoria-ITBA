"""La ventana y el análisis: los pedidos de la Parte 2 y sus paneles.

Espectro, complejidad, conectividad, filtros, impedancia, ICA, derivar y
re-referenciar: cada uno toma lo que necesita de la sesión, calcula —en otro
hilo si tarda— y le pasa el resultado a su panel. También el aviso de los
canales planos (hito 32) y volver a la señal original.

**Es un pedazo de `MainWindow`** (hito 76), no una pieza aparte: la clase de
acá no hereda de nada y no se instancia sola. `MainWindow` la hereda junto con
las otras seis, **antes de `QMainWindow`** para que sus métodos le ganen a los
de Qt. Todas comparten el estado que arma `MainWindow.__init__`, así que la
partición es por tema y no por dependencias: el código se leía en un archivo
de 4300 líneas y 170 métodos, y ahora cada tema tiene el suyo.

Cubre del pliego: V5_F de "Filtración" (`_olvidar_ica`, que descarta la
descomposición cuando la señal deja de ser la suya). El cálculo está en
`analysis/`; lo que vive acá es el ciclo de vida de la ICA entre el ajuste y el
«Aplicar».
"""

import threading
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import QFileDialog, QInputDialog

from psglab.core.recording import Recording
from psglab.analysis.derivation import derive
from psglab.analysis.complexity import MEASURES, complexity_by_window, warm_up
from psglab.analysis.connectivity import (
    METHOD_LABELS,
    average_connectivity,
    compute_connectivity,
    connectivity_by_window,
)
from psglab.analysis.ica import (
    apply_ica,
    component_time_course,
    component_topography,
    explained_variance,
    fit_ica,
)
from psglab.analysis.impedance import (
    DEFAULT_LIMIT_KOHM,
    impedance_report,
    load_impedances_from_file,
    read_impedances,
)
from psglab.analysis.filters import apply_filters, settings_for_kinds
from psglab.analysis.psd import band_power, compute_psd, describe_method
from psglab.analysis.reference import average_reference, rereference
from psglab.core.windows import count_windows, window_to_samples
from psglab.readers.base import warm_up_readers
from psglab.utils.errors import PsgLabError

#: Medidas de complejidad que la interfaz ofrece para recorrer la noche.
#:
#: **Son las de `MEASURES` menos la entropía de muestra**, y la exclusión está
#: medida, no supuesta: sobre una ventana de 30 s a 256 Hz tarda 124 ms contra
#: 0,07–1,7 ms de las otras tres, así que sobre las 2650 ventanas de un
#: registro real son más de cinco minutos con la ventana congelada.
#:
#: `complexity_by_window()` la acepta igual: es una función de biblioteca y
#: quien la llama desde un script puede esperar. La política es de la interfaz.
MEDIDAS_RAPIDAS = tuple(m for m in MEASURES if m != "sample_entropy")

#: Con qué método se mide la conectividad. **Se pide explícito** y no por el
#: valor por omisión de `compute_connectivity()`: el rótulo de la escala de
#: color sale de acá, y con el método implícito los dos podían separarse sin
#: que nada fallara.
METODO_DE_CONECTIVIDAD: str = "wpli"


class AnalysisMixin:
    """Lo de `MainWindow` que pide los análisis de la Parte 2 y muestra sus paneles.
    """

    def _reiniciar_paneles_de_analisis(self) -> None:
        """Deja los paneles de análisis como corresponden al registro recién abierto.

        **Seguían mostrando el anterior.** El espectro decía «Espectro de «C3»»
        sobre un registro sin C3; la métrica y la conectividad eran de otra
        señal; la tabla de impedancias listaba los canales viejos con el informe
        de los nuevos; y el panel de filtros conservaba los sugeridos del otro
        registro, así que en uno de 100 Hz «Aplicar» pedía el notch de 50 Hz.

        Los que muestran un resultado se vacían, porque recalcularlos es
        trabajo que nadie pidió. Los que muestran una configuración —filtros e
        impedancias— se cargan con la del registro nuevo, que no calcula nada.
        La ICA la olvida `_olvidar_ica()`.
        """
        self._olvidar_resultados()
        if self._session is not None:
            self.filter_panel.set_recording(self._session.recording)
        self._cargar_impedancias()

    def _olvidar_resultados(self) -> None:
        """Vacía el espectro, la métrica y la conectividad, con sus títulos.

        Se llama al abrir un registro y **cada vez que cambia la señal**:
        filtrar, derivar, re-referenciar, aplicar la ICA o volver a la
        original. Hasta el hito 30, después de filtrar el espectro seguía
        mostrando el de la señal sin filtrar, con el mismo título y sin decir
        nada. Es la misma regla que `_olvidar_ica()` aplica a la descomposición:
        un resultado de una señal que ya no está no se muestra como si fuera de
        ésta. Se vacía en vez de recalcularlo porque recalcular es trabajo que
        nadie pidió; el panel vacío dice desde dónde se vuelve a pedir.
        """
        self.psd_panel.clear_spectrum()
        self.psd_panel.clear_band_powers()
        self.metric_panel.clear_metric()
        self.connectivity_panel.clear_matrix()

    def warm_up_in_background(self) -> None:
        """Paga en otro hilo las dos esperas que se cobraban a la primera vez.

        **Los lectores primero**, porque abrir un registro es lo primero que
        hace el usuario: `mne.io` carga el módulo de cada formato recién al
        usarlo, y eso eran 8,65 de los 9,2 s de la primera lectura de cada
        sesión del programa, con la ventana congelada (hito 33). La segunda
        lectura del mismo archivo tardaba 18 ms.

        **Después `antropy`**, que compila con `numba` al importarse: 7 s en
        esta máquina, 21 s en la del hito 17, y los pagaba la primera medida de
        complejidad. En otro hilo no congela la ventana: medido en el hito 31,
        la interfaz sigue respondiendo con algún tirón de hasta 65 ms.

        Si el usuario llega antes que el hilo, el lock de importación de Python
        lo hace esperar lo que falte y nada se importa dos veces.

        `daemon` para que cerrar el programa no espere a que termine. **Lo
        lanza sólo `main.py`**, por `create_main_window(warm_up=True)`: cada
        ventana de la suite de tests lanzaría un hilo.
        """
        threading.Thread(target=_precalentar, name="precalentar-analisis", daemon=True).start()

    # -- Análisis (Parte 2) --------------------------------------------------

    def _aplicar_analisis(
        self,
        que_hace: str,
        calcular: Callable[[Recording], Recording],
        mostrar: str | None = None,
        accion: str | None = None,
    ) -> None:
        """Corre un análisis y lleva su resultado a la pantalla.

        Es el camino único de todo el menú Análisis: los módulos devuelven un
        `Recording` nuevo —no tocan el original, que es la regla 1 de la
        carpeta— y acá se lo entrega a la sesión con `set_recording()`, que
        conserva la ventana, los canales y las amplitudes.

        Un error del análisis sale como cartel y **no cambia nada**: la señal
        que el investigador está mirando sigue siendo la de antes.

        Args:
            mostrar: canal que hay que hacer visible además de los que ya
                estaban. `Session.set_recording()` conserva los visibles que
                sobreviven y **un canal nuevo no sobrevive: nace**, así que sin
                esto una derivación se creaba y no se veía. Mostrarlo es una
                decisión de presentación —el usuario acaba de pedirlo— y por eso
                vive acá y no en `core/`.
            accion: qué no se pudo hacer si falla, para la primera línea del
                cartel; ver `_show_error()`.
        """
        if self._session is None:
            return
        try:
            with self._trabajando(que_hace.replace("Se ", "").capitalize()):
                procesado = calcular(self._session.recording)
            self._session.set_recording(procesado)
        except PsgLabError as error:
            self._show_error(error, accion)
            return
        if mostrar is not None and mostrar not in self._session.visible_channels:
            self._session.set_visible_channels(
                [*self._session.visible_channels, mostrar]
            )
        self.signal_view.set_session(self._session)
        self.channel_selector.set_recording(procesado)
        # La señal cambió, así que la descomposición que hubiera dejó de ser de
        # este registro. Va **después** del `except`: si el análisis falló, la
        # señal es la de antes y la ICA sigue siendo válida. La reproducción
        # se detiene por lo mismo: la página puede haber cambiado de largo.
        self._olvidar_ica()
        self._olvidar_resultados()
        self.playback.stop()
        self.accion_señal_original.setEnabled(True)
        self.refresh()
        self.statusBar().showMessage(que_hace, 5000)

    def _olvidar_ica(self) -> None:
        """Descarta la descomposición ICA porque la señal dejó de ser la suya.

        **Es la única guarda que hay contra el error más caro del menú Análisis.**
        `fit_ica()` se ajusta sobre la señal que había en ese momento, y el panel
        se queda abierto esperando que el usuario elija qué quitar. Si entre el
        ajuste y el "Aplicar" la señal cambió —se filtró, se derivó, se
        re-referenció, se volvió a la original, o se abrió otro registro—, la
        matriz de desmezclado ya no corresponde.

        **Y no falla sola.** Filtrar no cambia los nombres de los canales, así que
        MNE acepta el pedido sin protestar y devuelve una señal reconstruida con
        una descomposición ajena. El resultado es plausible, irreversible y
        equivocado, que es exactamente lo que `analysis/ica.py` dice querer
        evitar cuando advierte que "el usuario puede no darse cuenta".

        Olvidar es lo correcto y no una molestia: volver a ajustar es un clic, y
        la alternativa —conservarla y avisar— le pide al investigador que decida
        sobre algo que no puede ver. `apply_ica()` tiene además su propia guarda
        para el caso en que los canales sí cambien.

        No hace nada si no hay ninguna descomposición cargada, así que se la
        puede llamar desde cualquier camino sin preguntar antes.
        """
        if self._ica is None:
            return
        self._ica = None
        self.ica_panel.clear_components()
        self.ica_dialog.hide()

    def _elegir_canal(self, titulo: str, etiqueta: str) -> str | None:
        """Pregunta un canal de los que hay. `None` si el usuario cancela."""
        if self._session is None:
            return None
        nombres = self._session.recording.channel_names()
        elegido, acepto = QInputDialog.getItem(self, titulo, etiqueta, nombres, 0, False)
        return elegido if acepto else None

    def derive_dialog(self) -> None:
        """Pregunta los dos canales y agrega la derivación (sección "Derivar").

        Se pregunta de a uno y no con un diálogo propio porque son dos listas
        de lo mismo: un formulario para eso sería más código y no más claro.
        """
        if self._session is None:
            return
        canal = self._elegir_canal("Derivar", "Canal:")
        if canal is None:
            return
        referencia = self._elegir_canal("Derivar", f"«{canal}» menos:")
        if referencia is None:
            return
        self._aplicar_analisis(
            f"Se agregó la derivación «{canal}-{referencia}»",
            lambda registro: derive(registro, canal, referencia),
            mostrar=f"{canal}-{referencia}",
            accion=f"derivar «{canal}-{referencia}»",
        )

    def rereference_dialog(self) -> None:
        """Pregunta la referencia nueva y re-referencia (sección "Rereferenciar")."""
        referencia = self._elegir_canal("Re-referenciar", "Referencia nueva:")
        if referencia is None:
            return
        self._aplicar_analisis(
            f"Se re-referenció a «{referencia}»",
            lambda registro: rereference(registro, [referencia]),
            accion="re-referenciar la señal",
        )

    def apply_average_reference(self) -> None:
        """Re-referencia al promedio de los EEG.

        No pregunta nada: `kind_only=True` es el valor seguro y el que el
        docstring del módulo defiende. Si el registro no tiene EEG, el módulo se
        niega y acá eso se convierte en un cartel.
        """
        self._aplicar_analisis(
            "Se re-referenció al promedio de los canales EEG",
            lambda registro: average_reference(registro),
            accion="re-referenciar la señal",
        )

    # -- El canal plano (hito 32) -------------------------------------------
    #
    # Con un canal plano el espectro sale en cero, la dimensión de Higuchi no
    # existe y la conectividad cuenta 0: las tres respuestas son correctas, y sin
    # explicarlas parecen un error del programa. Los números no cambian; la
    # regla de qué es plano es `Recording.flat_channels()`.

    def _planos_en_la_ventana(self, ventana: int, canales: list[str]) -> list[str]:
        """Cuáles de esos canales están planos en una época."""
        if self._session is None:
            return []
        registro = self._session.recording
        inicio, fin = window_to_samples(ventana, registro.sampling_rate)
        return registro.flat_channels(inicio, fin, canales)

    def _ventanas_planas(self, canales: list[str]) -> Counter[str]:
        """En cuántas épocas de la noche está plano cada canal que lo esté alguna vez.

        Recorre la noche una sola vez con todos los canales: con el registro de
        prueba son 2650 épocas, y cada una es un recorte sin copia.
        """
        planas: Counter[str] = Counter()
        if self._session is None:
            return planas
        registro = self._session.recording
        for ventana in range(count_windows(registro.n_samples, registro.sampling_rate)):
            planas.update(self._planos_en_la_ventana(ventana, canales))
        return planas

    def _nota_de_la_noche(self, series: dict[str, np.ndarray]) -> str:
        """El renglón que explica los ceros y los huecos de una medida de la noche."""
        total = max((len(v) for v in series.values()), default=0)
        planas = self._ventanas_planas(list(series))
        if planas:
            canal, cuantas = planas.most_common(1)[0]
            return (
                f"<br>«{canal}» está plano en {cuantas} de {total} ventanas: ahí la "
                "medida vale 0 o no existe."
            )
        huecos = max((int(np.isnan(v).sum()) for v in series.values()), default=0)
        if huecos:
            return f"<br>{huecos} de {total} ventanas sin valor: son demasiado cortas para medir."
        return ""

    def _sin_contenido_en(self, canales: list[str], banda: tuple[float, float]) -> str:
        """La nota de los canales que no tienen nada en una banda (hito 72).

        Un canal grabado más lento que el registro llega a la frecuencia de
        éste, pero no tiene nada por encima de la mitad de la suya: medirle la
        conectividad en alfa es medir interpolación. `""` si no hay ninguno.
        """
        if self._session is None:
            return ""
        desde, _ = banda
        lentos = [
            canal
            for canal in canales
            if self._session.recording.content_limit_hz(canal) <= desde
        ]
        if not lentos:
            return ""
        uno = len(lentos) == 1
        return (
            f"<br>{self._nombrar(lentos)} {'se grabó' if uno else 'se grabaron'} "
            f"más lento que el registro y no {'tiene' if uno else 'tienen'} nada en "
            "esa banda: su conectividad ahí no dice nada."
        )

    @staticmethod
    def _nombrar(canales: list[str]) -> str:
        """«C3», «C4» y «O1», como se nombran los canales en el resto del programa."""
        nombres = [f"«{canal}»" for canal in canales]
        return nombres[0] if len(nombres) == 1 else ", ".join(nombres[:-1]) + " y " + nombres[-1]

    # -- Los paneles de análisis ----------------------------------------------
    #
    # Uno por pedido del menú «Analizar» y «Filtrar»: calcular con lo que haya
    # en la sesión y pasarle el resultado a su panel.

    def show_psd_dialog(self) -> None:
        """Calcula el espectro de la ventana actual y lo muestra (V1_F de PSD).

        **De la ventana actual y no del registro entero**, porque es lo que el
        investigador está mirando: el espectro de las ocho horas promedia el
        sueño lento con la vigilia y no dice nada de la época que se está
        scoreando. El título del panel lleva el número de ventana para que no
        haya duda de cuál es.

        Se abre en una ventana aparte y no como panel fijo: un espectro se mira
        cuando hace falta, y la pantalla principal ya tiene la señal, el
        scoring, la navegación, el histograma y el contexto.
        """
        if self._session is None:
            return
        canal = self._elegir_canal("Espectro", "Canal:")
        if canal is None:
            return
        ventana = self._session.current_window
        try:
            frecuencias, potencias = compute_psd(
                self._session.recording,
                channels=[canal],
                window_index=ventana,
                method=self._preferencias.psd_method,
            )
            bandas = self._preferencias.bands()
            potencias_por_banda = {
                nombre: (
                    float(np.ravel(band_power(frecuencias, potencias, extremos))[0]),
                    float(
                        np.ravel(
                            band_power(frecuencias, potencias, extremos, relative=True)
                        )[0]
                    ),
                )
                for nombre, extremos in bandas.items()
            }
        except PsgLabError as error:
            self._show_error(error, "calcular el espectro")
            return

        self.psd_panel.set_spectrum(frecuencias, potencias, [canal], bands=bandas)
        # Con qué se estimó: el método se elige en la configuración, y sin esta
        # línea dos espectros de la misma ventana podían no coincidir sin que
        # el panel dijera por qué. `compute_psd()` ya aceptó el método, así que
        # describirlo no puede fallar.
        self.psd_panel.set_method_description(
            describe_method(self._preferencias.psd_method)
        )
        # **La potencia de cada banda, que es la otra mitad de V1_F.** El panel
        # sombreaba las bandas y nunca decía cuánta potencia tenía cada una;
        # `band_power()` la calculaba desde el hito 13 y no la leía nadie.
        # Se pasan las dos: la absoluta y la relativa, que es la que
        # `analysis/psd.py` documenta como la que permite comparar entre
        # participantes, porque la absoluta depende del cráneo y la impedancia.
        # Las bandas son las de la configuración: las convencionales mientras el
        # usuario no las cambie.
        self.psd_panel.set_band_powers(potencias_por_banda)
        # **La descripción va en el panel y no en el título del dock**, que Qt
        # usa como texto de la entrada en «Herramientas»: el menú se renombraba
        # con cada cálculo (hito 31).
        descripcion = f"Espectro de «{canal}» — ventana {ventana + 1}"
        if self._planos_en_la_ventana(ventana, [canal]):
            descripcion += "<br>El canal está plano en esta ventana: no hay potencia que medir."
        # **Una banda por encima de lo que el registro alcanza da cero**, y un
        # cero no se distingue de un cero real: se dice cuáles y hasta dónde
        # llega el archivo (hito 33). La regla es la misma que usa `band_power`:
        # la banda es semiabierta, `[desde, hasta)`.
        sin_medir = [
            nombre
            for nombre, (desde, hasta) in bandas.items()
            if not ((frecuencias >= desde) & (frecuencias < hasta)).any()
        ]
        if sin_medir:
            tope = self._session.recording.sampling_rate / 2
            descripcion += (
                f"<br>{self._nombrar(sin_medir)} "
                f"{'queda' if len(sin_medir) == 1 else 'quedan'} fuera de lo que este "
                f"registro puede medir, que llega hasta {tope:g} Hz: su potencia sale "
                "en cero."
            )
        # **Y un canal grabado más lento** (hito 72): el archivo lo trae a la
        # frecuencia del registro, pero por encima de la mitad de la suya lo
        # que se ve es interpolación, y la potencia de esas bandas no es suya.
        limite = self._session.recording.content_limit_hz(canal)
        if limite < self._session.recording.sampling_rate / 2:
            descripcion += (
                f"<br>«{canal}» se grabó a {f'{2 * limite:g}'.replace('.', ',')} Hz: "
                f"por encima de {f'{limite:g}'.replace('.', ',')} Hz, lo que se ve "
                "es interpolación y no señal."
            )
        self.psd_panel.set_caption(descripcion)
        self.psd_dialog.show()
        self.psd_dialog.raise_()

    def show_complexity_dialog(self) -> None:
        """Recorre la noche con una medida de complejidad y la grafica.

        **La lista no ofrece la entropía de muestra**, y es una decisión de la
        interfaz y no del módulo: medida sobre el registro real tarda más de
        cinco minutos, contra menos de cinco segundos las otras tres. Con la
        ventana congelada ese rato, el investigador no sabe si el programa
        está trabajando o se colgó.

        `complexity_by_window()` sí la acepta: es una función de biblioteca y
        quien la llama desde un script puede esperar. La política es de acá.
        """
        if self._session is None:
            return
        canal = self._elegir_canal("Complejidad", "Canal:")
        if canal is None:
            return
        medida, acepto = QInputDialog.getItem(
            self, "Complejidad", "Medida:", list(MEDIDAS_RAPIDAS), 0, False
        )
        if not acepto:
            return
        try:
            with self._trabajando(f"Calculando {medida} sobre toda la noche"):
                series = complexity_by_window(
                    self._session.recording, [canal], measure=medida
                )
        except PsgLabError as error:
            self._show_error(error, "calcular la complejidad")
            return

        self._preparar_el_eje_de_la_metrica()
        self.metric_panel.set_metric(medida, series)
        self.metric_panel.set_caption(
            f"{medida} — «{canal}»" + self._nota_de_la_noche(series)
        )
        self.metric_dialog.show()
        self.metric_dialog.raise_()

    def show_connectivity_dialog(self) -> None:
        """Calcula la conectividad de la ventana actual y la muestra.

        **De la ventana actual**, por el mismo motivo que el espectro: la
        conectividad de las ocho horas promedia el sueño lento con la vigilia,
        y en sueño lo que interesa es cómo cambia entre fases.
        """
        if self._session is None:
            return
        canales = self._session.visible_channels
        if len(canales) < 2:
            self._show_error(
                PsgLabError(
                    "La conectividad se mide entre canales, así que hacen falta "
                    "al menos dos visibles.",
                    details=f"canales visibles: {canales}.",
                ),
                "medir la conectividad",
            )
            return
        # **Las mismas bandas que el espectro.** Dos definiciones distintas de
        # «sigma» en el mismo programa serían una trampa: el usuario que
        # corrigió una en la configuración espera verla corregida acá también.
        bandas = self._preferencias.bands()
        banda, acepto = QInputDialog.getItem(
            self, "Conectividad", "Banda:", list(bandas), 0, False
        )
        if not acepto:
            return

        ventana = self._session.current_window
        try:
            with self._trabajando(f"Midiendo la conectividad en {banda}"):
                matriz = compute_connectivity(
                    self._session.recording,
                    channels=canales,
                    band=bandas[banda],
                    method=METODO_DE_CONECTIVIDAD,
                    window_index=ventana,
                )
        except PsgLabError as error:
            self._show_error(error, "medir la conectividad")
            return

        self.connectivity_panel.set_matrix(
            matriz, canales, measure=METHOD_LABELS[METODO_DE_CONECTIVIDAD]
        )
        promedio = average_connectivity(matriz)
        descripcion = (
            f"Conectividad en {banda} — ventana {ventana + 1} — "
            f"promedio {promedio:.3f}".replace(".", ",", 1)
        )
        planos = self._planos_en_la_ventana(ventana, canales)
        if planos:
            descripcion += (
                f"<br>{'Plano' if len(planos) == 1 else 'Planos'} en esta ventana: "
                f"{self._nombrar(planos)}. Su conectividad cuenta 0 y baja el promedio."
            )
        descripcion += self._sin_contenido_en(canales, bandas[banda])
        self.connectivity_panel.set_caption(descripcion)
        self.connectivity_dialog.show()
        self.connectivity_dialog.raise_()

    def show_connectivity_night_dialog(self) -> None:
        """Mide la conectividad época por época y la grafica a lo largo de la noche.

        **Era un hueco declarado**, no una decisión: `connectivity_by_window()`
        existía desde el hito 14 y `MetricPanel` desde el hito 19, que lo dice
        en su propio docstring, y no había ningún camino que los juntara. El
        hito 20 lo dejó anotado como pregunta de producto. Se ofrece al cerrar
        el refactor de la interfaz.

        Lo que se grafica es **el promedio de cada matriz**, sin la diagonal:
        una matriz por época no se puede mirar a lo largo de ochocientas
        épocas, y un número por época sí se compara contra el hipnograma, que
        es para lo que sirve ver la noche entera.

        Es la operación más cara del menú después de la ICA: medido en el hito
        14, entre 0,3 y 0,5 minutos por noche con cuatro canales. Por eso va con
        el cursor de espera.
        """
        if self._session is None:
            return
        canales = self._session.visible_channels
        if len(canales) < 2:
            self._show_error(
                PsgLabError(
                    "La conectividad se mide entre canales, así que hacen falta "
                    "al menos dos visibles.",
                    details=f"canales visibles: {canales}.",
                ),
                "medir la conectividad de la noche",
            )
            return
        bandas = self._preferencias.bands()
        banda, acepto = QInputDialog.getItem(
            self, "Conectividad de la noche", "Banda:", list(bandas), 0, False
        )
        if not acepto:
            return

        # **Lo único que se lee de la sesión se lee acá**, en el hilo de la
        # interfaz: el otro hilo recibe el registro y los nombres ya resueltos y
        # no vuelve a preguntarle nada a `Session`.
        registro = self._session.recording
        limites = bandas[banda]

        def medir() -> object:
            matrices = connectivity_by_window(registro, canales, band=limites)
            return np.array([average_connectivity(matriz) for matriz in matrices])

        self._en_segundo_plano(
            f"Midiendo la conectividad en {banda} a lo largo de la noche",
            medir,
            lambda promedios: self._mostrar_la_conectividad_de_la_noche(
                banda, canales, promedios
            ),
            accion="medir la conectividad de la noche",
        )

    def _mostrar_la_conectividad_de_la_noche(
        self, banda: str, canales: list[str], promedios: object
    ) -> None:
        """Dibuja lo que midió el otro hilo. **Acá sí se tocan widgets.**"""
        etiqueta = f"Conectividad en {banda}"
        self._preparar_el_eje_de_la_metrica()
        self.metric_panel.set_metric(
            etiqueta, {f"Promedio de {len(canales)} canales": promedios}
        )
        # Los canales van en su renglón, y con más de seis se cuentan en vez de
        # nombrarse: treinta y dos nombres no entran en el ancho del gráfico.
        promediados = (
            ", ".join(canales) if len(canales) <= 6 else f"{len(canales)} canales visibles"
        )
        planos = self._ventanas_planas(canales)
        nota = ""
        if planos:
            nota = (
                f"<br>Con tramos planos: {self._nombrar(list(planos))}. Ahí su "
                "conectividad cuenta 0 y baja el promedio."
            )
        bandas = self._preferencias.bands()
        if banda in bandas:
            nota += self._sin_contenido_en(canales, bandas[banda])
        self.metric_panel.set_caption(
            f"{etiqueta} a lo largo de la noche<br>{promediados}{nota}"
        )
        self.metric_dialog.show()
        self.metric_dialog.raise_()

    def show_filter_dialog(self) -> None:
        """Abre el panel de filtros (V1_F de "Filtración").

        Arranca con los sugeridos de cada clase de canal presente. **Abrirlo no
        filtra nada**: hay que apretar Aplicar. Un menú que filtre con sólo
        abrirse le cambiaría la señal a alguien que entró a mirar qué había.
        """
        if self._session is None:
            return
        self.filter_panel.set_recording(self._session.recording)
        self.filter_dialog.show()
        self.filter_dialog.raise_()

    def apply_filters_from_panel(self) -> None:
        """Aplica lo que el panel tenga escrito.

        Se filtra **la señal que se está viendo**, no la original: así se puede
        filtrar después de derivar o de re-referenciar, que es el orden en que
        se trabaja. Y como todo el menú Análisis pasa por `_aplicar_analisis`,
        "Volver a la señal original" deshace también esto: un filtro mal
        elegido no obliga a reabrir el archivo.
        """
        if self._session is None:
            return
        por_clase = self.filter_panel.settings()
        # **Sin ningún filtro escrito no se toca la señal.** Antes se la
        # reemplazaba por una copia idéntica: la barra decía «Se filtró la
        # señal», se habilitaba volver a la original y se descartaba la ICA ya
        # ajustada, todo por un filtrado que no filtró nada.
        if all(filtros.is_empty for filtros in por_clase.values()):
            self._show_error(
                PsgLabError(
                    "No hay ningún filtro escrito, así que la señal no cambió. "
                    "Para quitar un filtro ya aplicado está «Montaje › Volver a "
                    "la señal original».",
                    details=f"filtros por clase: {por_clase}",
                ),
                "filtrar la señal",
            )
            return
        antes = self._session.recording
        self._aplicar_analisis(
            "Se filtró la señal",
            lambda registro: apply_filters(
                registro, settings_for_kinds(registro, por_clase)
            ),
            accion="filtrar la señal",
        )
        if self._session is None or self._session.recording is antes:
            return
        # **Qué canales quedaron sin pasa-altos** (hito 67). `settings_for_kinds()`
        # no se lo da a un canal grabado más lento que el registro, porque lo
        # dejaría plano; el panel lo avisa antes, y acá se confirma después: el
        # EMG del EDF del laboratorio quedaba con el 0,0 % de su señal y la barra
        # decía sólo «Se filtró la señal».
        sin_pasa_altos = [
            nombre
            for nombre, filtros in settings_for_kinds(antes, por_clase).items()
            if filtros.highpass_hz is None
            and por_clase[antes.channel_by_name(nombre).kind].highpass_hz is not None
        ]
        if sin_pasa_altos:
            uno = len(sin_pasa_altos) == 1
            self.statusBar().showMessage(
                f"Se filtró la señal, sin pasa-altos en {self._nombrar(sin_pasa_altos)}: "
                f"{'se grabó' if uno else 'se grabaron'} más lento que el registro, "
                f"y {'lo' if uno else 'los'} habría dejado "
                f"{'plano' if uno else 'planos'}.",
                15000,
            )

    def show_impedance_dialog(self) -> None:
        """Abre el control de impedancia (V1_F de "Impedancia").

        Arranca con lo que traiga el archivo. **En un EDF eso es siempre nada**,
        y no es un fallo: el estándar no tiene ningún campo de impedancia. Ahí
        el investigador las importa de un archivo del equipo o las escribe.
        """
        if self._session is None:
            return
        self._cargar_impedancias()
        self.impedance_dialog.show()
        self.impedance_dialog.raise_()

    def _cargar_impedancias(self) -> None:
        """Llena el panel con los canales del registro y lo que traiga el archivo."""
        if self._session is None:
            return
        self.impedance_panel.set_channels(
            self._session.recording.channel_names(),
            read_impedances(self._session.recording),
        )
        self._refrescar_informe_de_impedancia()

    def load_impedances_dialog(self) -> None:
        """Importa las impedancias de un archivo del equipo de adquisición."""
        if self._session is None:
            return
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Importar impedancias",
            "",
            "Archivos de texto (*.txt *.csv);;Todos los archivos (*)",
        )
        if not ruta:
            return
        try:
            cargadas = load_impedances_from_file(Path(ruta))
        except PsgLabError as error:
            self._show_error(error, "importar las impedancias")
            return
        # **Un archivo sin impedancias no es un error de la biblioteca**, que
        # devuelve un diccionario vacío, pero sí una sorpresa: sin este aviso
        # importarlo no hacía nada y no decía nada (hito 32).
        if not cargadas:
            self._show_error(
                PsgLabError(
                    f"«{Path(ruta).name}» no trae ninguna impedancia, así que no se "
                    "cambió nada.",
                    details="El archivo está vacío o sólo tiene comentarios.",
                ),
                "importar las impedancias",
            )
            return

        # Se conserva lo que ya estaba escrito a mano: el archivo agrega, no
        # reemplaza. Un laboratorio puede tener medido medio montaje.
        combinadas = {**self.impedance_panel.values(), **cargadas}
        self.impedance_panel.set_channels(
            self._session.recording.channel_names(), combinadas
        )
        self._refrescar_informe_de_impedancia()

    def _limpiar_impedancias(self) -> None:
        """Deja todos los canales sin medir."""
        self.impedance_panel.clear_all()
        self._refrescar_informe_de_impedancia()

    def _refrescar_informe_de_impedancia(self) -> None:
        """Rearma el informe con lo que haya cargado.

        Se le pasa **la lista de canales**, que es lo que le permite distinguir
        el tercer estado: sin ella, el informe no puede saber cuáles faltan,
        porque los canales sin medir no están en el diccionario a propósito.
        """
        if self._session is None:
            return
        self.impedance_panel.set_report(
            impedance_report(
                self.impedance_panel.values(),
                DEFAULT_LIMIT_KOHM,
                channels=self._session.recording.channel_names(),
            )
        )

    def show_ica_dialog(self) -> None:
        """Ajusta la ICA y abre el panel para inspeccionarla (V5_F).

        **No aplica nada.** Ajustar e inspeccionar son dos pasos separados de
        aplicar, justamente porque quitar el componente equivocado modifica la
        señal de forma irreversible. El panel muestra las topografías y espera.

        **Corre en otro hilo desde el hito 47**, que es lo que quedaba del
        [hito 33](../../docs/TODO.md#hito-33-la-auditoría-del-19-de-septiembre).
        Es con diferencia lo más caro del programa —la auditoría midió 9 s sobre
        un registro real, y sobre ruido blanco, que es el peor caso para que
        FastICA converja, se midieron 345 s—, y **no cambia la señal**: por eso
        es el mismo trabajo que la conectividad de la noche y no necesitó
        ninguna decisión nueva. Las dos que sí la cambian —aplicar la ICA y
        filtrar— resultaron costar décimas de segundo; ver el hito 47.
        """
        if self._session is None:
            return
        # **Lo único que se lee de la sesión se lee acá**, en el hilo de la
        # interfaz: el otro recibe el registro ya resuelto y no vuelve a
        # preguntarle nada a `Session`.
        registro = self._session.recording

        def descomponer() -> object:
            descomposicion = fit_ica(registro)
            # **Las topografías se calculan adentro del hilo.** Son parte del
            # costo y tampoco tocan widgets; dejarlas afuera devolvería el
            # trabajo a medio hacer al hilo que se quiso liberar.
            topografias = [
                component_topography(descomposicion, numero)
                for numero in range(int(descomposicion.n_components_))
            ]
            # La varianza de cada componente también (hito 54): reconstruye la
            # señal desde cada uno, sobre una muestra de la noche.
            return descomposicion, topografias, explained_variance(descomposicion, registro)

        self._en_segundo_plano(
            "Descomponiendo la señal en componentes",
            descomponer,
            self._mostrar_la_ica,
            accion="calcular la ICA",
        )

    def _mostrar_la_ica(self, resultado: object) -> None:
        """Guarda la descomposición y abre el panel. **Acá sí se tocan widgets.**"""
        descomposicion, topografias, varianzas = resultado
        self._ica = descomposicion
        if self._session is not None:
            self.ica_panel.set_start_time(self._session.recording.start_time)
        self.ica_panel.set_components(topografias, varianzas)
        self.ica_dialog.show()
        self.ica_dialog.raise_()

    def _mostrar_curva_del_componente(self, component: int) -> None:
        """Reconstruye la serie del componente elegido y se la da al panel.

        **De la ventana actual**, por el mismo motivo que el espectro y la
        conectividad: la serie de las ocho horas no se puede mirar, y
        reconstruirla entera cuesta una copia completa de la señal.

        Es la mitad que faltaba de V5_F: `component_time_course()` existía desde
        el hito 15 con la promesa, en su propio docstring, de ser "lo que se
        dibuja debajo de la señal para ver **cuándo** ocurre el artefacto", y
        hasta el hito 19 no la llamaba nadie.
        """
        if self._session is None or self._ica is None:
            return
        ventana = self._session.current_window
        try:
            valores = component_time_course(
                self._ica, component, self._session.recording, window_index=ventana
            )
        except PsgLabError as error:
            # El panel ya dibujó la topografía y dejó la curva vacía, así que el
            # investigador conserva la mitad del criterio que sí se pudo dar.
            self._show_error(error, "mostrar el componente")
            return
        # **En segundos del registro** (hito 54), que es lo que numera el eje del
        # visualizador: así la curva se lee en la misma hora que la señal.
        frecuencia = self._session.recording.sampling_rate
        inicio, _ = window_to_samples(ventana, frecuencia)
        segundos = (inicio + np.arange(len(valores))) / frecuencia
        self.ica_panel.set_time_course(segundos, valores)

    def _apply_ica(self, exclude: list[int]) -> None:
        """Reconstruye la señal sin los componentes que el usuario marcó.

        **Pasa por `_aplicar_analisis()`**, que es el camino único del menú
        Análisis: así se puede volver a la señal original desde el menú, que es
        la única red que hay contra una exclusión equivocada — y quitar un
        componente no se puede deshacer sobre los datos ya transformados.
        """
        if self._session is None or self._ica is None:
            return
        cuantos = len(exclude)
        que_hizo = (
            "Se quitó 1 componente independiente"
            if cuantos == 1
            else f"Se quitaron {cuantos} componentes independientes"
        )
        # **Se toma la descomposición en una variable local antes de aplicar.**
        # `_aplicar_analisis()` llama a `_olvidar_ica()` al terminar bien, así que
        # una lambda que leyera `self._ica` la encontraría en `None` la próxima
        # vez que alguien la invocara.
        descomposicion = self._ica
        self._aplicar_analisis(
            que_hizo,
            lambda registro: apply_ica(registro, descomposicion, exclude),
            accion="quitar los componentes",
        )
        self.ica_dialog.hide()

    def restore_original_recording(self) -> None:
        """Vuelve a la señal tal como se leyó del archivo.

        **Es lo que hace reversible todo el menú.** Sin esto, un filtro o una
        referencia mal elegidos obligarían a cerrar y reabrir el registro,
        perdiendo el scoring que el usuario venía haciendo.
        """
        if self._session is None or self._registro_original is None:
            return
        try:
            self._session.set_recording(self._registro_original)
        except PsgLabError as error:
            self._show_error(error, "volver a la señal original")
            return
        self.signal_view.set_session(self._session)
        self.channel_selector.set_recording(self._registro_original)
        # Deshacer también cambia la señal, así que la descomposición que hubiera
        # se ajustó sobre la procesada y ya no corresponde. Lo mismo los
        # resultados de análisis.
        self._olvidar_ica()
        self._olvidar_resultados()
        self.playback.stop()
        self.accion_señal_original.setEnabled(False)
        self.refresh()
        self.statusBar().showMessage("Se volvió a la señal original", 5000)


def _precalentar() -> None:
    """Lo que corre el hilo de `MainWindow.warm_up_in_background()`, en orden.

    Está suelto y no adentro de la ventana porque no la toca: si tocara algo de
    Qt desde otro hilo habría que pensarlo mucho más.
    """
    warm_up_readers()
    warm_up()
