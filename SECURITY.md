# Seguridad

<!-- tipo: guia · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: documento del repositorio, escrito y verificado con sus pruebas -->

## Cómo reportar una vulnerabilidad

No la publique en una propuesta ni en un comentario abierto. Use el reporte privado de vulnerabilidades del servicio donde se aloja este repositorio o escriba al contacto de seguridad indicado en la ficha del repositorio (`<contacto de seguridad: a definir antes de publicar>`).

Incluya: qué ocurre, cómo reproducirlo, qué impacto tiene y qué versión (`VERSION`) afecta. Se acusa recibo, se evalúa y se responde con un plan de corrección; se pide mantener la reserva hasta que haya una versión corregida.

## Alcance

Entra en alcance: herramientas, hooks e instalador que puedan ejecutar código no deseado, filtrar datos, escribir fuera de su carpeta o debilitar una política de seguridad.

## Qué no debe contener ningún aporte

- Credenciales (contraseñas, tokens, claves de acceso o privadas, cadenas de conexión con contraseña).
- Identificadores de infraestructura reales: cuentas, ARNs, IP, hosts internos.
- Datos de personas: correos, nombres, documentos.
- Referencias a una empresa, cliente o proyecto concretos.
- Archivos locales o sensibles: `.env`, `*.pem`, volcados `*.sql`, estados `*.tfstate`.

Si un secreto llega a publicarse, se rota primero y después se reescribe el historial (ver `docs/PUBLICAR.md`). El escaneo `herramientas/harness-escaneo-publico.py` revisa el árbol y el historial antes de cada publicación.
