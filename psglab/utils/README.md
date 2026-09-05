# `utils/` — unidades y errores

Utilidades transversales. **Este paquete no depende de ningún otro del
proyecto**, así que cualquier capa lo puede importar sin generar un ciclo.

| Archivo | De qué se ocupa |
|---|---|
| `units.py` | Conversión de amplitudes a microvoltios. |
| `errors.py` | Todas las excepciones propias del programa. |

## `units.py` — todo el programa trabaja en µV

**La conversión se hace una sola vez, al importar el archivo.** Ninguna otra
capa vuelve a preguntarse por la unidad: si un valor viaja por `core/`, `ui/` o
`analysis/`, está en microvoltios.

Los archivos declaran su unidad de formas variadas (`uV`, `µV`, `microvolt`,
`V`, `mV`), así que la normalización es explícita y tolerante:
`normalize_unit_name()` unifica las variantes y `TO_MICROVOLTS` guarda los
factores.

`to_microvolts()` **eleva `UnknownUnitError` en vez de asumir un factor** ante
una unidad desconocida. Es deliberado: escalar mal la señal produce un scoring
incorrecto que nadie va a notar mirando la pantalla.

### Por qué µV y no mV

El pliego escribe "mV", pero su propio ejemplo dice "75mv" y el criterio de 75
sobre EEG es el clásico de amplitud de ondas lentas **en microvoltios**. En
milivoltios sería mil veces la amplitud fisiológica real. Confirmado con el
cliente: **µV**.

## `errors.py` — errores pensados para investigadores

Todas las excepciones heredan de **`PsgLabError`**, así que la interfaz captura
esa sola clase y muestra un cartel legible en vez de dejar caer una traza de
Python.

Los usuarios del programa son investigadores, con o sin experiencia en
informática: un `KeyError: 'C3'` no le sirve a nadie. Por eso cada error lleva
dos campos:

- `message` — texto en español, dirigido al usuario.
- `details` — la causa técnica, para el diagnóstico. No se muestra en el cartel
  principal, pero se registra y se puede desplegar.

```python
raise ChannelNotFoundError(
    "El registro no tiene un canal llamado 'C3'.",
    details=f"Canales disponibles: {', '.join(nombres)}",
)
```

Están agrupadas por tema: importación de archivos, canales, scoring y
anotaciones, herramientas, y análisis. **Al agregar un error nuevo, ponerlo en
su grupo** y hacerlo heredar de `PsgLabError`. Dos tests de
`tests/test_errors.py` recorren el módulo entero para que un error nuevo que se
olvide de heredar haga fallar la suite.

`PsgLabError.__init__` está implementado y no es un stub, a diferencia del resto
del esqueleto: es la base de todas las excepciones, y si el constructor fallara
ninguna de las clases de abajo podría siquiera construirse para ser elevada.

## Estado

Pendientes **4 stubs**, todos en `units.py`, en el
[hito 1 del TODO](../../docs/TODO.md#hito-1-cimientos).

`errors.py` ya está implementado y **tiene su test**
(`tests/test_errors.py`): `PsgLabError.__init__` es la base de todas las
excepciones y no debe convertirse en un stub.
