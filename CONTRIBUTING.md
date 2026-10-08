# Cómo aportar

<!-- tipo: guia · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Este repositorio guarda un método de trabajo reutilizable. Un aporte entra solo si es genérico, tiene evidencia y viene con pruebas.

## El flujo de aprendizaje

Quien aporta, sea una persona o una instancia que usa el harness, sigue siempre estos pasos:

1. **Lección clasificada.** Describa qué pasó y clasifíquelo (un error evitable, un formato, una regla, una herramienta). Las herramientas de la carpeta `herramientas/` ayudan a extraer y clasificar.
2. **Paquete anonimizado.** Convierta el caso en uno genérico: sin nombres de empresa, proyecto, personas, hosts ni identificadores. Use valores de ejemplo.
3. **Revisión.** Abra una propuesta con el paquete. Una persona con permiso de fusión la revisa contra los criterios de abajo.
4. **Versión nueva.** Al aceptarse, se fusiona, se actualiza `VERSION` y se anota el cambio.

## Criterios de aceptación

- **Sin datos de empresa:** ningún nombre, cuenta, host, correo, ticket ni cliente reales. El escaneo de publicación debe dar 0 hallazgos (`python3 herramientas/harness-escaneo-publico.py .`).
- **Con evidencia:** indique de dónde sale la regla (un caso observado, un documento, una medición). Una regla sin respaldo se rechaza.
- **Con pruebas:** todo código lleva pruebas (`python3 -m unittest`) y las existentes siguen pasando; toda regla verificable lleva su comprobación.
- **Genérico:** debe servir a más de un proyecto; lo específico va en perfiles o convenciones opcionales.
- **Sin secretos ni archivos locales:** nunca `.env`, claves, volcados de base de datos ni estados de infraestructura.
- Los documentos llevan su cabecera de frescura (`revisado`, `vence`, `fuente`).

## Cómo se revisa

La persona revisora comprueba los criterios en orden: escaneo y pruebas en verde, anonimización, evidencia, y que no duplique lo existente. Puede pedir cambios o rechazar con una razón escrita. Al aportar, usted acepta que su contribución se publica bajo la licencia del repositorio una vez elegida.

Para vulnerabilidades, no abra una propuesta pública: vea `SECURITY.md`.
