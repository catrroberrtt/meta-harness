# Señales de la opción ERP

<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-09 · vence: 90d · fuente: herramientas/harness-erp.py y su prueba de que el archivo de señales es válido (herramientas/tests/test_erp.py) -->

`senales.toml` es el dato editable de `harness erp`: qué palabras de los documentos de un negocio señalan qué módulos del ERP estándar. No es un perfil de stack (por eso la carpeta empieza por `_`). Reglas de puntuación, umbrales y cómo editarlo: `docs/OPCION-ERP.md`, sección «Cómo se descubren las señales».

- Términos en minúsculas y **sin tildes**; peso 3 = específico del módulo, 2 = habitual, 1 = genérico.
- Un id de módulo debe existir en `modulos/catalogo.json` del ERP; si no, la herramienta avisa y lo ignora.
- Sin nombres de empresas ni datos reales: palabras del oficio.
- Tras editarlo: `python3 -m unittest herramientas/tests/test_erp.py` (con `HARNESS_ERP_BASE_PRUEBA=<ruta del ERP>` comprueba además los ids contra el catálogo real).
