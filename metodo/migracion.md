<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: especificación del harness §18 -->
# Migración: réplica fiel y mejoras aparte

Modo `migrar` (punto de partida C: replicar un sistema existente). Principio: **«igual que antes» y «mejor que antes» nunca se mezclan en el mismo cambio.** Primero se replica y se prueba la equivalencia; las mejoras se anotan y se deciden después.

Herramientas: `herramientas/harness-mejoras.py` (registro `mejoras.md` de la instancia) y `herramientas/harness-equivalencia.py` (casos de comparación). Formatos: `plantillas/mejora.md` y `plantillas/equivalencia.md`.

## Flujo

1. **Entender el origen (entradas).** Se lee lo que haya: código o volcado, esquema, diccionario, hojas de cálculo, descripciones en archivos. Se deja por escrito qué se leyó y qué no. Sin esa información de partida no se avanza: se dice qué falta y dónde ponerlo. Lo que no se pueda deducir se pregunta, diciendo qué se intentó.
2. **Replicar primero lo que el origen hace, también lo que parece un error.** La réplica reproduce reglas, redondeos, orden, mensajes y casos borde tal como son. Que algo «parezca mal» no es motivo para corregirlo aquí.
3. **Probar la equivalencia origen ↔ nuevo.** Casos de comparación (`plantillas/equivalencia.md`) con la misma entrada en ambos sistemas; se corre `harness-equivalencia.py`. Cubre caso normal, bordes, errores y, si hay dinero o cantidades, decimales exactos. Todo desvío es o bien un defecto de la réplica (se corrige) o bien una **diferencia aceptada** declarada con su motivo y su aprobador.
4. **Toda mejora se anota y NO se aplica en la réplica.** Una entrada por mejora en `mejoras.md` (`plantillas/mejora.md`) con evidencia de dónde se vio. Anotar no cuesta nada y no compromete; aplicar sí.
5. **Revisión por lotes con una persona.** `harness-mejoras.py revisar` imprime las propuestas agrupadas por riesgo y esfuerzo; la persona aprueba o descarta cada una con motivo (`decidir`). El agente no decide por ella.
6. **Las aprobadas entran como cambios SDD normales, con su especificación, después de la equivalencia.** Solo cuando la equivalencia está cerrada. Cada una pasa por el flujo completo (especificar, validar, planificar, implementar, verificar, documentar) y se marca `aplicada` citando esa especificación. La equivalencia se vuelve a correr: las diferencias que la mejora introduce se declaran como aceptadas con el id de la mejora.

## ¿Mejora o réplica?

Pregunta única: **¿el origen hace esto hoy?**

| Situación | Es | Qué se hace |
|---|---|---|
| El origen lo hace así, aunque sea ilógico, feo o ineficiente | **réplica** | Se reproduce. Si molesta, se anota una mejora |
| El origen documenta una cosa y hace otra | **réplica de lo que hace** | Se replica el comportamiento real; la discrepancia se anota |
| El origen no lo hace (función nueva, validación ausente, mensaje más claro) | **mejora** | Se anota, no se agrega |
| Reorganizar código, nombres o estructura sin cambiar salidas | **libre** (detalle interno) | Se hace, y la equivalencia lo respalda |
| Cambio de rendimiento sin cambiar salidas | **libre**, con la equivalencia como red | Si cambia el orden o el redondeo, ya es mejora |
| No se sabe qué hace el origen en ese caso | **pregunta** | No se adivina: se pregunta o se prueba contra el origen |

Duda entre las dos: se trata como réplica y se anota la mejora.

## Cuando replicar un defecto es peligroso

1. **Se replica y se marca.** Lleva un comentario/etiqueta visible en la réplica («defecto replicado a propósito, ver M-NNN») y una mejora en el registro con riesgo alto.
2. **Si hay riesgo de daño o de seguridad** (pérdida o corrupción de datos, dinero mal calculado, acceso indebido, exposición de datos personales, acción irreversible), **se escala a una persona antes de replicar**. No se replica ni se corrige hasta tener su decisión por escrito. Mientras tanto la pieza queda marcada como bloqueada en el plan.
3. La decisión (replicar con la salvaguarda indicada, o corregir ya como diferencia aceptada) se registra en la entrada de mejora y, si cambia la salida, como diferencia aceptada en la equivalencia.
4. Una salvaguarda externa a la lógica (límite, aviso, bloqueo de la ruta) no cuenta como mejora a la réplica si la persona la pide; igual se anota.

## Qué garantiza el mecanismo

- `harness-mejoras.py` solo escribe el archivo del registro; nunca toca el código de la réplica y rechaza un registro fuera de la instancia indicada con `--instancia`. Aprobar una mejora **no** la aplica.
- Una mejora solo pasa a `aplicada` si estaba `aprobada` y se cita la especificación del cambio.
- `harness-equivalencia.py` sale con 0 solo si no quedan diferencias sin aceptar; comparaciones numéricas con aritmética exacta y tolerancia explícita por caso.

## Documentar mientras se migra

Cada cambio deja su rastro en el almacén de documentación y mantiene al día los índices a medida que se construye; no hay etapa de documentación al final.
