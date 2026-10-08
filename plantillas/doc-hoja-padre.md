<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: hoja padre «Flujo total e índice» y páginas hijas

Obligatoria antes de crear ramas o código en un cambio de tamaño {{M o L}} (`documentacion.completa-antes-de-codificar`). Un resumen no cumple; las páginas llevan el detalle completo (nombres, columnas, SQL).

## Hoja padre [OBLIGATORIO]
- Qué es y quién interviene.
- El flujo de punta a punta, por fases.
- Estados de un vistazo.
- Tabla `parte del flujo → sistema → ticket → página`.
- Mapa de las páginas hijas.

## Páginas hijas (lista por `documentacion.paginas`)
| Página | Nivel de detalle exigido |
|---|---|
| Decisiones de producto | Cada decisión con alternativa descartada y motivo |
| Estados y reglas de negocio | Guardados vs calculados; reglas numeradas; casos límite con número |
| Modelo de datos | Ver `doc-modelo-y-migraciones.md` |
| Migraciones | Ver `doc-modelo-y-migraciones.md` |
| Cada sistema | Módulos, pantallas, flujos, permisos, auditoría, qué se reutiliza |
| Integraciones y correos | Cuándo salen, quién las dispara, idempotencia |
| Infraestructura y despliegue | Orden por ambiente, qué no se verificó |
| Paridad con la función existente | Cómo lo resuelve hoy el sistema; qué se copia y qué cambia |
| Calidad | Qué cubre QA y qué bloquea la salida |
| Reparto y orden de trabajo | Quién hace qué, dependencias, flujo de ramas |
| Preguntas abiertas | `preguntas-abiertas.md` (página viva) |
| Permisos | Actuales (verificados en datos) y matriz propuesta |
| Contrato de API | `doc-contrato-api.md` |
| Casos de prueba | `casos-de-prueba.md` |
| Mapa de reutilización | `mapa-reutilizacion.md` |

Cada página usa `doc-pagina.md`. Orden: analizar y decidir → borradores locales → revisión → publicar bajo la raíz y verificar (hijas, enlaces, padre, tablas alineadas) → recién entonces plan, ramas y código. Una página vieja que contradice lo vigente recibe aviso de «histórica».

## Ejemplo mínimo
```
Raíz: Pedidos parciales · flujo total e índice
 Fase 1 Pedido → Fase 2 Entrega parcial → Fase 3 Cierre
 | Parte | Sistema | Ticket | Página |
 | Entrega | Servidor | PROJ-123 | Contrato de API |
```
