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

Son **ochenta y cinco hitos**, del 0 al 84, que son las filas de la tabla de
progreso; el 84 sigue abierto hasta la revisión independiente. La cuenta vive
sólo en este archivo:
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
      [hito 79](HISTORIAL.md#hito-79-la-auditoría-del-26-de-septiembre).
- [ ] **Los filtros sugeridos**, que pueden no ser los que el laboratorio
      usa. Ver la decisión 8 del [hito 79](HISTORIAL.md#hito-79-la-auditoría-del-26-de-septiembre).

Y una comprobación que sólo puede hacer una persona frente a la pantalla:

- [x] **`python -m tests.medir_reparto` con la letra del programa.** Abre una
      ventana de verdad, así que no la corre la suite; hasta el hito 78 medía
      con la letra del sistema. Ver el
      [hito 78](HISTORIAL.md#hito-78-que-la-suite-vea-la-letra-real).
      Hecho el 28 de septiembre de 2026, en Windows, al medir el reparto con
      los paneles de análisis abiertos: nada se corta, y con el espectro
      abierto la señal se queda con más de la mitad del ancho. Ver la tanda 5
      del [hito 79](HISTORIAL.md#hito-79-la-auditoría-del-26-de-septiembre).

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

Las pull requests contra `Master` tienen además [una revisión de
Claude](../.github/workflows/claude-review.yml), que lee el diff contra las
reglas de `CLAUDE.md` y bloquea el merge si encuentra algo grave. En `Add` no
corre.

Todas las pull requests reciben también un comentario de Codecov con la
cobertura de las líneas que cambiaron. Es informativo y no bloquea.

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
| [79. La auditoría del 26 de septiembre](HISTORIAL.md#hito-79-la-auditoría-del-26-de-septiembre) | — | 0 | ✅ cerrado |
| [80. La suite sale sin desarmar Qt](HISTORIAL.md#hito-80-la-suite-sale-sin-desarmar-qt) | — | 0 | ✅ cerrado |
| [81. La cobertura de los tests](HISTORIAL.md#hito-81-la-cobertura-de-los-tests) | — | 0 | ✅ cerrado |
| [82. La revisión de Claude contra Master](HISTORIAL.md#hito-82-la-revisión-de-claude-contra-master) | — | 0 | ✅ cerrado |
| [83. La cobertura en cada pull request](HISTORIAL.md#hito-83-la-cobertura-en-cada-pull-request) | — | 0 | ✅ cerrado |
| [84. Recuperar copias antiguas sin perderlas](TODO.md#hito-84-recuperar-copias-antiguas-sin-perderlas) | — | 0 | en revisión |
| | **0** | **0** | |

## Hito 84: Recuperar copias antiguas sin perderlas

El formato 2 conservaba las copias de formato 1, pero no las ofrecía y no
avisaba dónde quedaban. La implementación está en la rama
`hito-84/recuperacion-v1`; falta la revisión independiente de Prisma antes de
cerrar el hito.

- [x] Comparar la identidad antigua con el registro original y adaptar en
      memoria las copias sin canales derivados, con preflight antes de ofrecerlas.
- [x] Advertir sobre la identidad débil del formato 1 y sobre los filtros
      anteriores a un montaje reconstruido.
- [x] Archivar los bytes originales antes de reemplazar o borrar una copia
      antigua, e informar la ubicación de las copias conservadas.
- [ ] Revisión independiente de Prisma y corrección de los hallazgos que bloqueen.
- [x] Tests: `tests/test_recovery.py`, **51 tests en verde**;
      `tests/test_work_guard.py`, **48 tests en verde**; y
      `tests/test_contratos.py`, **1453 tests en verde**. Suite completa:
      4959 aprobados y 25 salteados en macOS con Python 3.14.

**La columna de stubs nunca midió el hito 9**, y por eso el hito 9 existió: sus
seis ítems eran código escrito que nadie llamaba. `contar_stubs()` cuenta
`raise NotImplementedError`, no caminos muertos, y con esa medida los hitos 6 y
7 se dieron por cerrados con la mitad de la interfaz sin conectar.

## Al agregar o cerrar un ítem

Actualizá en el mismo commit: este archivo, la fila de `TRAZABILIDAD.md` y el
`README.md` de la carpeta que tocaste.

**Al cerrar un hito, su sección se muda entera a
[`HISTORIAL.md`](HISTORIAL.md)**, al final, con un renglón en el párrafo que
encadena los hitos; su fila de la tabla pasa a ✅ y a apuntar al historial.
`test_cada_hito_vive_en_su_archivo` lo exige. Las cuentas de tests que se
lleva son las de ese momento, y ya no se corrigen. Los PR van a la branch **`Add`**, nunca
a `Master`, y vienen comentados.
