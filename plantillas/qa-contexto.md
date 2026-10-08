<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: contexto y propósito del módulo (QA del tema)

Carpeta `{{raiz-documentacion}}/<tema>/qa/`, compartida por todas las fechas del tema (describe el estado acumulado, no un incremento). Tema nuevo: copiar la plantilla, no escribir desde cero.

```markdown
# {{tema}} — contexto y propósito
## Propósito de negocio ({{ticket o épica}})      [OBLIGATORIO]  qué resuelve, para quién, qué pregunta responde
## Cómo funciona (el hecho que sostiene lo demás) [OBLIGATORIO]  la regla más fácil de pasar por alto
## Historial de cambios del tema                  1. {{fecha-slug}} — qué cambió
## Los tipos de revisión y por qué están separados
- Interfaz: lo que VE y HACE un usuario.
- Servicio: contrato y reglas en la fuente, sin pasar por la interfaz.
Un mismo hallazgo puede aparecer en ambas, cada una desde su ángulo.
```
Antes de escribir las revisiones: releer el tracker (épica, criterios de aceptación, decisiones cerradas) y usarlo para **corregir** el checklist recibido, no solo transcribirlo.

## Ejemplo mínimo
```
# pedidos — contexto
Propósito: permitir entregas parciales (PROJ-100).
Regla central: el total de un pedido nunca cambia por entregar en partes.
```
