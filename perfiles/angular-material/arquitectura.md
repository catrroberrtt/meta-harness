# Arquitectura · Angular + Material
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (convenciones de frontend §1-§3, guía de diseño F1-F8 y A10-A14, reglas aprendidas del frontend); ver evidencia.md -->

> Capas, escalas S/M/L, dónde va cada cosa y reglas de dependencia del frontend. Cada regla lleva un identificador (`ARQ-n`) que `evidencia.md` traza a su fuente. Todas están **pendientes de evidencia**: vienen de una sola instancia.

**Principio rector.** Una abstracción se gana con evidencia, no con previsión: se crea cuando hay hoy 2 o más usos reales (3 si es duplicación), con la misma razón de cambio y se puede nombrar por un concepto de la pantalla. Si no, se deja en línea. Lo contrario también es un defecto: no abstraer cuando ya hay 3 copias. (`ARQ-1`)

## 1. Estructura de una funcionalidad

```
src/app/pages/<área>/<funcionalidad>/
  <funcionalidad>.module.ts            # módulo de la funcionalidad (o rutas + componentes standalone)
  <funcionalidad>-routing.module.ts    # enrutador hijo
  template/   -> componente-página (listado)
  edit/       -> contenedor de detalle (a menudo con pestañas)
     <sub-área>/  componente + servicio + interfaz   # una hoja standalone por pestaña o sección
```

- `ARQ-2` Una carpeta por funcionalidad, con su enrutador propio y **carga diferida** desde el enrutador raíz de páginas. La entrada lleva el título en `data` y la guarda de permiso.
- `ARQ-3` Los contenedores y páginas se declaran en el módulo; las **hojas nuevas** (sub-secciones, pestañas, diálogos) son `standalone: true` con `imports` explícitos y se listan en el módulo o en el contenedor que las usa.
- `ARQ-4` Cada hoja agrupa junto a sí su servicio y su interfaz cuando solo ella los usa. Lo que usan 3 o más sitios sube a una carpeta compartida (ver `ARQ-11`).
- `ARQ-5` Las rutas hermanas no comparten prefijo de URL cuando el título del encabezado se resuelve por prefijo: dos rutas con la misma raíz muestran el título de la primera. Se nombran sin prefijo común.

## 2. Dónde va cada cosa

| Qué se resuelve | Dónde | Regla |
|---|---|---|
| Llamadas HTTP | **Servicio** de la funcionalidad (o el del recurso si ya existe). **Ningún componente inyecta el cliente HTTP** | `ARQ-6` |
| Estado de vista (cargando, pestaña activa, fila elegida) | **Componente** | `ARQ-7` |
| Encadenar 2 o más llamadas con reglas («si falla X no hagas Y») | **Servicio** de la funcionalidad, con prueba | `ARQ-8` |
| Reglas de estado (editable, bloqueado, puede publicar), etiquetas y formato de campos | **Mapeador**: funciones puras en un archivo aparte | `ARQ-9` |
| Validación o constante repetida en 3 o más componentes (tipos y tope de archivo, formatos) | **Carpeta compartida**, como constante o función pura | `ARQ-10`, `ARQ-11` |
| Formato visual repetido en 3 o más plantillas | **Pipe puro**; en TypeScript, la misma función | `ARQ-12` |
| Algo que afecta a **todas** las llamadas (token, indicador de carga, errores) | **Interceptor** | `ARQ-13` |
| Permisos de ruta y de elemento | **Guarda** de ruta y **directiva** de permiso | `ARQ-14` |
| Códigos de error del servidor que el cliente compara | **Constante exportada** | `ARQ-15` |

- `ARQ-6` El componente no conoce URLs, parámetros ni cabeceras. La URL base sale siempre de la configuración del entorno, nunca de un literal.
- `ARQ-9` Una regla que depende de un estado del negocio vive **una sola vez**. Tres variantes de «es editable» en tres sitios son el olor.
- `ARQ-13` Una necesidad de una sola pantalla va en el servicio de esa pantalla, no en un interceptor. El interceptor no se vuelve contenedor de excepciones: la excepción por petición se marca con un contexto HTTP (`PAT-9`).
- `ARQ-15` Un código de error del servidor nunca es un literal dentro del componente; si solo cambia el texto del aviso, basta el normalizador de errores (`COD-24`).

## 3. Cuánta estructura: la escala S/M/L

La escala se **deriva** de los umbrales de la guía de decisión (el origen no nombra «S/M/L» para el frontend); se elige antes del estilo y cada pieza extra lleva una frase de justificación. (`ARQ-16`)

| Tamaño | Cuándo | Piezas |
|---|---|---|
| **S** | Una lectura que se pinta tal cual, sin transformación | componente · método en el servicio · interfaz de respuesta |
| **M** | Respuesta con 4 o más campos transformados, o cálculo y formato usados en 2 o más sitios, o que se prueba aparte | S + **mapeador** puro (`toViewModel`) con su prueba si hay cálculo |
| **L** | Una pantalla que coordina 3 o más servicios con pasos fijos y 2 o más hijos que comparten estado | M + **servicio con alcance de pantalla** (facade) provisto en el padre + hojas standalone por responsabilidad |

- `ARQ-17` **Servicio nuevo o método nuevo**: método si el servicio es del mismo recurso y queda con 15 o menos métodos públicos; servicio nuevo si lo supera o es otro recurso. No hay un servicio por endpoint ni un servicio vacío que solo reexporta. (El motor del origen avisa por encima de 15 y falla por encima de 25.)
- `ARQ-18` **Dividir un componente**: candidato si el `.ts` pasa de ~300 líneas o la plantilla de ~150, o tiene 2 o más responsabilidades (tabla + filtro + formulario). Antes de partir se pregunta qué parte es lógica pura (mapeador), HTTP (servicio) o interfaz (se queda). **Si ninguna sale con prueba, no se parte por tamaño.**
- `ARQ-19` **Subcomponente frente a plantilla en línea**: subcomponente standalone si el bloque tiene `@Input` propios y se repite 2 o más veces, o la plantilla pasa de ~150 líneas, o tiene estado propio. Un bloque de 30 líneas o menos usado una vez va en línea. Un bloque idéntico en 3 o más pantallas es un subcomponente de presentación (solo `@Input`).

## 4. Estado, composición y lo que NO se hace

- `ARQ-20` **Estado local o servicio con alcance**; no hay store global. Si 2 pantallas sin relación necesitan el mismo dato: servicio de raíz con caché corta. Un solo componente: propiedades o signals locales; padre e hijos de la misma pantalla: servicio provisto en el padre.
- `ARQ-21` **Facade** solo con 3 o más servicios y 2 o más hijos que comparten ese estado. Nunca para «ocultar» el cliente HTTP.
- `ARQ-22` **Mapeador** solo cuando se transforman 4 o más campos o hay cálculo; una respuesta que se pinta tal cual no lleva mapeador.
- `ARQ-23` Dos listados que se parecen solo en estructura (paginación, búsqueda con espera) comparten **constantes y el operador de cierre de suscripciones**, no una clase base ni una tabla genérica.
- `ARQ-24` Dos diálogos parecidos de **dominios distintos** (rechazar un pago, rechazar una cuenta) no se unifican; tampoco las etiquetas de estado de cada dominio.
- `ARQ-25` Un servicio de recurso transversal es de raíz; uno de una funcionalidad se provee en su módulo o componente (sin `providedIn`), y vive y muere con ella.

## 5. Descubrimiento antes de crear

- `ARQ-26` Si el patrón ya existe en el proyecto, se usa ese (el del módulo vecino). Lo nuevo se propone con su justificación.
- `ARQ-27` Antes de crear un servicio de utilidad (exportar a hoja de cálculo, descargar archivos, formatear) se busca por **la librería que importa**, no por el nombre que uno supone: una búsqueda por nombres inventados da falso negativo y termina en un duplicado.
- `ARQ-28` Un servicio de exportación recibe filas ya resueltas y **no sabe nada de HTTP, rangos ni filtros**: traer los datos es del servicio de la pantalla; pintar y descargar es del servicio de exportación, uno solo para todo el proyecto.
- `ARQ-29` Una librería que no existe en el proyecto se **propone** (nombre, motivo, alternativas) y no se instala por cuenta propia.
