---
description: Ejecuta el gate de calidad declarado por la instancia y muestra el resultado con su código de salida.
---
<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: método de trabajo del harness (metodo/forma-de-trabajo.md) y plantillas de esta carpeta -->

# harness-gate

1. Lee en `AGENTS.md`, sección «Gate de calidad», el comando declarado.
2. Si dice que el comando está «por definir», **detente**: no lo inventes; pregunta a la persona cuál es y pídele que lo declare en `convenciones.toml` (clave `gate.comando`).
3. Si está declarado, ejecútalo en la terminal tal cual y muestra la salida y el **código de salida**.
4. Si la política de la instancia pide confirmación para ese comando (por ejemplo, build o pruebas), pídela antes de correrlo.
5. Informa el resultado sin maquillarlo: qué pasó, qué falló y qué no se pudo comprobar. Opcionalmente, `harness doctor` revisa herramientas y frescura de documentos.

Este comando no cambia la política ni los archivos de la instancia.
