<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: estandares/diseno-web.md; secciones adaptadas, con redacción propia, de nexu-io/open-design (Apache-2.0), design-systems/default/DESIGN.md -->
# Plantilla: ficha de marca (`sitio/DISENO.md`)

Una página con la identidad de **una** empresa. Es el contexto que se entrega a la herramienta de generación o al agente. Se rellena en la instancia. No se copia la identidad de otra empresa ni se parte de un sistema «inspirado en» una marca ajena.

## 1. Esencia [OBLIGATORIO]
- **Nombre y descriptor**: Ejemplo S. A. — software de gestión para comercios.
- **En tres adjetivos**: sobria, cercana, precisa.
- **Voz**: tuteo o usted; frases cortas; qué palabras sí y cuáles no.

## 2. Color [OBLIGATORIO]
- **Color base de marca** (un hex; de él sale la escala `--brand-400…900`): `#276eb1`.
- **Uso**: el acento solo en la acción principal y en los enlaces; superficies neutras; color de estado solo cuando hay un estado.
- **Pares de contraste que se garantizan** (los comprueba el verificador): texto sobre fondo, texto atenuado sobre fondo y sobre superficie, texto sobre marca, foco sobre fondo.

## 3. Tipografía [OBLIGATORIO]
- **Titulares**: (familia con licencia que la empresa posee, o pila del sistema).
- **Cuerpo**: (igual).
- **Licencia y origen de las fuentes**: (si hay archivos, van en `sitio/activos/` con su línea en `LICENCIAS.md`).
- **Escala**: tamaños en `rem`.

## 4. Componentes
Botón principal y secundario · enlace · tarjeta · formulario · navegación · pie: radio, relleno, estados (normal, foco, desactivado, error).

## 5. Disposición y profundidad
Ancho máximo, espacio entre secciones, cuántos niveles de sombra (máximo dos), cuándo se separa con borde y cuándo con espacio.

## 6. Logotipo e imágenes
Archivo del logotipo (lo aporta la empresa), zona de respeto, tamaño mínimo, fondos permitidos. Estilo de imágenes y quién tiene los derechos. Texto alternativo: cómo se escribe.

## 7. Hacer y no hacer
- Hacer: (3 a 5 reglas concretas).
- No hacer: imitar la identidad de otra empresa; degradados de «confianza»; emojis como iconos; cifras sin fuente; imágenes de marcadores externos.

## 8. Responsive y movimiento
Puntos de corte, qué cambia en pantallas pequeñas, animaciones permitidas y cómo respetan `prefers-reduced-motion`.

## 9. Guía corta para el agente
Cinco líneas que resumen lo anterior para quien genere el borrador.
