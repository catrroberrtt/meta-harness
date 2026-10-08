<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: hallazgo validado

Un hallazgo no se presenta como alarma sin pasar cuatro chequeos con datos o código.

| Chequeo | Pregunta | Resultado |
|---|---|---|
| Alcance | ¿Cuántos casos y qué proporción del total? | |
| Vigencia | ¿Desde cuándo? ¿Sigue pasando? Fecha del último caso | |
| Impacto | ¿Qué flujo o pantalla lo toca hoy? ¿Puede una operación actuar sobre esos casos? | |
| Ruido | ¿Estados cancelados, umbrales mal puestos, un solo proyecto, atípicos? | |

Etiqueta [OBLIGATORIO] (`hallazgo.etiquetas`): **alarma** (vigente e impacto verificado) · **observación** (acotada, impacto sin verificar) · **histórico** (ya pasó y no se repite). Sin validar: decir «sin validar» y no usar lenguaje de alarma.

## Ejemplo mínimo
```
Hallazgo: 31 pedidos con diferencia. Alcance: 27 de un solo lote de 2022; 3 de 0,06; 1 cancelado.
Vigencia: último caso 2022-11. Etiqueta: histórico.
```
