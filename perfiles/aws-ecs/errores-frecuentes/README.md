# Errores frecuentes · AWS ECS
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (guías de diagnóstico, runbooks, comentarios del código de infraestructura y contraste entre documentación y código); ver evidencia.md -->

> Patrones de falla de este stack: síntoma → causa → receta. Cada uno lleva un identificador (`ERR-n`). Todos están **pendientes de evidencia**.

| Id | Síntoma | Causa | Receta |
|---|---|---|---|
| `ERR-1` | Se cambió un secreto o una variable y «no pasó nada» | Las tareas en ejecución no releen el secreto; sigue vivo el valor viejo | Actualizar el secreto, **forzar nuevo despliegue** del servicio, esperar a que se estabilice y verificar el valor (`REC-2`) |
| `ERR-2` | Las tareas se reinician sin parar | Código de salida 1 (error de la app), 137 (falta de memoria), 143 (sin cierre ordenado); o la comprobación de salud mata una tarea que aún arranca | Ver tareas detenidas y su `exitCode` (`OBS-12`); subir memoria; revisar el manejo de la señal de cierre; alargar el periodo de gracia (`REN-3`) |
| `ERR-3` | Los destinos del balanceador salen «no saludables» | La ruta de salud no existe o no devuelve 200; el grupo de seguridad de las tareas no deja entrar al balanceador; el puerto del contenedor no es el que escucha la app | Probar la ruta de salud; revisar la entrada del grupo de seguridad de las tareas desde el del balanceador; igualar el puerto declarado y el real |
| `ERR-4` | `CannotPullContainerError` o «acceso denegado» al arrancar | Una imagen pública como marcadora no otorga lectura del registro privado; o falta el permiso para obtener el token del registro; o la imagen/etiqueta no existe | Conceder explícitamente lectura al rol de ejecución y el permiso del token (recurso comodín); comprobar que la etiqueta existe; el mismo permiso lo necesita la tarea única de migración |
| `ERR-5` | Un `diff` o un despliegue **reemplaza** un recurso (o la creación choca con «ya existe») | Se cambió el nombre físico o el identificador lógico, o se creó un recurso nuevo en lugar de convertir el existente | Leer el `diff` buscando *replacement*; conservar el identificador lógico cuando se convierte un recurso (`COD-10`, `COD-11`); en producción, medir el impacto antes |
| `ERR-6` | Se necesita restaurar un ambiente no productivo y no hay copia | Por diseño, no se hicieron copias lógicas allí | Aceptarlo y anotarlo (`DAT-6`); si se necesitan datos reales para un análisis, abrir un túnel puntual a la base viva; **verificar siempre de qué ambiente es la copia** que se analiza |
| `ERR-7` | Una migración falla a mitad del despliegue | El esquema queda a medias | El pipeline debe terminar **antes** de actualizar el servicio (`DAT-9`); el retroceso es una decisión aparte porque el rollback de código no deshace el esquema (`DAT-10`) |
| `ERR-8` | La pila queda en `UPDATE_ROLLBACK_FAILED` | Un recurso no se pudo revertir | Leer los eventos de la pila; `continue-update-rollback` con la lista de recursos a omitir; en el peor caso, destruir y recrear |
| `ERR-9` | Un certificado queda en `PENDING_VALIDATION` | Faltan los registros de validación en la zona DNS, o los servidores de nombres del registrador no apuntan a la zona gestionada | Revisar los registros `CNAME` de validación; actualizar los servidores de nombres tras crear la zona; esperar 5-10 min |
| `ERR-10` | Se desplegó (o se intentó) en la cuenta o el ambiente equivocados | Valores por defecto de cuenta o región, o perfil activo distinto | Bandera de ambiente obligatoria; sin cuenta/región por defecto (`COD-3`); comprobar la cuenta activa con la identidad antes de aplicar |
| `ERR-11` | El pipeline falla con `AccessDenied` tras añadir un recurso | La política del rol de CI no cubre el recurso nuevo | Ampliar el rol en la pila de identidades **acotando al recurso** (`SEG-3`) y redesplegar esa pila |
| `ERR-12` | Las alertas de costo o de operación no llegan | La suscripción del correo al tema sigue «pendiente de confirmación» | Listar las suscripciones del tema y confirmar; probar con una publicación manual (`OBS-7`) |
| `ERR-13` | La documentación afirma un control que el código no tiene | Documento y código divergieron (por ejemplo, una protección o un umbral documentados que el código no aplica) | Verificar **en el código y en la plantilla sintetizada** antes de citar un control; añadir una aserción (`PRU-3`) o corregir el documento con fecha |
| `ERR-14` | Se escaló a mano y al rato vuelve al número anterior | El autoescalado recalcula el deseado | Subir `minCapacity` en la configuración (`REN-4`) |
| `ERR-15` | Un secreto cambia de significado al reordenar la lista | El constructo mapea secretos a variables **por posición** en la lista | Pasar el mapeo explícito por clave en lugar de depender del orden; no reordenar la lista de secretos |
| `ERR-16` | El balanceador falla al crearse o aparece con un nombre cortado | Los nombres de balanceador admiten 32 caracteres | Truncar de forma determinista y verificar el nombre resultante (`COD-7`) |
| `ERR-17` | Una pila «solo de producción» aparece al listar un ambiente bajo | El listado puede incluir pilas que la aplicación deshabilita después, al sintetizar | Sintetizar el ambiente y comprobar la salida (`ARQ-11`) |
| `ERR-18` | La regla de seguridad de la base es más ancha de lo necesario | La regla de entrada es por rango de red, no por grupo de seguridad de origen | Pasar a reglas por grupo de seguridad cuando haya que restringir (`DAT-1`) |
| `ERR-19` | Una alarma de facturación absoluta no se puede crear | La métrica de cargos estimados solo existe en la cuenta pagadora | Usar presupuesto con avisos reales y proyectados (`REN-13`) |

## Patrones de proceso

- `ERR-20` **Creer que otra cuenta tiene lo mismo.** Un nombre de pila, un bastión o una base no existe en otra cuenta solo porque exista en la de producción; se verifica en la cuenta del ambiente.
