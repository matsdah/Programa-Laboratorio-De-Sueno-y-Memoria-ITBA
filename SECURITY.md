# Política de seguridad

Esta página dice qué se considera una vulnerabilidad y cómo avisar sin exponerla.

| Rama | Recibe correcciones de seguridad |
| --- | --- |
| `Master` | ✅ |
| Cualquier otra | ❌ |

## ¿Cómo reportar?

Usá el reporte privado de GitHub: en la pestaña **Security** del repositorio, botón
**Report a vulnerability**, o directamente
[desde este enlace](https://github.com/matsdah/Programa-Laboratorio-De-Sueno-y-Memoria-ITBA/security/advisories/new).
Así sólo lo ven quienes mantienen el proyecto.

## ¿Qué cuenta como vulnerabilidad?

- **Un archivo** —EDF, BrainVision o un **scoring
  importado**— que al abrirlo ejecute código, escriba fuera de donde debe o deje
  el programa colgado o sin memoria. Los lectores están en
  [`psglab/readers/`](psglab/readers/README.md) y la mayoría delega en MNE.
- **Datos reales de participantes en el repositorio**, en cualquier rama o en el
  historial.
- **Una dependencia vulnerable** que la aplicación use de una forma que la vuelva
  explotable.

## Lo que ya se hace

- El [CI](.github/workflows/ci.yml) corre la suite completa en Windows, macOS y Linux y
  falla si entra una dependencia con licencia GPL.
- [Dependabot](.github/dependabot.yml) actualiza acciones del workflow y
  las alertas de seguridad de las dependencias de Python.
- CodeQL analiza el código con la configuración por defecto de GitHub.
- El [`.gitignore`](.gitignore) excluye los formatos de registro para que
- un registro no se pueda commitear por descuido.
