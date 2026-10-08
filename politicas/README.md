# Políticas por proyecto

<!-- tipo: estándar · capa: 4 -->
<!-- revisado: 2026-10-07 · vence: 90d · fuente: esquema de politicas.toml y su generador -->

Qué puede y qué no puede hacer el agente en un proyecto (datos, git, comandos, despliegue, costos, secretos, verificación), escrito en **un archivo TOML por proyecto**, sin presuponer ambientes, puertos, cuentas ni ramas.

| Archivo | Para qué |
|---|---|
| `ESQUEMA.md` | todas las secciones y claves, qué falla si falta algo, y el mapa de las reglas duras de la instancia de origen a la política |
| `politicas.defecto.toml` | valores por defecto conservadores y sin datos de ningún proyecto (punto de partida: se copia y se completa) |

Flujo: el instalador detecta o pregunta los ambientes y arma el archivo del proyecto → `python3 instalador/generar-politicas.py <politicas.toml> --salida <directorio>` genera el hook de acceso a la base (plantilla en `hooks/plantillas/`) → el instalador lo registra, nunca el generador.

La política **de cada proyecto vive en ese proyecto**, no aquí: este repositorio solo contiene el esquema, los valores por defecto y las plantillas.
