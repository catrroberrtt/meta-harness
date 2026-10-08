<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: mapeo diseño ↔ implementación

Se llena antes de maquetar (inventario de piezas) y otra vez antes de decir «listo», mirando la pantalla real. Sin tabla no hay cierre de una interfaz. También cuando algo pasa de «pendiente» a «existe»: buscar los textos que decían lo contrario.

Cómo: usar la entrega de diseño más reciente (confirmar con la persona); **ver** el diseño, no solo leerlo; ver la implementación al lado; apagar lo que se levantó.

| Pieza del diseño | Cómo está en la implementación | Veredicto | Qué se hace | ¿Toca API? |
|---|---|---|---|---|

Veredictos permitidos [OBLIGATORIO]: **igual** · **mejora** (decirlo) · **falta** · **distinto** · **descartado** (con la razón: decisión de negocio, patrón del producto, contrato con la API).

Prioridad cuando chocan (`diseno.prioridad`): observaciones de QA > estilo del producto existente > diseño como guía de estructura. Las propuestas marcadas «a validar» no se implementan sin decisión; se listan como descartadas o pendientes. Lo que falta y el servidor ya tiene se resuelve en la interfaz; solo lo inexistente pide API, nombrando el endpoint.

## Qué mirar en la pantalla real
- Cada acción que el servidor prohíbe: la pantalla la apaga y explica por qué.
- Acciones irreversibles o que mueven dinero: confirmación escrita.
- Estados activo y apagado de cada botón, en claro y oscuro.
- Ancho de paneles con el dato más largo real; nada cortado.
- Textos que describen el estado del sistema, contrastados con el servidor.
- Fechas con el día de la zona horaria del negocio.

Dónde queda: `{{raiz-documentacion}}/<tema>/<fecha>-mapeo-diseno-<modulo>/` con sello de verificación, la tabla, lo ejecutado, lo descartado y **lo que no se vio en pantalla**.

## Ejemplo mínimo
| Pieza | Implementación | Veredicto | Qué se hace | ¿API? |
|---|---|---|---|---|
| Botón «Rechazar» rojo | sale azul | distinto | quitar color fijo de la clase | no |
| Filtro por fecha | no existe | falta | añadir selector | sí: parámetro `desde` |
