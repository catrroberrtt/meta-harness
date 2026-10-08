<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: revisión de QA (variantes `interfaz` y `servicio`)

Archivos por `qa.revisiones`: `revision-interfaz.md` (QA funcional en el navegador) y `revision-servicio.md` (contra los endpoints, sin interfaz). Se actualizan en el mismo lugar cuando el comportamiento validado cambia.

```markdown
# {{tema}} — QA de {{interfaz|servicio}}
> verificado-contra-git: {{sha}} · {{repo}} · {{fecha}}      [OBLIGATORIO, uno por repo]

## ⚠ Fixes pendientes de esta revisión                        [OBLIGATORIO aunque no tenga filas]
| # | Repo | Qué hay que corregir | Evidencia | Ticket o motivo de no tenerlo |
|---|---|---|---|---|

## 1. {{Categoría}}
- [ ] {{ítem verificable}}
```
El checkbox dice «¿se verificó?», no «¿está corregido?»: todo bug real que exige cambiar código va además a «Fixes pendientes». Un ítem confirmado pasa a `[x]` con fecha y evidencia; un comportamiento nuevo no previsto se agrega **sin marcar**.

## Variante `servicio` — categorías mínimas
Contrato exacto (campos y tipos, qué no debe traer) · qué mueve cada parámetro y qué no · `null` frente a `0` · errores y permisos (sin sesión ≠ sin permiso ≠ permiso revocado; un perfil con uno de dos permisos).
## Variante `interfaz` — categorías mínimas
Filtros, cambio de moneda o unidad, datos mostrados, tarjetas, gráficos, tablas, descargas (formato real del archivo), errores y bordes, estado visible cuando el servidor niega.

## Auditoría independiente (lista mínima, `qa.auditoria-independiente`) [OBLIGATORIO]
No alcanza con lo que dicta la persona más el tracker; se busca activamente:
- Guardas y autorización: ¿más de una guarda encadenada?, ¿lógica propia con varias condiciones?, ¿mensaje distinto por causa?
- Validación de entradas: probar el límite exacto de cada regla (cero, negativo, límite+1); parámetros desconocidos descartados en silencio; parámetros que solo actúan en pareja.
- Interfaz: ¿la pantalla comprueba el permiso o depende de que el servidor responda 403?

## Hallazgo mínimo (cuatro campos)
1. Repro exacto con dato concreto. 2. Petición y respuesta reales. 3. Esperado frente a real, con valores. 4. Hipótesis descartadas y cómo.

## Ejemplo mínimo
```
## ⚠ Fixes pendientes
| 1 | pedidos-api | cantidad 0 devuelve 500 | POST /pedidos/1/entregas {"cantidad":0} → 500 | PROJ-140 |
## 1. Errores y permisos
- [x] pedido inexistente → 404 (2026-10-07)
- [ ] sin permiso → 403
```
