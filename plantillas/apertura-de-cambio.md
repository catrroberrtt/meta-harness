<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: apertura de un ticket (antes de planificar o codificar)

Bloque corto. Todos los campos son obligatorios.

1. **Cuál es el ticket** — clave: {{CLAVE}} · título: {{título}} · padre: {{padre}} · estado: {{estado}}
2. **Qué se hace** — una o dos frases, en lenguaje de negocio.
3. **Qué conlleva** — capas (servidor / interfaz / infraestructura), archivos a crear o tocar, endpoints (método + ruta), permisos nuevos o reutilizados, migraciones (nombre), riesgo (dinero, concurrencia, datos reales), qué cambia para otros módulos.
4. **Qué NO incluye** — lo que queda fuera a propósito y dónde se atiende.

Criterio de cierre: un ticket no se cierra a medias; todas las capas completas y validadas, o queda abierto diciendo cuál falta.

## Ejemplo mínimo
```
1. PROJ-123 · Pedidos parciales · padre PROJ-100 · Por hacer
2. Permitir entregar un pedido en varias partes.
3. Servidor: POST /pedidos/:id/entregas; interfaz: pantalla de entrega; migración AgregarEntregas; riesgo: concurrencia al entregar.
4. No incluye correos de aviso (PROJ-130).
```
