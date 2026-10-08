# Aprendizaje: qué sube al harness y qué se queda en la instancia
<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: método de aprendizaje del repositorio -->

El harness es el repositorio que más conocimiento reutilizable concentra. Cuando una instancia (un proyecto concreto) aprende algo, hay que decidir si eso sirve a cualquier proyecto o solo a ese. Este documento fija el camino, y `herramientas/harness-aportar.py` lo aplica de forma explicable. La herramienta propone; **nunca sube nada por sí misma**.

## 1. Registrar la lección en la instancia

Toda lección nace en la instancia: un hallazgo de revisión, un error de QA, una regla descubierta al implementar. Se escribe como un documento corto con título, la marca `<!-- tipo: estandar · capa: 2 -->` (o el tipo que corresponda), la regla y cómo revisarla. Se registra con el mecanismo de la instancia (libro de hallazgos, carpeta de criterios). Una clase de error que aparece **2 o más veces** debe volverse chequeo mecánico, no recordatorio.

## 2. Las cuatro preguntas de clasificación

| Pregunta | Si es sí | Va a |
|---|---|---|
| ¿Se explica sin nombrar al proyecto y aplica a cualquier proyecto con ese stack o proceso? | General técnica | Harness (método, estándar o perfil) |
| ¿Es un error frecuente (2 o más veces, o en 2 proyectos) que se evita con una regla o un chequeo? | Patrón de calidad | Harness, con su chequeo |
| ¿Depende de reglas, cifras, datos, personas o decisiones del negocio? | De negocio | Se queda en la instancia |
| ¿Mezcla ambas? | Mixta | Se parte: lo de negocio se queda; lo técnico sube con un ejemplo inventado |

Ejemplo general: «un listado paginado no debe repetir el conteo total en cada página». Ejemplo de negocio: «la cuota se cobra el día 5 y la penalidad es de un monto fijo». Ejemplo mixto: «redondea al guardar y no al mostrar» (técnico) junto con «la cuota se redondea a dos decimales» (negocio).

## 3. Qué se hace con cada resultado

- **General**: se arma un paquete de aporte (sección 4).
- **De negocio**: se queda; la herramienta no arma nada.
- **Mixta**: la herramienta lista línea por línea qué se queda y qué sube y propone el corte. Se reescribe en dos documentos y se vuelve a correr sobre el técnico.
- **General con referencias** (cita un ticket, repo, persona o ruta solo como ejemplo): las referencias se sustituyen por marcas (`<TICKET>`, `<repo>`, `<persona>`, `<ruta-local>`) y el resultado se vuelve a evaluar; si queda una sola, no hay paquete.

## 4. Cómo decide la herramienta

```
python3 herramientas/harness-aportar.py <leccion.md> --instancia <raiz> [--salida <carpeta>]
```

Lee de la raíz de la instancia, todos opcionales: `patrones-proyecto.txt` (una expresión regular por línea; las líneas que empiezan con `#` son comentario; también puede indicarse con la variable `HARNESS_PATRON_PROYECTO`), `dominio.txt` (términos del negocio, uno por línea) y `personas.txt`. Sin patrón usa uno genérico de claves de ticket y números de PR.

- **Señal de negocio**: término de `dominio.txt`, importe con moneda, porcentaje junto a una palabra de tarifa o riesgo, frase de decisión del negocio.
- **Señal de referencia**: patrón del proyecto, persona, ruta local, URL privada, número de cuenta.
- Veredicto: sin señal de negocio es *general*; si menos del 40 % de las líneas de contenido son de negocio es *mixta*; de lo contrario, *de negocio*.
- Imprime siempre la **razón** y las líneas que la causan, más las señales débiles (nombres propios, entornos, cantidades) que solo avisan.

Sin `--salida` no escribe nada. Con `--salida` y veredicto general que pasa el gate de extracción, crea una carpeta con el documento anonimizado, `gate.txt` (resultado del gate) y `ORIGEN.md` (nota de origen sin proyecto, personas ni tickets, con la lista de verificación del revisor). No toca la instancia ni el harness, y no sobrescribe un paquete existente.

## 5. Revisar un aporte

Quien revisa abre el paquete y comprueba: el documento se entiende sin conocer el origen; los ejemplos son inventados; las marcas `<...>` leen bien; tipo y capa son correctos; las señales débiles de `ORIGEN.md` no ocultan nada del negocio. Si todo está bien, se incorpora con `harness-extraer.py --aplicar --destino <harness>` (copia, nunca mueve ni sobrescribe) y se sube por pull request. Lo que traiga otro proyecto entra por el mismo camino y el mismo gate.

## 6. Versionar el harness

El archivo `VERSION` lleva la versión semántica (`MAYOR.MENOR.PARCHE`). Un documento nuevo o una regla añadida sube el menor; una corrección sube el parche; un cambio que obligue a las instancias a ajustar su configuración sube el mayor. Cada versión publicada lleva una etiqueta `vX.Y.Z` en el repositorio y una entrada en el registro de cambios.

## 7. Cómo una instancia recibe una versión nueva

La instancia fija la versión que usa en `harness.lock`. El comando `update` compara esa versión con la etiqueta pedida, trae solo los archivos del harness (método, estándares, perfiles, herramientas) y reescribe `harness.lock`. La configuración local (`patrones-proyecto.txt`, `dominio.txt`, políticas, plantillas propias) vive fuera de los directorios que `update` reemplaza y nunca se pisa. Si un archivo del harness fue editado a mano en la instancia, `update` lo informa y no lo sobrescribe.

## Límites

La clasificación es un filtro de seguridad, no un juicio. Sin `dominio.txt` no ve el negocio que no se nombra con cifras; una regla de negocio escrita en lenguaje corriente puede parecer técnica. Siempre la revisa una persona antes de subir.
