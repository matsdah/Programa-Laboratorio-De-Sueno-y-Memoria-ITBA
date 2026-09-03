"""Interfaz gráfica del programa, construida con PySide6 y pyqtgraph.

Esta capa lee el estado de `psglab.core` y lo dibuja; no guarda reglas de
negocio propias. Si una regla vive acá, está en el lugar equivocado: hay que
moverla a `core/`, donde se puede testear sin abrir una ventana.

Se eligió PySide6 y no PyQt porque PyQt es GPL o comercial pago, y usarlo
obligaría a relicenciar el proyecto, que el pliego pide bajo licencia MIT.
"""
