<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: estado de un tema («¿en qué quedamos?»)

Cabecera con sello [OBLIGATORIO]: `verificado-contra-git: {{sha}} · {{repo}} · {{fecha}}` contra la **rama validada** (no contra la rama de trabajo de turno). Se genera con la foto de fuentes: estado de cada repo, divergencias entre ramas, PR abiertos, repos sin clonar. Nunca se arma la lista de pendientes copiando una nota de un solo documento; se cruza git, PR abiertos, fixes de QA abiertos y cerrados, y el tracker.

| # | Qué | Estado (hecho / no hecho / pendiente) | Evidencia (fuente y fecha) | Dueño | ¿Bloquea? |
|---|---|---|---|---|---|

Secciones: Hecho · No hecho · Decisiones pendientes (con valor por defecto) · Lo no verificado, con motivo. Los documentos anteriores a una decisión se marcan «DOCUMENTO HISTÓRICO» en su primera línea.

## Ejemplo mínimo
```
verificado-contra-git: 1a2b3c4 · pedidos-api · 2026-10-07
| 1 | Entrega parcial | hecho | rama integrada, PR #45 | Ana | no |
| 2 | Aviso por correo | pendiente | sin PR | Luis | no |
No verificado: despliegue a producción (sin acceso).
```
