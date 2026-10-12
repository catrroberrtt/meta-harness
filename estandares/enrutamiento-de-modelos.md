# Enrutamiento de modelos: cada tarea al modelo más barato que cumple la vara

<!-- tipo: estándar técnico · capa: 2 -->
<!-- revisado: 2026-10-12 · vence: 90d · fuente: criterio de trabajo con agentes, sin cifras de rendimiento propias; la tabla se calibra con la medición de abajo -->

Elegir el modelo es una decisión de **costo y riesgo**, no de gusto. Este estándar fija cómo decidirlo y cómo comprobar que la decisión fue buena.
Independiente del proveedor: se habla de niveles (pequeño, medio, grande), no de productos.

## Principio

> La tarea se envía al **nivel más barato que supera la vara de calidad**, y se **escala solo cuando la prueba falla**, no por intuición.

Dos cosas no se negocian: **el riesgo manda sobre el precio** (dinero, seguridad y datos personales nunca bajan de nivel solo por ahorrar) y **todo lo
delegado se verifica por alguien que no es quien lo hizo**.

## Tabla de partida

| Tipo de tarea | Nivel de partida | Cuándo escalar | Quién verifica |
|---|---|---|---|
| Cambio **mecánico y ya identificado** (renombrar, mover, ajustar estilos, formatear, completar plantillas) | Pequeño | La primera vuelta no pasa las pruebas o toca más archivos de los previstos | Las pruebas y un diff revisado |
| **Búsqueda y lectura** acotada (localizar dónde se usa algo, resumir un archivo) | Pequeño | El resultado contradice el código al contrastarlo | Se contrasta una muestra contra el código |
| **Investigación y diagnóstico** (por qué falla, qué documentación aplica) | Medio | No encuentra la causa tras dos intentos con evidencia distinta | Quien decide repite una comprobación clave |
| **Implementación** con diseño ya aprobado | Medio | Las pruebas fallan por una decisión de diseño, no por un detalle | Pruebas automáticas y revisión del diff |
| **Diseño**, arbitraje entre alternativas, cambios de arquitectura | Grande | — | Revisión humana de la decisión |
| **Revisión independiente** de un cambio ajeno | Medio o grande, **distinto** del que lo escribió | — | Es la verificación |
| Cualquier cosa que toque **dinero, permisos, seguridad o datos personales** | Grande, sin bajar por costo | — | Revisión humana más prueba específica |

## Reglas

1. **Prompt autocontenido.** Un modelo delegado no ve la conversación: se le da el objetivo, los archivos exactos, lo que no debe tocar y cómo se sabe que terminó.
2. **Una unidad de trabajo, un dueño.** Dos modelos no editan los mismos archivos a la vez.
3. **Sin permiso de salida.** Quien recibe una tarea mecánica no commitea, no sube, no publica ni crea cosas hacia afuera: devuelve el cambio.
4. **El nivel de la sesión principal no se cambia desde dentro.** Se decide al empezar; lo barato se delega a un subagente de nivel menor.
5. **Escalar deja rastro.** Si una tarea subió de nivel, se anota por qué (prueba que falló); esa es la información que ajusta la tabla.

## Cómo calibrar la tabla (medirla, no suponerla)

Con 10 tareas reales de cada tipo, resueltas por cada nivel:

| Medida | Cómo se obtiene |
|---|---|
| Tasa de aprobación | Cuántas pasan la vara (pruebas y revisión) en el primer intento |
| Costo por tarea aprobada | Costo total del nivel dividido entre las aprobadas, no entre las intentadas |
| Reintentos | Cuántas necesitaron más de una vuelta |

Se baja el nivel de un tipo de tarea cuando el nivel menor aprueba **casi tantas** y cuesta **claramente menos por tarea aprobada**. Se sube cuando
la tasa del nivel actual no alcanza la vara. Una tabla sin medición es una opinión: revísala cada trimestre con datos nuevos.

## Qué no cubre

No fija precios ni modelos concretos (cambian rápido). No decide cuándo una tarea necesita un humano: eso lo marcan las reglas de seguridad del proyecto.
