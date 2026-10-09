# Delegación — Entregas parciales

| Tarea | Encargado | Requisitos | Escribe | No toca | Entrega | Aceptación | Reversa | Estado |
|---|---|---|---|---|---|---|---|---|
| Servicio y tabla de entregas con bloqueo | Agente de servidor | RQ-01, RQ-02, RQ-03 | src/entregas/, migraciones/1791-entregas.ts, pruebas/entregas.spec.ts | src/pedidos/ | Rama feat/entregas con commits y resultado del gate | CA-01.1, CA-02.1 y CA-03.1 pasan con `npm test -- entregas` | Revertir la migración | aceptada |
| Pantalla de entrega | Agente de interfaz | RQ-01 | src/web/entregas/ | src/web/pedidos/ | Rama feat/entregas-ui con captura del flujo | CA-01.1 visible en pantalla | Revertir la rama | aceptada |
