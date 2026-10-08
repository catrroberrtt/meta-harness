# Accesos primero

<!-- tipo: herramienta · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Antes de orquestar, el instalador comprueba los accesos que ESTE caso necesita (spec §15 y §18).
Comprueba, no guarda: ni credenciales, ni escrituras en ningun recurso.

## Dos niveles de configuracion
- **Politica del proyecto** (versionada): que ambientes existen y que se permite.
- **Acceso local** (`acceso.local.toml`, por persona, **NO versionada**): como llega esta persona a
  cada ambiente (metodo, host o alias, puerto, NOMBRE de perfil). **Debe ir en el `.gitignore` de la
  instancia.** Parte de `acceso.local.ejemplo.toml`. Dos personas con accesos distintos comparten la
  misma politica.

## Uso
```
python3 instalador/preflight-accesos.py --politica politicas.toml --acceso acceso.local.toml \
    --partida A|B|C [--modo adopt|init|update|migrar] [--json] \
    [--aceptar-degradado datos --registrar <archivo fuera del proyecto>]
```
Salida: tabla Recurso - Metodo - Estado (OK / FALTA / DEGRADADO) - Que pedir.
Codigos: `0` puede orquestar; `2` falta algo requerido (se lista exactamente que); `1` error de
configuracion (por ejemplo, una politica sin ambientes: nunca se asume uno).

## Los tres puntos de partida (`--partida`)
| Partida | Exige antes de orquestar | Modo por defecto |
|---|---|---|
| **A** proyecto empezado (defecto) | Lo de §15 segun el modo: repositorios, documentacion, tickets, datos (cada ambiente no productivo de la politica), nube y, en `init`, CI. En `update`: repositorios y documentacion | `adopt` |
| **B** desde cero | **Ni datos ni nube.** Si un almacen de documentacion con la informacion de partida (carpeta con archivos, o espacio de Confluence). Datos y nube se piden cuando el plan los necesita (si estan declarados se muestran, sin bloquear) | `init` |
| **C** migracion | Lectura del sistema origen (`codigo`, `volcado`) o su **descripcion en archivos** (esquema, diccionario, hojas de calculo) en `[origen]` | `migrar` |

En B y C, sin la informacion de partida **no avanza** y dice que falta y donde ponerla (por ejemplo
la carpeta `[documentacion] carpeta` o `[origen] ruta`, con `.md`, xlsx/csv, esquemas SQL o diagramas).
En B y C la politica puede no tener ambientes todavia; en A una politica sin ambientes es un error.

## Modo degradado declarado (solo datos)
`--aceptar-degradado datos` convierte la falta de acceso a datos en `DEGRADADO`; **no aprueba en
silencio**: imprime «verificacion con datos: NO DISPONIBLE (sin acceso)», y cada gate debe mostrarla
asi. `--registrar <archivo>` deja el limite anotado; el archivo no puede estar dentro del proyecto
analizado ni de un repositorio git.

## Reglas que nunca se rompen
- Nunca se leen valores de secretos ni se escribe en un recurso. De perfiles de nube solo se leen
  NOMBRES; de variables de entorno solo si existen.
- Un campo del acceso local con aspecto de secreto (clave, token, contrasena...) se ignora y se avisa
  por nombre de campo; su valor se redacta de cualquier salida y registro.
- Toda comprobacion de red o de comandos esta detras de `Sondas`, inyectable en las pruebas.

Catalogo de recursos y metodos: `CATALOGO.md`.
