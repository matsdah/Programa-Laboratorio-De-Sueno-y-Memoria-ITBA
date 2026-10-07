# `scripts/` — instalar PSGLab en WSL

En Windows 11, el Control inteligente de aplicaciones bloquea las DLL sin firma
que instala `pip` —pandas, numba, scipy— y no admite excepciones. **Dentro de
WSL corre la versión Linux del programa**, que ese control no revisa. Por qué
ésa es la salida, y no un ejecutable firmado, está en
[`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md#en-windows-se-instala-por-wsl-y-no-con-un-ejecutable-firmado).

**Nada de esta carpeta es parte del programa**: `psglab/` no la importa y la
suite de pytest no la recolecta.

| Archivo | De qué se ocupa |
|---|---|
| `install_wsl.sh` | Instala una versión de PSGLab en Ubuntu, con su venv, el lanzador y los accesos directos. Corre en Ubuntu o en Debian, dentro de WSL o no, sin `sudo`: los paquetes del sistema se instalan con `apt`. |
| `verify_install_wsl.sh` | Lo prueba escenario por escenario. Lo corre el job «Instalador de WSL» del CI. |

## Cómo se instala

Los pasos para quien instala están en el
[README del proyecto](../README.md#en-windows-sin-instalar-python-wsl). En
resumen, desde la terminal de Ubuntu:

```bash
curl -fsSL https://raw.githubusercontent.com/matsdah/Programa-Laboratorio-De-Sueno-y-Memoria-ITBA/Master/scripts/install_wsl.sh | bash
```

Correrlo de nuevo actualiza. Las opciones:

| Opción | Qué hace |
|---|---|
| `VERSION` | Instala esa versión, por ejemplo `v0.1.0`. Sin ella, la más nueva publicada, **contando las pre-releases**. Con `curl`, va como `\| bash -s -- v0.1.0`. |
| `--source DIR` | Instala desde un árbol local en vez de bajar una release. Es lo que usan el CI y quien prueba un cambio. No copia `.git`, los entornos ni `data/`. |
| `--skip-system-packages` | No corre `apt`. Sirve cuando los paquetes de Ubuntu ya están. **Dentro de WSL la contraseña se pide igual**, una vez, para publicar el acceso en el menú Inicio; si no se escribe, el instalador avisa y termina sin ese acceso. |
| `--resolve-only` | Dice qué versión instalaría y termina. |

## Si Ubuntu entra como root

El instalador se niega a correr como root, porque todo quedaría en la carpeta
de root y no en la de quien lo va a usar. **Si la terminal de Ubuntu ya
entra como root**, sin `sudo` de por medio, hace falta un usuario común. En
WSL, desde esa terminal, con el nombre que quieras en lugar de `nombre`:

```bash
adduser nombre
usermod -aG sudo nombre
printf '[user]\ndefault=nombre\n' >> /etc/wsl.conf
```

Después, en PowerShell, `wsl --terminate Ubuntu`, y al volver a abrir Ubuntu
entra con ese usuario: ahí se corre el comando de instalación. **No alcanza
con `su - nombre`**: borra las variables de WSL, y el instalador no crearía
los accesos de Windows. Fuera de WSL, sí: se entra con ese usuario y se corre
el comando.

## Qué deja y dónde

Con `BASE` = `$XDG_DATA_HOME`, que por omisión es `~/.local/share`:

| Ruta | Qué es |
|---|---|
| `BASE/psglab/<versión>.XXXXXX/` | Una versión, con el código en `app/` y su entorno en `venv/`. |
| `BASE/psglab/actual` | Enlace a la versión en uso. **Recién se cambia cuando la prueba de humo pasó**: una instalación que falla no pisa la que andaba, y la próxima buena borra lo que haya quedado a medias. **La versión anterior no se borra si PSGLab está abierto**: queda hasta la próxima instalación, y el programa abierto sigue andando hasta que se cierre. |
| `BASE/psglab/launch` | El lanzador. Entra en la carpeta de usuario de Windows, le da a Qt la escala de pantalla de Windows y abre el programa de `actual`. |
| `BASE/psglab/psglab.png` | El icono, que dibuja el programa instalado. Una versión anterior a que existiera no lo trae, y los accesos directos quedan sin icono. |
| `BASE/applications/psglab.desktop` | El acceso directo de Linux. |
| `/usr/share/applications/psglab.desktop` | Sólo dentro de WSL: una copia del anterior, con `sudo`. **WSLg publica en el menú Inicio sólo lo de esta carpeta**, como «PSGLab (Ubuntu)»: el de `BASE/applications` no apareció. Si `sudo` no anda, el instalador avisa el comando y sigue. |
| `%LOCALAPPDATA%\PSGLab\psglab.ico` y `PSGLab.lnk` en el escritorio | Sólo dentro de WSL: el acceso directo del escritorio de Windows y su icono. |

**El lanzador entra en la carpeta, y no la línea `Path=` del acceso directo**:
WSLg arma su `.lnk` con `wslg.exe --cd "~"` y esa línea no llega. Entrar en la
carpeta de usuario de Windows es lo que hace que el diálogo de apertura arranque
en las carpetas de siempre la primera vez.

**El lanzador también pone la escala.** WSLg le pasa al programa escala 1
aunque Windows esté en 125 %, y el texto salía un quinto más chico que en el
resto de Windows. En cada arranque lee la escala de Windows del registro, con
`reg.exe`, y se la da a Qt con `QT_SCALE_FACTOR`; una puesta a mano se respeta.

Las preferencias, los registros recientes y la copia de recuperación no son del
instalador: los escribe el programa en `~/.config/psglab`, como en cualquier
Linux.

## Cómo se prueba

```bash
bash scripts/verify_install_wsl.sh               # todos los escenarios
bash scripts/verify_install_wsl.sh install_once  # uno solo
```

Corre en Ubuntu, dentro de WSL o no. **Nunca toca una instalación de verdad**:
cada escenario trabaja con su propio `XDG_DATA_HOME` en una carpeta temporal de
la carpeta personal —no de `/tmp`, que en WSL es un disco en memoria de pocos
gigabytes y cada instalación ocupa más de uno—. Sin `VERIFY_SYSTEM_PACKAGES=1`
todas las instalaciones corren con `--skip-system-packages`, así que los
paquetes de Ubuntu tienen que estar instalados antes; la lista es
`PAQUETES_DEL_SISTEMA`, en `install_wsl.sh`, más `desktop-file-utils`.

## Cómo se desinstala

En Ubuntu:

```bash
rm -rf ~/.local/share/psglab ~/.local/share/applications/psglab.desktop
sudo rm -f /usr/share/applications/psglab.desktop
```

El segundo comando es el que lo saca del menú Inicio.

En Windows, borrar `PSGLab.lnk` del escritorio y la carpeta
`%LOCALAPPDATA%\PSGLab`. Las preferencias y la copia de recuperación quedan en
`~/.config/psglab` de Ubuntu, que se borra aparte si se quiere.
