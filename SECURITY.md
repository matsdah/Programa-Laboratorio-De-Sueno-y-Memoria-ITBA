# Política de seguridad

PsgLab es un programa de escritorio para visualizar y scorear registros de
polisomnografía. No abre puertos, no tiene servidor y no manda nada por la red:
lo que puede salir mal está en cómo lee los archivos que se le dan y en dónde
escribe los que produce. Esta página dice qué se considera una vulnerabilidad y
cómo avisarnos sin exponerla.

## Versiones con soporte

No hay versiones publicadas. Las correcciones se hacen sobre la rama por
defecto, y lo que esté en otra rama no recibe arreglos por separado.

| Rama | Recibe correcciones de seguridad |
| --- | --- |
| `Master` | ✅ |
| Cualquier otra | ❌ |

## Cómo reportar una vulnerabilidad

**No abras un issue, una discusión ni un pull request públicos.** Usá el
reporte privado de GitHub: en la pestaña **Security** del repositorio, botón
**Report a vulnerability**, o directamente
[desde este enlace](https://github.com/matsdah/Programa-Laboratorio-De-Sueno-y-Memoria-ITBA/security/advisories/new).
Sólo lo ven quienes mantienen el proyecto.

Para que podamos reproducirlo, incluí:

- el commit o la rama en que lo encontraste (`git rev-parse --short HEAD`);
- el sistema operativo y la versión de Python;
- los pasos, desde abrir el programa o desde un script;
- qué pasó y qué debería haber pasado.

Si hace falta un archivo para reproducirlo, que sea **sintético**: armado para
la prueba, con señal generada. **Nunca adjuntes un registro de participantes**,
ni siquiera por el canal privado.

## Qué esperar

Somos un equipo chico, dentro de un proyecto académico, así que los plazos son
los que podemos cumplir y no los de una empresa:

- acuse de recibo dentro de los **7 días**;
- una evaluación —si lo consideramos una vulnerabilidad y con qué gravedad—
  dentro de los **30 días**;
- si se corrige, el aviso se publica como *security advisory* del repositorio
  una vez que el arreglo esté en `Master`, con crédito a quien lo reportó si
  así lo quiere.

## Qué entra y qué no

Cuenta como vulnerabilidad:

- **Un archivo de entrada armado a propósito** —EDF, BrainVision o un scoring
  importado— que al abrirlo ejecute código, escriba fuera de donde debe o deje
  el programa colgado o sin memoria. Los lectores están en
  [`psglab/readers/`](psglab/readers/README.md) y la mayoría delega en MNE.
- **Una escritura fuera del destino elegido**: los archivos de salida, la copia
  de recuperación o las preferencias que se guardan en el perfil del usuario
  terminando en otro lugar, o pisando algo que no son.
- **Datos de participantes en el repositorio**, en cualquier rama o en el
  historial. Esto no es un defecto del programa pero es lo más grave que puede
  pasarle al proyecto, y se reporta por el mismo canal privado, no en público.
- **Una dependencia vulnerable** que PsgLab use de una forma que la vuelva
  explotable.

No cuenta:

- una vulnerabilidad de una dependencia a la que PsgLab no llega por ningún
  camino: esa se reporta al proyecto que corresponde (MNE, PySide6, NumPy,
  SciPy…);
- lo que requiere que el atacante ya controle la cuenta del usuario o la
  máquina, porque en ese punto no necesita a PsgLab;
- la configuración de las computadoras del laboratorio.

## Lo que ya hace el repositorio

- El [CI](.github/workflows/ci.yml) corre la suite en Windows, macOS y Linux y
  falla si entra una dependencia con licencia GPL.
- [Dependabot](.github/dependabot.yml) actualiza las acciones del workflow, y
  las alertas de seguridad de las dependencias de Python están prendidas.
- CodeQL analiza el código con la configuración por defecto de GitHub.
- El [`.gitignore`](.gitignore) excluye los formatos de registro y los archivos
  de salida, para que un registro no se pueda commitear por descuido.
