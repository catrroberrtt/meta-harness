<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: PLAN-<slug>.md

Archivo en la raíz del repo (`plan.ubicacion`), excluido del control de versiones local; no se borra al terminar (lo borra la persona). No usar el modo de plan de la herramienta que lo esconda. Se llena y se aprueba **por fases**; no se avanza sin OK.

Variantes: `servicio` y `interfaz-por-fases`; las fases son la lista `plan.fases`. Al cerrar cada fase se pregunta: {{ajustar fase 1 · … · aprobar y continuar}}.

## 0. Consulta previa (intake) [OBLIGATORIO]
Ver `intake.md`. Resumir lo que ya se sabía y lo que falta confirmar.

## Variante `servicio`
1. **Especificación** — nombre, método y ruta, parámetros, petición y respuesta de ejemplo (provisional hasta validar la consulta), errores, autenticación, auditoría.
2. **Arquitectura y capas** — flujo análogo completo leído, bloque de impacto de cada entidad que se escribe, tabla de reglas del flujo análogo (heredar o descartar), `mapa-reutilizacion.md`, tamaño de estructura {{S/M/L}} con una frase por pieza extra, decisiones de diseño una por línea.
3. **Modelo de datos** — entidades, ORM vs SQL crudo y por qué, columnas, **SQL crudo equivalente siempre**, migración a escribir (no ejecutar).
4. **Verificación** — cómo se prueba con datos reales (`evidencia-datos.md`).
5. **Aprobación por capa**; 6. **Manifiesto** (`manifiesto.md`).

## Variante `interfaz-por-fases`
Intake · A arquitectura y componentes · B.1 especificaciones de diseño (`mapeo-diseno.md`) · B.2 maquetación sin integración (estados: cargando, vacío, error, con datos) · C especificación del API campo por campo · D código de integración · puerta final (manifiesto) · verificación.

## Ejemplo mínimo
```
# PLAN — Entrega parcial
## 0. Intake  Objetivo: entregar en partes. Consume: pantalla de entrega. Escritura. Afecta esquema: sí.
## 1. Especificación  POST /pedidos/:id/entregas ...
## 2. Capas  Reutiliza PedidoService; crea EntregaRepository (una frase: tabla nueva).
## Aprobación  [ ] especificación  [ ] capas  [ ] datos  [ ] verificación
```
