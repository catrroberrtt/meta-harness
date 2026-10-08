<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: especificación del harness §18 -->
# Plantilla: caso de comparación origen ↔ nuevo

Un caso = una entrada ejecutada en el sistema origen y en el nuevo. Se guardan como JSON o CSV y se evalúan con `herramientas/harness-equivalencia.py`.

| Campo | Contenido |
|---|---|
| `id` [OBLIGATORIO] | {{EQ-001}} |
| `entrada` [OBLIGATORIO] | {{datos o petición exactos, reproducibles}} |
| `salida_origen` [OBLIGATORIO] | {{lo que el origen devolvió, tal cual}} |
| `salida_nuevo` [OBLIGATORIO] | {{lo que devolvió el nuevo}} |
| `tolerancia` | {{solo numérica, explícita por caso; por defecto 0 (exacto)}} |
| `aceptada_motivo` | {{si la diferencia es aceptada: por qué y quién la aprobó (id de mejora si aplica)}} |

Veredicto (lo calcula la herramienta): `equivalente` · `diferencia aceptada` (con motivo) · `diferencia` (sin aceptar; hay que corregir la réplica o declararla). Los números se comparan con aritmética decimal exacta, nunca con flotantes. Un caso sin motivo no se acepta.

## Ejemplo mínimo (JSON)
```json
[
  {"id": "EQ-001", "entrada": "pedido con 3 líneas de 1.10", "salida_origen": "3.30", "salida_nuevo": "3.3"},
  {"id": "EQ-002", "entrada": "pedido con 3 líneas de 0.333", "salida_origen": "0.99", "salida_nuevo": "1.00",
   "aceptada_motivo": "M-001 aprobada: redondeo único al final"},
  {"id": "EQ-003", "entrada": "pedido vacío", "salida_origen": "error 400", "salida_nuevo": "error 422"}
]
```
Resultado: EQ-001 equivalente, EQ-002 diferencia aceptada, EQ-003 diferencia sin aceptar (exit 1).

Cuando la salida es estructurada (objeto o lista) en JSON, se compara campo a campo; los números dentro respetan la misma tolerancia.
