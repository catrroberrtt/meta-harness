# Herramientas

<!-- tipo: herramienta · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

Scripts parametrizados que miden en vez de recordar: detección de proyecto (modo `adopt`), clasificación de documentos por tipo y especificidad, y a futuro gate, lint y extractor.

- `harness-detectar.py <carpeta> [--json]`: informe de solo lectura «cómo es este proyecto».
- `clasificar-skill.py [--md]`: inventario de tipo, tecnicidad y especificidad; el patrón de lo «propio del proyecto» se fija con `HARNESS_PATRON_PROYECTO` o `patrones-proyecto.txt`.
- `harness-trazabilidad.py <cambio> [--etapa especificacion|delegacion|implementacion|cierre] [--repo <carpeta>] [--json]`: comprueba la trazabilidad de un cambio (`metodo/terminado-y-trazabilidad.md`). Solo lectura y sin red. Detecta requisito sin prueba, prueba sin requisito, especificación sin criterios de aceptación o sin aprobar, suposiciones abiertas, tarea delegada sin contrato de archivos, solapes de archivos entre tareas, filas «verificado» sin commit o evidencia, casillas de cierre vacías; con `--repo` comprueba con `git` local que los commits y archivos citados existen. Salida 0 / 1 (errores) / 2 (uso). Ejemplo ejecutable: `python3 herramientas/harness-trazabilidad.py plantillas/ejemplos/cambio-ejemplo`. Pruebas: `python3 -m unittest herramientas/tests/test_trazabilidad.py`.

- `harness-erp.py <carpeta-del-negocio> --erp-base <ruta> [--senales archivo.toml] [--json|--md]`: opción ERP. Lee documentos locales (reutiliza `harness-leer-entradas.py`), puntúa las señales de `perfiles/_erp/senales.toml` y propone producto y módulos del catálogo del ERP con su estado real. Solo lectura, sin red. Lo usa `harness erp`; ver `docs/OPCION-ERP.md`. Pruebas: `python3 -m unittest herramientas/tests/test_erp.py`.

## Origen

Lo aporta la instancia del proyecto; el mapa de migración vive en la instancia (parametrizacion).

## Patrones de la instancia

Una instancia aporta su propio `patrones-proyecto.txt` (una regex por línea, `#` para comentarios) en la raíz que se analiza.
Alternativamente se define la variable de entorno `HARNESS_PATRON_PROYECTO`; sin ninguno se usa el patrón genérico.
El harness nunca guarda esos patrones: pertenecen a la instancia.

<!-- open-design:inicio -->
## Webs (adaptador `diseno-web`)

- `web-verificar-sitio.py <carpeta> [--json] [--estricto]`: verificador estático de un sitio generado (lang, title, encabezados, alt, contraste de tokens, px en fuentes, pesos, enlaces rotos, secretos, remotos y trackers no declarados, licencias de activos, relleno). Sin red ni navegador; lo que no comprueba está en `estandares/diseno-web.md` §5.
- `web-detectar-herramienta.py [--json]`: dice si hay una herramienta externa de generación (sin ejecutarla); si no, el adaptador usa el modo manual.
<!-- open-design:fin -->
