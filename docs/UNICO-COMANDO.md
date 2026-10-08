# Un solo comando: de una máquina limpia a una instancia lista

<!-- tipo: herramienta · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

```sh
curl -fsSL <url>/bootstrap/instalar.sh | sh -s -- --instancia owner/nombre
# o, si ya tienes el comando:
harness instalar owner/nombre
```

Sustituye los cuatro pasos manuales (arranque público, `acceso-github.sh --aplicar`, `harness instalar`, `restaurar-entorno.sh --aplicar`). La lógica vive en `instalador/orquestador.py`; el script de arranque solo instala `harness` y le pasa el relevo (reconectando la entrada a la terminal, porque `curl | sh` consume stdin).

## Flujo

1. **Un plan inicial** (nada se ha escrito): instancia, carpeta, qué falta, y los pasos siguientes. Una confirmación (`--si` la salta).
2. **Paquetes**: si faltan `git`, `python3`, `ssh` o `gh` (como programas de **Linux**), un único `sudo apt update && sudo apt install -y <faltantes>` con **una** confirmación de administrador.
3. **Acceso a GitHub** (`acceso_github.py`): `gh auth login --hostname github.com --git-protocol ssh --web --skip-ssh-key` **en esta misma terminal** (muestra el código de un solo uso y la URL; en WSL, `BROWSER` apunta a `wslview` o `explorer.exe` si existen). Las banderas que tu versión de `gh` no liste en `gh auth login --help` se omiten. Luego llave SSH propia (se reutiliza o se crea; solo se registra la pública), huella de `github.com` contra las oficiales y verificación.
4. **Clonar** la instancia. Con `harness.lock` se fija la versión (`update`); sin él (instancia anterior al instalador) no se ejecuta `update`.
5. **Entorno de la instancia**:
   - si trae `.harness/entorno.toml` (contrato en `ENTORNO-INSTANCIA.md`): se valida entero **antes** de ejecutar nada; luego prerrequisitos, repositorios y pasos;
   - si no, y trae `scripts/restaurar-entorno.sh`: se muestra su **plan** (sin `--aplicar`), un resumen de hasta 12 líneas, **una** confirmación y se ejecuta con `--aplicar` en modo interactivo (el script pregunta lo suyo sobre la red);
   - si no hay ninguno, termina bien y lo dice.
6. **`harness doctor`** y el resumen **hecho / omitido / pendiente de ti**, con el comando exacto de cada pendiente.

## Qué pregunta siempre (aunque uses `--si`)

Administrador (`sudo`), inicio de sesión de `gh` en el navegador, clonar los repositorios que piden confirmación, pasos con `red = true` o `pesado = true`, y `scripts/restaurar-entorno.sh --aplicar`. `--si` solo salta el plan inicial y las preguntas de bajo riesgo (pasos sin red ni peso con `por_defecto = "preguntar"`). Sin terminal, lo delicado queda como **pendiente** con su comando.

## Casos de una máquina real (Windows + WSL2 + Ubuntu limpia)

| Caso | Qué hace |
|---|---|
| Directorio actual en `/mnt/c/...` | Avisa y trabaja en `~` (la carpeta por defecto pasa a `~/<nombre>`). |
| Listas de apt vacías | `apt update` va dentro del mismo comando consolidado. |
| `npm`, `docker`, `gh`... solo en el PATH de Windows | Los ignora y avisa «solo existe como programa de Windows» (en WSL, rutas `/mnt/<unidad>/`). |
| `gh auth login` hecho en PowerShell | Ya no hace falta: lo ejecuta el propio programa en la misma terminal. |
| Instancia sin `harness.lock` | Se clona sin `update`. |
| `curl \| sh` | Las preguntas se leen de `/dev/tty`; el relevo reconecta stdin a la terminal. |

## Reanudar

El avance se guarda en `${XDG_STATE_HOME:-~/.local/state}/meta-harness/instalar-<owner>-<nombre>.json` (permisos 600): solo nombres de pasos hechos y la carpeta de la instancia; nunca secretos, tokens ni rutas de llaves. Repetir el mismo comando salta lo hecho y dice qué retoma. Borrar el archivo reinicia.

## Qué nunca hace

- Instalar, restaurar o clonar bases de datos (clientes, contenedores, respaldos, túneles, SSO de datos). El resumen incluye siempre el bloque «Acceso a datos (lo das tú)».
- Ejecutar `sudo` sin confirmación (la contraseña la escribes tú; el programa no la ve).
- Imprimir o guardar tokens, llaves privadas o URLs con credenciales (se descartan del argumento).
- Ejecutar comandos de la instancia mediante shell: los `[[pasos]]` son listas.
- Saltarse una confirmación delicada por `--si`.
- Tocar `/mnt/<unidad>` ni sobrescribir llaves o carpetas existentes.

Códigos de salida: 0 todo hecho u omitido a propósito · 2 detenido o quedan pendientes tuyos · 3 sin permiso en la instancia · 4 fallo. `harness instalar owner/nombre --plan` solo muestra el plan; `--solo-clonar` conserva el flujo corto anterior.
