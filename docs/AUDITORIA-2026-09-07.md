# Auditoría del repositorio — 7 de septiembre de 2026

**Este informe no lleva estado.** Es la foto de lo que se encontró ese día,
recorriendo las nueve carpetas, los 17 documentos versionados y la
configuración del repositorio. Qué falta hacer y en qué orden vive en
[`TODO.md`](TODO.md), que es el único documento del proyecto que lleva la
cuenta.

Es la segunda. La primera, [`AUDITORIA.md`](AUDITORIA.md), es del 4 de
septiembre y **no se toca**: encontró otra cosa, en otro momento, y reescribirla
borraría el registro de cómo estaba el repositorio entonces.

Las referencias van como `ruta:línea` y no como enlaces, por el mismo motivo que
en la primera: los números de línea envejecen con el primer commit que toca el
archivo, y un enlace roto haría fallar el chequeo de enlaces. **Los hallazgos
corregidos citan el estado anterior a los commits de esta misma rama**, así que
sus líneas ya no coinciden; los que quedaron abiertos sí apuntan al archivo tal
como está.

## Por qué se hizo

En dos días entraron los hitos 4, 5, 6 y 7: los lectores, los exportadores, las
seis herramientas y la interfaz entera. El código pasó de 170 stubs a 0, la
suite de unos 400 tests a 1090, y `python main.py` pasó de terminar en
`NotImplementedError` a abrir la ventana.

La documentación se escribió mientras eso pasaba, y buena parte se escribió
cuando las cosas todavía no existían.

Al cerrar el hito 6 apareció una muestra sin buscarla: `CLAUDE.md` seguía
afirmando que `python main.py` termina en `NotImplementedError` "y es el
comportamiento esperado, no un bug", y el `README.md` de la raíz que faltaban
leer archivos, exportarlos y la interfaz. Se corrigieron ahí mismo, pero se
encontraron de casualidad. Esta auditoría fue a buscar el resto.

## El estado real, medido

| Magnitud | Valor |
|---|---|
| Archivos `.py` en `psglab/` | 51 — 43 módulos y 8 `__init__.py` |
| Stubs (`raise NotImplementedError`) | 26, todos de la Parte 2, en 8 módulos |
| Stubs de la Parte 1 | 0 |
| Tests | 1090 recolectados, 1090 en verde, 0 salteados |
| Archivos de test | 25, más `conftest.py` |
| Documentos versionados | 17, 3.894 renglones (sin contar este informe) |
| Hitos cerrados | 0 a 7; queda abierto el 8 |

## Qué encontró y qué no puede encontrar el chequeo automático

`tests/test_consistencia.py` verifica **cuentas**: stubs, tests recolectados,
IDs del pliego en las dos direcciones, enlaces y anclas, ASCII, capas sin Qt,
type hints, párrafos repetidos. Las verifica bien y **ninguna estaba mal**.

Lo que no puede verificar es la **prosa**. "Falta implementar X" no tiene
números que comparar, y la prosa es la mayor parte de esos 3.894 renglones. Los
23 hallazgos de abajo salieron todos de ahí.

---

## 1. La Parte 1 terminó y seis documentos seguían diciendo que no

Es la misma frase, repetida en seis lugares, corregida en dos de ellos al cerrar
el hito 6 y sobreviviente en los otros seis porque nadie los miró.

**El peor es `docs/EXPLICACION.txt:39`**, que es el documento escrito para el
cliente:

> ESQUELETO, CON LA CAPA DE NEGOCIO TERMINADA. […] Falta leer archivos,
> exportarlos y la interfaz, asi que si se ejecuta el programa ahora, avisa que
> la funcion pedida esta pendiente.

Sobrevivió a las dos correcciones anteriores por un motivo estructural: es un
`.txt`, y `archivos_markdown()` sólo recorre los `.md`. De los quince chequeos
que tocan documentación, a este archivo le llegan dos.

Los demás:

| Dónde | Qué decía | Qué pasa de verdad |
|---|---|---|
| `README.md:197` | los tests sin implementar están apagados con `pytestmark`, "así que la corrida informa una parte de la suite como `skipped`" | no queda ninguno apagado |
| `psglab/readers/README.md:120` | "lo que falta de esta carpeta no es código sino sus tests" | los dos existen y corren, **ocho líneas debajo de "la carpeta está terminada"** |
| `psglab/readers/base.py:166` | "el despacho está implementado; lo que falta es el `read()` de cada formato" | los dos `read()` están implementados |
| `tests/README.md:20` | encabezado "Mientras el proyecto sea un esqueleto" | la Parte 1 no es un esqueleto |
| `tests/README.md:89` | "`test_readers.py`, cuando se abra el hito 4" | el hito 4 cerró el 6 de septiembre |
| `docs/README.md:5` | el TODO es la cola "de la Parte 1" | la Parte 1 está cerrada |

### El caso al revés

`tests/README.md:180` pedía **extender** `test_exporters` "para que cubra de
verdad `statistics.py` e `information_txt.py`, que hoy no importa". Los importa
desde el hito 5, y hoy `test_la_tabla_de_cobertura_declara_lo_que_el_test_importa`
**exige** que los importe. La tarea pendiente estaba hecha y el documento pedía
hacerla.

### Y dos comentarios adentro de los propios tests

Incomodan más que los README, porque están en los archivos que existen para
evitar esto.

`tests/test_consistencia.py:72` afirmaba que `information_txt.py` y
`statistics.py` "no figuran acá" y que "`test_exporters.py` ni siquiera los
importa", **inmediatamente encima del diccionario que los lista**.

`psglab/core/session.py:227` justificaba `add_window_listener()` diciendo que la
obligación quedaría "en la única capa que no lleva tests unitarios". El hito 6
acotó esa regla y `psglab/ui/README.md` ya la enunciaba acotada; el comentario
se quedó con la versión vieja.

---

## 2. Descripciones del código que el código desmiente

No son estado que envejeció: son afirmaciones sobre cómo funciona el programa.

### El ejemplo de `tools/README.md` no compilaba

`psglab/tools/README.md:105` mostraba, como el ejemplo canónico de cómo una
herramienta publica lo que quiere dibujar:

```python
return [BandOverlay(tool_name=self.name, y_center_uv=y, height_uv=75.0)]
```

Desde el hito 7 `BandOverlay` lleva un cuarto campo obligatorio, `channel_name`,
justamente porque `Session.scale_uv()` es por canal y sin el canal la banda deja
de medir microvoltios. Copiar ese ejemplo daba `TypeError`. Se verificó
ejecutándolo, antes y después de corregirlo.

### `exporters/README.md` reintroducía una confusión que el código había eliminado

`psglab/exporters/README.md:88` decía que `statistics.py` calcula, entre otras
cosas, el "tiempo total de registro".

Esa función se llamaba `total_recording_time` y se renombró a
`scored_time_seconds()` porque con el nombre viejo `Informacion.txt` imprimía
dos números distintos que parecían el mismo, sin que nada explicara por qué no
cerraban. El docstring de `psglab/exporters/statistics.py:219` cuenta esa
historia. El README conservaba el nombre viejo y, con él, el significado
equivocado.

En la misma línea, `psglab/exporters/README.md:75` llamaba "tiempo scoreado" a
lo que el informe rotula "Tiempo abarcado por las ventanas" —el rótulo largo
existe para no llamarlo tiempo scoreado— y omitía dos secciones que el informe
siempre escribe: la frecuencia de muestreo y el listado de canales.

### Una funcionalidad prometida por dos README que no existe

`psglab/readers/README.md:85` y `psglab/ui/README.md:38` decían los dos que la
clase de canal detectada es "un punto de partida que el usuario puede corregir".

No hay forma de corregirla. `Channel` es `@dataclass(frozen=True)`
(`psglab/core/recording.py:44`), `ChannelSelector` expone `set_recording`,
`set_visible`, `toggle_kind`, `visible_channels` y `selected_channels` —ninguno
reasigna una clase— y no existe ningún `set_kind` en el paquete.

Se cambió la promesa por la limitación real, con su alcance: la clase decide
cómo se agrupan los canales en el selector y qué dice la etiqueta, no cómo se
lee ni cómo se dibuja la señal. Un canal mal clasificado se ve y se scorea
igual.

### El resto

- **`psglab/README.md:92` decía 42 módulos y son 43.** La frase se contradecía
  sola: "los 42 módulos del paquete importan —51 archivos `.py` contando los
  ocho `__init__.py`—", y 42 + 8 no da 51.
- **La convención de idioma no era la que se sigue.** Decía "identificadores en
  inglés", y medio paquete tiene identificadores internos en español a propósito
  (`_linea_debajo`, `TOLERANCIA_DE_CLIC_UV`, `_decodificar_cabecera`). La regla
  real es API pública en inglés, interior en español; ahora está escrita así.
- **El menú "Análisis" no existe.** El esquema de la ventana lo dibujaba, igual,
  en `psglab/ui/README.md:16` y en el docstring de `psglab/ui/main_window.py:6`.
  `_build_menus()` crea cuatro menús. Es de la Parte 2 y ahora está marcado como
  tal.
- **`psglab/ui/README.md:107` llamaba al hito 6 "el último de la Parte 1".**
  Después vino el 7 y el 8 sigue abierto.
- **"El medidor de ocupación y la Übersicht" son tres.** `psglab/tools/README.md:134`
  y `psglab/tools/base.py:167` nombraban dos herramientas que usan
  `on_window_changed`; falta el histograma. `psglab/core/README.md:51` ya decía
  "son tres".
- **`psglab/core/__init__.py:8` decía depender sólo de la stdlib y numpy.**
  Importa `psglab.config`, `psglab.utils.errors` y `psglab.utils.validation`.
  `psglab/core/README.md:8` lo tenía bien.
- **Dos funciones públicas sin figurar**: `get_tool()` en la fila del registro de
  herramientas y `check_index()` en la de `validation.py`, que es un tercio de
  la API de ese módulo.

### `CLAUDE.md` describe mal dos de sus propios chequeos

Es el documento con más chance de desincronizarse del test, porque su sección
"Lo que se verifica solo" es una descripción en prosa de `test_consistencia.py`
y nada la ata.

`CLAUDE.md:143` hablaba de "las **tres** cuentas de stubs de `docs/TODO.md`" y
enumeraba tres. El chequeo compara **cuatro** fuentes: el resumen del principio,
los ítems `· N stubs` de cada módulo, las filas de la tabla de progreso y la
fila de totales.

`CLAUDE.md:164` decía que cada README de carpeta declara
`Pendientes **N stubs** en M módulos` "y se verifican **los dos números**". El
segundo es opcional —el chequeo lo mira sólo si está— y hoy lo omiten tres
README: `core/`, `utils/` y `analysis/`.

---

## 3. Una fila duplicada que el chequeo no podía ver

`tests/README.md` tenía `test_occupancy.py` **dos veces** en su tabla, en dos
líneas distintas y con descripciones distintas.

El chequeo que verifica esa tabla existe y funciona, pero compara **conjuntos**:
comprueba que los nombres de las filas y los archivos del disco sean el mismo
conjunto, y un elemento repetido no cambia un conjunto. Borrar la fila repetida
no alteró la suite en nada, que es la demostración de que nunca la vio.

Se arregla cambiando el `set` por una lista y comparando también las longitudes.
Queda anotado abajo, con los demás huecos.

---

## 4. El entorno de desarrollo, roto por cuarta vez

Encontrado al empezar la auditoría, porque bloqueaba correr un solo test.

`.venv/pyvenv.cfg` había sido reescrito apuntando a una instalación nueva de
Python 3.14 en `%LOCALAPPDATA%\Python\pythoncore-3.14-64`, mientras
`site-packages` seguía con las ruedas compiladas para 3.12. El `python.exe` del
entorno no se había tocado: como carga su DLL según el `home` de ese archivo,
pasó a informar 3.14 y a no encontrar numpy.

El síntoma no menciona el entorno:

```
No module named 'numpy._core._multiarray_umath'
```

La línea `command` del propio `pyvenv.cfg` registra la causa: un
`python -m venv .venv` sobre un entorno que ya existía.

**Es la misma rotura que el README ya documentaba para WSL**, con otro
disparador. Se reparó apuntando `home` y `version` de vuelta al intérprete
original, sin reinstalar un solo paquete. El caso se agregó a los problemas
conocidos del `README.md`, que ahora documenta las cuatro formas conocidas de
romper el entorno: WSL, renombrar la carpeta, la Execution Policy y ésta.

---

## 5. Los huecos del chequeo automático

No se cerraron en esta auditoría: son trabajo de código, no de documentación, y
cada uno merece su test. Van ordenados por lo que costaría escribirlos.

**Baratos y que valen la pena:**

1. **La tabla de `tests/README.md` compara conjuntos** y no ve duplicados
   (sección 3). Cambiar a lista y comparar longitudes.
2. **`docs/EXPLICACION.txt` está fuera de `archivos_markdown()`**, así que no se
   le verifican enlaces ni párrafos repetidos ni la marca `PENDIENTE DE`. Es el
   documento que lee el cliente y el que más tardó en corregirse. Además, como
   se escribe sin acentos a propósito, el chequeo que busca "ambigüedad abierta"
   nunca podría encontrarlo: habría que normalizar acentos al comparar.
3. **No hay chequeo inverso para `docs/TRAZABILIDAD.md` ni para
   `SIN_TEST_PROPIO`.** Una fila que nombre un archivo borrado es invisible.
   `COBERTURA_DE_TESTS` y `SIN_CONTRATO` sí lo tienen.
4. **`SIN_CONTRATO` sólo valida lo que está antes de `::`**: si `clamp` se
   renombra, la exención queda muerta sin avisar.
5. **La tabla de archivos de cada README de carpeta no se verifica.** Existe el
   equivalente para `TRAZABILIDAD.md`; es casi copiar y pegar.

**Medianos:**

6. **`CAPAS_SIN_INTERFAZ` no incluye `tools/` ni `analysis/`**, aunque las dos
   carpetas declaren no conocer la interfaz y hoy lo cumplan. La regla
   documentada es más ancha que la verificada: un `import PySide6` en `tools/`
   no rompe nada.
7. **La suma de los ítems `· N stubs` del TODO no verifica nada desde que se
   cerró la Parte 1.** Todos los ítems están tachados —`· ~~4 stubs~~ ·`— y la
   expresión regular no admite las tildes de tachado, así que encuentra cero y
   compara 0 contra 0. Está dormida, no rota: vuelve a proteger en cuanto entre
   un ítem sin tachar. Se arregla tolerando `~~`.
8. **`NUMEROS_EN_PALABRAS` llega hasta "veinticinco".** Hoy son 24 los archivos
   que importan `psglab` al cargarse. Al llegar a 26 el diccionario devuelve
   `None`, el número no coincide y **la suite se pone roja con la documentación
   correcta**, sin que el mensaje explique por qué.
9. **Ningún chequeo verifica que un símbolo nombrado en un `.md` exista.** Es lo
   que dejó pasar el ejemplo roto de `BandOverlay` y las dos funciones sin
   figurar. Acotado a los identificadores que aparecen junto a una ruta
   `psglab/…`, sería escribible sin ahogarse en falsos positivos.
10. **La tabla de licencias de `docs/ARQUITECTURA.md` no se compara contra los
    `requirements`.** El job de licencias del CI mira el entorno instalado, no
    la tabla, así que una dependencia nueva la deja incompleta en silencio.

**Inherentemente manual:**

11. **`CLAUDE.md`, `README.md`, `docs/README.md` y `docs/ARQUITECTURA.md` no
    tienen ningún chequeo propio**, más allá de enlaces y párrafos repetidos.
    Son unos 900 renglones, e incluyen la descripción en prosa de los tests. Es
    donde aparecieron los dos errores de la sección 2.
12. **`contar_stubs()` mide `raise NotImplementedError`, no "implementado".** Un
    cuerpo `pass` o `...` cuenta como terminado, y de esa medición dependen
    todas las cuentas del TODO, las de los README y el chequeo de tests
    salteados.

---

## 6. Lo que se revisó y está sano

Vale tanto como los hallazgos, porque acota dónde no hay que volver a mirar.

- **Las cuentas, todas.** Ninguna de las que verifica `test_consistencia.py`
  estaba mal: stubs del TODO y de los ocho README, tests en verde, IDs del
  pliego en las dos direcciones, enlaces y anclas, ASCII de `EXPLICACION.txt`,
  capas sin Qt, type hints, párrafos repetidos.
- **Los 43 módulos declaran su `Cubre del pliego:`** y ninguno quedó fuera de
  `docs/TRAZABILIDAD.md`.
- **No queda ninguna marca `TODO`, `FIXME`, `XXX` ni `HACK` en el código.** La
  única marca pendiente es el `PENDIENTE DE DEFINICIÓN CON EL CLIENTE` de
  `psglab/analysis/impedance.py`, que está declarada a propósito y es de la
  Parte 2.
- **`psglab/utils/README.md` y `psglab/core/README.md` están limpios**, más allá
  de la omisión de `check_index()`. Las afirmaciones puntuales que hacen se
  verificaron una por una y son exactas: las seis funciones de `windows.py` que
  reciben la frecuencia, los cinco grupos de errores, los dos tests que recorren
  `errors.py` con `inspect`, las tres herramientas que dependen de
  `add_window_listener()`.
- **`psglab/tools/README.md`, fuera del ejemplo roto**, verificó exacto en todo
  lo demás: qué herramienta hereda de qué base, cuáles declaran
  `exclusive = False`, la tabla de unidades, el aviso del 3000 %, las dos ramas
  de `OCCUPANCY_COUNTS_OVERLAP_ONCE`.
- **`.gitignore` y `.gitattributes`** están completos, explicados y son
  coherentes con lo que la documentación promete sobre no versionar registros de
  participantes.
- **Los tres `requirements`** dicen la verdad sobre por qué están separados,
  incluido el techo `numpy<2.6` y su motivo.
- **El ejemplo de "cómo agregar un formato"** de `psglab/readers/README.md` sí
  compila contra la clase `Reader` real.

---

## Anexo: lo que quedó fuera del alcance

- **`psglab/analysis/`**, que es la Parte 2: ni su código ni su README. Describe
  algo que todavía no existe, así que no puede estar desactualizado respecto del
  código. Queda anotado, sin corregir, que `psglab/analysis/README.md:83` dice
  "No empezarlos antes de cerrar la Parte 1", condición que ya se cumplió.
- **`AUDITORIA.md`**, la primera. Se la dejó intacta a propósito. Conviene saber
  que su tabla "El estado real, medido" describe el 4 de septiembre —196 stubs
  en 29 módulos— y que quien la abra buscando el estado de hoy va a leer un
  número viejo. No es un error del documento: es lo que significa una foto
  fechada.
- **El hito 8**, la lista de comprobación de entrega, que va por separado.
