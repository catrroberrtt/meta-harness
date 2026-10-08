# Pruebas · AWS ECS
<!-- tipo: perfil · capa: 3 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: instancia de origen única (pipelines de validación, pruebas de la plantilla sintetizada en un repositorio de infraestructura y guía de despliegue); ver evidencia.md -->

> Qué se verifica de la infraestructura antes de aplicarla y cómo se ensaya. Cada regla lleva un identificador (`PRU-n`). Todas están **pendientes de evidencia**.

## 1. Antes de la plantilla

- `PRU-1` **Puerta `validate`** antes de sintetizar, comparar o desplegar: comprobación de tipos sin emitir + pruebas unitarias. Los scripts de síntesis, `diff` y despliegue la llaman primero.
- `PRU-2` En la solicitud de integración corren, en este orden: análisis estático (lint), formato, tipos, pruebas, síntesis de la plantilla, análisis de reglas de buenas prácticas (informativo mientras la infraestructura madura, luego obligatorio, con supresiones justificadas) y `diff` contra lo desplegado.

## 2. Pruebas sobre la plantilla sintetizada

- `PRU-3` Aserciones sobre la plantilla con la biblioteca del propio CDK (`Template.fromStack`, `hasResourceProperties`, `resourceCountIs`). Qué se afirma en la instancia donde existen:
  - el cargador de configuración **falla** con ambiente ausente, desconocido o con mayúsculas distintas;
  - la configuración de producción tiene postura endurecida (protección contra borrado, alta disponibilidad, retención, modo de bloqueo del WAF);
  - la pila de identidad **no crea usuarios IAM ni claves de acceso** y sí un rol con el nombre esperado.
- `PRU-4` Las variables de entorno que el cargador necesita para las pruebas se fijan en un **archivo de preparación** que se carga antes de importar los módulos de configuración.
- `PRU-5` Una aserción nace de un error real: la regla «cero usuarios IAM» existe porque el patrón anterior los tenía.

## 3. Antes de aplicar

- `PRU-6` **`diff` siempre antes de desplegar**; en producción, el `diff` se revisa y el despliegue exige aprobación interactiva (no se usa `--require-approval never` fuera del ambiente más bajo).
- `PRU-7` Se despliega **primero al ambiente más bajo**; nunca se salta a producción. Los cambios entre pilas se revisan con `diff --all`, porque una salida modificada obliga a actualizar la pila que la consume.
- `PRU-8` **Detección de deriva programada:** un trabajo diario en días hábiles ejecuta `diff` por ambiente y advierte si el estado real se desvió de lo que declara el código (cambios hechos a mano en la consola).

## 4. Después de aplicar o de volver atrás

- `PRU-9` Lista de comprobación posterior: el servicio responde en su URL; los logs no muestran errores nuevos; las métricas de error y latencia están en su nivel base; el equipo fue avisado; se abrió un ticket con la causa raíz.
- `PRU-10` El pipeline espera a que el servicio se **estabilice** (`wait services-stable`) antes de dar por bueno el despliegue.

## Por extraer

- Pruebas de carga y de capacidad: no hay evidencia de que se hayan ejecutado.
- Simulacros de restauración y de recuperación ante desastres: solo hay procedimientos escritos.
- Cobertura de pruebas de la infraestructura: falta un criterio de qué debe estar cubierto.
