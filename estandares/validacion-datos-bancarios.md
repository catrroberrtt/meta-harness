# Validación de cuentas bancarias dirigida por catálogo

<!-- tipo: estándar técnico · capa: 2 -->
<!-- revisado: 2026-10-12 · vence: 90d · fuente: patrón aplicado y probado en un sistema real, descrito sin datos del proyecto -->

Cómo validar un número de cuenta y su código interbancario (CCI) **sin escribir reglas por banco en el código**: las reglas
viven en el catálogo de bancos y el mismo mecanismo sirve a cualquier formulario que pida una cuenta (cobros, pagos, cuentas
de empresas, cambio de cuenta). Independiente del stack.

## Principio

> La regla de cada banco es **dato**, no código. Agregar o corregir un banco es editar una fila del catálogo.

El catálogo de bancos trae, por banco:

| Dato | Para qué sirve |
|---|---|
| **Código** de 3 dígitos | Es el prefijo con el que empieza el CCI de ese banco |
| **Reglas por tipo de cuenta** (ahorros, corriente…) | Mínimo y máximo de dígitos del número de cuenta, y del CCI |

El código interbancario peruano mide siempre **20 dígitos**: 3 de banco, 3 de oficina, 12 de cuenta y 2 de control.

## Las cuatro reglas

1. **Solo dígitos.** El número de cuenta y el CCI se guardan sin espacios ni guiones; al pegar, se descartan.
2. **El CCI empieza con el código del banco elegido y ese prefijo no se puede quitar.** Al elegir banco el campo se
   completa solo; borrar todo lo devuelve al prefijo; cambiar de banco lo reinicia.
3. **El largo del número de cuenta sale de las reglas del banco.** Si no se guarda el tipo de cuenta, se acepta el rango
   que cubre **cualquiera** de sus tipos (la unión), y se documenta como límite conocido.
4. **El servidor repite la regla.** La pantalla ayuda; el servidor decide. Un cliente que se salte la pantalla no puede
   guardar un CCI de otro banco.

## Casos borde que el diseño ya resuelve

| Caso | Qué se hace |
|---|---|
| Banco **sin reglas cargadas** | Rango por defecto (9 a 20 dígitos) y CCI de 20; el prefijo se exige si el banco tiene código |
| Banco **sin código** | No se exige prefijo |
| Reglas guardadas como **texto JSON** o mal formadas | Se leen con tolerancia: si no se pueden interpretar, se usa el rango por defecto, nunca falla |
| Dos bancos con el **mismo código** | Es un dato a corregir en el catálogo; la regla no distingue entre ellos |
| Usuario **pega un CCI completo de otro banco** | No se reescribe en silencio: se deja a la vista y el error dice qué prefijo corresponde |
| Cuentas **ya guardadas** antes de la regla | No se revalidan solas; solo se validan altas y cambios nuevos |

## Mensajes (en lenguaje claro)

Un error dice **qué banco**, **qué se esperaba** y **qué tiene**: «El número de cuenta de BCP debe tener entre 13 y 14
dígitos» o «El CCI de BCP debe empezar con 002, el código del banco». La respuesta del servidor lleva un código de error
estable, el primer problema como mensaje y la lista completa en el detalle.

## Estructura recomendada

| Pieza | Responsabilidad |
|---|---|
| **Reglas puras** (sin acceso a datos) | Calcular límites, listar problemas, lanzar el error. Probables sin infraestructura |
| **Lectura del banco** | Una sola consulta: nombre, código y reglas |
| **Casos de uso** (alta y cambio de cuenta) | Buscar el banco, validar **antes** de abrir la transacción |
| **Espejo en la pantalla** | Mismas reglas, para guiar al escribir (ejemplo en el campo, ayuda con el rango, teclado numérico) |

Las reglas del espejo y las del servidor deben mantenerse **idénticas**; una prueba por lado con los mismos casos lo vigila.

## Qué probar (mínimo)

- Cada banco con reglas: largo justo, uno menos y uno más.
- Banco sin reglas, sin código y con reglas ilegibles.
- Letras y espacios en cuenta y CCI.
- CCI de 19 y de 21 dígitos; CCI que empieza con el código de otro banco.
- Cambio de banco con el formulario ya lleno.

## Para el ERP

Es directamente reutilizable en cualquier módulo que registre una cuenta de tercero (socios, proveedores, empleados, tesorería):
la tabla de bancos y las cuatro reglas se heredan; cada módulo solo decide **cuándo** validar (al guardar la ficha, al
registrar un pago, al cambiar la cuenta).
