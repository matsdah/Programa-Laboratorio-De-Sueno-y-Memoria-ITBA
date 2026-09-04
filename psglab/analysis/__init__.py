"""Parte 2: procesamiento y métricas de la señal.

Todas las funciones de esta capa reciben un `Recording` y devuelven o bien un
`Recording` nuevo, o bien números. Ninguna modifica el registro original: el
usuario tiene que poder comparar la señal filtrada con la cruda, y volver
atrás si el filtro no fue el adecuado.

Ninguna función de acá conoce la interfaz gráfica, así que los análisis se
pueden correr también desde un script del laboratorio sin abrir el programa.

Funcionalidades futuras (fuera del alcance actual, confirmado con el cliente):
detección de potencial evocado y acoplamiento de husos de sueño. Cuando se
retomen, entran como módulos nuevos en este paquete.

Cubre del pliego: ningún ID propio del paquete. Los requisitos de la Parte 2
los cubren sus módulos, uno por sección.
"""
