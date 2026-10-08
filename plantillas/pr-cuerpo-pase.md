<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: cuerpo de un PR de entrega o pase (8 secciones)

Lista de secciones editable con la clave `pr.secciones-pase`. Por defecto:

1. **Resumen del cambio** [OBLIGATORIO] — qué se libera y por qué, entendible en 30 segundos; viñetas por capacidad; repos hermanos; origen y destino.
2. **Impacto esperado** [OBLIGATORIO] — tres párrafos: usuarios finales · operación interna · rendimiento, seguridad y disponibilidad (con números medidos).
3. **Lista de control** [OBLIGATORIO] — `[x]` solo lo comprobado: QA funcional, PR previos integrados, build y pruebas con fecha, comprobaciones con datos reales, aprobaciones.
4. **Plan de despliegue** [OBLIGATORIO] — componentes en orden, qué dispara el merge, migraciones (tabla; cuáles no viajan), variables de entorno, pasos previos y posteriores, ventana y responsables.
5. **Plan de respaldo** [OBLIGATORIO] — pasos de reversión, tiempo estimado, impacto sobre datos ya creados.
6. **Evidencias y artefactos** [OBLIGATORIO] — PR asociados, scripts de migración, tickets enlazados (URL completa), documentación enlazada.
7. **Pruebas de código** — revisión manual y hallazgos de seguridad; «sin vulnerabilidades» solo si es cierto.
8. **Observaciones** — derivas, archivos que difieren de la rama validada, preguntas abiertas, o «No se identificaron observaciones».

## Auditoría previa (antes de pedir aprobación)
- [ ] Variables de entorno nuevas existen en el destino.
- [ ] Datos que siembran las migraciones no chocan con los del destino.
- [ ] Cada rutina de base reemplazada se compara con la del destino y con la última migración de la rama estable.
- [ ] Orden de migraciones comprobado (las pendientes corren aunque su marca de tiempo sea menor).
- [ ] Dependencias, CI y build tocados revisados.
- [ ] Estado en el repositorio remoto (mezclable, checks en verde).
- [ ] Cada cifra del cuerpo contrastada con el dato real.

## Tabla de verificación (opcional)
| Afirmación | Fuente primaria | Fecha | Veredicto |
|---|---|---|---|

## Ejemplo mínimo
```
## 1. Resumen del cambio
Pedidos: nuevo estado «Parcial». Va de feat/pedidos-parcial a main (no de integración a main).
## 3. Lista de control
- [x] build y pruebas, código de salida 0 (2026-10-07)
- [ ] aprobación del responsable de producto
## 6. Evidencias
PR previo: #45 · Ticket: https://tracker.example.com/browse/PROJ-123
```
