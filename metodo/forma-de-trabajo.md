<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Forma de trabajo

Cómo se trabaja y cómo se muestra el trabajo. Aplica a toda tarea que cambie código, datos o documentación. Los formatos están en `plantillas/`; los valores, en las convenciones de la instancia.

## 1. Intake antes de proponer
- Primero se consulta el conocimiento previo: índice, módulo afectado y sus relacionados, la entrada más reciente de implementaciones del tema y sus revisiones de QA, y los patrones de calidad que lo citen.
- No se propone ni se diseña hasta haber preguntado **solo lo que falte** (`plantillas/intake.md`): objetivo y consumidor, módulo y ruta, qué reutilizar, datos y tablas, reglas y volumen, lectura o escritura, quién llama.
- Si la persona no sabe una ruta: búsqueda dirigida y confirmar; nunca un rastreo general.
- Si el cambio itera un tema con QA previa, se revisa su checklist (incluidos los ítems abiertos) antes de planificar.
- Cada pregunta dice qué se intentó y por qué no alcanza. Solo llegan a la persona las decisiones de negocio y lo que exige un acceso que no hay.

## 2. Mapa de reutilización
Antes de proponer, para cada concepto de dominio:

| Concepto | Qué existe (ruta verificada) | Reutiliza / extiende / crea | Por qué |
|---|---|---|---|

- Se lee completo el flujo existente más parecido; se pregunta quién más lee o escribe cada entidad que el cambio toca.
- Si el cambio es una variante de otro flujo, cada regla de ese flujo se decide por escrito (aplica / no aplica, porque… / pendiente de negocio).
- Lo que existe en otro repo o plataforma no se da por pendiente ni por inexistente sin comprobarlo allí.
- Es lo primero que se aprueba del plan.

## 3. Documentación antes del código (cambios M y L)
Hoja padre y páginas con detalle completo, aprobadas, antes de ramas y código (`documentacion.completa-antes-de-codificar`). La copia local es la fuente; la publicada se verifica. Un ticket se abre con el bloque de cuatro puntos (`plantillas/apertura-de-cambio.md`) y **no se cierra a medias**.

## 4. Plan por capas con aprobación por fase
El plan (`plantillas/plan.md`) vive en la raíz del repo y no se borra. Se llena por capas o fases; al cerrar cada una se pregunta qué ajustar o si se aprueba. **No se avanza de fase sin OK.** El formato de una respuesta es provisional hasta validar la consulta de datos que la respalda.

## 5. Manifiesto de archivos con OK explícito
Última puerta: lista de cada archivo nuevo o modificado con su contenido y el orden de creación. **Sin OK explícito no se escribe código.**

## 6. Diseño frente a implementación
Antes de maquetar y otra vez antes de cerrar, se llena `plantillas/mapeo-diseno.md` mirando la pantalla real. Prioridad cuando chocan: observaciones de QA, luego el estilo del producto, luego el diseño. Una interfaz se prueba en el navegador antes de entregarla.

## 7. Gate de salida
- Orden fijo (`plantillas/checklist-entrega.md`); no es opcional ni a criterio del momento.
- El agente ejecuta build y pruebas acotados y pega resultado y código de salida; sin eso no se dice «build OK».
- Se releen las reglas, no se recuerdan.
- Tras corregir un bug con causa generalizable: patrón nuevo y barrido por la misma firma en el resto del módulo.
- Se apagan los procesos levantados y se limpian los datos de prueba.
- Ciclo de verificación antes de responder (`verificacion.topes`):

| Pregunta | Revisar en este orden (cortar al tener evidencia) | Tope |
|---|---|---|
| ¿Qué falta o en qué quedamos? | estado del tema (git, PR abiertos, QA abierta) → todos los documentos del tema → historial del archivo citado | {{n}} acciones |
| ¿Existe o cómo funciona X? | índice de conocimiento → módulo → búsqueda semántica → código en la rama validada | {{n}} |
| Cifra, monto, conteo | consulta directa (con origen y fecha) → perfil de columnas → verificación de cifras | {{n}} |
| ¿Está listo? | gate → lint → evidencia de datos | {{n}} |
| Bug u observación de QA | QA previa del tema → patrones → reproducir → historial (¿ya corregido?) | {{n}} |

Los topes se fijan de antemano y se suben por tipo, no en general.

## 8. Informes con evidencia
- Toda afirmación de estado («existe», «falta», «listo», «pendiente») lleva su evidencia o va marcada «no verificado».
- Ningún veredicto sin evidencia de datos: `plantillas/evidencia-datos.md`, con «qué NO prueba» obligatorio.
- Números y estados se citan desde su fuente primaria, con fecha; un aviso del motor no se ignora.
- Un hallazgo no se llama alarma sin pasar alcance, vigencia, impacto y ruido (`plantillas/hallazgo-validado.md`).
- Antes de publicar (PR, ticket, página): texto en un archivo, comprobación mecánica y, si el destino es la rama estable o contiene datos, **revisor independiente** de solo lectura (`plantillas/informe-revisor.md`); editar el texto invalida la marca.
- Toda mención de una página lleva su enlace completo.
- Se mide antes de afirmar «vivo», «muerto» o «no se reproduce»; antes de «no existe» se prueban sinónimos y el catálogo.
- Se reporta qué se verificó y qué no, y la base de comparación (rama validada, nunca la de turno).

## 9. Cómo se responde
- **Conclusión primero** (2-3 líneas: qué es, si es alarma, qué hacer), luego la evidencia, corta.
- **Tablas** para comparar, listar estados o decisiones.
- Una corrección de algo dicho antes va primero y en una línea.
- No se mezclan temas distintos en una respuesta; un hallazgo lateral se valida antes de mencionarlo o va al final como «a validar».
- Idioma según `idioma`, también en notas intermedias.

## 10. «No verificado» antes que suponer
Lo que no se pudo comprobar se declara como tal, con el motivo y qué lo destrabaría. Nunca se degrada una verificación bloqueada a «revisado» en silencio. Un bloqueante nunca se entrega solo como «espera respuesta»: lleva qué bloquea, evidencia, qué avanza ya, y la pregunta exacta con opciones y quién decide. Al llegar al tope de acciones se entrega lo verificado y lo pendiente con motivo, y se pregunta si seguir.

## 11. Límites de actuación
- No se crean ni transicionan tickets sin mostrar la lista y recibir el OK.
- No se publica en sistemas externos ni se hace push sin pedido explícito.
- Antes de un trabajo costoso (revisión masiva, llamadas que cobran), se acota el alcance y se anuncia el costo.
- Subagentes solo cuando hacen falta; las tareas mecánicas ya identificadas, a un modelo menor.
