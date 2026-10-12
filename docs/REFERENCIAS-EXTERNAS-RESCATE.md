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
| Promover un cambio aprendido solo si mejora, es seguro y es reversible | Evitar que un aprendizaje defectuoso se vuelva regla | **Hecho:** `aprender.py` exige evidencia, revierte y, con `--falla`, solo promueve si el comando que falló ahora pasa |
| Núcleo sin dependencias de capas superiores y adaptadores por agente | Portabilidad entre agentes | **Hecho:** `.codex/hooks.json` con los mismos hooks (formato documentado de Codex; sin probar contra Codex real) |
| Escapar los campos antes de escribir archivos generados (TOML, JSON, shell) | Inyección a través de datos que alimentan el generador | **Hecho en el generador de entornos y en 12 validadores del harness** (se encontraron y corrigieron 2 fallos reales). Falta auditar el compositor del ERP |
| «Descubrimiento» en 5 pasos: construir, exponer, catalogar, avisar en el momento del fallo, probar la propagación | Funciones útiles que nadie encuentra | **Hecho en el entorno generado** (verificar, compuerta, secretos, publicación, frescura, búsqueda) con prueba de propagación. Falta en `harness doctor` |
| Seis tipos de deriva (núcleo, plantilla, catálogo, edición local, superficie, firma) con clasificación segura/accionable/urgente | Saber qué se desactualizó de un entorno generado | **Hecho:** `harness entorno --comparar` (tres vías, lock con hashes) y `--aplicar-seguras`. No hay actualización automática, a propósito |
| Eject vs upgrade como dos caminos distintos | No obligar a depender del origen | **Hecho:** el entorno generado es independiente desde el primer día |
| Contrato de humo obligatorio antes de publicar y señales de calidad | Evitar basura en un catálogo | **Hecho:** `verificar.sh` del entorno exige los archivos de cada módulo, y una prueba compara ese catálogo con el generador |
| Manifiesto firmado de procedencia por liberación | Probar qué se publicó y desde qué commit | **Hecho (versión ligera):** cada commit automático anota el árbol sobre el que pasó la compuerta; `--comprobar-sellos` detecta contenido cambiado después. Sin firma criptográfica (ver «No se adopta») |
| Importador repo→plan determinista: «reglas generan, incrustaciones recomiendan», nunca se ejecuta código del repo | Arranque en frío sin caja negra | **Confirma `adopt`**; pendiente revisar que nunca ejecute código del proyecto analizado |
| Prueba adversarial (rojo/azul) de inyección de instrucciones y uso indebido de herramientas | Comprobar las defensas de verdad | **Hecho:** batería adversarial sobre los hooks y scripts generados y sobre los hooks reales del entorno del equipo (se encontraron huecos reales) |
| Enrutar cada consulta al modelo más barato que alcanza | Costo | **Hecho:** `estandares/enrutamiento-de-modelos.md` (tabla de partida y forma de medirla) |
| Cada mutación toca una superficie de una lista cerrada, con inspección previa que descalifica el resto | Autoedición acotada | **Hecho:** `promover` solo escribe entre marcadores y la nota se valida (una línea, sin marcadores) |
| Un mismo dato afirmado en varios lugares debe coincidir, con defensa por capas de la más rápida a la más lenta (invariantes entre lenguajes) | Un cambio se hace en 2 sitios y se olvida el tercero | **Hecho:** pruebas que comparan el catálogo con `verificar.sh`, los hooks declarados y las plantillas |
| Paquete de diagnóstico «para pegar»: un JSON con el estado, sin secretos, para quien atiende un problema | Soporte sin ida y vuelta de preguntas | **Hecho:** `harness doctor --bundle` (sin secretos ni rutas personales, con prueba de fugas) |
| La documentación no debe prometer más que el código (reconciliar lo que se afirma contra lo medido) | Credibilidad | **Hecho:** `test_docs.py` comprueba que las rutas, herramientas, subcomandos y módulos que cita la documentación existen |
| Mutación dirigida por el fallo: la mejora responde a una traza que falló, no a una corazonada | Aprendizaje con dirección | **Hecho:** `--falla` registra el comando y su código de salida como evidencia estructurada |

**No se adopta el componente, sí la idea ligera:**

| Componente de la referencia | Qué se hizo en su lugar |
|---|---|
| Núcleo en Rust compilado a WASM | Nada que compilar. Se conserva la **frontera** («el núcleo no importa de capas superiores») como prueba: los scripts de un entorno solo usan la biblioteca estándar |
| Publicación en npm con identidad en la nube y firma criptográfica de cada liberación | **Sello de contenido** (id del árbol de git en cada commit automático) sin gestión de claves. La firma criptográfica queda fuera: exige custodiar una clave y no la necesitamos hoy |
| Memoria vectorial propia (incrustaciones, decaimiento, cuarentena) | Nada. `buscar-documentacion.py` busca por texto y el conocimiento se indexa a mano; una memoria vectorial es un sistema que mantener sin evidencia de que haga falta |
| Asignación de crédito por turno de una trayectoria | **Evidencia estructurada** de la lección (`--falla`): el comando que falló y su código, y la comprobación al promover |

## Cómo se añade una referencia nueva

1. Revisión de riesgo en solo lectura (instalación, red, binarios, instrucciones dirigidas a agentes).
2. Una fila por idea: qué problema resuelve, y el estado en nuestro harness (hecho / en parte / pendiente / no se adopta).
3. Lo que no cambia el harness no se anota.
