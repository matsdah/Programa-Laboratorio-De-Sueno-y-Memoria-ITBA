# TODO — scorer de polisomnografía

La cola de trabajo del proyecto. **Este archivo es el único lugar que dice qué
está hecho y qué falta**; `TRAZABILIDAD.md` dice *dónde* va cada requisito y no
lleva estado, para que no haya dos fuentes que se desincronicen.

**Lo cerrado está en [`HISTORIAL.md`](HISTORIAL.md)**: cada hito terminado,
con lo que se hizo, lo que se decidió y lo que se midió. Se separó el
27 de septiembre de 2026, en el hito 79: este archivo había llegado a siete
mil líneas, y lo abierto —que es lo que se viene a buscar— quedaba al final.
Acá queda lo abierto, las preguntas al cliente, cómo se trabaja y la tabla de
progreso de todos los hitos. **Un hito que se cierra se muda al historial**;
ver «Al agregar o cerrar un ítem», al final.

Quedan **0 stubs** (`raise NotImplementedError`) en 0 módulos: las dos Partes
están cerradas y ningún módulo de `psglab/` eleva `NotImplementedError`.

Son **ochenta hitos**, del 0 al 79, que son las filas de la tabla de
progreso; **el 79 es el único abierto**. La cuenta vive sólo en este archivo:
hasta el hito 79 la repetían cuatro documentos, y cada hito nuevo obligaba a
corregir los cuatro.

## Preguntas abiertas con el cliente

Lo que no depende de escribir código sino de una respuesta. Cada una está
explicada donde se originó; acá está para que no se pierda entre lo cerrado.

- [ ] **Qué vía de impedancia usa el laboratorio.** Las tres están
      implementadas en `psglab/analysis/impedance.py`, marcada `PENDIENTE DE
      DEFINICIÓN CON EL CLIENTE`; la respuesta decide cuál se ofrece primero.
      Ver el [hito 0](HISTORIAL.md#hito-0-desbloquear).
- [ ] **V2_F, V3_F y V4_F de «Filtración»**, que no aparecen en ningún
      documento: los IDs saltan de V1_F a V5_F. Pueden ser tres requisitos que
      el proyecto nunca registró. Ver la introducción de la
      [Parte 2](HISTORIAL.md#parte-2-módulo-de-análisis-de-bioseñales).
- [x] **Anotaciones.txt e Informacion.txt fuera del menú.** Salieron por
      decisión del usuario el 16 de septiembre de 2026 y se piden desde un
      script; falta confirmarlo con el cliente. Ver el
      [hito 23](HISTORIAL.md#hito-23-ajustes-de-la-barra-de-menú).
      Ya no hay nada que confirmar: **volvieron a «Archivo» en el hito 79**,
      que es lo que pide el pliego, por pedido del mismo usuario.
- [ ] **Las definiciones del informe de sueño**, al final de
      `Informacion.txt`: tiempo en cama como el registro entero, la vigilia
      del final fuera de la vigilia después del inicio, los arousals como
      ventanas marcadas. Están en el docstring de
      `exporters/statistics.py::sleep_summary()`. Ver la decisión 7 del
      [hito 79](#hito-79-la-auditoría-del-26-de-septiembre).
- [ ] **Los filtros sugeridos**, que pueden no ser los que el laboratorio
      usa. Ver la decisión 8 del [hito 79](#hito-79-la-auditoría-del-26-de-septiembre).

Y una comprobación que sólo puede hacer una persona frente a la pantalla:

- [ ] **`python -m tests.medir_reparto` con la letra del programa.** Abre una
      ventana de verdad, así que no la corre la suite; hasta el hito 78 medía
      con la letra del sistema. Ver el
      [hito 78](HISTORIAL.md#hito-78-que-la-suite-vea-la-letra-real).

## Cómo se usa

Los hitos están **ordenados por dependencias reales**, sacadas del grafo de
importaciones del paquete. No es el orden de `TRAZABILIDAD.md`, que sigue las
secciones del pliego: quien lo lea de arriba abajo arrancaría por
`readers/brainvision.py`, que necesita `core/recording.py` terminado para poder
devolver algo.

**No empieces un módulo si el hito anterior no está cerrado.** Vas a escribir
contra firmas que todavía elevan `NotImplementedError` y no vas a poder testear
nada.

### Lo que el CI verifica solo

Desde que el equipo es de tres, [el workflow](../.github/workflows/ci.yml) corre
los tests en los tres sistemas operativos, los chequeos de consistencia de
`tests/test_consistencia.py` y la verificación de licencias.

**Pero no corre en cualquier push.** `ci.yml` filtra los dos eventos por rama
—`branches: [Add, Master]`—, así que un push a una rama de trabajo **no dispara
nada** hasta que se abra la pull request contra alguna de esas dos. En el día a
día el único control es `python -m pytest` local, y conviene correrlo entero: el
chequeo de las cuentas de tests se saltea si se le pasa un archivo suelto.

Esto no es teórico y ya costó caro: el [hito 17](HISTORIAL.md#hito-17-cierre-de-la-parte-2)
encontró que los PR #19 y #20 estaban apilados sobre ramas de trabajo y **tenían
cero checks**. Dos de los cuatro hitos que quedaban sin mergear nunca se habían
verificado fuera de una máquina Windows. Y reapuntar un PR no alcanza para
disparar el CI: `pull_request` corre con `opened`, `synchronize` y `reopened`, y
cambiar la base es `edited`; hay que cerrarlo y reabrirlo.

Con la pull request abierta sí quiere decir que **no hace falta acordarse** de
que las cuentas de este archivo cuadren, ni de que los enlaces no se rompan, ni
de borrar el `pytestmark` al terminar un módulo: si algo de eso queda mal, el
pull request falla.

### Cuándo un ítem está terminado

Las cuatro condiciones, no tres:

1. Los stubs del módulo están implementados.
2. **Su test existe y corre.** Si el archivo de test ya existe, hay que borrar
   la línea `pytestmark = pytest.mark.skip(...)` del principio. Si no existe,
   hay que crearlo (regla del pliego, sección 7: un test por componente).
3. Su fila de `TRAZABILIDAD.md` sigue siendo cierta.
4. El `README.md` de la carpeta sigue siendo cierto.

Mientras el `pytestmark` esté, la suite pasa en verde **sin haber verificado
nada**. Un verde por omisión es peor que un rojo.

## Progreso

| Hito | Módulos con stubs | Stubs | Estado |
|---|---|---|---|
| [0. Desbloquear](HISTORIAL.md#hito-0-desbloquear) | — | 0 | ✅ cerrado |
| [1. Cimientos](HISTORIAL.md#hito-1-cimientos) | — | 0 | ✅ cerrado |
| [2. Scoring y anotaciones](HISTORIAL.md#hito-2-scoring-y-anotaciones) | — | 0 | ✅ cerrado |
| [3. Sesión](HISTORIAL.md#hito-3-sesión) | — | 0 | ✅ cerrado |
| [4. Importación](HISTORIAL.md#hito-4-importación) | — | 0 | ✅ cerrado |
| [5. Exportadores](HISTORIAL.md#hito-5-exportadores) | — | 0 | ✅ cerrado |
| [6. Interfaz](HISTORIAL.md#hito-6-interfaz) | — | 0 | ✅ cerrado |
| [7. Herramientas](HISTORIAL.md#hito-7-herramientas) | — | 0 | ✅ cerrado |
| [8. Cierre](HISTORIAL.md#hito-8-cierre-de-la-parte-1) | — | 0 | ✅ cerrado |
| [9. Lo que la interfaz no consume](HISTORIAL.md#hito-9-lo-que-la-interfaz-no-consume) | — | 0 | ✅ cerrado |
| [10. Cimientos de la Parte 2](HISTORIAL.md#hito-10-cimientos-de-la-parte-2) | — | 0 | ✅ cerrado |
| [11. Derivar y re-referenciar](HISTORIAL.md#hito-11-derivar-y-re-referenciar) | — | 0 | ✅ cerrado |
| [12. Filtración](HISTORIAL.md#hito-12-filtración) | — | 0 | ✅ cerrado |
| [13. PSD](HISTORIAL.md#hito-13-psd) | — | 0 | ✅ cerrado |
| [14. Complejidad y conectividad](HISTORIAL.md#hito-14-complejidad-y-conectividad) | — | 0 | ✅ cerrado |
| [15. ICA](HISTORIAL.md#hito-15-ica) | — | 0 | ✅ cerrado |
| [16. Impedancia](HISTORIAL.md#hito-16-impedancia) | — | 0 | ✅ cerrado |
| [17. Cierre de la Parte 2](HISTORIAL.md#hito-17-cierre-de-la-parte-2) | — | 0 | ✅ cerrado |
| [18. Escala](HISTORIAL.md#hito-18-escala) | — | 0 | ✅ cerrado |
| [19. Lo que la interfaz no consumía](HISTORIAL.md#hito-19-lo-que-la-interfaz-no-consumía) | — | 0 | ✅ cerrado |
| [20. La red](HISTORIAL.md#hito-20-la-red) | — | 0 | ✅ cerrado |
| [21. Limpieza](HISTORIAL.md#hito-21-limpieza) | — | 0 | ✅ cerrado |
| [22. Refactor de la interfaz](HISTORIAL.md#hito-22-refactor-de-la-interfaz) | — | 0 | ✅ cerrado |
| [23. Ajustes de la barra de menú](HISTORIAL.md#hito-23-ajustes-de-la-barra-de-menú) | — | 0 | ✅ cerrado |
| [24. Vista inicial y reproducción](HISTORIAL.md#hito-24-vista-inicial-y-reproducción) | — | 0 | ✅ cerrado |
| [25. Rendimiento](HISTORIAL.md#hito-25-rendimiento-al-abrir-y-al-desplazar) | — | 0 | ✅ cerrado |
| [26. El diseño de la ventana](HISTORIAL.md#hito-26-el-diseño-de-la-ventana) | — | 0 | ✅ cerrado |
| [27. La navegación desde el medio](HISTORIAL.md#hito-27-la-navegación-desde-el-medio) | — | 0 | ✅ cerrado |
| [28. Un solo menú de herramientas](HISTORIAL.md#hito-28-un-solo-menú-de-herramientas) | — | 0 | ✅ cerrado |
| [29. Verificación de las herramientas](HISTORIAL.md#hito-29-verificación-de-las-herramientas) | — | 0 | ✅ cerrado |
| [30. Las decisiones de la verificación](HISTORIAL.md#hito-30-las-decisiones-de-la-verificación) | — | 0 | ✅ cerrado |
| [31. El recorrido manual](HISTORIAL.md#hito-31-el-recorrido-manual) | — | 0 | ✅ cerrado |
| [32. Los pendientes del TODO](HISTORIAL.md#hito-32-los-pendientes-del-todo) | — | 0 | ✅ cerrado |
| [33. La auditoría del 19 de septiembre](HISTORIAL.md#hito-33-la-auditoría-del-19-de-septiembre) | — | 0 | ✅ cerrado |
| [34. El rediseño de la pantalla principal](HISTORIAL.md#hito-34-el-rediseño-de-la-pantalla-principal) | — | 0 | ✅ cerrado |
| [35. Dos esquemas y ninguna perilla](HISTORIAL.md#hito-35-dos-esquemas-y-ninguna-perilla) | — | 0 | ✅ cerrado |
| [36. Las dos barras](HISTORIAL.md#hito-36-las-dos-barras) | — | 0 | ✅ cerrado |
| [37. El canalón](HISTORIAL.md#hito-37-el-canalón) | — | 0 | ✅ cerrado |
| [38. Lo que faltaba del prototipo](HISTORIAL.md#hito-38-lo-que-faltaba-del-prototipo) | — | 0 | ✅ cerrado |
| [39. La carrocería de los paneles](HISTORIAL.md#hito-39-la-carrocería-de-los-paneles) | — | 0 | ✅ cerrado |
| [40. Lo que cada panel dice de lo suyo](HISTORIAL.md#hito-40-lo-que-cada-panel-dice-de-lo-suyo) | — | 0 | ✅ cerrado |
| [41. Los seis paneles, y no cuatro](HISTORIAL.md#hito-41-los-seis-paneles-y-no-cuatro) | — | 0 | ✅ cerrado |
| [42. Lo largo deja de congelar la ventana](HISTORIAL.md#hito-42-lo-largo-deja-de-congelar-la-ventana) | — | 0 | ✅ cerrado |
| [43. Una tipografía, y su hermana de ancho fijo](HISTORIAL.md#hito-43-una-tipografía-y-su-hermana-de-ancho-fijo) | — | 0 | ✅ cerrado |
| [44. Tres cosas que se vieron en la pantalla](HISTORIAL.md#hito-44-tres-cosas-que-se-vieron-en-la-pantalla) | — | 0 | ✅ cerrado |
| [45. La banda no se dibujaba y la lupa miraba un solo canal](HISTORIAL.md#hito-45-la-banda-no-se-dibujaba-y-la-lupa-miraba-un-solo-canal) | — | 0 | ✅ cerrado |
| [46. Tres cabos sueltos](HISTORIAL.md#hito-46-tres-cabos-sueltos) | — | 0 | ✅ cerrado |
| [47. Lo caro era ajustar, y no cambia la señal](HISTORIAL.md#hito-47-lo-caro-era-ajustar-y-no-cambia-la-señal) | — | 0 | ✅ cerrado |
| [48. La auditoría de los tests](HISTORIAL.md#hito-48-la-auditoría-de-los-tests) | — | 0 | ✅ cerrado |
| [49. La envolvente se calcula una vez](HISTORIAL.md#hito-49-la-envolvente-se-calcula-una-vez) | — | 0 | ✅ cerrado |
| [50. Los pendientes, revisados](HISTORIAL.md#hito-50-los-pendientes-revisados) | — | 0 | ✅ cerrado |
| [51. La Übersicht muestra la señal](HISTORIAL.md#hito-51-la-übersicht-muestra-la-señal) | — | 0 | ✅ cerrado |
| [52. Una anotación se puede corregir](HISTORIAL.md#hito-52-una-anotación-se-puede-corregir) | — | 0 | ✅ cerrado |
| [53. Cuatro defectos que encontró el prototipo](HISTORIAL.md#hito-53-cuatro-defectos-que-encontró-el-prototipo) | — | 0 | ✅ cerrado |
| [54. Lo que faltaba del prototipo](HISTORIAL.md#hito-54-lo-que-faltaba-del-prototipo) | — | 0 | ✅ cerrado |
| [55. Lo último del prototipo](HISTORIAL.md#hito-55-lo-último-del-prototipo) | — | 0 | ✅ cerrado |
| [56. La rueda y el panel táctil sobre la señal](HISTORIAL.md#hito-56-la-rueda-y-el-panel-táctil-sobre-la-señal) | — | 0 | ✅ cerrado |
| [57. Cuánta memoria cuesta cada cosa](HISTORIAL.md#hito-57-cuánta-memoria-cuesta-cada-cosa) | — | 0 | ✅ cerrado |
| [58. La ICA se ajusta sobre una muestra de la noche](HISTORIAL.md#hito-58-la-ica-se-ajusta-sobre-una-muestra-de-la-noche) | — | 0 | ✅ cerrado |
| [59. Filtrar y quitar componentes sin copiar la señal entera](HISTORIAL.md#hito-59-filtrar-y-quitar-componentes-sin-copiar-la-señal-entera) | — | 0 | ✅ cerrado |
| [60. Re-referenciar ya estaba en el mínimo](HISTORIAL.md#hito-60-re-referenciar-ya-estaba-en-el-mínimo) | — | 0 | ✅ cerrado |
| [61. La varianza de la ICA sin reconstruir la señal](HISTORIAL.md#hito-61-la-varianza-de-la-ica-sin-reconstruir-la-señal) | — | 0 | ✅ cerrado |
| [62. Accesibilidad: teclado, foco y bordes](HISTORIAL.md#hito-62-accesibilidad-teclado-foco-y-bordes) | — | 0 | ✅ cerrado |
| [63. Lo menor de la auditoría de accesibilidad](HISTORIAL.md#hito-63-lo-menor-de-la-auditoría-de-accesibilidad) | — | 0 | ✅ cerrado |
| [64. El flujo de scoring](HISTORIAL.md#hito-64-el-flujo-de-scoring) | — | 0 | ✅ cerrado |
| [65. Los textos de la interfaz](HISTORIAL.md#hito-65-los-textos-de-la-interfaz) | — | 0 | ✅ cerrado |
| [66. Los carteles en macOS](HISTORIAL.md#hito-66-los-carteles-en-macos) | — | 0 | ✅ cerrado |
| [67. La integridad de los datos](HISTORIAL.md#hito-67-la-integridad-de-los-datos) | — | 0 | ✅ cerrado |
| [68. Los errores inesperados](HISTORIAL.md#hito-68-los-errores-inesperados) | — | 0 | ✅ cerrado |
| [69. Los formatos de scoring](HISTORIAL.md#hito-69-los-formatos-de-scoring) | — | 0 | ✅ cerrado |
| [70. La unidad de cada canal](HISTORIAL.md#hito-70-la-unidad-de-cada-canal) | — | 0 | ✅ cerrado |
| [71. Lo desactualizado y lo menor](HISTORIAL.md#hito-71-lo-desactualizado-y-lo-menor) | — | 0 | ✅ cerrado |
| [72. La frecuencia de origen](HISTORIAL.md#hito-72-la-frecuencia-de-origen) | — | 0 | ✅ cerrado |
| [73. Las marcas del registro](HISTORIAL.md#hito-73-las-marcas-del-registro) | — | 0 | ✅ cerrado |
| [74. Los cabos sueltos](HISTORIAL.md#hito-74-los-cabos-sueltos) | — | 0 | ✅ cerrado |
| [75. Las fases sugeridas](HISTORIAL.md#hito-75-las-fases-sugeridas) | — | 0 | ✅ cerrado |
| [76. La ventana en ocho archivos](HISTORIAL.md#hito-76-la-ventana-en-ocho-archivos) | — | 0 | ✅ cerrado |
| [77. Una sola tipografía](HISTORIAL.md#hito-77-una-sola-tipografía) | — | 0 | ✅ cerrado |
| [78. Que la suite vea la letra real](HISTORIAL.md#hito-78-que-la-suite-vea-la-letra-real) | — | 0 | ✅ cerrado |
| [79. La auditoría del 26 de septiembre](#hito-79-la-auditoría-del-26-de-septiembre) | — | 0 | ⬜ abierto |
| | **0** | **0** | |

**La columna de stubs nunca midió el hito 9**, y por eso el hito 9 existió: sus
seis ítems eran código escrito que nadie llamaba. `contar_stubs()` cuenta
`raise NotImplementedError`, no caminos muertos, y con esa medida los hitos 6 y
7 se dieron por cerrados con la mitad de la interfaz sin conectar.

---

## Hito 79: La auditoría del 26 de septiembre

**Abierto el 26 de septiembre de 2026.** El usuario pidió una auditoría del
proyecto entero: las herramientas, los errores posibles, el diseño, el reparto
de los paneles visto por quien scorea, los flujos habituales de un programa de
scoring de sueño, la legibilidad del código para quien no programa y las clases
que crecieron de más. Como las tres anteriores, **no tiene archivo propio**: lo
que encontró está acá, en el orden en que conviene atacarlo.

**No tiene stubs que contar.**

### Cómo se hizo

- **Se leyó el paquete**: los 83 archivos de Python de `psglab/` —unas
  29 000 líneas—,
  los README de cada carpeta, `ARQUITECTURA.md`, `EXPLICACION.txt`, el
  workflow del CI y la estructura de la suite.
- **La suite completa, antes de tocar nada**: 4105 tests pasados, ninguno
  salteado, 6 advertencias, en 2 min 40 s (Windows 11, Python 3.12.10).
- **Cada error se reprodujo** con un script contra el código de verdad —la
  ventana armada fuera de pantalla, sin tocar el archivo de preferencias— y no
  sólo leyendo. Los que dicen «por inspección» no se corrieron.
- **Un barrido estático**: `pyflakes` no encuentra nada salvo las cuatro
  importaciones que son el trabajo (`warm_up` y compañía), y un script listó
  los nombres públicos que ningún otro archivo del paquete usa.
- **La herramienta de capturas**, para mirar el reparto de los paneles.

### Lo que salió bien, y hay que cuidar

Las capas respetan la dirección de las dependencias; ningún error del modelo
llega como traza; la validación de entradas es pareja en `core/`, `readers/` y
`analysis/`; los lectores y los formatos de scoring rechazan lo ambiguo en vez
de adivinarlo; y la red de `test_consistencia.py` encontró sola casi todo lo
que las auditorías anteriores buscaban a mano. **Nada de lo de abajo es una
crítica a esa base**: es lo que quedó entre sus mallas.

### Tanda 1: los errores confirmados

Van primero porque no piden ninguna decisión, son chicos y cada uno tiene un
síntoma que se puede afirmar en un test. **Cada test tiene que fallar con el
código de hoy** antes de arreglar nada.

- [x] **La banda de amplitud no se puede mover.** Es no exclusiva, así que
      nunca es `_mouse_tool`, y `ToolsMixin.eventFilter()` sólo le reparte el
      mouse a ésa: `AmplitudeBandTool.on_mouse_move()` no lo llama nadie.
      Reproducido con la ventana armada: después de mover el mouse sobre tres
      carriles, el centro de la banda sigue en 0,0 µV. El pliego pide que el
      usuario **pase la banda por encima de la señal**. La red del hito 30 no
      lo ve porque la llamada es genérica (`herramienta.on_mouse_move`).
      - Arreglado: el movimiento se le reparte a todas las `_drawing_tools`,
        y los clics sólo a `_mouse_tool`; la banda pasa al canal que está bajo
        el mouse, que es contra el que llega medida la `y`. Antes de que el
        mouse entre, sigue yendo sobre el seleccionado o el primero visible.
- [x] **La ocupación pierde el canal de sus líneas al desplazar la página.**
      `OccupancyTool._reanclar()` arma las líneas nuevas sin `channel_name`.
      Reproducido: una línea trazada sobre C4 queda con canal `None` después
      de un desplazamiento, se dibuja sobre el primer carril y un clic encima
      ya no la borra. Es el hueco que el hito 46 cerró al trazar y no al
      reanclar.
- [x] **La lupa ignora el desplazamiento vertical del canal.**
      `SignalView._a_carril_desde_datos()` no resta el offset y
      `_a_carril()` sí. Reproducido: una señal de 500 µV con offset de 500
      queda en 0,0 carriles en la curva y en 2,25 en la lupa, fuera del
      cristal. **Pasa siempre con los canales respiratorios y los de clase
      Otro**, que se centran solos al abrir el registro (hito 70).
- [x] **Quedarse sin memoria al abrir se informa como archivo dañado.** Los
      lectores de EDF y BrainVision atrapan `Exception` alrededor de MNE, y
      `MemoryError` lo es: el cartel manda a buscar el problema en el archivo.
      Por inspección. Arreglo: `memoria_suficiente("abrir el registro")`
      antes del `except` genérico.
- [x] **«Amplitud › Personalizado…» sin canales visibles eleva `IndexError`**
      (`ViewMixin.ask_amplitude_scale()`, `visible_channels[0]`), que sale
      como el cartel de los errores inesperados. Por inspección.
- [x] **Un canal derivado abre con 100 µV aunque sea un EOG o un ECG.**
      `Session.set_recording()` les da `DEFAULT_SCALE_UV` a los canales nuevos
      en vez de la escala de su clase (`DEFAULT_SCALE_BY_KIND_UV`), y no mide
      los respiratorios. Por inspección.
- [x] **El alcance de «µV por carril» está escrito dos veces.**
      `ViewMixin.set_amplitude_scale()` reimplementa
      `Session._channels_under_amplitude()` —el comentario de al lado dice que
      no— y discrepa: saltea los seleccionados que están ocultos. Llevarlo a
      un método de `Session`.
- [x] **Cambiar la selección de canales no redibuja la banda**, que se
      apoya sobre el seleccionado: queda en el carril viejo hasta el próximo
      evento. Por inspección.
- [x] **`Recording.flat_channels()` rechaza un entero de numpy** que
      `get_segment()` acepta. Hoy no explota porque `window_to_samples()`
      devuelve enteros de Python.

**Tanda cerrada el 26 de septiembre de 2026**, en la rama
`auditoria/tanda-1-errores`, un commit por tema.

  - Test: `tests/test_occupancy.py`, **52 tests en verde**;
    `tests/test_signal_view.py`, **98 tests en verde**;
    `tests/test_amplitude_band.py`, **24 tests en verde**;
    `tests/test_readers.py`, **94 tests en verde**;
    `tests/test_session.py`, **167 tests en verde**;
    `tests/test_recording.py`, **60 tests en verde**;
    `tests/test_contratos.py`, **1371 tests en verde**; y por la ventana, en
    los seis `test_entrega*.py`.

Cada test nuevo se corrió contra el código sin su arreglo, y todos fallan: la
línea reanclada sin canal, la lupa sin restar el desplazamiento, la banda que
no recibe el movimiento, `MemoryError` informado como archivo dañado, el EOG
derivado a 100 µV, el respiratorio nuevo sin centrar, el alcance de «µV por
carril» salteando los seleccionados ocultos, «Personalizado…» sin canales, la
selección sin redibujar la banda y el entero de numpy rechazado.

### Tanda 2: el flujo de scoring

Lo que un programa de scoring suele tener y éste no, o tiene con un paso de
más. **Varias piden una decisión antes**; están marcadas.

- [x] **Deshacer y rehacer** (Ctrl+Z, Ctrl+Y) para el scoring y las
      anotaciones. Con el paso solo a la ventana siguiente del hito 64, una
      tecla de más scorea la ventana que viene y hoy no hay vuelta atrás: hay
      que volver con la flecha y rescorear. `ui/shortcuts.py` lo declara «un
      subsistema completo» y «no pedido». Propuesta: `core/history.py`, sin
      Qt, con una pila acotada de cambios sobre `Scoring` y `AnnotationSet`.
      Hecho con **fotos y no comandos**: `History` guarda la nomenclatura,
      las fases, la capa de sugeridas y las anotaciones, que son inmutables
      y por eso son referencias; deshacer es volver a la foto anterior. Así
      no hace falta que cada camino que cambia el trabajo sepa invertirse:
      la ventana llama a `record()` en `refresh()` —por donde pasan todos los
      del scoring— y en los cuatro de la anotación que no pasan por ahí, y
      si nada cambió no se guarda nada. Doscientos pasos. Deshacer va a la
      ventana del cambio. Se deshacen también la nomenclatura, confirmar y
      descartar sugeridas e importar un scoring encima; lo recuperado de la
      copia no, porque sería perderlo. `Scoring.suggestions()` devuelve la
      capa entera para poder volver a ponerla. Borrar una anotación sigue
      preguntando, y el cartel dice ahora que se puede deshacer.
  - Test: `tests/test_history.py`, **16 tests en verde**; y en
    `tests/test_menus.py` y `tests/test_entrega_scoring.py`, el menú, Ctrl+Z y
    Ctrl+Y apretados de verdad, y que anotar se registre.
- [x] **Recuperar el trabajo después de un cierre inesperado.** *(Decidido: sí;
      ver «Lo que decidió el usuario».)* El programa no autoguarda
      para no elegir por el usuario dónde ni en qué formato, y eso se
      conserva: la propuesta es un archivo de recuperación en el perfil, que
      no se exporta ni aparece en ninguna carpeta, y que al reabrir el mismo
      registro ofrece volver a donde estaba. Scorear una noche lleva horas, y
      hoy un corte de luz se las lleva. Va en `ui/work_guard.py`, que desde
      el cierre de la tanda 3 es el que cuida el trabajo.
      Hecho. La regla es `core/recovery.py`, sin Qt ni disco: guarda las
      fases, los arousals, las anotaciones con sus canales y colores y la
      ventana donde estaba el usuario; reconoce el registro por nombre,
      frecuencia, largo y canales, y no por la ruta; y restaura todo o nada,
      dejando lo recuperado **sin exportar**, que es lo que es. `WorkGuard`
      la escribe cada 10 s si hay trabajo sin exportar y cambió algo —en un
      archivo aparte que después se renombra, así que un corte a mitad deja
      la anterior—, la borra cuando el usuario decide qué hacer con su
      trabajo (exportar, descartar, cerrar normalmente) y la ofrece al
      reabrir el mismo registro; descartarla la borra. Sólo la escribe la
      ventana del usuario: la de los tests no toca el perfil. Error propio:
      `UnreadableRecoveryError`.
  - Test: `tests/test_recovery.py`, **28 tests en verde**;
    `tests/test_work_guard.py`, **25 tests en verde**; y en
    `tests/test_entrega.py`, un corte de punta a punta por la ventana.
- [x] **Los diálogos de abrir, importar y exportar arrancan en la carpeta
      del registro**, y recuerdan la última. Hoy arrancan en el directorio
      desde donde se lanzó el programa, y el nombre propuesto es siempre
      `Scoring.txt`: dos participantes exportados a la misma carpeta se pisan.
      Hecho: arrancan en la carpeta del registro abierto, o sin registro en
      la del último que se abrió.
- [x] **Ir a la próxima ventana sin scorear**, y a la anterior: es como se
      retoma un scoring a medias. Hoy hay que buscarla en la franja.
- [x] **0 y 5 como teclas de W y R**, además de las letras. Son los códigos
      de `Scoring.txt`, que el laboratorio ya usa, y dejan el scoring entero
      en el teclado numérico.
      Hecho, y también el 6 para M en Rechtschaffen y Kales; la N y Mayús+N
      van a la próxima y a la anterior sin scorear, con `Scoring.next_unscored()`.
  - Test: `tests/test_scoring.py`, **57 tests en verde**;
    `tests/test_shortcuts.py`, **39 tests en verde**;
    `tests/test_contratos.py`, **1371 tests en verde**;
    `tests/test_entrega_interfaz.py`, **103 tests en verde**.

  Cada test nuevo falla sin su cambio: la próxima sin scorear, las teclas
  0, 5 y N y la carpeta de los diálogos. La N y Mayús+N ganaron su entrada
  con el menú «Scoring», más abajo.

- [x] **Anotar sin un cartel por evento.** *(Decidido: clase activa.)* Cada tramo
      arrastrado abre un `QInputDialog` modal; marcar cien husos son cien
      carteles. Propuesta: una «clase activa» que usa el arrastre, elegida en
      una lista o con una tecla, y el cartel sólo con Mayúsculas.
      Hecho. La clase activa la guarda el anotador (`active_label`) y
      sobrevive a apagarlo y a abrir otro registro: es cómo trabaja el
      usuario. Se elige con **C** —un menú sobre la señal con «Preguntar cada
      vez», las clases del registro y «Nueva clase…»— o desde «Scoring ›
      Elegir la clase al anotar…», y elegirla enciende «Anotar». Cada
      arrastre y la E la usan sin cartel; **Mayúsculas al soltar** pregunta
      igual, sin cambiarla, y `tool_controller` le pasa a la ventana si
      estaba apretada. La barra de estado dice con qué clase se anota. La
      ayuda de atajos suma C y, en «Anotación», lo que hace el mouse.
  - Test: `tests/test_annotator.py`, **49 tests en verde**;
    `tests/test_tool_controller.py`, **16 tests en verde**;
    `tests/test_entrega_anotacion.py`, **59 tests en verde**.
- [ ] **Los parámetros de cada análisis, adentro de su panel.** Hoy cada
      pedido encadena carteles modales para elegir canal, medida o banda
      —derivar son dos seguidos— y el panel se abre después. Los paneles ya
      son docks: pueden llevar su selector y un botón «Calcular», con el
      canal seleccionado por omisión.
- [x] **El panel de Scoring a la vista al abrir.** *(Decidido: visible y
      compacto.)* La tarea principal del programa hoy no se
      ve: se descubre por la ayuda de atajos. Una fila compacta con las fases
      y el arousal, o el panel entero la primera vez.
      Hecho: una sola fila —las fases con su tecla, «Arousal (A)» y el
      selector de nomenclatura al final—, a la vista al abrir a la izquierda
      del hipnograma, sin quitarle alto a la señal. El pie con la ventana y
      su fase sólo se ve con el panel suelto; acoplado lo dicen las barras de
      abajo, y el lector de pantalla lo recibe como descripción del panel.
      **La captura encontró tres defectos que la suite daba por buenos**:
      en un renglón, cada elemento de alto fijo le ponía tope al renglón
      entero, y los botones de dos renglones salían aplastados a 30 px con la
      tecla encima de la fase; «REM» se cortaba a «!EN», porque los 40 px de
      `ANCHO_MINIMO_DE_BOTON` no alcanzaban con el relleno del estilo; y el
      selector decía «AASN». Ahora los botones crecen al alto del más alto,
      cada uno se queda con el ancho de su texto —el relleno sale de
      `theme.RELLENO_HORIZONTAL_DE_CONTROL`— y el selector no se achica.
  - Test: `tests/test_scoring_panel.py`, **36 tests en verde**;
    `tests/test_docks.py`, **41 tests en verde**.
- [x] **Un menú «Scoring».** *(Decidido: sí, y ordenar la barra.)* Las fases, el arousal, ir
      a la próxima sin scorear, deshacer y las fases sugeridas están
      repartidos entre las teclas y «Analizar»; «Escala de tiempo» y
      «Amplitud» ocupan dos lugares de la barra que podrían ir en «Ver».
      Hecho: la barra queda Archivo, Ver, Scoring, Montaje, Filtrar,
      Analizar, Herramientas y Ayuda. «Scoring» lleva una entrada por fase
      de la nomenclatura activa, con su tecla; el arousal; anotar la
      ventana; la próxima y la anterior sin scorear; ir a una ventana; y
      «Fases sugeridas», que salió de «Analizar». **Se pone al día al
      abrirse** —las fases de la nomenclatura, la de la ventana tildada, el
      arousal tildado— y sin registro apaga sus entradas, porque los
      métodos no hacen nada sin sesión. «Escala de tiempo», «Amplitud» y
      «Vistas de canales» abren «Ver». Deshacer y rehacer entraron
      después, con `core/history.py`: antes no había qué ofrecer, y una
      entrada que no hace nada es peor que ninguna.
  - Test: `tests/test_menus.py`, **54 tests en verde**. Cada test nuevo
    falla sin su cambio: los cuatro bloques de «Scoring», la tecla de cada
    fase, las sugeridas fuera de «Analizar», las entradas apagadas sin
    registro, scorear y marcar el arousal desde el menú, lo tildado al
    abrirse y las fases de Rechtschaffen y Kales.
- [x] **El informe de sueño estándar.** *(Decidido: se hace y se confirma con el laboratorio.)*
      `Informacion.txt` tiene la duración por fase y las métricas de
      episodios que pide el pliego, y no trae lo primero que busca un
      laboratorio: tiempo en cama, tiempo total de sueño, eficiencia,
      latencia de sueño y de REM, vigilia después del inicio, porcentaje de
      cada fase sobre el sueño, cantidad e índice de arousals. Se calcula con
      lo que ya hay en `exporters/statistics.py`.
      Hecho, **y falta la confirmación del laboratorio**, que está entre las
      preguntas abiertas del principio. `statistics.sleep_summary()` lo
      calcula y `Informacion.txt` lo trae en una sección nueva al final,
      **sin mover nada de lo que ya traía**. Las decisiones, en su
      docstring: el tiempo en cama es el registro entero, porque no hay
      marcas de luces; MT no es sueño; las latencias van hasta el comienzo
      de la ventana; la vigilia después del inicio es la que queda entre la
      primera y la última ventana de sueño; y los arousals son las ventanas
      de sueño marcadas, no eventos. Lo que no existe —la latencia de REM de
      una noche sin REM— se dice con palabras y no con un cero, como el
      resto del archivo, y las ventanas sin scorear se avisan arriba.
      **Anotaciones.txt e Informacion.txt volvieron a «Archivo»**, debajo
      del scoring, porque el pliego los pide y el informe no servía si sólo
      se podía pedir desde un script.
  - Test: `tests/test_exporters.py`, **60 tests en verde**;
    `tests/test_menus.py`, **54 tests en verde**; y en
    `tests/test_entrega.py`, los dos archivos exportados por la ventana.
- [x] **La lupa del tamaño de la página.** El radio es de un segundo por el
      aumento: con una página de una hora la lente no se ve, y con una de un
      segundo tapa todo. Llevarlo a una fracción de la página.
      Hecho. **El radio que se elige es el de la página de una época**, y
      `MagnifierTool.radius_for_page()` lo escala en proporción: con la
      página de arranque la lente mide lo mismo que antes, y con cualquier
      otra ocupa la misma fracción de la pantalla. No hizo falta una
      preferencia nueva —la que había guarda el mismo número, y la ventana
      de configuración dice ahora que es el de la página de una época—.
  - Test: `tests/test_magnifier.py`, **36 tests en verde**: el radio con
    páginas de 1 s a una hora, y el círculo publicado con una de 3 s.
- [x] **El montaje AASM de un clic** (F4-M1, C4-M1, O2-M1 y los EOG):
      `derive_montage()` existe desde la Parte 2 y la ventana sólo deriva de
      a un par.
      Hecho: «Montaje › Montaje AASM». **Revisa la decisión del hito 19**, que
      dejó `derive_montage()` como biblioteca porque nadie había pedido un
      montaje entero desde el programa; el usuario lo pidió, y sale de
      `SOLO_BIBLIOTECA`. `plan_aasm_montage()` busca los electrodos con los
      nombres de los equipos —«EEG C4-REF» es el C4, LOC y ROC son E1 y E2—
      y arma F4-M1, C4-M1, O2-M1, su respaldo F3-M2, C3-M2 y O1-M2, y E1-M2 y
      E2-M2. Sin mastoides usa los lóbulos, y el derivado se llama «C4-A1»
      para no decir algo que no se registró. Lo que el registro ya trae
      derivado no se repite, y lo que falta se dice en la barra de estado
      —«O1-M2 (falta O1)»— hasta el próximo mensaje; sin ninguna derivación
      posible, un cartel. `derive_montage()` recibe ahora el nombre y la
      clase de cada derivado: «E1-M2» es un EOG aunque M2 sea un electrodo
      de EEG, y la regla de `derive()` le daba «Otro». Se vuelve atrás con
      «Volver a la señal original», como derivar.
  - Test: `tests/test_derivation.py`, **52 tests en verde**; y en
    `tests/test_entrega_analisis.py`, el montaje por la ventana: la resta, la clase,
    lo que falta, no repetir y volver atrás.
- [x] **Más rótulos de canal reconocidos.** `readers/channel_types.py` deja
      en «Otro» nombres comunes de polisomnografía —ABD, THO, Chest, Therm,
      Nasal, Pres, PTAF, Effort, Pleth, Pulse, Pos, Leg, LAT, RAT, M1, M2—, y
      con eso pierden la escala de su clase y el atajo del selector. Y `loc`
      y `roc` se buscan sin límite de palabra: «Clock» sale EOG.
      Hecho. El esfuerzo (ABD, THO, Chest, Effort), el flujo (Therm, Nasal,
      Pres, PTAF, Cannula) y la oximetría (Pleth, Pulse) son respiratorios
      —la oximetría no tiene clase propia y va donde ya iba la SpO2—; las
      piernas (Leg, LAT, RAT) son EMG; y **M1, M2, A1 y A2 son EEG**, que es
      lo que necesita el montaje: `derive()` le da a «C4-M1» la clase de sus
      dos canales sólo si coinciden, y con M1 en «Otro» la derivación que se
      scorea salía «Otro». **Pos queda en «Otro» a propósito**: no es de
      ninguna clase. El límite de palabra no era sólo de `loc` y `roc`: `e1`
      hacía EOG a «Line1», `ojo` a «Cable rojo» y `chin` hacía EMG a
      «Machine». Los patrones cortos se anclan al comienzo de la palabra, y
      los nombres de clase —`eog`, `emg`, `ecg`— siguen valiendo pegados,
      como en «HEOG». Y los acentos se sacan antes de partir el nombre:
      «Mentón» se partía en «ment» y «n» y dejaba de ser EMG.
  - Test: `tests/test_channel_types.py`, **93 tests en verde**. Veinticinco
    de los nuevos fallan sin el cambio; los demás cuidan que no se pase de
    largo: «Lateral» y «Pos» siguen en «Otro».
- [x] **El arousal existe dos veces sin relación**: la marca de la ventana
      (tecla A) y la clase de anotación «Arousal». *(Decidido: la marca.)*
      Hecho, con la decisión 6: **anotar un arousal marca su ventana**, la de
      su comienzo, que es donde la AASM cuenta uno que cruza el borde. La
      regla es de `core/`: `annotations.is_arousal()` reconoce la clase como
      se la escriba y `Session.mark_arousal_of()` marca. La ventana la aplica
      en cada camino que crea o cambia una anotación: arrastrar, la E,
      cambiar la clase a «Arousal», correr su comienzo e importar las marcas
      del archivo. **Borrar no desmarca**: la marca pudo haberse puesto a
      mano. Anotar y marcar son un solo paso de deshacer.
  - Test: `tests/test_annotations.py`, **97 tests en verde**;
    `tests/test_session.py`, **167 tests en verde**;
    `tests/test_entrega_scoring.py`, **46 tests en verde**.

### Tanda 3: partir las clases grandes

**Va antes que buena parte de la tanda 2**, aunque se ve menos: cada
funcionalidad nueva le suma métodos a `MainWindow`, y es más barato mudarlos
una vez que agregarlos al lugar que después hay que partir.

- [x] **`MainWindow` pasa de siete mixins a controladores con estado
      propio.** El hito 76 la partió por tema, y lo dice: «es una partición,
      no un desacople»; los ocho archivos comparten el estado de
      `__init__` y siguen siendo una clase de 170 métodos. En este orden, uno
      por hito, cada uno con sus tests migrados en el mismo cambio:
      1. `ui/tool_controller.py`: las herramientas, quién tiene el mouse,
         quién dibuja, el filtro de eventos y los overlays. Es el que toca
         la tanda 1.
         **Hecho.** `ToolController` reemplaza al mixin `window_tools.py`,
         que se borró, y la ventana lo guarda en `tool_controller`. No
         conoce la ventana: recibe los cuatro widgets que usa y le avisa por
         señales de Qt lo que es de ella —ir a una ventana desde el
         hipnograma, redibujarlo, soltar el anotador y su clic derecho, que
         abren carteles—. La rueda no era de ninguna herramienta y pasó a
         `window_view.py`, con su propio `eventFilter()`; el cursor ↔ del
         anotador pasó al controlador. Los tests de la ventana cambiaron
         `_toggle_tool()`, `_tools` y `_tool_actions` por
         `tool_controller.toggle()`, `.tools` y `.actions`, y el contador de
         la lupa dejó de ser un método de la ventana.
         - Test: `tests/test_tool_controller.py`, **16 tests en verde**, que
           arma el controlador sin la ventana, que es lo que no se podía.
      2. `ui/playback_controller.py`: el cursor, el reloj y cómo mueven la
         página.
         **Hecho.** `PlaybackController` se queda con el reloj y con el
         cursor, que era `MainWindow._cabezal` y leían cinco métodos de tres
         archivos; la ventana lo guarda en `playback_controller` y le
         pregunta `playhead` antes de mover la página. Le avisa por señales
         que cambió la época, que se llegó al final y qué no se pudo.
         `toggle_playback()` queda en la ventana porque los atajos se buscan
         ahí por nombre. `stop()` saca también el cursor que deja un paso
         pedido a mano, y el banco de rendimiento lo usa en vez de escribir
         `_cabezal`. El docstring de `ui/playback.py` decía todavía que la
         reproducción no tocaba la época, como antes del hito 27.
         - Test: `tests/test_playback_controller.py`, **13 tests en verde**,
           sin la ventana.
      3. `ui/analysis_controller.py`: la ICA, la señal original y la tarea en
         segundo plano.
         **Hecho.** `AnalysisController` se queda con
         `_registro_original`, `_ica` y `_tarea`, que estaban repartidos
         entre `main_window.py` y `window_analysis.py`, con la barra de
         espera y las acciones que se apagan mientras corre un cálculo. La
         ventana lo guarda en `analysis_controller`; qué análisis pedir y
         cómo mostrarlo sigue en `window_analysis.py`, que es presentación.
         `replace_recording()` pone el resultado en la sesión y olvida la
         ICA sólo si salió bien; `restore_original()` vuelve. Avisa por
         señales el error, la ICA olvidada y si hay a qué volver.
         `wait_for_background()` queda en la ventana, que la usa al cerrar.
         - Test: `tests/test_analysis_controller.py`, **12 tests en verde**,
           sin la ventana.
      4. `ui/work_guard.py`: el trabajo sin exportar, los diálogos de
         exportar y la recuperación de la tanda 2.
         **Hecho, sin la recuperación**, que es una funcionalidad nueva y
         tiene su ítem en la tanda 2: va a vivir acá. `WorkGuard` se queda
         con exportar, su diálogo, la carpeta de los diálogos y el cartel
         del trabajo sin exportar, que eran la mitad de `window_files.py`.
         La ventana lo guarda en `work_guard` y le pregunta
         `can_discard()` antes de soltar la sesión; `export()`,
         `export_scoring_dialog()` y `closeEvent()` quedan en la ventana y
         delegan. El error de exportar le llega por señal, y la pregunta de
         reemplazar un archivo se la pasa la ventana. Los tests que
         contestaban `_preguntar_por_el_trabajo` contestan `WorkGuard.ask`.
         - Test: `tests/test_work_guard.py`, **25 tests en verde**, sin la
           ventana.

      `MainWindow` queda armando las piezas y los carteles. **Los cuatro
      están hechos**: quedan seis mixins, que son partición por tema, y
      cuatro controladores con estado propio que se testean sin la ventana.
      De paso salieron cuatro imports que los pasos anteriores habían dejado
      sin uso en `main_window.py` y `window_annotation.py`.
- [x] **`Session` delega la presentación de los canales** en
      `core/channel_display.py`: visibles, seleccionados, escala y
      desplazamiento de cada uno, ajustar al panel y centrar. Son la mitad de
      sus 1100 líneas y la mitad que toca la tanda 1. `Session` conserva sus
      métodos públicos, que delegan.
      Hecho: `Session` bajó de 1179 a unas 900 líneas, y ningún test de
      `test_session.py` cambió. **`ChannelDisplay` no sabe de épocas**: lo
      que mide —centrar, ajustar al panel, la escala de las clases sin una
      propia— lo mide sobre un tramo de muestras. La sesión valida la época,
      la convierte y le pasa el tramo, así que la guarda de qué ventana
      existe sigue en un solo lugar, y un tramo imposible lo rechaza
      `Recording.get_segment()`. De `set_recording()` se lleva la regla de qué
      sobrevive a un registro procesado, y devuelve los canales nuevos para
      que la sesión los mida sobre la época actual. V2_P, V3_P y V5_F pasan
      a `channel_display.py` en `TRAZABILIDAD.md`.
  - Test: `tests/test_channel_display.py`, **25 tests en verde**, sin
    sesión: que mida sobre el tramo que se le pasa y no sobre otro, el
    alcance de la amplitud, las clases sin escala propia y qué sobrevive a
    un registro procesado. `tests/test_contratos.py`, **1371 tests en
    verde**, con sus filas y tres rechazos obligatorios.
- [x] **`SignalView` (1344 líneas) separa lo que dibujan las herramientas**
      —banda, bandas de anotación, segmentos, lente— en
      `ui/overlay_items.py`, y la caché de la envolvente en su propia clase.
      Hecho: quedó en 949 líneas. `OverlayLayer` dibuja los cuatro tipos y le
      pregunta la geometría al visualizador, que la expone con
      `lane_center()`, `to_lanes()` —una **posición**, que resta el
      desplazamiento del canal— y `height_to_lanes()` —una **longitud**, que
      no lo resta—; `EnvelopeCache` es numpy y un diccionario, sin Qt.
      **Separarlos encontró un error**: la banda de amplitud convertía su
      alto como una posición, así que sobre un canal desplazado medía
      cualquier cosa. Con 500 µV de desplazamiento, la banda de 75 µV medía
      4,16 carriles en vez de 0,34: doce veces. Los respiratorios se centran
      solos al abrir un registro, así que le pasaba a cualquiera que midiera
      sobre uno.
  - Test: `tests/test_overlay_items.py`, **24 tests en verde**, y
    `tests/test_envelope_cache.py`, **7 tests en verde**, sin Qt;
    `tests/test_signal_view.py` sigue con **98 tests en verde**.
- [x] **Los lectores comparten lo que repiten.** `edf.py` y `brainvision.py`
      tienen el mismo `_factor_a_microvoltios()`, el mismo armado de canales
      y la misma lectura de marcas: a un módulo común de `readers/`.
      Hecho, en `readers/from_mne.py`: `microvolt_factor()`,
      `build_channels()` —que convierte en el lugar y deduce la clase con la
      unidad ya convertida— y `marks_of()`. **La tabla de grafías que MNE
      lleva a volts sigue siendo de cada lector**, y se le pasa: MNE usa una
      por formato, con mayúsculas y sin normalizar, y confundirla con la de
      `utils/units.py` fue el error del hito 33. Los dos lectores bajaron unas
      setenta líneas cada uno y `test_readers.py` no cambió.
  - Test: `tests/test_from_mne.py`, **11 tests en verde**, sin archivo: qué
    fila se convierte y desde qué unidad, que la tabla decida y no la
    unidad, la clase con la unidad convertida y las marcas.
- [x] **Una sola guarda de registro en `analysis/`**: `_exigir_registro()`
      está escrita siete veces, en siete módulos.
      Hecho: **eran nueve**, porque `complexity.py` e `impedance.py` la
      llevaban escrita adentro de la función. Queda una, en
      `mne_bridge._exigir_registro()`, que ya era la que usaba
      `auto_scoring.py`: es lo que todo `analysis/` importa, y no carga MNE.
      **Recibe el comienzo del mensaje**, así que cada análisis le sigue
      diciendo al investigador qué no pudo hacer —«No se puede filtrar
      eso», «No se puede calcular el espectro de eso»— y no un rechazo
      genérico. Las sugerencias de fases, que usaban el genérico del
      puente, ganaron el suyo. `test_analysis_tiene_una_sola_guarda_de_registro`
      rechaza una copia nueva: contra el código de antes encuentra las nueve.
  - Test: `tests/test_mne_bridge.py`, **34 tests en verde**, con el mensaje
    de cada uno de los dieciocho análisis que reciben primero el registro;
    `tests/test_consistencia.py`, **121 tests en verde**.
- [x] **Una sola forma de escribir un número para el usuario.**
      `.replace(".", ",")` aparece 22 veces y hay tres `_numero()`: un
      `utils/formato.py` con el número con coma, los Hz y las duraciones.
      Hecho, en `utils/formatting.py` —en inglés, como pide `CLAUDE.md` para
      los nombres de archivo—: `number()` con coma y sin ceros de más,
      `quantity()` con su unidad, `duration()` —el `duration_text()` de
      `ui/menus.py`, que bajó para que lo pueda usar cualquier capa— y
      `parse_number()`, que lee con coma o con punto y no acepta «inf». Un
      NaN se escribe «—» y no «nan». **Eran veinticinco `replace`**, y dos de
      los tres `_numero()` no escribían sino que leían lo que tipea el
      investigador. **Y unos veinte mensajes ni siquiera lo hacían**: «El
      pasa-altos de 0.3 Hz no se puede aplicar…», «La banda de 0.5 a 4 Hz…»,
      la frecuencia de muestreo de la barra de estado, y
      `test_connectivity.py` exigía la resolución con punto. Ahora salen con
      coma. `Informacion.txt` no cambia ni un carácter.
      `test_todo_numero_que_ve_el_usuario_sale_de_formatting` rechaza un
      `{x:g}` o una coma puesta a mano fuera del módulo —contra el código de
      antes encuentra setenta y siete—, salvo en `details` y en el XML de
      scoring, que es de máquina y lleva punto. **No ve un número interpolado
      sin formato**, `f"{x} Hz"`.
  - Test: `tests/test_formatting.py`, **46 tests en verde**;
    `tests/test_contratos.py`, **1371 tests en verde**;
    `tests/test_consistencia.py`, **121 tests en verde**.
- [x] **`tests/test_entrega.py` (6400 líneas, 370 tests) se parte por
      tema**, siguiendo a los controladores.
      Hecho, cuando ya eran 7258 líneas y 437 tests: **seis archivos de
      test**, y lo que comparten en `tests/entrega_comun.py`, que no es un
      test. `test_entrega.py` se queda con la entrega —abrir, navegar,
      scorear, exportar— y con lo que protege el trabajo: los formatos del
      scoring, el trabajo sin exportar, la recuperación y abrir otro
      registro. Los otros cinco, por tema: `_scoring` —el hipnograma, las
      sugeridas, deshacer y rehacer, el arousal—, `_anotacion`, `_vista`
      —la Übersicht, la reproducción, la rueda—, `_analisis` —la Parte 2 y
      el cálculo en otro hilo— e `_interfaz` —la configuración, el teclado,
      los textos—. **La partió un script y no a mano**: cada sección fue
      entera a su archivo, y a `entrega_comun.py` fue sólo lo que usa más de
      uno, con lo que eso necesita. Los 437 identificadores de test son los
      mismos antes y después, comparados uno por uno.
  - Test: `tests/test_entrega.py`, **79 tests en verde**;
    `tests/test_entrega_scoring.py`, **46 tests en verde**;
    `tests/test_entrega_anotacion.py`, **59 tests en verde**;
    `tests/test_entrega_vista.py`, **47 tests en verde**;
    `tests/test_entrega_analisis.py`, **103 tests en verde**;
    `tests/test_entrega_interfaz.py`, **103 tests en verde**.
- [ ] **Los docks se llaman `*_dock`.** Siguen llamándose `psd_dialog` y
      compañía para no tocar ocho tests; quien lee el código busca un
      diálogo que no existe.

### Tanda 4: que el código lo lea alguien que no programa

**Medido**: de las 24 800 líneas no vacías de `psglab/`, el 34 % son
docstrings y el 10 % comentarios, y el código nombra algún hito 382 veces.
Gran parte de esa prosa **cuenta la historia del cambio** —«hasta el hito 33
esto…», «lo encontró la auditoría…»— en vez de decir qué hace el código hoy.
Para quien llega sin contexto, triplica lo que hay que leer para entender una
función, y la historia ya está en este archivo y en git.

- [ ] **La regla**: un docstring dice qué hace y por qué, en presente. La
      historia va al hito y al commit. Se aplica al tocar cada módulo, no en
      una sola pasada; **`core/` primero**, que es lo que se lee para
      entender el modelo.
- [ ] **Un trinquete en `test_consistencia.py`**: la cantidad de menciones a
      hitos dentro de `psglab/` no puede crecer. Sin él, la regla de arriba
      depende de acordarse.
- [ ] **«Dónde cambiar qué», en `EXPLICACION.txt`**: la duración de la
      época, los colores, las teclas, los filtros sugeridos, los nombres de
      los archivos de salida. Es la pregunta de quien abre el código sin
      programar.
- [ ] **El código muerto que la red no ve.** La red del hito 30 mira
      `analysis/`, `tools/` y los paneles, no `core/`, `readers/` ni
      `utils/`, y ahí sobrevivieron: en `core/windows.py`,
      `seconds_to_window_fraction()`, `window_fraction_to_seconds()`,
      `seconds_to_sample()` y `sample_to_seconds()`, las conversiones de antes
      del refactor que sólo usan los tests; en `core/viewport.py`, `at_start`,
      `at_end` y `replaced()`; `AnnotationSet.count_by_label()`, cuyo
      docstring dice que lo usa `Informacion.txt` y no lo usa;
      `detect_all()` e `is_eeg_position()`; `MixedSamplingRateError`, que no
      se eleva nunca; `PlaybackClock.toggle()`; y
      `OverviewTool._draw_window()`, que su propio docstring dice conservar
      por la trazabilidad. Extender la red y borrar o declarar cada uno.
- [ ] **Los docstrings que dicen lo contrario de lo que hace el código**:
      `core/windows.py` y `tools/annotator.py` todavía hablan de segundos
      desde el comienzo de la ventana; `ui/signal_view.py` dibuja «la ventana
      de 30 segundos actual» y su eje sin hora se rotula «Segundos de la
      ventana»; `ui/menus.py` dice que «Archivo» dejó de ser un menú;
      `ui/main_window.py` nombra un menú «Paneles» y deja un comentario del
      hito 62 sin código debajo; un comentario de
      `ui/window_preferences.py` perdió el nombre que citaba en la mudanza
      del hito 76; `config.MAX_GRID_LINES` habla de una `InfiniteLine` por
      línea; y el comentario de arriba de `ci.yml` dice que corre contra las
      ramas de trabajo.
- [x] **Este archivo en dos.** *(Decidido: sí.)* Son 6500 líneas, y la
      introducción encadena ochenta hitos en un solo párrafo. Lo cerrado
      podría ir a un historial y el TODO quedar con lo abierto y las reglas.
      Cerrar un hito pide hoy seis ediciones; la cuenta de hitos escrita en
      cuatro documentos es la que más se desincroniza, y podría quedar sólo
      acá. Toca `test_consistencia.py`, que lee este archivo.
      Hecho: los hitos 0 a 78 están en `HISTORIAL.md`, con el párrafo que los
      encadena, y este archivo quedó en unas setecientas líneas. Las
      **preguntas abiertas con el cliente**, que estaban repartidas entre lo
      cerrado —la impedancia en el hito 0, V2_F a V4_F de «Filtración» en la
      introducción de la Parte 2, los dos archivos de salida fuera del menú en
      el 23— tienen su sección al principio. La cuenta de hitos se escribe
      sólo acá. En `test_consistencia.py`: la cuenta se exige sólo a este
      archivo; las cuentas de tests del historial ya no se comparan, porque
      son las del cierre de cada hito —una llegó a estar escrita cuarenta y
      ocho veces—; el chequeo de hitos cerrados lee las secciones de los dos
      archivos —leyendo sólo éste se las salteaba todas en silencio—; y uno
      nuevo, `test_cada_hito_vive_en_su_archivo`, exige que cada hito esté en
      el archivo que le toca y que su fila apunte ahí. Cerrar un hito pasa a
      ser cinco ediciones.
  - Test: `tests/test_consistencia.py`, **121 tests en verde**.

### Tanda 5: rendimiento y robustez

- [x] **Abrir un registro y filtrar, fuera del hilo de la interfaz**, con
      `BackgroundTask`, como ya van la ICA y la conectividad de la noche. Hoy
      congelan la ventana: abrir, 4,3 s en el registro de prueba.
      Hecho. **Filtrar** pasa por `analysis_controller.run_in_background()`
      como la ICA: la barra de espera se mueve, «Montaje» y «Filtrar» se
      apagan mientras dura, y si la señal cambió mientras tanto el resultado
      se descarta. **Abrir** tiene su propia `BackgroundTask`, para no esperar
      a una ICA —abrir mientras se ajusta se podía y se sigue pudiendo—: el
      diálogo y los recientes van por `open_recording_in_background()`, y
      `open_recording()` sigue leyendo en el hilo de la interfaz para los
      scripts y los tests. Mientras lee, **el registro anterior se sigue
      usando**, y la pregunta por el trabajo sin exportar llega después de
      leer, así que cuenta lo hecho mientras tanto. Dos aperturas a la vez no:
      la segunda se ignora y se dice. Cerrar la ventana mientras lee espera
      la lectura y la descarta: tomarla volvía a preguntar por el trabajo y
      cambiaba la sesión mientras se cerraba.
  - Test: en `tests/test_entrega_analisis.py`, que el archivo se lea y la señal se
    filtre en otro hilo, que mientras tanto siga el registro anterior, el
    error de lectura, dos aperturas a la vez, abrir con un cálculo en curso
    y cerrar mientras lee. Los catorce tests que filtraban por la ventana
    esperan ahora el resultado con `wait_for_background()`, como los de la ICA.
- [x] **Los overlays no se rehacen enteros en cada movimiento del mouse.**
      Con la lupa o el anotador activos, `set_overlays()` saca y vuelve a
      crear cada banda de anotación de la página y su rótulo en cada evento;
      con una página larga y cientos de marcas importadas son cientos de
      ítems por movimiento. Medir con el banco antes de tocar.
      Hecho en `OverlayLayer`: un overlay que ya está dibujado con la misma
      página, los mismos canales, la misma escala y desplazamiento de cada
      uno y el mismo esquema se deja como está. La lente se rehace siempre,
      porque depende de cuánto mide un píxel. Medido con el banco
      —`medir_overlays()`, nuevo en `tests/medir_rendimiento.py`—, página de
      5 min y la lupa moviéndose, en offscreen:

      | Anotaciones en la página | Antes | Después |
      |---|---|---|
      | 0 | 5,9 ms | 5,9 ms |
      | 100 | 221 ms | 35 ms |
      | 400 | 1026 ms | 122 ms |

  - Test: en `tests/test_overlay_items.py`, qué se reutiliza y qué cambio
    de geometría obliga a rehacer.
- [x] **Una sola pieza para todas las bandas de anotación**, como la
      grilla. Después del ítem anterior, `set_overlays()` cuesta unos 6 ms
      por movimiento con 400 anotaciones; **el 94 % de lo que queda es Qt
      pintando** 400 `LinearRegionItem`, cada uno con sus dos
      `InfiniteLine`, en cada cuadro. Lo paga también la reproducción, que
      repinta la escena entera. Es el mismo remedio que la grilla del hito
      25: un solo objeto que pinte todos los rectángulos de la página. Los
      bordes que se agarran para corregir un tramo son del anotador, que
      recibe el clic por coordenadas y no por ítem, así que no dependen de
      que cada banda sea un objeto. Medirlo con el banco, intercalado.
      Hecho: `AnnotationBands`, en `ui/overlay_items.py`. **Juntar los
      objetos no alcanzó**: bajó a unos 80 ms, y el perfil pasó a ser el
      propio relleno. Rellenar 400 rectángulos traslúcidos de 5 × 700 px
      cuesta unos 70 ms aunque sea una sola llamada, y opacos 1,5 ms; lo
      más probable es que Qt mezcle fila por fila. Como todas las filas de
      una banda son iguales, los rellenos se componen en una tira de un
      píxel de alto que se estira a todo el alto. Los rótulos siguen siendo
      un `TextItem` cada uno: eran el 6 % del perfil. Medido intercalado
      con el banco, página de 5 min y la lupa moviéndose, en offscreen:

      | Anotaciones en la página | Antes | Después |
      |---|---|---|
      | 0 | 9,1–9,3 ms | 9,5–9,8 ms |
      | 100 | 35–39 ms | 14–15 ms |
      | 400 | 117–130 ms | 26–28 ms |

      **Se ve igual**, comparado píxel a píxel contra las `LinearRegionItem`
      —también con densidad 2—: 1/255 de redondeo, salvo que ahora los
      bordes van encima de todos los rellenos, y el de una banda que cae
      dentro de otra ya no queda teñido. Comparar encontró un error antes de
      que llegara a la pantalla: con ocho cifras, `QColor` lee `#AARRGGBB` y
      pyqtgraph `#RRGGBBAA`.
  - Test: en `tests/test_overlay_items.py`, que cien anotaciones sean una
    pieza, que se pinten de su color y donde van —a cada lado de los dos
    bordes— y que lleguen al carril que se agrega sin redibujarlas.
- [x] **El hipnograma no se rearma en cada flecha.** `_reflejar_epoca()`
      llama a `_redraw_histogram()`, que limpia y vuelve a crear la curva,
      las barras y las marcas, aunque `HistogramTool.update_window()` exista
      para no hacerlo.
      Hecho. **Eran dos por flecha**: además de `_reflejar_epoca()`, la
      herramienta avisa que se movió la época actual, y el hipnograma no la
      dibuja. `update_window()` no era la salida —pone al día los datos de
      la herramienta, no el dibujo—: `_redraw_histogram()` compara ahora una
      firma de lo que dibuja —las fases y las sugeridas, la nomenclatura, el
      esquema, el eje en hora y la hora de inicio— y si no cambió no hace
      nada. Medido intercalado con `medir_flecha()`, nuevo en el banco, sobre
      una noche de 8 h con la mitad scoreada: **de 26–27 ms a 8 ms** por
      flecha.
      De paso, la firma de los overlays del visualizador llevaba el
      **nombre** del esquema, y uno armado con `dataclasses.replace()` se
      llama igual y pinta distinto: las dos llevan ahora el esquema entero.
      Y el banco terminaba con un cartel modal que nadie contestaba —cerraba
      la ventana con lo que las mediciones anotan sin exportar—, que es
      probablemente el cuelgue que no se diagnosticó al medir los overlays.
  - Test: en `tests/test_entrega_scoring.py`, que una flecha deje la misma curva y
    que scorear, cambiar el eje a hora, la nomenclatura sin nada scoreado u
    otro registro con otra hora la rehagan: sacar cualquiera de esas cosas
    de la firma lo nota un test. En `tests/test_overlay_items.py`, un
    esquema con el mismo nombre y otros colores.
- [x] **`AnnotationSet` con búsqueda binaria**: `_insertar()` rearma la
      lista de comienzos en cada anotación y `in_range()` recorre todas en
      cada repintado.
      Hecho. **Agregar era cuadrático**, no sólo lento: rearmar la lista de
      comienzos en cada anotación hacía que importar 20 000 marcas tardara
      cinco segundos, y lo mismo pagan deshacer y la recuperación, que
      vuelven a agregar todo. `AnnotationSet` guarda ahora la lista de
      comienzos al lado, en el mismo orden, y la duración más larga, que
      acota hacia atrás lo que puede solaparse con un tramo; `remove()`
      busca sólo entre las que empiezan en la misma muestra. Medido con
      `medir_anotaciones()`, nuevo en el banco, intercalado:

      | Anotaciones | Agregar todas | Las de un tramo de 5 min |
      |---|---|---|
      | 1 000 | 8–13 ms → 1,3 ms | 0,04–0,07 ms → 0,003 ms |
      | 5 000 | 176–200 ms → 10 ms | 0,17 ms → 0,006 ms |
      | 20 000 | 4,9 s → 100–126 ms | 1,5 ms → 0,05 ms |

      Con la lista de comienzos, la búsqueda binaria podía elevar
      `TypeError` al pedir borrar una anotación cuyo comienzo no es un
      número, algo que `list.remove()` no hacía: se atrapa y sale el error
      de siempre.
  - Test: en `tests/test_annotations.py`, **la búsqueda contra la cuenta
    ingenua** en ocho secuencias al azar de agregar, borrar, borrar por
    posición y reemplazar, con comienzos repetidos y duraciones de una
    muestra a cinco minutos. Lo único que no ve ningún test es no volver a
    medir la duración más larga al borrar la más larga, porque no cambia
    ningún resultado: sólo deja la búsqueda más ancha.
- [x] **Los archivos de salida se escriben enteros o no se escriben**: a un
      temporal y después renombrado, como ya hace `preferences.save()`. Un
      corte a mitad de camino hoy deja el archivo truncado.
      Hecho en `exporters/atomic.py`, y lo usan los seis escritores: los tres
      archivos del pliego y el scoring en CSV, EDF+ y XML. El provisorio va
      **al lado del destino**, en el mismo disco, porque `os.replace()` entre
      discos no es de un paso; y con **un nombre fijo** y no de `tempfile`,
      porque `mkstemp()` lo crea en 0600 y el renombrado lo conserva: el
      archivo exportado quedaba ilegible para el resto del laboratorio. Si
      algo falla, el provisorio se borra y el error sale igual, así que
      `WorkGuard.export()` lo sigue mostrando como hasta ahora.
  - Test: en `tests/test_exporters.py` y `tests/test_scoring_formats.py`, un
    disco que se llena a mitad de camino en los tres archivos del pliego y
    un CSV que se corta en la tercera ventana: sin el cambio, los cuatro
    dejan el destino truncado.
- [x] **El XML de scoring, sin expansión de entidades.** Abrir un XML hecho
      a propósito puede agotar la memoria. Riesgo bajo: hace falta abrir un
      archivo malicioso.
      Hecho, y no sólo con un test. **La protección que había era la de
      expat**, que desde la 2.4 corta una expansión desmedida; pero en Linux
      Python puede usar el expat del sistema, así que eso dependía de la
      máquina, y un test que pidiera «se rechaza» habría verificado la
      máquina y no el programa. `_leer_xml()` hace ahora una pasada previa
      con `xml.parsers.expat` que **rechaza cualquier declaración de
      entidad**, antes de que se use: un scoring no necesita ninguna, ni el
      del NSRR ni el que escribe este programa. Cubre también las externas y
      las de parámetro. Sin dependencia nueva: la versión en C de
      `ET.XMLParser` no expone su expat, que es donde `defusedxml` cuelga
      la misma guarda.
  - Test: en `tests/test_scoring_formats.py`, la risa del millón, una
    entidad inofensiva sobre un scoring por lo demás válido —la que expat
    sí deja pasar—, una externa y una de parámetro, afirmando el motivo del
    rechazo y no sólo el rechazo; y que un `DOCTYPE` sin entidades se siga
    leyendo. En `tests/test_entrega.py`, que por la ventana sea un cartel y
    el scoring quede como estaba. Sin la guarda fallan los cinco que
    rechazan.
- [ ] **Medir el reparto con los paneles de análisis abiertos.** En la
      captura de 1800 px la señal quedaba con alrededor de un tercio del
      ancho y el panel de contexto con la mitad del alto. Puede ser propio de
      la herramienta de capturas: lo decide `python -m tests.medir_reparto`,
      que abre una ventana en la pantalla y lo corre quien esté frente a ella.

### Lo que decidió el usuario

**Contestadas el 26 de septiembre de 2026.** Revisan tres decisiones de hitos
anteriores —la 2 la del hito 33, la 3 las de los hitos 24 y 64, la 4 la forma
de anotar del hito 9—, y el motivo es el de la tanda 2: son los pasos de más
de quien scorea una noche entera.

1. **La banda de amplitud sigue al mouse** sobre el canal que está debajo,
   que es contra el que se mide la `y`. Quedó así en la tanda 1.
2. **Se agrega el archivo de recuperación en el perfil.** No exporta nada ni
   elige formato: al reabrir el mismo registro después de un cierre
   inesperado, ofrece volver a donde estaba.
3. **El panel de Scoring, a la vista y compacto al abrir**: una fila con las
   fases, sus teclas y el arousal, abajo junto al hipnograma.
4. **Anotar con una clase activa.** Se elige una vez —en una lista o con una
   tecla— y cada arrastre la usa sin cartel; con Mayúsculas al soltar,
   pregunta como hasta ahora.
5. **Un menú «Scoring»**, con las fases, el arousal, ir a la próxima sin
   scorear, deshacer y las fases sugeridas, que salen de «Analizar».
   «Escala de tiempo» y «Amplitud» pasan adentro de «Ver».
6. **Anotar un arousal marca su ventana.** Borrar la anotación no la
   desmarca: la marca pudo haberse puesto a mano.
7. **El informe de sueño estándar se hace** como una sección nueva al final
   de `Informacion.txt`, sin cambiar lo que ya trae, y **se confirma con el
   laboratorio antes de mergear**.
8. **Los filtros sugeridos se preguntan al laboratorio.** `DEFAULT_FILTERS`
   usa 0,3–15 Hz para el EOG, 0,5–70 Hz para el ECG y 0,05–5 Hz para lo
   respiratorio, y la AASM recomienda 0,3–35 Hz, 0,3–70 Hz y 0,1–15 Hz para
   el flujo. Son valores clínicos y los actuales pueden ser del laboratorio:
   no se tocan hasta tener la respuesta.
   - [ ] Preguntar al laboratorio qué filtros usa.
9. **Este archivo se parte en dos**: lo cerrado a `docs/HISTORIAL.md`, y acá
   lo abierto y las reglas. La cuenta de hitos queda sólo en este archivo, y
   `tests/test_consistencia.py` se ajusta en el mismo cambio.

### Lo que ya se corrigió en esta auditoría

- [x] **La documentación que decía algo falso**, sin tocar código:
      `README.md` hablaba de dos dependencias de la Parte 2 —son tres desde
      que entró YASA—, titulaba «la Parte 1 está terminada» y decía que `ui/`
      sólo depende de `core/` y `tools/`; `psglab/README.md` repetía lo
      último en su diagrama; `ARQUITECTURA.md` ubicaba un clic «en el
      segundo 12 de la ventana actual», no tenía a YASA ni a sus tres
      dependencias en la tabla de licencias y hablaba de Papel como un
      esquema vigente; `EXPLICACION.txt` decía que el programa abre sólo con
      la señal y los canales, sin el hipnograma, y también contaba dos
      dependencias.
- [x] **La cuenta de hitos**, a ochenta en los cuatro documentos que la
      declaran, y el numeral «ochenta» en el diccionario de
      `tests/test_consistencia.py`, que llegaba hasta setenta y nueve.

---

## Al agregar o cerrar un ítem

Actualizá en el mismo commit: este archivo, la fila de `TRAZABILIDAD.md` y el
`README.md` de la carpeta que tocaste.

**Al cerrar un hito, su sección se muda entera a
[`HISTORIAL.md`](HISTORIAL.md)**, al final, con un renglón en el párrafo que
encadena los hitos; su fila de la tabla pasa a ✅ y a apuntar al historial.
`test_cada_hito_vive_en_su_archivo` lo exige. Las cuentas de tests que se
lleva son las de ese momento, y ya no se corrigen. Los PR van a la branch **`Add`**, nunca
a `Master`, y vienen comentados.
