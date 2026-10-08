# Observabilidad · Angular + Material
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (protocolo de verificación visual, código de interceptores observado); contenido parcial; ver evidencia.md -->

> Registros, trazas, métricas y alertas del cliente. Cada regla lleva un identificador (`OBS-n`). **Estado: parcial.** Solo se registran las reglas con evidencia; el resto sigue por extraer.

## Lo que sí tiene evidencia

- `OBS-1` La **consola del navegador** y la **red** son las señales de salud de una pantalla durante la verificación: al terminar un flujo se leen los mensajes de la consola (patrón de errores) y las peticiones (4xx/5xx inesperados); sin errores nuevos ni advertencias nuevas del framework (`PRU-9`).
- `OBS-2` Los fallos de API se **registran en un solo punto**: el interceptor de errores. Los módulos no repiten el aviso genérico; una petición que cuenta el error con sus palabras lo declara con un contexto HTTP (`PAT-9`), para no tener dos avisos por el mismo fallo.
- `OBS-3` Un normalizador de errores (`COD-24`) entrega el código y el mensaje de cada fallo con un texto por defecto, de modo que el aviso y cualquier registro vean la misma forma.
- `OBS-4` Los códigos de error que el cliente compara son constantes y coinciden con los del servidor (`SEG-3`); un literal suelto impide rastrear dónde se usa.

## Por extraer (sin evidencia, no se rellena a ojo)

- Captura de errores del cliente hacia un servicio externo y manejador global de errores (`ErrorHandler`): el origen no tiene uno registrado.
- Trazas de usuario y métricas de uso o de rendimiento percibido.
- Correlación del identificador de petición entre cliente y servidor.
- Alertas sobre errores del navegador.

Motivo (R24): el origen no registra reglas de estos puntos, y el código observado no contiene captura remota de errores. Se completa cuando una segunda instancia aporte evidencia.
