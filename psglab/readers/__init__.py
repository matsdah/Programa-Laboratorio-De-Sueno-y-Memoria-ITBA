"""Importación de archivos de registro polisomnográfico.

Cada formato vive en su propio archivo y se registra en `base.py`. Agregar
un formato nuevo es agregar un archivo acá y registrarlo: no hay que tocar
`main.py` ni la interfaz. Eso es lo que hace escalable la importación, que es
uno de los objetivos centrales del pliego ("cualquier formato de archivo de
registro de polisomnografía").

Cubre del pliego: ningún ID propio del paquete. Cada formato lo cubre su
módulo.
"""
