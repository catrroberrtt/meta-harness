# Acceso a GitHub (paso a paso)

<!-- tipo: herramienta · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Herramienta: `instalador/acceso-github.sh` (envoltorio de `instalador/acceso_github.py`).
Por defecto es **modo plan**: solo muestra lo que haria. Con `--aplicar` recorre los pasos y **pide confirmacion en cada uno**.

```
instalador/acceso-github.sh                      # plan
instalador/acceso-github.sh --aplicar --repositorio <url> --salida <carpeta>
```

## Que hace
1. **`gh`**: si falta, detecta el gestor de paquetes (apt, dnf, yum, pacman, zypper, brew, winget, choco), muestra el comando completo y lo ejecuta solo si confirmas; si necesita administrador lo dice y lo pide aparte. Sin gestor o si dices no, imprime como hacerlo a mano.
2. **Sesion**: comprueba `gh auth status`. Sin sesion, y con tu confirmacion, ejecuta `gh auth login --hostname github.com --git-protocol ssh --web --skip-ssh-key` **en esta misma terminal** (solo con las banderas que tu `gh` liste en `--help`; en WSL, `BROWSER` apunta a `wslview` o `explorer.exe` si existen). Tu apruebas el codigo y la URL en el navegador. Si dices que no, te indica hacerlo tu en el MISMO sistema (una sesion de PowerShell no vale en WSL).
3. **Metodo**: SSH (por defecto) o HTTPS por `gh` (`gh auth setup-git`).
4. **Llave SSH**: reutiliza una existente (ed25519, ecdsa o RSA de al menos 3072 bits). Si no hay, propone `ssh-keygen -t ed25519` en una ruta que no existe (nunca sobrescribe), deja que `ssh-keygen` te pida la frase de contrasena (recomendada), la añade al `ssh-agent` y registra **solo la publica** con `gh ssh-key add` y el titulo `<maquina> <fecha>`, mostrando titulo y huella antes. Si ya esta registrada, no la duplica.
5. **Permisos y SSO**: si falta `admin:public_key`, propone `gh auth refresh -s admin:public_key`. Si la organizacion exige SSO, explica que la llave debe autorizarse (GitHub → Settings → SSH and GPG keys → Configure SSO) y se detiene.
6. **Huella del servidor**: antes de aceptar `github.com` en `known_hosts`, compara la huella que presenta el servidor con las oficiales (`gh api meta`). Si no coinciden o no se pueden obtener, no acepta.
7. **Verificacion**: `ssh -T git@github.com` y, con `--repositorio`, `git ls-remote` (sin pedir credenciales). Si falla, clasifica la causa (sin llave, sin permiso en el repositorio, sin SSO, red) y dice que pedir y a quien.
8. Ofrece configurar nombre y correo globales de git **solo si faltan y lo aceptas**.

Registro: `<salida>/acceso-github.log` con acciones y resultados, sin secretos (solo en modo `--aplicar`).

## Que NO hace
- No lee, imprime ni copia una llave privada (solo abre archivos `.pub`).
- No ve ni guarda contrasenas, frases ni tokens; no pasa tokens por argumentos; no imprime URLs con credenciales (las rechaza).
- No ejecuta `curl | sh`, ni instala o usa administrador sin tu confirmacion.
- No sobrescribe llaves, no toca la configuracion global de git sin tu aceptacion.
- No acepta la huella de `github.com` sin compararla con las oficiales.
- En modo plan no ejecuta ningun comando ni escribe nada.

## Que necesita la persona
- Una cuenta de GitHub y poder iniciar sesion con `gh auth login`.
- Permiso de la sesion de `gh` para gestionar llaves (`admin:public_key`); el programa propone ampliarlo.
- Para repositorios de una organizacion: pertenecer a ella con acceso de **lectura** al repositorio (lo da quien lo administra) y, si la organizacion usa SSO, **autorizar la llave** para ella.
- Permisos de administrador en su maquina solo si instala `gh` con un gestor que lo requiere.
- Red hacia github.com (puerto 22 para SSH; si esta bloqueado, usar HTTPS).

## Codigos de salida
0 listo · 1 uso incorrecto · 2 detenido (falta algo que debe dar o hacer otra persona) · 3 cancelado.
