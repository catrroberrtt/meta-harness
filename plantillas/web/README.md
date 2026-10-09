<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: estandares/diseno-web.md y adaptadores/diseno-web/README.md -->
# Plantillas de web

Cuatro piezas para armar la web de una empresa sin copiar la marca de nadie. Los ejemplos usan una empresa inventada («Ejemplo S. A.»); los datos reales viven en la instancia, nunca aquí.

| Pieza | Para qué |
|---|---|
| `brief-landing.md` | Qué se quiere lograr, para quién y con qué contenido real |
| `ficha-de-marca.md` | La identidad de la empresa en una página (voz, color, tipografía, componentes, qué evitar) |
| `mapa-de-tokens.md` | Cómo se traducen los tokens del ERP a los de la web y a los documentos |
| `tokens.ejemplo.css` | Archivo de tokens de partida (valores inventados) que el verificador entiende |

Uso: rellenar las tres primeras en la instancia, copiar `tokens.ejemplo.css` a `sitio/tokens.css` con los valores de la empresa y correr `python3 herramientas/web-verificar-sitio.py sitio/`.
