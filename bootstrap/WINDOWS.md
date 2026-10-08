# meta-harness en Windows

<!-- tipo: guia · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Los scripts de meta-harness son de Linux. En Windows corren dentro de **WSL2 con Ubuntu**, no en PowerShell ni en las carpetas de Windows. El script `instalar.ps1` prepara eso y lanza por ti el comando de Linux.

## Requisitos

- Windows 10 (versión reciente) o Windows 11, con virtualización activada en la BIOS.
- Conexión a internet.
- Para instalar Ubuntu por primera vez: PowerShell como administrador (solo ese paso).
- Nada de credenciales: el script no pide ni guarda ninguna.

## El comando

En PowerShell (también sirve Windows PowerShell 5.1, que no entiende `&&`; por eso el script no lo usa):

```powershell
irm https://raw.githubusercontent.com/catrroberrtt/meta-harness/main/bootstrap/instalar.ps1 | iex
```

Con opciones (descárgalo y ejecútalo con `-File`):

```powershell
irm https://raw.githubusercontent.com/catrroberrtt/meta-harness/main/bootstrap/instalar.ps1 -OutFile instalar.ps1
powershell -ExecutionPolicy Bypass -File .\instalar.ps1 -Instancia owner/nombre -Version X.Y.Z
```

Parámetros: `-Instancia owner/nombre`, `-Distribucion` (por defecto `Ubuntu-24.04`), `-Version` (por defecto la última), `-Si` (no preguntar) y `-SoloPlan` (muestra el plan y no cambia nada). Empieza siempre con `-SoloPlan` si dudas.

## Qué verás

1. El **PLAN** completo: si `wsl.exe` existe, qué distribución usará, la URL y la versión que se ejecutarán.
2. Una pregunta `[S/N]` antes de cada acción que cambia el sistema.
3. Si falta Ubuntu: la instalación con `wsl --install -d Ubuntu-24.04`.
4. La primera vez, Ubuntu te pide crear un usuario y una contraseña de Linux. Esa contraseña es solo de Ubuntu; no se muestra al escribirla. Cuando termines, pulsa Enter en PowerShell.
5. Comprobaciones dentro de Ubuntu (`python3`, `git`, `curl`) sin cambiar nada.
6. El comando de Linux, desde el directorio personal de Linux (nunca desde las carpetas de Windows). Puede pedir `sudo` y abrir el inicio de sesión de GitHub.
7. Avisos finales (Docker Desktop y `claude`).

## Si falla

- **No existe `wsl`** (`wsl.exe: NO encontrado`): abre PowerShell como administrador, ejecuta `wsl --install -d Ubuntu-24.04`, reinicia y repite el comando. Si el comando no existe, actualiza Windows.
- **No eres administrador**: el script no intenta instalar. Abre PowerShell como administrador (menú Inicio, escribe PowerShell, clic derecho, Ejecutar como administrador) y vuelve a ejecutar el mismo comando.
- **Falta Ubuntu**: acepta la instalación cuando el script la proponga (necesita administrador). Alternativa manual: `wsl --install -d Ubuntu-24.04`.
- **Reinicio pendiente**: si tras instalar la distribución todavía no aparece, debes reiniciar Windows, abrir Ubuntu desde el menú Inicio para crear tu usuario y volver a ejecutar el mismo comando.
- **`docker-desktop` es la única distribución**: es interna de Docker y no sirve. El script la ignora y propone instalar Ubuntu. No la borres.
- **Python < 3.12**: Ubuntu 24.04 trae 3.12. Si ves una versión menor, usa `-Distribucion Ubuntu-24.04` o instala Python 3.12 dentro de Ubuntu. El comando de Linux instala lo que falte con una confirmación de administrador (sudo).
- **La comprobación `wsl -d <distro> -- echo ok` falla**: abre Ubuntu desde el menú Inicio, termina de crear el usuario y repite.

## Avisos

- Docker Desktop necesita activar la integración con WSL para usar `docker` dentro de Ubuntu.
- El `claude` de Windows no es el de Ubuntu: el agente se instala por separado en cada sistema.
