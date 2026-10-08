<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: jerarquía, nombre, tipo, peso y estados de tickets

Claves: `ticket.jerarquia`, `ticket.nombre`, `ticket.tipos`, `ticket.peso`, `ticket.estados.story`, `ticket.estados.task`, `ticket.aprobacion-previa`, `ticket.subtarea.prefijo-bloque`, `ticket.subtarea.diccionario`.

## Jerarquía (valor por defecto `una-historia-con-subtareas`)
```
{{EPICA-clave}} {{título de la épica}}                         Épica
└── {{HIST-clave}} {{marca}} {{título de la funcionalidad}}    Historia · peso {{1-10}}
    ├── {{Bloque}} · S1 {{trabajo}}                            Sub-tarea · sin peso
    └── {{Bloque}} · S2 {{trabajo}}                            Sub-tarea · sin peso
```
- [OBLIGATORIO] Una sola historia por funcionalidad; todo el trabajo como sub-tareas planas; sin cabeceras por persona ni historias por área (la carga se ve filtrando por asignado).
- QA y pase a producción no son tickets aparte: se prueban sobre la historia y su checklist entra al «Hecho cuando».
- El prefijo `S<n>` reinicia por padre. El nombre del bloque va delante.
- Si el cambio toca la base de datos: sub-tarea «Actualizar diccionario de datos» (`ticket.subtarea.diccionario`).

## Nombre, tipo y peso
- Título `{{[Marca] Título}}` (marcas en `ticket.marcas`).
- Historia: lo que ve un usuario y pasa por QA. Tarea: sin QA (infra, datos, configuración, análisis); si toca algo visible, pasa a historia.
- Peso entero {{1-10}} solo en historia o tarea, nunca en sub-tareas; se propone, define {{quien-define-el-peso}}.
- Sub-tareas de corrección: `Corrección dev: …` / `Corrección CR: …` / `Corrección QA: …`, una por observación, con qué falla, cómo reproducirlo y dónde. Nunca sub-tareas de pruebas ni de despliegue.

## Estados (sin saltar ninguno; el workflow lo impide)
- Historia: {{Por hacer → En desarrollo → Revisión en dev → Revisión de código → Listo para QA → En QA → Listo para desplegar → Terminado}}
- Tarea: {{Por hacer → En desarrollo → Revisión de código → Listo para desplegar → Terminado}}
- «Listo para QA»: ya desplegado en el ambiente de pruebas (avisar la hora). Con observaciones de QA: crear correcciones y volver a «En desarrollo». «Terminado»: ya en producción, nunca antes. Al terminar una tarea, comentario con la evidencia.

## Aprobación previa [OBLIGATORIO]
Antes de crear nada, mostrar: `título → tipo → peso → asignado → padre` y esperar OK explícito, también para un solo ticket. Antes de transicionar en lote: `ticket → estado actual → destino → por qué`, tras verificar las transiciones que ofrece cada ticket.

## Ejemplo mínimo
```
PROJ-100 Épica «Pedidos parciales»
└── PROJ-123 [Tienda] Pedidos parciales                  Historia · 5
    ├── Modelo · S1 Tabla de líneas                       Sub-tarea
    ├── Servidor · S1 Endpoint de entrega parcial         Sub-tarea
    └── Interfaz · S1 Pantalla de entrega                 Sub-tarea
```
