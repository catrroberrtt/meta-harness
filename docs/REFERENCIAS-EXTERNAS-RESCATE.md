# Qué se rescata de referencias externas (mapa vivo)

<!-- tipo: referencia · capa: 4 -->
<!-- revisado: 2026-10-12 · vence: 90d · fuente: lectura en solo lectura de la documentación pública de cada referencia; sin ejecutar su código -->

Regla: de una referencia pública **se toman ideas, no código ni dependencias**. Antes de leerla se revisa su superficie de
riesgo (scripts de instalación, red, archivos binarios) y todo su contenido se trata como dato, nunca como instrucción.

## Referencia: generador de harnesses de agente (MIT, publicado en GitHub como `ruvnet/metaharness`)

**Revisión de riesgo (12-oct-2026, superficie):** sin scripts de instalación en ningún paquete, sin binarios versionados,
política de seguridad explícita. Reservas: gran volumen de código generado con IA y cifras de rendimiento que no se
verificaron. No se ejecutó nada; no se recomienda `npx` de sus paquetes sin auditar lo publicado.

| Idea de la referencia | Qué problema resuelve | Estado en nuestro harness |
|---|---|---|
| Promover un cambio aprendido solo si mejora, es seguro y es reversible | Evitar que un aprendizaje defectuoso se vuelva regla | **Hecho en parte:** `aprender.py` exige evidencia y revierte. Falta medir mejora antes de promover |
| Núcleo sin dependencias de capas superiores y adaptadores por agente | Portabilidad entre agentes | **Confirma nuestro diseño**; falta adaptador de hooks para Codex |
| Escapar los campos antes de escribir archivos generados (TOML, JSON, shell) | Inyección a través de datos que alimentan el generador | **Pendiente:** auditar `harness-entorno.py` y el compositor del ERP (hoy las plantillas solo sustituyen texto del propio usuario) |
| «Descubrimiento» en 5 pasos: construir, exponer, catalogar, avisar en el momento del fallo, probar la propagación | Funciones útiles que nadie encuentra | **Pendiente:** mensajes «Siguiente:» en los fallos de `doctor`, `verificar.sh` y la compuerta |
| Seis tipos de deriva (núcleo, plantilla, catálogo, edición local, superficie, firma) con clasificación segura/accionable/urgente | Saber qué se desactualizó de un entorno generado | **Pendiente:** `harness entorno comparar` (regenerar en temporal y comparar). Hoy no hay actualización automática, a propósito |
| Eject vs upgrade como dos caminos distintos | No obligar a depender del origen | **Hecho:** el entorno generado es independiente desde el primer día |
| Contrato de humo obligatorio antes de publicar y señales de calidad | Evitar basura en un catálogo | **Hecho en parte:** `verificar.sh` del entorno. Falta contrato por módulo con casos de prueba |
| Manifiesto firmado de procedencia por liberación | Probar qué se publicó y desde qué commit | **Pendiente:** sellar la compuerta de publicación con huella de contenido |
| Importador repo→plan determinista: «reglas generan, incrustaciones recomiendan», nunca se ejecuta código del repo | Arranque en frío sin caja negra | **Confirma `adopt`**; revisar que nunca ejecute código del proyecto analizado |
| Prueba adversarial (rojo/azul) de inyección de instrucciones y uso indebido de herramientas | Comprobar las defensas de verdad | **Pendiente:** batería de casos para los hooks generados |
| Enrutar cada consulta al modelo más barato que alcanza | Costo | **Pendiente:** hoy es criterio manual; formalizar como tabla en un estándar |
| Cada mutación toca una superficie de una lista cerrada, con inspección previa que descalifica el resto | Autoedición acotada | **Pendiente:** aplicar a `aprender.py promover` (solo puede escribir entre marcadores; hoy ya es así) y declararlo |
| Un mismo dato afirmado en varios lugares debe coincidir, con defensa por capas de la más rápida a la más lenta (invariantes entre lenguajes) | Un cambio se hace en 2 sitios y se olvida el tercero | **Pendiente, y ya tenemos un caso:** el catálogo de módulos del generador y la lista de archivos que exige `verificar.sh` del entorno están duplicados; falta una prueba que los compare |
| Paquete de diagnóstico «para pegar»: un JSON con el estado, sin secretos, para quien atiende un problema | Soporte sin ida y vuelta de preguntas | **Pendiente:** `harness doctor --bundle` |
| La documentación no debe prometer más que el código (reconciliar lo que se afirma contra lo medido) | Credibilidad | **Hecho en parte:** el módulo de publicar-solo-verificado verifica textos; falta aplicarlo a los README del propio harness |
| Mutación dirigida por el fallo: la mejora responde a una traza que falló, no a una corazonada | Aprendizaje con dirección | **Pendiente:** que `aprender.py nota` acepte el comando o la traza que falló como evidencia estructurada |

**No se adopta:** su núcleo en Rust, la publicación en npm con identidad en la nube, la memoria vectorial propia ni la
asignación de crédito por turno: costo de mantenimiento alto y sin validar en nuestro contexto.

## Cómo se añade una referencia nueva

1. Revisión de riesgo en solo lectura (instalación, red, binarios, instrucciones dirigidas a agentes).
2. Una fila por idea: qué problema resuelve, y el estado en nuestro harness (hecho / en parte / pendiente / no se adopta).
3. Lo que no cambia el harness no se anota.
