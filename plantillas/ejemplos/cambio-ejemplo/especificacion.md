# Especificación — Entregas parciales de un pedido

Ejemplo inventado (tienda ficticia «Pedidos»). No describe ningún proyecto real.

## Contexto
Problema: un pedido solo puede entregarse completo; despacho entrega en varias partes y lo anota fuera del sistema. Alcance: registrar entregas parciales y mostrar el saldo. Fuera de alcance: avisos por correo (se atienden en otro cambio). Tamaño: M.

## Suposiciones
- SU-01 · establecido · Un pedido nunca cambia de cliente después de creado · origen: regla de negocio confirmada por el área de ventas.
- SU-02 · de-trabajo · Las cantidades son enteras · origen: datos de la tabla de líneas de pedido.

## Requisitos
- RQ-01 · Cuando despacho registra una entrega con cantidad menor o igual al saldo, el sistema guarda la entrega y reduce el saldo.
  - CA-01.1 · Dado un pedido de 10 unidades sin entregas, cuando se registra una entrega de 4, entonces el saldo es 6 y existe 1 entrega de 4.
  - CA-01.2 · Dado un saldo de 6, cuando se registra una entrega de 6, entonces el saldo es 0 y el pedido pasa a «entregado».
- RQ-02 · Si la cantidad de la entrega supera el saldo, el sistema rechaza la entrega sin guardar nada.
  - CA-02.1 · Dado un saldo de 6, cuando se registra una entrega de 7, entonces la respuesta es 422 con el código ENTREGA_EXCEDE_SALDO y no se crea ninguna fila.
- RQ-03 · [no funcional] Cuando dos entregas llegan a la vez para el mismo pedido, el saldo final es coherente.
  - CA-03.1 · Con 2 peticiones simultáneas de 6 sobre un saldo de 10, exactamente una tiene éxito y el saldo final es 4.

## Desafío previo (M y L)
- Cómo falla esto: dos operarios entregan lo mismo a la vez y el saldo queda negativo.
- Qué suposición lo rompería: SU-02 (si aparecen cantidades decimales, el saldo entero deja de servir).
- Alternativa descartada y por qué: columna «cantidad_entregada» en el pedido; no deja historial de entregas.

## Decisiones
- El saldo se calcula (cantidad del pedido menos entregas), no se guarda.

## Aprobación
- [x] OK explícito de la responsable de despacho (2026-01-10)
