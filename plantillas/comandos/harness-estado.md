---
description: Muestra el estado de la instancia del harness (versión, qué está instalado, qué cambió y qué quedó pendiente).
---
<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: método de trabajo del harness (metodo/forma-de-trabajo.md) y plantillas de esta carpeta -->

# harness-estado

Ejecuta en la terminal, desde la instancia o indicando su ruta, la herramienta del harness:

```
harness estado
```

(El comando `harness` está en la carpeta `cli/` del harness; si no está en el `PATH`, usa su ruta, que figura en `harness.lock`, clave `fuente`.)

Muestra la salida completa y resume en tres líneas: versión, qué hay instalado y qué está pendiente. No modifiques nada: este comando es solo de lectura. Si el comando no existe o falla, di exactamente qué intentaste y qué salió; no inventes el estado.
