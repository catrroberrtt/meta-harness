<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: estandares/diseno-web.md y frontend/src/styles/_tokens.scss del ERP base (solo nombres y papeles, sin valores de ninguna empresa) -->
# Plantilla: mapa de tokens ERP ↔ web ↔ documentos

Une la identidad de una empresa en las tres superficies. Los **nombres y papeles** son el contrato; los **valores** salen de la instancia (color base de la empresa). Se rellena la columna «Valor de la empresa» y se copia a `sitio/tokens.css`.

## Origen único
Un solo color base `{{color_base}}` (hex). Del color base se genera la escala `--brand-400…900` con la misma función en las tres superficies (en el ERP, `core/tema/marca.ts`; en la web y en los documentos, el mismo cálculo o los mismos seis valores copiados). Cambiar el color base cambia las tres a la vez.

## Tabla de mapeo
| Papel | ERP (`_tokens.scss`) | Web (`tokens.css`) | Documento (Word/PDF/hoja) | Valor de la empresa (claro) | Valor (oscuro) |
|---|---|---|---|---|---|
| Marca, 6 pasos | `--brand-400…900` | `--brand-400…900` | color de acento y de títulos (500 y 700) | | |
| Texto sobre marca | texto blanco de botón | `--on-brand` | texto de botones y cabeceras | | |
| Fondo | `--app-bg` | `--bg` | fondo de página (blanco) | | |
| Superficie | `--app-surface`, `--app-surface-2` | `--surface`, `--surface-2` | relleno de cuadros y tablas | | |
| Borde | `--app-border` | `--border` | líneas de tabla | | |
| Texto | `--app-text` | `--text` | cuerpo | | |
| Texto atenuado | `--app-muted` | `--muted` | notas al pie | | |
| Foco | `--focus-ring` | `--focus-ring` | (no aplica) | | |
| Estados | `--tone-ok/warn/danger/info-bg/fg` | igual | etiquetas de estado | | |
| Radios | `--radius`, `--radius-control` | igual | (no aplica) | | |
| Titulares / cuerpo | `--font-display`, `--font-body` | igual | fuentes del documento | | |
| Ancho y ritmo | — | `--max-w`, `--section-gap`, `--text-sm…--text-4xl` | márgenes | | |

## Reglas
1. **Un token, un papel.** No se usa `--brand-500` para decorar si su papel es la acción.
2. **Pares con contraste garantizado**, en claro y en oscuro: `--text`/`--bg`, `--text`/`--surface`, `--muted`/`--bg`, `--muted`/`--surface`, `--on-brand`/`--brand-600`, `--brand-600`/`--bg` (enlaces), `--focus-ring`/`--bg` (≥ 3:1). Se declaran en `tokens.css` y los comprueba el verificador.
3. **El tema oscuro redefine los mismos nombres**; la web no inventa nombres propios para el oscuro.
4. **Fuentes con licencia propia.** Si la marca usa una tipografía comercial, la empresa aporta la licencia; si no, pila del sistema.
5. **Lo del marco del ERP no viaja** (barra lateral, barra superior, mosaicos, alturas de fila).
6. **Sin copiar marcas ajenas**: los valores son de la empresa, nunca de un sistema «inspirado en» otra.
