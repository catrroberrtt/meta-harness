<!-- tipo: metodo · capa: 1 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: formatos de la instancia de origen -->
# Plantilla: modelo de datos y migraciones

## Modelo de datos [OBLIGATORIO]
Por cada tabla, diccionario columna por columna:
| Columna | Tipo | Nulo | Clave/índice | Restricción | Nota de negocio |
|---|---|---|---|---|---|
Además: estados, reglas que protege el modelo y **resultado de la prueba del esquema** (qué se corrió y qué dio).

## Migraciones [OBLIGATORIO]
Por cada migración, por nombre exacto:
- Nombre: `{{marca-de-tiempo}}-{{Nombre}}` · ticket: {{CLAVE}}
- Qué agrega o cambia · dependencias · orden de ejecución
- SQL probado (en bloque de código) y reversa
- Cómo corre en el despliegue; cuáles no viajan a producción

Reglas: nunca «habrá migraciones» sin nombrarlas ni mostrar su contenido; el diccionario de datos del proyecto se actualiza (sub-tarea).

## Ejemplo mínimo
```
Tabla entrega (id PK, pedido_id FK→pedido, cantidad INT NOT NULL CHECK > 0, creada_en DATETIME)
Migración 1791000000000-AgregarEntrega · PROJ-123
  up:   CREATE TABLE entrega (...);   down: DROP TABLE entrega;
  Prueba del esquema: 5 inserciones válidas, 3 rechazadas por restricción.
```
