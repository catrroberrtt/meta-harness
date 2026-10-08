---
name: sdd-verificar
description: Verifica un cambio con evidencia observable antes de darlo por terminado: gate de calidad, pruebas, criterios de aceptación y cotejo de equivalencia cuando aplica. Úsala siempre antes de decir que algo está listo, correcto o verificado.
---
<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: método de trabajo del harness (metodo/forma-de-trabajo.md) y plantillas de esta carpeta -->

# sdd-verificar

## Cuándo usarla
- Terminaste una fase o el cambio completo y vas a reportarlo como listo.
- La persona pide revisar o validar algo ya hecho.

## Pasos
1. Corre el gate de la instancia (el comando está en `AGENTS.md`, sección «Gate de calidad»; si tu agente tiene el comando neutral `harness-gate`, úsalo). Pega el resultado **y el código de salida**.
2. Recorre cada criterio de aceptación de `cambios/<slug>/` y asócialo a un resultado observable: salida de prueba, consulta real mostrada, captura de pantalla.
3. Si hay cifras o datos, usa `plantillas/evidencia-datos.md`: nada de veredictos sin la consulta real que los respalda.
4. Si el cambio reemplaza o migra algo, cotéjalo con `herramientas/harness-equivalencia.py` y reporta las diferencias.
5. Completa `plantillas/checklist-entrega.md` y deja lo que solo una persona puede comprobar listado como pendiente suyo.
6. Reporta con la estructura: qué se verificó, cómo, resultado real, y qué **no** se pudo verificar.

## Qué NO hacer
- No digas «listo», «correcto» o «verificado» sin un resultado que se vea.
- No ocultes pruebas que fallan ni las omitas para que el gate pase.
- No ejecutes por tu cuenta lo que la política prohíbe al agente (por ejemplo, servidores de desarrollo o escrituras fuera del ambiente de pruebas): pídeselo a la persona.
- No cierres si quedó una pregunta abierta que afecta el resultado.
