<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: estandares/diseno-web.md; idea de brief con dimensiones explícitas adaptada de nexu-io/open-design (Apache-2.0), skills/design-brief -->
# Plantilla: brief de landing

Se rellena antes de generar nada (con herramienta o a mano). Los campos `[OBLIGATORIO]` no se omiten; lo que no se sabe se escribe **pendiente** y se resuelve con la empresa, no se inventa.

## 1. Objetivo
- **Tipo de página** [OBLIGATORIO]: landing · sitio corporativo · página de producto · precios · lista de espera · preguntas frecuentes · documentación pública.
- **Qué debe lograr** [OBLIGATORIO]: una sola acción principal medible (por ejemplo «solicitar una demostración»).
- **Acción secundaria**: (opcional, una).

## 2. Público e idioma
- **Quién llega y desde dónde** [OBLIGATORIO]: (ej.: dueños de comercios pequeños que llegan desde una búsqueda).
- **Idioma(s)** [OBLIGATORIO]: código BCP 47 (`es-PE`). Una página por idioma.
- **Nivel de conocimiento**: (ej.: no técnico).

## 3. Contenido real [OBLIGATORIO]
| Sección | Texto/dato real | Fuente verificable | Estado |
|---|---|---|---|
| Titular | (pendiente) | | pendiente |
| Qué hace el producto | | | |
| Pruebas (cifras, clientes, testimonios) | | | Solo con permiso por escrito; si no hay, se omite la sección |
| Precios | | | |
| Contacto | | | |

## 4. Módulos del ERP que se pueden prometer (solo opción ERP)
Copiar de `erp.lock.json` de la instancia **solo los instalados y en estado «hecho»**. Todo lo demás no se menciona.

| Módulo instalado | Qué puede decir la web | Qué NO puede decir |
|---|---|---|
| (ej.) Almacén | Control de existencias y movimientos | Que está integrado con tienda en línea si ese módulo no está |

## 5. Dirección visual (desde la ficha de marca)
- **Ficha de marca**: `sitio/DISENO.md` (obligatoria).
- **Ánimo**: (ej.: profesional y cálido).  **Densidad**: aireada · media · compacta.
- **Disposición**: una columna · dos columnas · mosaico.  **Ancho máximo**: (ej.: `72rem`).
- **Excluir**: (ej.: animaciones largas, degradados, carruseles, vídeo de fondo).
- **Tema oscuro**: sí · no.

## 6. Secciones, en orden
(ej.) Cabecera con logotipo · Héroe (titular, subtítulo, acción principal) · Beneficios (3 a 6) · Prueba · Precios (si aplica) · Preguntas · Llamada final · Pie con datos legales.
Variar el esqueleto habitual solo si el contenido lo pide; no rellenar una sección vacía: omitirla.

## 7. Restricciones
- Peso máximo por página: (por defecto 1 MB).
- Recursos remotos permitidos: ninguno salvo lo declarado aquí con motivo.
- Textos legales: (los aporta la empresa).
- Herramienta de generación: ninguna · nombre. ¿Permiso para usar la red y servicios de terceros? sí · **no** (por defecto).

## Ejemplo mínimo (datos inventados)
Tipo: landing. Acción principal: «Pedir una demostración». Público: dueños de ferreterías que llegan desde una búsqueda. Idioma: `es-PE`. Módulo instalado: Almacén (hecho). Ánimo: sobrio y cercano. Excluir: carruseles. Herramienta: ninguna (modo manual).
