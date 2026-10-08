# Adaptadores de agente

<!-- tipo: estandar · capa: 2 -->
<!-- revisado: 2026-10-07 · vence: 60d · fuente: documentación oficial de cada agente (ver MATRIZ.md) -->

Esta carpeta contiene la **matriz de capacidades** de los agentes de programación con IA que el harness puede configurar, y (más adelante) un adaptador por agente.

## Contenido

- `MATRIZ.md`: qué soporta cada agente en 11 capacidades (instrucciones, reglas por ruta, hooks, subagentes, comandos, skills, MCP, memoria, permisos, modo no interactivo, plugins), con la ruta o el formato exacto, el estado, la URL oficial y la fecha de lectura. Incluye el «Mínimo común» y «Qué se pierde sin hooks».
- `README.md`: este archivo.

## Cómo usar la matriz

1. Antes de escribir o cambiar un adaptador, abrir la sección de la capacidad en `MATRIZ.md` y usar **solo** lo marcado «sí». Lo marcado «parcial» se usa con la salvedad anotada; lo «no verificado» **no se promete**.
2. Contrastar la ruta o el formato exacto con la URL citada (la matriz resume; la fuente manda).
3. Lo que el agente no soporta se declara **degradado** en el estado de la instalación junto con la imposición alternativa (ver «Qué se pierde sin hooks» en la matriz): permisos de la base de datos, hooks de git, protección de ramas e integración continua.
4. Si un adaptador necesita algo «no verificado», primero se verifica en la documentación oficial y se actualiza la matriz; después se escribe el adaptador.
5. Lo único que se asume portable entre agentes: un archivo de instrucciones en Markdown (`AGENTS.md`), la terminal y el formato `SKILL.md`. Hooks, reglas y comandos tienen formato propio por agente.

## Cómo se actualiza

- Fuente: **solo documentación oficial** de cada agente. No usar blogs, vídeos ni memoria.
- Por cada celda se registra: ruta o formato, estado (sí / parcial / no / no verificado), URL y fecha de lectura (aquí, la fecha de la cabecera aplica a todas las celdas, salvo que una fila indique otra).
- Una celda sin fuente oficial confirmada dice «no verificado»; nunca se rellena por lo que «suele» ser. Si una página no carga, redirige o está desactualizada, se anota en «Límites de esta lectura».
- **Vigencia: 60 días.** La cabecera `revisado` / `vence: 60d` marca cuándo se debe volver a leer la documentación. Pasado el plazo, la matriz se considera vencida: se revisa antes de generar o regenerar cualquier adaptador. También se revisa antes si se añade un agente o si un agente anuncia un cambio de formato.
- Al revisar: cambiar la fecha de `revisado`, releer las páginas listadas en «Agentes y fuentes» y mover a «sí/parcial/no» lo que se haya podido confirmar de la lista de pendientes.

## Cabecera obligatoria de todo documento del harness

Las dos primeras líneas de contenido tras el título H1:

```
<!-- tipo: estandar · capa: 2 -->
<!-- revisado: AAAA-MM-DD · vence: 60d · fuente: documentación oficial de cada agente (ver MATRIZ.md) -->
```

La fecha se obtiene con `date +%F` el día de la revisión (no se escribe a mano de memoria). En este documento y en `MATRIZ.md` la fecha de la última revisión es **2026-10-07**.
