<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-08 · vence: 90d · fuente: metodo/terminado-y-trazabilidad.md -->
# Plantilla: lista de cierre (`cierre.md`) — «nunca se escapa algo»

Se copia al cambio y se marca punto por punto al cerrar. `[x]` hecho (con la evidencia citada), `[-]` no aplica **con motivo** (`N/A: …`). Una casilla vacía impide cerrar. Qué comprueba el guion y qué una persona: `metodo/terminado-y-trazabilidad.md` §7.

## Estructura
```markdown
# Cierre — {{título}}

- [ ] Especificación aprobada antes de escribir código ({{quién, fecha}})
- [ ] Matriz completa: cada requisito con criterio, prueba, commit y evidencia ({{resultado de harness trazar}})
- [ ] Gate de calidad ejecutado, con código de salida pegado ({{archivo de evidencia}})
- [ ] Revisión etapa 1 (conformidad con la especificación) por alguien distinto del implementador ({{quién}})
- [ ] Revisión etapa 2 (calidad, seguridad, rendimiento) ({{quién}})
- [ ] Datos y cifras verificados con datos reales, o declarados no verificados en la matriz
- [ ] Capas completas (servidor, interfaz, infraestructura) o el cambio queda abierto diciendo cuál falta
- [ ] Tareas delegadas aceptadas tras verificarlas por cuenta propia
- [ ] Documentación y tickets al día, con enlaces completos
- [ ] Conocimiento e índices actualizados
- [ ] Lección registrada (`metodo/aprendizaje.md`) o N/A con motivo
- [ ] Procesos levantados apagados y datos de prueba limpiados o declarados
- [ ] Lo no verificado figura en el informe final, con motivo
```

## Ejemplo mínimo
Ver `plantillas/ejemplos/cambio-ejemplo/cierre.md`.
