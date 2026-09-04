"""Modelo de datos y reglas de negocio del programa.

Esta capa NO importa nada de `psglab.ui`. Esa restricción es deliberada: es
lo que permite testear el modelo, el scoring y las estadísticas sin abrir una
ventana gráfica, y es la base del testeo recurrente que pide el pliego
(sección 7).

Sólo depende de la biblioteca estándar y de numpy.
"""
