<!-- tipo: guia · capa: 4 -->
<!-- revisado: 2026-10-12 · vence: 90d · fuente: herramientas/harness-aprender.py y sus pruebas (herramientas/tests/test_aprender.py, cli/tests/test_erp.py); cada comando se ejecutó -->

# Aprendizaje automático: lo que se aprende en un proyecto no se repite en el siguiente

Este repositorio concentra el conocimiento reutilizable. Hasta ahora subir una lección era un paso manual y por documento
(`herramientas/harness-aportar.py`). Con `harness aprender` ese camino queda **automático hasta el borde de la revisión humana**: el
harness lee las fuentes que le registraste, separa lo general de lo del negocio y deja una cola de aportes anonimizados. Lo que
entra al árbol del repositorio lo decide una persona.

## 1. Cómo funciona

```
fuentes registradas ──► partir en secciones (##) ──► clasificar ──► cola local ──► revisar ──► promover ──► árbol del harness
 (solo lectura)          cada sección con su hash     general /       (fuera del      ver /       gate + prohibidos      (commit lo
                                                      mixta / negocio  repositorio)    descartar   + escaneo público      hace una persona)
```

| Paso | Qué ocurre | Dónde queda |
|---|---|---|
| Registrar | `harness aprender fuentes agregar <nombre> <ruta> --tipo erp\|instancia\|carpeta` | `~/.config/meta-harness/fuentes.toml` (archivo del usuario, no se versiona) |
| Escanear | Lee cada documento de la fuente, lo parte por secciones `##` y clasifica cada una con la regla de `harness-aportar.py` | Cola en `~/.local/share/meta-harness/aportes/` (o `HARNESS_COLA`) |
| Revisar | `harness aprender listar` · `ver <id>` · `descartar <id> --motivo …` | El ledger recuerda lo descartado y no lo vuelve a proponer mientras la sección no cambie |
| Promover | `harness aprender promover <id> --tipo estandar --aplicar` | Copia el documento a la carpeta que corresponde al tipo; no hace commit ni push |

## 2. Por qué la cola vive fuera del repositorio

La cola contiene texto aún sin revisar y el ledger guarda de qué fuente y archivo salió cada sección. Mantenerlas **fuera del árbol**
evita que algo sin revisar se publique por un `git add -A` y que la verificación de referencias prohibidas encuentre nombres de
proyecto en un archivo de trabajo. Solo cruza al árbol lo que pasa el gate de extracción, la lista de términos prohibidos y el
escaneo de publicación, y solo con `--aplicar`.

## 3. Garantías

- **Las fuentes no se modifican.** Si la cola estuviera dentro de una fuente, el escaneo se detiene.
- **Nada se sube.** No hay commit ni push; promover deja el cambio en el árbol para que una persona lo revise y lo confirme.
- **Idempotente.** Una sección sin cambios no se reprocesa; una sección descartada no resucita; una sección cambiada reemplaza su paquete.
- **Falla abierta en silencio.** Con `--silencioso` el escaneo nunca rompe la sesión que lo disparó.
- **Lo de negocio se queda.** Una sección con términos, cifras o decisiones del negocio (según `dominio.txt` de la fuente) no se empaqueta.
- **Lo anonimizado se vuelve a evaluar.** Si tras sustituir referencias queda una sola señal, el aporte se bloquea.

## 4. El ERP central como base

Un ERP estándar que vive en su propio repositorio es la **fuente** de lo aprendido al construirlo (estándares, criterios, decisiones). Se
registra una vez:

```
harness aprender fuentes agregar erp-base <ruta-del-erp> --tipo erp
```

A partir de ahí:

1. **Entra conocimiento:** cada escaneo propone al harness las secciones generales de la documentación del ERP; al promoverlas, quedan en
   `estandares/`, `metodo/` o `perfiles/` y llegan a cada proyecto nuevo con `harness update`.
2. **Sale conocimiento al armar un proyecto:** `harness erp --negocio <carpeta>` usa por defecto el ERP registrado (no hace falta pasar
   `--erp-base`; una ruta explícita gana). Para empezar un ERP u otro tipo de proyecto **no hace falta ninguna instancia de empresa**:
   basta el ERP central y el harness.
3. **Una instancia de empresa es otra fuente**, con `--tipo instancia`. Aporta lo técnico (referencias, convenciones); lo del negocio se
   queda en ella.

## 5. Automatismo

`hooks/plantillas/stop-aprender.sh.tpl` es el hook de fin de sesión: corre `escanear --silencioso --max-frecuencia 1800` y sale siempre
con 0. Instalación y variables en la propia plantilla (`HARNESS_RAIZ`, `HARNESS_APRENDER_CADA`). El hook solo escribe en la cola.

## 6. Sincronización automática del repositorio

`herramientas/harness-sincronizar.py` es el equivalente, para este repositorio, del hook que sincroniza el repositorio privado de una
instancia: al cerrar la sesión hace commit, trae lo remoto (fetch + merge) y sube. Como el remoto de este repositorio es **público**, antes
de commitear exige una **compuerta de publicación**; si falla, no commitea ni sube nada y lo avisa con un mensaje del hook:

| Compuerta | Qué comprueba |
|---|---|
| `verificar.sh` | Sintaxis, pruebas, frescura de documentos y referencias prohibidas |
| `harness-escaneo-publico.py` | Secretos, infraestructura, personas, términos prohibidos y archivos que no deben publicarse |
| Lista de términos prohibidos | Debe existir (`.prohibidos.txt`, `HARNESS_PROHIBIDOS` o `~/.config/meta-harness/prohibidos.txt`); sin ella no se publica |

Qué NO hace: subir otras ramas (solo `main`, con refspec explícito), subir etiquetas o versiones (un release sigue siendo un acto deliberado),
forzar un push, resolver un conflicto a ciegas (aborta y deja el commit local) ni correr si la rama actual no es `main`.
`--solo-compuerta` la prueba sin commitear; `--simulacro` muestra qué haría.

## 7. Límites

- La clasificación es un **filtro de seguridad, no un juicio**. Sin `dominio.txt` en la fuente, una regla de negocio escrita en lenguaje
  corriente puede parecer técnica: el comando avisa y la revisión humana es obligatoria.
- Se parte por secciones `##`; una sección muy corta (menos de cuatro líneas de contenido) se ignora y un enlace relativo roto en el
  fragmento hace que el gate lo bloquee hasta reescribirlo.
- La etiqueta `tipo/capa` del paquete es **provisional**: la fija quien promueve (`--tipo`).
- El hook se probó ejecutando el script y con pruebas; **no se probó con cada agente real**.
- Webs de empresa: el adaptador `diseno-web` y la herramienta externa opcional siguen siendo manuales (se ofrecen, no se ejecutan solos).
